import traceback
from datetime import datetime
from multiprocessing.dummy import Pool as ThreadPool
from threading import Lock

import log
from message.send import Message
from pt.siteuserinfo.site_user_info_factory import SiteUserInfoFactory
from utils.functions import singleton
from utils.http_utils import RequestUtils
from utils.sqls import get_config_site, insert_site_statistics_history, update_site_user_statistics, \
    get_site_statistics_recent_sites, get_site_user_statistics

lock = Lock()


@singleton
class Sites:
    message = None
    __sites_data = {}
    __pt_sites = None
    __last_update_time = None
    _MAX_CONCURRENCY = 10

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.message = Message()
        self.__pt_sites = get_config_site()
        self.__sites_data = {}
        self.__last_update_time = None

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
                p.map(self.__refresh_pt_data, refresh_sites)

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

                # 登记历史数据
                insert_site_statistics_history(site=site_name, upload=site_user_info.upload,
                                               user_level=site_user_info.user_level,
                                               download=site_user_info.download,
                                               ratio=site_user_info.ratio,
                                               seeding=site_user_info.seeding,
                                               seeding_size=site_user_info.seeding_size,
                                               leeching=site_user_info.leeching, bonus=site_user_info.bonus,
                                               url=site_url)
                # 实时用户数据
                update_site_user_statistics(site=site_name, username=site_user_info.username,
                                            user_level=site_user_info.user_level,
                                            join_at=site_user_info.join_at,
                                            upload=site_user_info.upload, download=site_user_info.download,
                                            ratio=site_user_info.ratio, seeding=site_user_info.seeding,
                                            seeding_size=site_user_info.seeding_size,
                                            leeching=site_user_info.leeching, bonus=site_user_info.bonus,
                                            url=site_url)

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
                    elif not res:
                        status.append("%s 签到失败，无法打开网站" % pt_task)
                    else:
                        status.append("%s 签到失败，状态码：%s" % (pt_task, res.status_code))
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
