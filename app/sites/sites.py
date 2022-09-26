import json
import traceback
from datetime import datetime
from multiprocessing.dummy import Pool as ThreadPool
from threading import Lock

import log
from app.message import Message
from app.filterrules import FilterRule
from app.sites import SiteUserInfoFactory
from app.utils.commons import singleton
from app.utils import RequestUtils, StringUtils
from app.db import SqlHelper

lock = Lock()


@singleton
class Sites:
    message = None
    filtersites = None
    __sites_data = {}
    __pt_sites = None
    __last_update_time = None
    _MAX_CONCURRENCY = 10

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.message = Message()
        self.filtersites = FilterRule()
        self.__pt_sites = SqlHelper.get_config_site()
        self.__sites_data = {}
        self.__last_update_time = None

    def get_sites(self,
                  siteid=None,
                  siteurl=None,
                  rss=False,
                  brush=False,
                  signin=False,
                  statistic=False):
        """
        获取站点配置
        """
        ret_sites = []
        for site in self.__pt_sites:
            # 是否解析种子详情为|分隔的第1位
            site_parse = str(site[9]).split("|")[0] or "Y"
            # 站点过滤规则为|分隔的第2位
            rule_groupid = str(site[9]).split("|")[1] if site[9] and len(str(site[9]).split("|")) > 1 else ""
            # 站点未读消息为|分隔的第3位
            site_unread_msg_notify = str(site[9]).split("|")[2] if site[9] and len(str(site[9]).split("|")) > 2 else "Y"
            # 自定义UA为|分隔的第4位
            ua = str(site[9]).split("|")[3] if site[9] and len(str(site[9]).split("|")) > 3 else ""
            # 站点用途：Q签到、D订阅、S刷流
            signin_enable = True if site[6] and str(site[6]).count("Q") else False
            rss_enable = True if site[6] and str(site[6]).count("D") else False
            brush_enable = True if site[6] and str(site[6]).count("S") else False
            statistic_enable = True if site[6] and str(site[6]).count("T") else False
            if rule_groupid:
                rule_name = self.filtersites.get_rule_groups(rule_groupid).get("name") or ""
            else:
                rule_name = ""
            site_info = {
                "id": site[0],
                "name": site[1],
                "pri": site[2],
                "rssurl": site[3],
                "signurl": site[4],
                "cookie": site[5],
                "rule": rule_groupid,
                "rule_name": rule_name,
                "parse": site_parse,
                "unread_msg_notify": site_unread_msg_notify,
                "signin_enable": signin_enable,
                "rss_enable": rss_enable,
                "brush_enable": brush_enable,
                "statistic_enable": statistic_enable,
                "ua": ua
            }
            if siteid and int(site[0]) == int(siteid):
                return site_info
            url = site[3] if not site[4] else site[4]
            if siteurl and url and StringUtils.url_equal(siteurl, url):
                return site_info
            if rss and (not site[3] or not rss_enable):
                continue
            if brush and (not site[3] or not brush_enable):
                continue
            if signin and (not site[4] or not signin_enable):
                continue
            if statistic and not statistic_enable:
                continue
            ret_sites.append(site_info)
        if siteid or siteurl:
            return {}
        return ret_sites

    def refresh_all_pt_data(self, force=False, specify_sites=None):
        """
        多线程刷新站点下载上传量，默认间隔6小时
        """
        if not self.__pt_sites:
            return
        if not force and self.__last_update_time and (datetime.now() - self.__last_update_time).seconds < 6 * 3600:
            return

        with lock:
            # 没有指定站点，默认使用全部站点
            if not specify_sites:
                refresh_sites = self.get_sites(statistic=True)
            else:
                refresh_sites = [site for site in self.get_sites(statistic=True) if site.get("name") in specify_sites]

            refresh_all = len(self.get_sites(statistic=True)) == len(refresh_sites)

            with ThreadPool(min(len(refresh_sites), self._MAX_CONCURRENCY)) as p:
                site_user_infos = p.map(self.__refresh_pt_data, refresh_sites)
                site_user_infos = [info for info in site_user_infos if info]

                # 登记历史数据
                SqlHelper.insert_site_statistics_history(site_user_infos)
                # 实时用户数据
                SqlHelper.update_site_user_statistics(site_user_infos)
                # 实时做种信息
                SqlHelper.update_site_seed_info(site_user_infos)

        # 更新时间
        if refresh_all:
            self.__last_update_time = datetime.now()

    def __refresh_pt_data(self, site_info):
        """
        更新单个pt site 数据信息
        :param site_info:
        :return:
        """
        site_name = site_info.get("name")
        site_url = self.__get_site_strict_url(site_info)
        if not site_url:
            return
        site_cookie = site_info.get("cookie")
        ua = site_info.get("ua")
        unread_msg_notify = site_info.get("unread_msg_notify")
        try:
            site_user_info = SiteUserInfoFactory.build(url=site_url, site_name=site_name, site_cookie=site_cookie, ua=ua)
            if site_user_info:
                log.debug(f"【SITES】站点 {site_name} 开始以 {site_user_info.site_schema()} 模型解析")
                # 开始解析
                site_user_info.parse()
                log.debug(f"【SITES】站点 {site_name} 解析完成")

                # 获取不到数据时，仅返回错误信息，不做历史数据更新
                if site_user_info.err_msg:
                    self.__sites_data.update({site_name: {"err_msg": site_user_info.err_msg}})
                    return

                # 发送通知，存在未读消息
                self.__notify_unread_msg(site_name, site_user_info, unread_msg_notify)

                self.__sites_data.update({site_name: {"upload": site_user_info.upload,
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
                                                      "message_unread": site_user_info.message_unread}
                                          })

                return site_user_info

        except Exception as e:
            log.error("【SITES】站点 %s 获取流量数据失败：%s - %s" % (site_name, str(e), traceback.format_exc()))

    def __notify_unread_msg(self, site_name, site_user_info, unread_msg_notify):
        if site_user_info.message_unread <= 0:
            return
        if self.__sites_data.get(site_name, {}).get('message_unread') == site_user_info.message_unread:
            return
        if not unread_msg_notify:
            return

        self.message.sendmsg(title=f"站点 {site_user_info.site_name} 收到 {site_user_info.message_unread} 条新消息，请登陆查看")

    def signin(self):
        """
        站点签到入口，由定时服务调用
        """
        status = []
        for site_info in self.get_sites(signin=True):
            if not site_info:
                continue
            site = site_info.get("name")
            try:
                site_url = site_info.get("signurl")
                site_cookie = site_info.get("cookie")
                ua = site_info.get("ua")
                log.info("【SITES】开始站点签到：%s" % site)
                if not site_url or not site_cookie:
                    log.warn("【SITES】未配置 %s 的站点地址或Cookie，无法签到" % str(site))
                    continue
                res = RequestUtils(cookies=site_cookie, headers=ua).get_res(url=site_url)
                if res and res.status_code == 200:
                    if not self.__is_signin_success(res.text):
                        status.append("%s 签到失败，cookie已过期" % site)
                    else:
                        status.append("%s 签到成功" % site)
                elif res and res.status_code:
                    status.append("%s 签到失败，状态码：%s" % (site, res.status_code))
                else:
                    status.append("%s 签到失败，无法打开网站" % site)
            except Exception as e:
                log.error("【SITES】%s 签到出错：%s - %s" % (site, str(e), traceback.format_exc()))
        if status:
            self.message.send_site_signin_message(status)

    @staticmethod
    def __is_signin_success(html_text):
        """
        检进是否成功进入站点而不是登录界面
        """
        if not html_text:
            return False
        return True if html_text.find("userdetails") != -1 else False

    def refresh_pt_date_now(self):
        """
        强制刷新站点数据
        """
        self.refresh_all_pt_data(True)

    def get_pt_date(self):
        """
        获取站点上传下载量
        """
        self.refresh_all_pt_data()
        return self.__sites_data

    def get_pt_site_statistics_history(self, days=7):
        """
        获取站点上传下载量
        """
        site_urls = []
        for site in self.get_sites(statistic=True):
            site_url = self.__get_site_strict_url(site)
            if site_url:
                site_urls.append(site_url)

        return SqlHelper.get_site_statistics_recent_sites(days=days, strict_urls=site_urls)

    def get_site_user_statistics(self, encoding="RAW"):
        """
        获取站点用户数据
        :param encoding: RAW/DICT
        :return:
        """

        site_urls = []
        for site in self.get_sites(statistic=True):
            site_url = self.__get_site_strict_url(site)
            if site_url:
                site_urls.append(site_url)

        raw_statistics = SqlHelper.get_site_user_statistics(strict_urls=site_urls)
        if encoding == "RAW":
            return raw_statistics

        return self.__todict(raw_statistics)

    @staticmethod
    def __todict(raw_statistics):
        statistics = []
        for site in raw_statistics:
            statistics.append({"site": site[0], "username": site[1], "user_level": site[2],
                               "join_at": site[3], "update_at": site[4],
                               "upload": site[5], "download": site[6], "ratio": site[7],
                               "seeding": site[8], "leeching": site[9], "seeding_size": site[10],
                               "bonus": site[11], "url": site[12], "favicon": site[13], "msg_unread": site[14]
                               })
        return statistics

    def refresh_pt(self, specify_sites=None):
        """
        强制刷新指定站点数据
        """
        if not specify_sites:
            return

        if not isinstance(specify_sites, list):
            specify_sites = [specify_sites]

        self.refresh_all_pt_data(force=True, specify_sites=specify_sites)

    @staticmethod
    def get_pt_site_activity_history(site, days=365 * 2):
        """
        查询站点 上传，下载，做种数据
        :param site: 站点名称
        :param days: 最大数据量
        :return:
        """
        site_activities = [["time", "upload", "download", "bonus", "seeding", "seeding_size"]]
        sql_site_activities = SqlHelper.get_site_statistics_history(site=site, days=days)
        for sql_site_activity in sql_site_activities:
            timestamp = datetime.strptime(sql_site_activity[0], '%Y-%m-%d').timestamp() * 1000
            site_activities.append(
                [timestamp, sql_site_activity[1], sql_site_activity[2], sql_site_activity[3], sql_site_activity[4],
                 sql_site_activity[5]])

        return site_activities

    @staticmethod
    def get_pt_site_seeding_info(site):
        """
        查询站点 做种分布信息
        :param site: 站点名称
        :return: seeding_info:[uploader_num, seeding_size]
        """
        site_seeding_info = {"seeding_info": []}
        seeding_info = SqlHelper.get_site_seeding_info(site=site)
        if not seeding_info:
            return site_seeding_info

        site_seeding_info["seeding_info"] = json.loads(seeding_info[0][0])
        return site_seeding_info

    @staticmethod
    def __get_site_strict_url(site):
        if not site:
            return
        site_url = site.get("signurl") or site.get("rssurl")
        if site_url:
            scheme, netloc = StringUtils.get_url_netloc(site_url)
            site_url = "%s://%s" % (scheme, netloc)
            return site_url
        return ""
