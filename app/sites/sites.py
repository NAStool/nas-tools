import json
import random
import re
import time
import traceback
from datetime import datetime
from functools import lru_cache
from multiprocessing.dummy import Pool as ThreadPool
from threading import Lock

from lxml import etree
from requests.utils import dict_from_cookiejar
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as es

import log
from app.message import Message
from app.sites import SiteUserInfoFactory
from app.sites.siteconf import SiteConf
from app.utils.commons import singleton
from app.utils import RequestUtils, StringUtils
from app.helper import ChromeHelper, CHROME_LOCK
from app.helper import DbHelper
from config import SITE_CHECKIN_XPATH, Config

lock = Lock()


@singleton
class Sites:
    message = None
    siteconf = None
    dbhelper = None

    _sites = []
    _siteByIds = {}
    _siteByUrls = {}
    _sites_data = {}
    _site_favicons = {}
    _rss_sites = []
    _brush_sites = []
    _statistic_sites = []
    _signin_sites = []
    _last_update_time = None

    _MAX_CONCURRENCY = 10

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()
        self.message = Message()
        self.siteconf = SiteConf()
        # 原始站点列表
        self._sites = []
        # 站点数据
        self._sites_data = {}
        # 站点数据更新时间
        self._last_update_time = None
        # ID存储站点
        self._siteByIds = {}
        # URL存储站点
        self._siteByUrls = {}
        # 开启订阅功能站点
        self._rss_sites = []
        # 开启刷流功能站点：
        self._brush_sites = []
        # 开启统计功能站点：
        self._statistic_sites = []
        # 开启签到功能站点：
        self._signin_sites = []
        # 站点图标
        self._site_favicons = {site.SITE: site.FAVICON for site in self.dbhelper.get_site_user_statistics()}
        # 站点数据
        self._sites = self.dbhelper.get_config_site()
        for site in self._sites:
            # 站点属性
            site_note = self.__get_site_note_items(site.NOTE)
            # 站点用途：Q签到、D订阅、S刷流
            site_rssurl = site.RSSURL
            site_signurl = site.SIGNURL
            site_cookie = site.COOKIE
            site_uses = site.INCLUDE or ''
            if site_uses:
                signin_enable = True if "Q" in site_uses and site_signurl and site_cookie else False
                rss_enable = True if "D" in site_uses and site_rssurl else False
                brush_enable = True if "S" in site_uses and site_rssurl and site_cookie else False
                statistic_enable = True if "T" in site_uses and (site_rssurl or site_signurl) and site_cookie else False
            else:
                signin_enable = False
                rss_enable = False
                brush_enable = False
                statistic_enable = False
            site_info = {
                "id": site.ID,
                "name": site.NAME,
                "pri": site.PRI or 0,
                "rssurl": site_rssurl,
                "signurl": site_signurl,
                "cookie": site_cookie,
                "rule": site_note.get("rule"),
                "parse": site_note.get("parse"),
                "signin_enable": signin_enable,
                "rss_enable": rss_enable,
                "brush_enable": brush_enable,
                "statistic_enable": statistic_enable,
                "favicon": self._site_favicons.get(site.NAME, ""),
                "ua": site_note.get("ua"),
                "unread_msg_notify": site_note.get("message") or 'N',
                "chrome": site_note.get("chrome") or 'N',
                "proxy": site_note.get("proxy") or 'N',
                "subtitle": site_note.get("subtitle") or 'N'
            }
            # 以ID存储
            self._siteByIds[site.ID] = site_info
            # 以域名存储
            site_strict_url = StringUtils.get_url_domain(site.SIGNURL or site.RSSURL)
            if site_strict_url:
                self._siteByUrls[site_strict_url] = site_info

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
        if siteid:
            return self._siteByIds.get(int(siteid)) or {}
        if siteurl:
            return self._siteByUrls.get(StringUtils.get_url_domain(siteurl)) or {}

        ret_sites = []
        for site in self._siteByIds.values():
            if rss and not site.get('rss_enable'):
                continue
            if brush and not site.get('brush_enable'):
                continue
            if signin and not site.get('signin_enable'):
                continue
            if statistic and not site.get('statistic_enable'):
                continue
            ret_sites.append(site)
        if siteid or siteurl:
            return {}
        return ret_sites

    def refresh_all_site_data(self, force=False, specify_sites=None):
        """
        多线程刷新站点下载上传量，默认间隔6小时
        """
        if not self._sites:
            return
        if not force and self._last_update_time and (datetime.now() - self._last_update_time).seconds < 6 * 3600:
            return

        with lock:
            # 没有指定站点，默认使用全部站点
            if not specify_sites:
                refresh_sites = self.get_sites(statistic=True)
            else:
                refresh_sites = [site for site in self.get_sites(statistic=True) if site.get("name") in specify_sites]
            if not refresh_sites:
                return

            refresh_all = len(self.get_sites(statistic=True)) == len(refresh_sites)

            # 并发刷新
            with ThreadPool(min(len(refresh_sites), self._MAX_CONCURRENCY)) as p:
                site_user_infos = p.map(self.__refresh_site_data, refresh_sites)
                site_user_infos = [info for info in site_user_infos if info]
            # 登记历史数据
            self.dbhelper.insert_site_statistics_history(site_user_infos)
            # 实时用户数据
            self.dbhelper.update_site_user_statistics(site_user_infos)
            # 实时做种信息
            self.dbhelper.update_site_seed_info(site_user_infos)

        # 更新时间
        if refresh_all:
            self._last_update_time = datetime.now()

    def __refresh_site_data(self, site_info):
        """
        更新单个site 数据信息
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
        chrome = True if site_info.get("chrome") == "Y" else False
        proxy = True if site_info.get("proxy") == "Y" else False
        try:
            site_user_info = SiteUserInfoFactory.build(url=site_url,
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

                self._sites_data.update({site_name: {
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
                    "message_unread": site_user_info.message_unread}
                })

                return site_user_info

        except Exception as e:
            log.error("【Sites】站点 %s 获取流量数据失败：%s - %s" % (site_name, str(e), traceback.format_exc()))

    def __notify_unread_msg(self, site_name, site_user_info, unread_msg_notify):
        if site_user_info.message_unread <= 0:
            return
        if self._sites_data.get(site_name, {}).get('message_unread') == site_user_info.message_unread:
            return
        if unread_msg_notify != 'Y':
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

    def test_connection(self, site_id):
        """
        测试站点连通性
        :param site_id: 站点编号
        :return: 是否连通、错误信息、耗时
        """
        site_info = self.get_sites(siteid=site_id)
        if not site_info:
            return False, "站点不存在", 0
        site_cookie = site_info.get("cookie")
        if not site_cookie:
            return False, "未配置站点Cookie", 0
        ua = site_info.get("ua")
        site_url = StringUtils.get_base_url(site_info.get("signurl") or site_info.get("rssurl"))
        if not site_url:
            return False, "未配置站点地址", 0
        emulate = site_info.get("chrome")
        chrome = ChromeHelper()
        if emulate == "Y" and chrome.get_status():
            # 首页
            with CHROME_LOCK:
                # 计时
                start_time = datetime.now()
                try:
                    chrome.visit(url=site_url, ua=ua, cookie=site_cookie)
                except Exception as err:
                    print(str(err))
                    return False, "Chrome模拟访问失败", 0
                # 循环检测是否过cf
                cloudflare = chrome.pass_cloudflare()
                seconds = int((datetime.now() - start_time).microseconds / 1000)
                if not cloudflare:
                    return False, "跳转站点失败", seconds
                # 判断是否已签到
                html_text = chrome.get_html()
                if not html_text:
                    return False, "获取站点源码失败", 0
                if self.is_signin_success(html_text):
                    return True, "连接成功", seconds
                else:
                    return False, "Cookie失效", seconds
        else:
            # 计时
            start_time = datetime.now()
            proxies = Config().get_proxies() if site_info.get("proxy") == "Y" else None
            res = RequestUtils(cookies=site_cookie,
                               headers=ua,
                               proxies=proxies
                               ).get_res(url=site_url)
            seconds = int((datetime.now() - start_time).microseconds / 1000)
            if res and res.status_code == 200:
                if not self.is_signin_success(res.text):
                    return False, "Cookie失效", seconds
                else:
                    return True, "连接成功", seconds
            elif res is not None:
                return False, f"连接失败，状态码：{res.status_code}", seconds
            else:
                return False, "无法打开网站", seconds

    def signin(self):
        """
        站点签到入口，由定时服务调用
        """
        status = []
        # 浏览器
        chrome = ChromeHelper()
        for site_info in self.get_sites(signin=True):
            if not site_info:
                continue
            site = site_info.get("name")
            try:
                site_url = site_info.get("signurl")
                site_cookie = site_info.get("cookie")
                ua = site_info.get("ua")
                emulate = site_info.get("chrome")
                if not site_url or not site_cookie:
                    log.warn("【Sites】未配置 %s 的站点地址或Cookie，无法签到" % str(site))
                    continue
                if emulate == "Y" and chrome.get_status():
                    # 首页
                    log.info("【Sites】开始站点仿真签到：%s" % site)
                    home_url = StringUtils.get_base_url(site_url)
                    with CHROME_LOCK:
                        try:
                            chrome.visit(url=home_url, ua=ua, cookie=site_cookie)
                        except Exception as err:
                            print(str(err))
                            log.warn("【Sites】%s 无法打开网站" % site)
                            status.append("【%s】无法打开网站！" % site)
                            continue
                        # 循环检测是否过cf
                        cloudflare = chrome.pass_cloudflare()
                        if not cloudflare:
                            log.warn("【Sites】%s 跳转站点失败" % site)
                            status.append("【%s】跳转站点失败！" % site)
                            continue
                        # 判断是否已签到
                        html_text = chrome.get_html()
                        if not html_text:
                            log.warn("【Sites】%s 获取站点源码失败" % site)
                            continue
                        # 查找签到按钮
                        html = etree.HTML(html_text)
                        xpath_str = None
                        for xpath in SITE_CHECKIN_XPATH:
                            if html.xpath(xpath):
                                xpath_str = xpath
                                break
                        if re.search(r'已签|签到已得', html_text, re.IGNORECASE) \
                                and not xpath_str:
                            log.info("【Sites】%s 今日已签到" % site)
                            status.append("【%s】今日已签到" % site)
                            continue
                        if not xpath_str:
                            if self.is_signin_success(html_text):
                                log.warn("【Sites】%s 未找到签到按钮，模拟登录成功" % site)
                                status.append("【%s】模拟登录成功" % site)
                            else:
                                log.info("【Sites】%s 未找到签到按钮，且模拟登录失败" % site)
                                status.append("【%s】模拟登录失败！" % site)
                            continue
                        # 开始仿真
                        try:
                            checkin_obj = WebDriverWait(driver=chrome.browser, timeout=6).until(
                                es.element_to_be_clickable((By.XPATH, xpath_str)))
                            if checkin_obj:
                                checkin_obj.click()
                                log.info("【Sites】%s 仿真签到成功" % site)
                                status.append("【%s】签到成功" % site)
                        except Exception as e:
                            log.warn("【Sites】%s 仿真签到失败：%s" % (site, str(e)))
                            status.append("【%s】签到失败！" % site)
                            continue
                # 模拟登录
                else:
                    proxies = Config().get_proxies() if site_info.get("proxy") == "Y" else None
                    if site_url.find("attendance.php") != -1:
                        checkin_text = "签到"
                    else:
                        checkin_text = "模拟登录"
                    log.info(f"【Sites】开始站点{checkin_text}：{site}")
                    # 访问链接
                    res = RequestUtils(cookies=site_cookie,
                                       headers=ua,
                                       proxies=proxies
                                       ).get_res(url=site_url)
                    if res and res.status_code == 200:
                        if not self.is_signin_success(res.text):
                            log.warn(f"【Sites】{site} {checkin_text}失败，请检查cookie")
                            status.append(f"【{site}】{checkin_text}失败，请检查cookie！")
                        else:
                            log.info(f"【Sites】{site} {checkin_text}成功")
                            status.append(f"【{site}】{checkin_text}成功")
                    elif res is not None:
                        log.warn(f"【Sites】{site} {checkin_text}失败，状态码：{res.status_code}")
                        status.append(f"【{site}】{checkin_text}失败，状态码：{res.status_code}！")
                    else:
                        log.warn(f"【Sites】{site} {checkin_text}失败，无法打开网站")
                        status.append(f"【{site}】{checkin_text}失败，无法打开网站！")
            except Exception as e:
                log.error("【Sites】%s 签到出错：%s - %s" % (site, str(e), traceback.format_exc()))
        if status:
            self.message.send_site_signin_message(status)

    @staticmethod
    def is_signin_success(html_text):
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
        self.refresh_all_site_data(True)

    def get_pt_date(self):
        """
        获取站点上传下载量
        """
        self.refresh_all_site_data()
        return self._sites_data

    def get_pt_site_statistics_history(self, days=7):
        """
        获取站点上传下载量
        """
        site_urls = []
        for site in self.get_sites(statistic=True):
            site_url = self.__get_site_strict_url(site)
            if site_url:
                site_urls.append(site_url)

        return self.dbhelper.get_site_statistics_recent_sites(days=days, strict_urls=site_urls)

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

        raw_statistics = self.dbhelper.get_site_user_statistics(strict_urls=site_urls)
        if encoding == "RAW":
            return raw_statistics

        return self.__todict(raw_statistics)

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
                               "favicon": site.FAVICON,
                               "msg_unread": site.MSG_UNREAD
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

        self.refresh_all_site_data(force=True, specify_sites=specify_sites)

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

    @staticmethod
    def __get_site_strict_url(site):
        if not site:
            return
        site_url = site.get("signurl") or site.get("rssurl")
        if site_url:
            return StringUtils.get_base_url(site_url)
        return ""

    def get_site_attr(self, url):
        """
        获取站点Cookie和UA等属性
        """
        cookie, ua, referer = None, None, False
        site_info = self.get_sites(siteurl=url)
        if site_info:
            cookie = site_info.get("cookie")
            ua = site_info.get("ua")
            referer = False
        else:
            short_url = StringUtils.get_base_url(url)
            site_info = self.get_public_sites(url=short_url)
            if site_info:
                referer = site_info.get('referer')
                if site_info.get("render"):
                    # 开渲染
                    chrome = ChromeHelper()
                    if not chrome.get_status():
                        log.warn("【Sites】该网站需要浏览器内核才能访问：%s" % short_url)
                    else:
                        with CHROME_LOCK:
                            try:
                                chrome.visit(url=short_url)
                                cookie = chrome.get_cookies()
                                ua = chrome.get_ua()
                            except Exception as err:
                                print(str(err))
                                log.warn("【Sites】无法打开网站：%s" % short_url)
                else:
                    try:
                        res = RequestUtils(timeout=10).get_res(short_url)
                        if res:
                            cookie = dict_from_cookiejar(res.cookies)
                    except Exception as err:
                        print(str(err))
        return cookie, ua, referer, site_info

    def parse_site_download_url(self, page_url, xpath, cookie=None, ua=None):
        """
        从站点详情页面中解析中下载链接
        :param page_url: 详情页面地址
        :param xpath: 解析XPATH
        :param cookie: 站点Cookie
        :param ua: 站点User-Agent
        """
        if not page_url or not xpath:
            return ""
        page_source = ""
        try:
            short_url = StringUtils.get_base_url(page_url)
            site_info = self.get_public_sites(url=short_url)
            if site_info and site_info.get("render"):
                # 开渲染
                chrome = ChromeHelper()
                if not chrome.get_status():
                    log.warn("【Sites】该网站需要浏览器内核才能访问：%s" % short_url)
                else:
                    with CHROME_LOCK:
                        try:
                            chrome.visit(url=page_url)
                            page_source = chrome.get_html()
                        except Exception as err:
                            print(str(err))
                            log.warn("【Sites】无法打开网站：%s" % short_url)
            else:
                req = RequestUtils(headers=ua, cookies=cookie).get_res(url=page_url)
                if req and req.status_code == 200:
                    if req.text:
                        page_source = req.text
            # xpath解析
            if page_source:
                html = etree.HTML(page_source)
                urls = html.xpath(xpath)
                if urls:
                    return str(urls[0])
        except Exception as err:
            print(str(err))
        return None

    @staticmethod
    @lru_cache(maxsize=128)
    def __get_site_page_html(url, cookie, ua):
        res = RequestUtils(cookies=cookie, headers=ua).get_res(url=url)
        if res and res.status_code == 200:
            res.encoding = res.apparent_encoding
            return res.text
        return ""

    def get_grapsite_conf(self, url):
        """
        根据地址找到RSS_SITE_GRAP_CONF对应配置
        """
        for k, v in self.siteconf.RSS_SITE_GRAP_CONF.items():
            if StringUtils.url_equal(k, url):
                return v
        return {}

    def check_torrent_attr(self, torrent_url, cookie, ua=None):
        """
        检验种子是否免费，当前做种人数
        :param torrent_url: 种子的详情页面
        :param cookie: 站点的Cookie
        :param ua: 站点的ua
        :return: 种子属性，包含FREE 2XFREE HR PEER_COUNT等属性
        """
        ret_attr = {
            "free": False,
            "2xfree": False,
            "hr": False,
            "peer_count": 0
        }
        if not torrent_url:
            return ret_attr
        xpath_strs = self.get_grapsite_conf(torrent_url)
        if not xpath_strs:
            return ret_attr
        html_text = self.__get_site_page_html(url=torrent_url, cookie=cookie, ua=ua)
        if not html_text:
            return ret_attr
        try:
            html = etree.HTML(html_text)
            # 检测2XFREE
            for xpath_str in xpath_strs.get("2XFREE"):
                if html.xpath(xpath_str):
                    ret_attr["free"] = True
                    ret_attr["2xfree"] = True
            # 检测FREE
            for xpath_str in xpath_strs.get("FREE"):
                if html.xpath(xpath_str):
                    ret_attr["free"] = True
            # 检测HR
            for xpath_str in xpath_strs.get("HR"):
                if html.xpath(xpath_str):
                    ret_attr["hr"] = True
            # 检测PEER_COUNT当前做种人数
            for xpath_str in xpath_strs.get("PEER_COUNT"):
                peer_count_dom = html.xpath(xpath_str)
                if peer_count_dom:
                    peer_count_str = peer_count_dom[0].text
                    peer_count_str_re = re.search(r'^(\d+)', peer_count_str)
                    ret_attr["peer_count"] = int(peer_count_str_re.group(1)) if peer_count_str_re else 0
        except Exception as err:
            print(str(err))
        # 随机休眼后再返回
        time.sleep(round(random.uniform(1, 5), 1))
        return ret_attr

    def is_public_site(self, url):
        """
        判断是否为公开BT站点
        """
        _, netloc = StringUtils.get_url_netloc(url)
        if netloc in self.siteconf.PUBLIC_TORRENT_SITES.keys():
            return True
        return False

    def get_public_sites(self, url=None):
        """
        查询所有公开BT站点
        """
        if url:
            _, netloc = StringUtils.get_url_netloc(url)
            return self.siteconf.PUBLIC_TORRENT_SITES.get(netloc)
        else:
            return self.siteconf.PUBLIC_TORRENT_SITES.items()

    @staticmethod
    def __get_site_note_items(note):
        """
        从note中提取站点信息
        """
        infos = {}
        if note:
            infos = json.loads(note)
        return infos
