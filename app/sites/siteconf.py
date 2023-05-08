import os
import pickle
import random
import time
from functools import lru_cache

from lxml import etree

from app.helper import ChromeHelper
from app.utils import ExceptionUtils, StringUtils, RequestUtils
from app.utils.commons import singleton
from config import Config


@singleton
class SiteConf:
    # 站点签到支持的识别XPATH
    _SITE_CHECKIN_XPATH = [
        '//a[@id="signed"]',
        '//a[contains(@href, "attendance")]',
        '//a[contains(text(), "签到")]',
        '//a/b[contains(text(), "签 到")]',
        '//span[@id="sign_in"]/a',
        '//a[contains(@href, "addbonus")]',
        '//input[@class="dt_button"][contains(@value, "打卡")]',
        '//a[contains(@href, "sign_in")]',
        '//a[contains(@onclick, "do_signin")]',
        '//a[@id="do-attendance"]',
        '//shark-icon-button[@href="attendance.php"]'
    ]

    # 站点详情页字幕下载链接识别XPATH
    _SITE_SUBTITLE_XPATH = [
        '//td[@class="rowhead"][text()="字幕"]/following-sibling::td//a/@href',
    ]

    # 站点登录界面元素XPATH
    _SITE_LOGIN_XPATH = {
        "username": [
            '//input[@name="username"]',
            '//input[@id="form_item_username"]',
            '//input[@id="username"]'
        ],
        "password": [
            '//input[@name="password"]',
            '//input[@id="form_item_password"]',
            '//input[@id="password"]'
        ],
        "captcha": [
            '//input[@name="imagestring"]',
            '//input[@name="captcha"]',
            '//input[@id="form_item_captcha"]'
        ],
        "captcha_img": [
            '//img[@alt="CAPTCHA"]/@src',
            '//img[@alt="SECURITY CODE"]/@src',
            '//img[@id="LAY-user-get-vercode"]/@src',
            '//img[contains(@src,"/api/getCaptcha")]/@src'
        ],
        "submit": [
            '//input[@type="submit"]',
            '//button[@type="submit"]',
            '//button[@lay-filter="login"]',
            '//button[@lay-filter="formLogin"]',
            '//input[@type="button"][@value="登录"]'
        ],
        "error": [
            "//table[@class='main']//td[@class='text']/text()"
        ],
        "twostep": [
            '//input[@name="two_step_code"]',
            '//input[@name="2fa_secret"]'
        ]
    }

    # 促销/HR的匹配XPATH
    _RSS_SITE_GRAP_CONF = {}

    def __init__(self):
        self.init_config()

    def init_config(self):
        try:
            with open(os.path.join(Config().get_inner_config_path(),
                                   "sites.dat"),
                      "rb") as f:
                self._RSS_SITE_GRAP_CONF = pickle.load(f).get("conf")
        except Exception as err:
            ExceptionUtils.exception_traceback(err)

    def get_checkin_conf(self):
        return self._SITE_CHECKIN_XPATH

    def get_subtitle_conf(self):
        return self._SITE_SUBTITLE_XPATH

    def get_login_conf(self):
        return self._SITE_LOGIN_XPATH

    def get_grap_conf(self, url=None):
        if not url:
            return self._RSS_SITE_GRAP_CONF
        for k, v in self._RSS_SITE_GRAP_CONF.items():
            if StringUtils.url_equal(k, url):
                return v
        return {}

    def check_torrent_attr(self, torrent_url, cookie, ua=None, proxy=False):
        """
        检验种子是否免费，当前做种人数
        :param torrent_url: 种子的详情页面
        :param cookie: 站点的Cookie
        :param ua: 站点的ua
        :param proxy: 是否使用代理
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
        xpath_strs = self.get_grap_conf(torrent_url)
        if not xpath_strs:
            return ret_attr
        html_text = self.__get_site_page_html(url=torrent_url,
                                              cookie=cookie,
                                              ua=ua,
                                              render=xpath_strs.get('RENDER'),
                                              proxy=proxy)
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
                    peer_count_str = ''.join(peer_count_dom[0].itertext())
                    peer_count_digit_str = ""
                    for m in peer_count_str:
                        if m.isdigit():
                            peer_count_digit_str = peer_count_digit_str + m
                        if m == " ":
                            break
                    ret_attr["peer_count"] = int(peer_count_digit_str) if len(peer_count_digit_str) > 0 else 0
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
        # 随机休眼后再返回
        time.sleep(round(random.uniform(1, 5), 1))
        return ret_attr

    @staticmethod
    @lru_cache(maxsize=128)
    def __get_site_page_html(url, cookie, ua, render=False, proxy=False):
        chrome = ChromeHelper(headless=True)
        if render and chrome.get_status():
            # 开渲染
            if chrome.visit(url=url, cookie=cookie, ua=ua, proxy=proxy):
                # 等待页面加载完成
                time.sleep(10)
                return chrome.get_html()
        else:
            res = RequestUtils(
                cookies=cookie,
                headers=ua,
                proxies=Config().get_proxies() if proxy else None
            ).get_res(url=url)
            if res and res.status_code == 200:
                res.encoding = res.apparent_encoding
                return res.text
        return ""
