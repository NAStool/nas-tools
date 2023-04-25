import json
from datetime import datetime
from multiprocessing.dummy import Pool as ThreadPool
from threading import Lock

import requests

import log
from app.helper import ChromeHelper, SubmoduleHelper, DbHelper
from app.message import Message
from app.sites.sites import Sites
from app.utils import RequestUtils, ExceptionUtils, StringUtils
from app.utils.commons import singleton
from config import Config

lock = Lock()


@singleton
class SiteUserInfo(object):
    sites = None
    dbhelper = None
    message = None

    _MAX_CONCURRENCY = 10
    _last_update_time = None
    _sites_data = {}

    def __init__(self):

        # 加载模块
        self._site_schema = SubmoduleHelper.import_submodules('app.sites.siteuserinfo',
                                                              filter_func=lambda _, obj: hasattr(obj, 'schema'))
        self._site_schema.sort(key=lambda x: x.order)
        log.debug(f"【Sites】加载站点解析：{self._site_schema}")
        self.init_config()

    def init_config(self):
        self.sites = Sites()
        self.dbhelper = DbHelper()
        self.message = Message()
        # 站点上一次更新时间
        self._last_update_time = None
        # 站点数据
        self._sites_data = {}

    def __build_class(self, html_text):
        for site_schema in self._site_schema:
            try:
                if site_schema.match(html_text):
                    return site_schema
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
        return None

    def build(self, url, site_id, site_name,
              site_cookie=None, ua=None, emulate=None, proxy=False):
        if not site_cookie:
            return None
        session = requests.Session()
        log.debug(f"【Sites】站点 {site_name} url={url} site_cookie={site_cookie} ua={ua}")

        # 站点流控
        if self.sites.check_ratelimit(site_id):
            return

        # 检测环境，有浏览器内核的优先使用仿真签到
        chrome = ChromeHelper()
        if emulate and chrome.get_status():
            if not chrome.visit(url=url, ua=ua, cookie=site_cookie, proxy=proxy):
                log.error("【Sites】%s 无法打开网站" % site_name)
                return None
            # 循环检测是否过cf
            cloudflare = chrome.pass_cloudflare()
            if not cloudflare:
                log.error("【Sites】%s 跳转站点失败" % site_name)
                return None
            # 判断是否已签到
            html_text = chrome.get_html()
        else:
            proxies = Config().get_proxies() if proxy else None
            res = RequestUtils(cookies=site_cookie,
                               session=session,
                               headers=ua,
                               proxies=proxies
                               ).get_res(url=url)
            if res and res.status_code == 200:
                if "charset=utf-8" in res.text or "charset=UTF-8" in res.text:
                    res.encoding = "UTF-8"
                else:
                    res.encoding = res.apparent_encoding
                html_text = res.text
                # 第一次登录反爬
                if html_text.find("title") == -1:
                    i = html_text.find("window.location")
                    if i == -1:
                        return None
                    tmp_url = url + html_text[i:html_text.find(";")] \
                        .replace("\"", "").replace("+", "").replace(" ", "").replace("window.location=", "")
                    res = RequestUtils(cookies=site_cookie,
                                       session=session,
                                       headers=ua,
                                       proxies=proxies
                                       ).get_res(url=tmp_url)
                    if res and res.status_code == 200:
                        if "charset=utf-8" in res.text or "charset=UTF-8" in res.text:
                            res.encoding = "UTF-8"
                        else:
                            res.encoding = res.apparent_encoding
                        html_text = res.text
                        if not html_text:
                            return None
                    else:
                        log.error("【Sites】站点 %s 被反爬限制：%s, 状态码：%s" % (site_name, url, res.status_code))
                        return None

                # 兼容假首页情况，假首页通常没有 <link rel="search" 属性
                if '"search"' not in html_text and '"csrf-token"' not in html_text:
                    res = RequestUtils(cookies=site_cookie,
                                       session=session,
                                       headers=ua,
                                       proxies=proxies
                                       ).get_res(url=url + "/index.php")
                    if res and res.status_code == 200:
                        if "charset=utf-8" in res.text or "charset=UTF-8" in res.text:
                            res.encoding = "UTF-8"
                        else:
                            res.encoding = res.apparent_encoding
                        html_text = res.text
                        if not html_text:
                            return None
            elif res is not None:
                log.error(f"【Sites】站点 {site_name} 连接失败，状态码：{res.status_code}")
                return None
            else:
                log.error(f"【Sites】站点 {site_name} 无法访问：{url}")
                return None
        # 解析站点类型
        site_schema = self.__build_class(html_text)
        if not site_schema:
            log.error("【Sites】站点 %s 无法识别站点类型" % site_name)
            return None
        return site_schema(site_name, url, site_cookie, html_text, session=session, ua=ua, emulate=emulate, proxy=proxy)

    def __refresh_site_data(self, site_info):
        """
        更新单个site 数据信息
        :param site_info:
        :return:
        """
        site_id = site_info.get("id")
        site_name = site_info.get("name")
        site_url = site_info.get("strict_url")
        if not site_url:
            return
        site_cookie = site_info.get("cookie")
        ua = site_info.get("ua")
        unread_msg_notify = site_info.get("unread_msg_notify")
        chrome = site_info.get("chrome")
        proxy = site_info.get("proxy")
        try:
            site_user_info = self.build(url=site_url,
                                        site_id=site_id,
                                        site_name=site_name,
                                        site_cookie=site_cookie,
                                        ua=ua,
                                        emulate=chrome,
                                        proxy=proxy)
            if site_user_info:
                log.debug(f"【Sites】站点 {site_name} 开始以 {site_user_info.site_schema()} 模型解析")
                # 开始解析
                site_user_info.parse()
                log.debug(f"【Sites】站点 {site_name} 解析完成")

                # 获取不到数据时，仅返回错误信息，不做历史数据更新
                if site_user_info.err_msg:
                    self._sites_data.update({site_name: {"err_msg": site_user_info.err_msg}})
                    return

                # 发送通知，存在未读消息
                self.__notify_unread_msg(site_name, site_user_info, unread_msg_notify)

                self._sites_data.update(
                    {
                        site_name: {
                            "upload": site_user_info.upload,
                            "username": site_user_info.username,
                            "user_level": site_user_info.user_level,
                            "join_at": site_user_info.join_at,
                            "download": site_user_info.download,
                            "ratio": site_user_info.ratio,
                            "seeding": site_user_info.seeding,
                            "seeding_size": site_user_info.seeding_size,
                            "leeching": site_user_info.leeching,
                            "bonus": site_user_info.bonus,
                            "url": site_url,
                            "err_msg": site_user_info.err_msg,
                            "message_unread": site_user_info.message_unread
                        }
                    })

                return site_user_info

        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【Sites】站点 {site_name} 获取流量数据失败：{str(e)}")

    def __notify_unread_msg(self, site_name, site_user_info, unread_msg_notify):
        if site_user_info.message_unread <= 0:
            return
        if self._sites_data.get(site_name, {}).get('message_unread') == site_user_info.message_unread:
            return
        if not unread_msg_notify:
            return

        # 解析出内容，则发送内容
        if len(site_user_info.message_unread_contents) > 0:
            for head, date, content in site_user_info.message_unread_contents:
                msg_title = f"【站点 {site_user_info.site_name} 消息】"
                msg_text = f"时间：{date}\n标题：{head}\n内容：\n{content}"
                self.message.send_site_message(title=msg_title, text=msg_text)
        else:
            self.message.send_site_message(
                title=f"站点 {site_user_info.site_name} 收到 {site_user_info.message_unread} 条新消息，请登陆查看")

    def refresh_site_data_now(self):
        """
        强制刷新站点数据
        """
        self.__refresh_all_site_data(force=True)
        # 刷完发送消息
        string_list = []

        # 增量数据
        incUploads = 0
        incDownloads = 0
        _, _, site, upload, download = SiteUserInfo().get_pt_site_statistics_history(2)

        # 按照上传降序排序
        data_list = list(zip(site, upload, download))
        data_list = sorted(data_list, key=lambda x: x[1], reverse=True)

        for data in data_list:
            site = data[0]
            upload = int(data[1])
            download = int(data[2])
            if upload > 0 or download > 0:
                incUploads += int(upload)
                incDownloads += int(download)
                string_list.append(f"【{site}】\n"
                                   f"上传量：{StringUtils.str_filesize(upload)}\n"
                                   f"下载量：{StringUtils.str_filesize(download)}\n"
                                   f"\n————————————")

        if incDownloads or incUploads:
            string_list.insert(0, f"【今日汇总】\n"
                                  f"总上传：{StringUtils.str_filesize(incUploads)}\n"
                                  f"总下载：{StringUtils.str_filesize(incDownloads)}\n"
                                  f"\n————————————")

            self.message.send_user_statistics_message(string_list)

    def get_site_data(self, specify_sites=None, force=False):
        """
        获取站点上传下载量
        """
        self.__refresh_all_site_data(force=force, specify_sites=specify_sites)
        return self._sites_data

    def __refresh_all_site_data(self, force=False, specify_sites=None):
        """
        多线程刷新站点下载上传量，默认间隔6小时
        """
        if not self.sites.get_sites():
            return

        with lock:

            if not force \
                    and not specify_sites \
                    and self._last_update_time:
                return

            if specify_sites \
                    and not isinstance(specify_sites, list):
                specify_sites = [specify_sites]

            # 没有指定站点，默认使用全部站点
            if not specify_sites:
                refresh_sites = self.sites.get_sites(statistic=True)
            else:
                refresh_sites = [site for site in self.sites.get_sites(statistic=True) if
                                 site.get("name") in specify_sites]

            if not refresh_sites:
                return

            # 并发刷新
            with ThreadPool(min(len(refresh_sites), self._MAX_CONCURRENCY)) as p:
                site_user_infos = p.map(self.__refresh_site_data, refresh_sites)
                site_user_infos = [info for info in site_user_infos if info]

            # 登记历史数据
            self.dbhelper.insert_site_statistics_history(site_user_infos)
            # 实时用户数据
            self.dbhelper.update_site_user_statistics(site_user_infos)
            # 更新站点图标
            self.dbhelper.update_site_favicon(site_user_infos)
            # 实时做种信息
            self.dbhelper.update_site_seed_info(site_user_infos)
            # 站点图标重新加载
            self.sites.init_favicons()

            # 更新时间
            self._last_update_time = datetime.now()

    def get_pt_site_statistics_history(self, days=7, end_day=None):
        """
        获取站点上传下载量
        """
        site_urls = []
        for site in self.sites.get_sites(statistic=True):
            site_url = site.get("strict_url")
            if site_url:
                site_urls.append(site_url)

        return self.dbhelper.get_site_statistics_recent_sites(days=days, end_day=end_day, strict_urls=site_urls)

    def get_site_user_statistics(self, sites=None, encoding="RAW"):
        """
        获取站点用户数据
        :param sites: 站点名称
        :param encoding: RAW/DICT
        :return:
        """
        statistic_sites = self.sites.get_sites(statistic=True)
        if not sites:
            site_urls = [site.get("strict_url") for site in statistic_sites]
        else:
            site_urls = [site.get("strict_url") for site in statistic_sites
                         if site.get("name") in sites]

        raw_statistics = self.dbhelper.get_site_user_statistics(strict_urls=site_urls)
        if encoding == "RAW":
            return raw_statistics

        return self.__todict(raw_statistics)

    def get_pt_site_activity_history(self, site, days=365 * 2):
        """
        查询站点 上传，下载，做种数据
        :param site: 站点名称
        :param days: 最大数据量
        :return:
        """
        site_activities = [["time", "upload", "download", "bonus", "seeding", "seeding_size"]]
        sql_site_activities = self.dbhelper.get_site_statistics_history(site=site, days=days)
        for sql_site_activity in sql_site_activities:
            timestamp = datetime.strptime(sql_site_activity.DATE, '%Y-%m-%d').timestamp() * 1000
            site_activities.append(
                [timestamp,
                 sql_site_activity.UPLOAD,
                 sql_site_activity.DOWNLOAD,
                 sql_site_activity.BONUS,
                 sql_site_activity.SEEDING,
                 sql_site_activity.SEEDING_SIZE])

        return site_activities

    def get_pt_site_seeding_info(self, site):
        """
        查询站点 做种分布信息
        :param site: 站点名称
        :return: seeding_info:[uploader_num, seeding_size]
        """
        site_seeding_info = {"seeding_info": []}
        seeding_info = self.dbhelper.get_site_seeding_info(site=site)
        if not seeding_info:
            return site_seeding_info

        site_seeding_info["seeding_info"] = json.loads(seeding_info[0])
        return site_seeding_info

    def get_pt_site_min_join_date(self, sites=None):
        """
        查询站点加入时间
        """
        statistics = self.get_site_user_statistics(sites=sites, encoding="DICT")
        if not statistics:
            return ""
        dates = []
        for s in statistics:
            if s.get("join_at"):
                try:
                    dates.append(datetime.strptime(s.get("join_at"), '%Y-%m-%d %H:%M:%S'))
                except Exception as err:
                    print(str(err))
                    pass
        if dates:
            return min(dates).strftime("%Y-%m-%d")
        return ""

    @staticmethod
    def __todict(raw_statistics):
        statistics = []
        for site in raw_statistics:
            statistics.append({"site": site.SITE,
                               "username": site.USERNAME,
                               "user_level": site.USER_LEVEL,
                               "join_at": site.JOIN_AT,
                               "update_at": site.UPDATE_AT,
                               "upload": site.UPLOAD,
                               "download": site.DOWNLOAD,
                               "ratio": site.RATIO,
                               "seeding": site.SEEDING,
                               "leeching": site.LEECHING,
                               "seeding_size": site.SEEDING_SIZE,
                               "bonus": site.BONUS,
                               "url": site.URL,
                               "msg_unread": site.MSG_UNREAD
                               })
        return statistics

    def update_site_name(self, old_name, name):
        """
        更新站点数据中的站点名称
        """
        self.dbhelper.update_site_user_statistics_site_name(name, old_name)
        self.dbhelper.update_site_seed_info_site_name(name, old_name)
        self.dbhelper.update_site_statistics_site_name(name, old_name)
        return True
