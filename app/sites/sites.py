import json
from datetime import datetime

import log
from app.helper import ChromeHelper, SiteHelper, DbHelper
from app.message import Message
from app.sites.site_limiter import SiteRateLimiter
from app.utils import RequestUtils, StringUtils
from app.utils.commons import singleton
from config import Config


@singleton
class Sites:
    message = None
    dbhelper = None

    _sites = []
    _siteByIds = {}
    _siteByUrls = {}
    _site_favicons = {}
    _rss_sites = []
    _brush_sites = []
    _statistic_sites = []
    _signin_sites = []
    _limiters = {}

    _MAX_CONCURRENCY = 10

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()
        self.message = Message()
        # 原始站点列表
        self._sites = []
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
        # 站点限速器
        self._limiters = {}
        # 站点图标
        self.init_favicons()
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
            uses = []
            if site_uses:
                rss_enable = True if "D" in site_uses and site_rssurl else False
                brush_enable = True if "S" in site_uses and site_rssurl and site_cookie else False
                statistic_enable = True if "T" in site_uses and (site_rssurl or site_signurl) and site_cookie else False
                uses.append("D") if rss_enable else None
                uses.append("S") if brush_enable else None
                uses.append("T") if statistic_enable else None
            else:
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
                "download_setting": site_note.get("download_setting"),
                "rss_enable": rss_enable,
                "brush_enable": brush_enable,
                "statistic_enable": statistic_enable,
                "uses": uses,
                "ua": site_note.get("ua"),
                "parse": True if site_note.get("parse") == "Y" else False,
                "unread_msg_notify": True if site_note.get("message") == "Y" else False,
                "chrome": True if site_note.get("chrome") == "Y" else False,
                "proxy": True if site_note.get("proxy") == "Y" else False,
                "subtitle": True if site_note.get("subtitle") == "Y" else False,
                "limit_interval": site_note.get("limit_interval"),
                "limit_count": site_note.get("limit_count"),
                "limit_seconds": site_note.get("limit_seconds"),
                "strict_url": StringUtils.get_base_url(site_signurl or site_rssurl)
            }
            # 以ID存储
            self._siteByIds[site.ID] = site_info
            # 以域名存储
            site_strict_url = StringUtils.get_url_domain(site.SIGNURL or site.RSSURL)
            if site_strict_url:
                self._siteByUrls[site_strict_url] = site_info
            # 初始化站点限速器
            if (site_note.get("limit_interval")
                and str(site_note.get("limit_interval")).isdigit()
                and site_note.get("limit_count")
                and str(site_note.get("limit_count")).isdigit()) \
                    or (site_note.get("limit_seconds")
                        and str(site_note.get("limit_seconds")).isdigit()):
                self._limiters[site.ID] = SiteRateLimiter(
                    limit_interval=int(site_note.get("limit_interval")) * 60,
                    limit_count=int(site_note.get("limit_count")),
                    limit_seconds=int(site_note.get("limit_seconds")) if site_note.get("limit_seconds") and str(
                        site_note.get("limit_seconds")).isdigit() else None
                )

    def init_favicons(self):
        """
        加载图标到内存
        """
        self._site_favicons = {site.SITE: site.FAVICON for site in self.dbhelper.get_site_favicons()}

    def get_sites(self,
                  siteid=None,
                  siteurl=None,
                  siteids=None,
                  rss=False,
                  brush=False,
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
            if statistic and not site.get('statistic_enable'):
                continue
            if siteids and str(site.get('id')) not in siteids:
                continue
            ret_sites.append(site)
        if siteid or siteurl:
            return {}
        return ret_sites

    def check_ratelimit(self, site_id):
        """
        检查站点是否触发流控
        :param site_id: 站点ID
        :return: True为触发了流控，False为未触发
        """
        if not self._limiters.get(site_id):
            return False
        state, msg = self._limiters[site_id].check_rate_limit()
        if msg:
            log.warn(f"【Sites】站点 {self._siteByIds[site_id].get('name')} {msg}")
        return state

    def get_sites_by_suffix(self, suffix):
        """
        根据url的后缀获取站点配置
        """
        for key in self._siteByUrls:
            # 使用.分割后再将最后两位(顶级域和二级域)拼起来
            key_parts = key.split(".")
            key_end = ".".join(key_parts[-2:])
            # 将拼起来的结果与参数进行对比
            if suffix == key_end:
                return self._siteByUrls[key]
        return {}

    def get_sites_by_name(self, name):
        """
        根据站点名称获取站点配置
        """
        ret_sites = []
        for site in self._siteByIds.values():
            if site.get("name") == name:
                ret_sites.append(site)
        return ret_sites

    def get_max_site_pri(self):
        """
        获取最大站点优先级
        """
        if not self._siteByIds:
            return 0
        return max([int(site.get("pri")) for site in self._siteByIds.values()])

    def get_site_dict(self,
                      rss=False,
                      brush=False,
                      statistic=False):
        """
        获取站点字典
        """
        return [
            {
                "id": site.get("id"),
                "name": site.get("name")
            } for site in self.get_sites(
                rss=rss,
                brush=brush,
                statistic=statistic
            )
        ]

    def get_site_names(self,
                       rss=False,
                       brush=False,
                       statistic=False):
        """
        获取站点名称
        """
        return [
            site.get("name") for site in self.get_sites(
                rss=rss,
                brush=brush,
                statistic=statistic
            )
        ]

    def get_site_favicon(self, site_name=None):
        """
        获取站点图标
        """
        if site_name:
            return self._site_favicons.get(site_name)
        else:
            return self._site_favicons

    def get_site_download_setting(self, site_name=None):
        """
        获取站点下载设置
        """
        if site_name:
            for site in self._siteByIds.values():
                if site.get("name") == site_name:
                    return site.get("download_setting")
        return None

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
        ua = site_info.get("ua") or Config().get_ua()
        site_url = StringUtils.get_base_url(site_info.get("signurl") or site_info.get("rssurl"))
        if not site_url:
            return False, "未配置站点地址", 0
        # 站点特殊处理...
        if '1ptba' in site_url:
            site_url = site_url + '/index.php'
        chrome = ChromeHelper()
        if site_info.get("chrome") and chrome.get_status():
            # 计时
            start_time = datetime.now()
            if not chrome.visit(url=site_url, ua=ua, cookie=site_cookie, proxy=site_info.get("proxy")):
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
            if SiteHelper.is_logged_in(html_text):
                return True, "连接成功", seconds
            else:
                return False, "Cookie失效", seconds
        else:
            # 计时
            start_time = datetime.now()
            res = RequestUtils(cookies=site_cookie,
                               headers=ua,
                               proxies=Config().get_proxies() if site_info.get("proxy") else None
                               ).get_res(url=site_url)
            seconds = int((datetime.now() - start_time).microseconds / 1000)
            if res and res.status_code == 200:
                if not SiteHelper.is_logged_in(res.text):
                    return False, "Cookie失效", seconds
                else:
                    return True, "连接成功", seconds
            elif res is not None:
                return False, f"连接失败，状态码：{res.status_code}", seconds
            else:
                return False, "无法打开网站", seconds

    @staticmethod
    def __get_site_note_items(note):
        """
        从note中提取站点信息
        """
        infos = {}
        if note:
            infos = json.loads(note)
        return infos

    def add_site(self, name, site_pri,
                 rssurl=None, signurl=None, cookie=None, note=None, rss_uses=None):
        """
        添加站点
        """
        ret = self.dbhelper.insert_config_site(name=name,
                                               site_pri=site_pri,
                                               rssurl=rssurl,
                                               signurl=signurl,
                                               cookie=cookie,
                                               note=note,
                                               rss_uses=rss_uses)
        self.init_config()
        return ret

    def update_site(self, tid, name, site_pri,
                    rssurl, signurl, cookie, note, rss_uses):
        """
        更新站点
        """
        ret = self.dbhelper.update_config_site(tid=tid,
                                               name=name,
                                               site_pri=site_pri,
                                               rssurl=rssurl,
                                               signurl=signurl,
                                               cookie=cookie,
                                               note=note,
                                               rss_uses=rss_uses)
        self.init_config()
        return ret

    def delete_site(self, siteid):
        """
        删除站点
        """
        ret = self.dbhelper.delete_config_site(siteid)
        self.init_config()
        return ret

    def update_site_cookie(self, siteid, cookie, ua=None):
        """
        更新站点Cookie和UA
        """
        ret = self.dbhelper.update_site_cookie_ua(tid=siteid,
                                                  cookie=cookie,
                                                  ua=ua)
        self.init_config()
        return ret
