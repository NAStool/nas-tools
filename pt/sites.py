import json
import traceback
from datetime import datetime
from multiprocessing.dummy import Pool as ThreadPool
from threading import Lock

import log
from message.send import Message
from pt.filterrules import FilterRule
from pt.siteuserinfo.site_user_info_factory import SiteUserInfoFactory
from utils.functions import singleton
from utils.http_utils import RequestUtils
from utils.sqls import get_config_site, insert_site_statistics_history, update_site_user_statistics, \
    get_site_statistics_recent_sites, get_site_user_statistics, get_site_statistics_history, get_site_seeding_info, \
    update_site_seed_info

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
        self.__pt_sites = get_config_site()
        self.__sites_data = {}
        self.__last_update_time = None

    def get_sites(self, siteid=None):
        """
        获取站点配置
        """
        ret_sites = []
        for site in self.__pt_sites:
            # 是否解析种子详情为|分隔的第1位
            site_parse = str(site[9]).split("|")[0] or "Y"
            # 站点过滤规则为|分隔的第2位
            rule_groupid = str(site[9]).split("|")[1] if site[9] and len(str(site[9]).split("|")) > 1 else ""
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
                "parse": site_parse
            }
            if siteid and int(site[0]) == int(siteid):
                return site_info
            ret_sites.append(site_info)
        if siteid:
            return {}
        return ret_sites

    def refresh_all_pt_data(self, force=False, specify_sites=None):
        """
        多线程刷新PT站下载上传量，默认间隔6小时
        """
        if not self.__pt_sites:
            return
        if not force and self.__last_update_time and (datetime.now() - self.__last_update_time).seconds < 6 * 3600:
            return

        with lock:
            # 没有指定站点，默认使用全部站点
            if not specify_sites:
                refresh_site_names = [site[1] for site in self.__pt_sites]
            else:
                refresh_site_names = specify_sites

            refresh_all = len(self.__pt_sites) == len(refresh_site_names)
            refresh_sites = [site for site in self.__pt_sites if site[1] in refresh_site_names]

            with ThreadPool(min(len(refresh_sites), self._MAX_CONCURRENCY)) as p:
                site_user_infos = p.map(self.__refresh_pt_data, refresh_sites)
                site_user_infos = [info for info in site_user_infos if info]

                # 登记历史数据
                insert_site_statistics_history(site_user_infos)
                # 实时用户数据
                update_site_user_statistics(site_user_infos)
                # 实时做种信息
                update_site_seed_info(site_user_infos)

        # 更新时间
        if refresh_all:
            self.__last_update_time = datetime.now()

    def __refresh_pt_data(self, site_info):
        """
        更新单个pt site 数据信息
        :param site_info:
        :return:
        """
        site_name, site_url, site_cookie = self.parse_site_config(site_info)
        if not site_url:
            return

        try:
            site_user_info = SiteUserInfoFactory.build(url=site_url, site_name=site_name, site_cookie=site_cookie)
            if site_user_info:
                log.debug(f"【PT】站点 {site_name} 开始以 {site_user_info.site_schema()} 模型解析")
                # 开始解析
                site_user_info.parse()
                log.debug(f"【PT】站点 {site_name} 解析完成")

                # 获取不到数据时，仅返回错误信息，不做历史数据更新
                if site_user_info.err_msg:
                    self.__sites_data.update({site_name: {"err_msg": site_user_info.err_msg}})
                    return

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
                                                      "err_msg": site_user_info.err_msg}
                                          })

                return site_user_info

        except Exception as e:
            log.error("【PT】站点 %s 获取流量数据失败：%s - %s" % (site_name, str(e), traceback.format_exc()))

    @staticmethod
    def parse_site_config(site_info):
        """
        解析site配置
        :param site_info:
        :return: site_name, site_url, site_cookie
        """
        if not site_info:
            return None, None, None

        site_name = site_info[1]
        site_url = site_info[4]
        if not site_url and site_info[3]:
            site_url = site_info[3]
        if not site_url:
            return site_name, None, None
        split_pos = str(site_url).rfind("/")
        if split_pos != -1 and split_pos > 8:
            site_url = site_url[:split_pos]
        site_cookie = str(site_info[5])
        return site_name, site_url, site_cookie

    def signin(self):
        """
        PT站签到入口，由定时服务调用
        """
        status = []
        if self.__pt_sites:
            for site_info in self.__pt_sites:
                if not site_info:
                    continue
                pt_task = site_info[1]
                try:
                    pt_url = site_info[4]
                    pt_cookie = site_info[5]
                    log.info("【PT】开始PT签到：%s" % pt_task)
                    if not pt_url or not pt_cookie:
                        log.warn("【PT】未配置 %s 的Url或Cookie，无法签到" % str(pt_task))
                        continue
                    res = RequestUtils(cookies=pt_cookie).get_res(url=pt_url)
                    if res and res.status_code == 200:
                        if not self.__is_signin_success(res.text):
                            status.append("%s 签到失败，Cookie已过期" % pt_task)
                        else:
                            status.append("%s 签到成功" % pt_task)
                    elif res and res.status_code:
                        status.append("%s 签到失败，状态码：%s" % (pt_task, res.status_code))
                    else:
                        status.append("%s 签到失败，无法打开网站" % pt_task)
                except Exception as e:
                    log.error("【PT】%s 签到出错：%s - %s" % (pt_task, str(e), traceback.format_exc()))
        if status:
            self.message.sendmsg(title="\n".join(status))

    @staticmethod
    def __is_signin_success(html_text):
        """
        检进是否成功进入PT网站而不是登录界面
        """
        if not html_text:
            return False
        return True if html_text.find("userdetails") != -1 else False

    def refresh_pt_date_now(self):
        """
        强制刷新PT站数据
        """
        self.refresh_all_pt_data(True)

    def get_pt_date(self):
        """
        获取PT站上传下载量
        """
        self.refresh_all_pt_data()
        return self.__sites_data

    def get_pt_site_statistics_history(self, days=7):
        """
        获取PT站上传下载量
        """
        site_urls = []
        for site in self.__pt_sites:
            _, url, _ = self.parse_site_config(site)
            if url:
                site_urls.append(url)

        return get_site_statistics_recent_sites(days=days, strict_urls=site_urls)

    def get_pt_site_user_statistics(self):
        """
        获取PT站用户数据
        :return:
        """
        site_urls = []
        for site in self.__pt_sites:
            _, url, _ = self.parse_site_config(site)
            if url:
                site_urls.append(url)

        return get_site_user_statistics(strict_urls=site_urls)

    def refresh_pt(self, specify_sites=None):
        """
        强制刷新PT指定站数据
        """
        if not specify_sites:
            return

        if not isinstance(specify_sites, list):
            specify_sites = [specify_sites]

        self.refresh_all_pt_data(force=True, specify_sites=specify_sites)

    @staticmethod
    def get_pt_site_activity_history(site, days=365*2):
        """
        查询站点 上传，下载，做种数据
        :param site: 站点名称
        :param days: 最大数据量
        :return:
        """
        site_activities = {"upload": [], "download": [], "bonus": [], "seeding": [], "seeding_size": []}
        sql_site_activities = get_site_statistics_history(site=site, days=days)
        for sql_site_activity in sql_site_activities:
            timestamp = datetime.strptime(sql_site_activity[0], '%Y-%m-%d').timestamp() * 1000
            site_activities["upload"].append([timestamp, sql_site_activity[1]])
            site_activities["download"].append([timestamp, sql_site_activity[2]])
            site_activities["bonus"].append([timestamp, sql_site_activity[3]])
            site_activities["seeding"].append([timestamp, sql_site_activity[4]])
            site_activities["seeding_size"].append([timestamp, sql_site_activity[5]])

        return site_activities

    @staticmethod
    def get_pt_site_seeding_info(site):
        """
        查询站点 做种分布信息
        :param site: 站点名称
        :return: seeding_info:[uploader_num, seeding_size]
        """
        site_seeding_info = {"seeding_info": []}
        seeding_info = get_site_seeding_info(site=site)
        if not seeding_info:
            return site_seeding_info

        site_seeding_info["seeding_info"] = json.loads(seeding_info[0][0])
        return site_seeding_info
