import time

from lxml import etree
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as es

import log
from app.helper import ChromeHelper, ProgressHelper, CHROME_LOCK, DbHelper
from app.helper.ocr_helper import OcrHelper
from app.sites import Sites
from app.utils import StringUtils
from app.utils.commons import singleton
from config import SITE_LOGIN_XPATH


@singleton
class SiteCookie(object):
    progress = None
    sites = None
    ocrhelper = None
    dbhelpter = None

    captcha_code = {}

    def __init__(self):
        self.progress = ProgressHelper()
        self.sites = Sites()
        self.ocrhelper = OcrHelper()
        self.dbhelpter = DbHelper()
        self.init_config()

    def init_config(self):
        self.captcha_code = {}

    def set_code(self, code, value):
        """
        设置验证码的值
        """
        self.captcha_code[code] = value

    def get_code(self, code):
        """
        获取验证码的值
        """
        return self.captcha_code.get(code)

    def __get_site_cookie_ua(self, url, username, password, ocrflag=False, chrome=None):
        """
        获取站点cookie和ua
        :param url: 站点地址
        :param username: 用户名
        :param password: 密码
        :param ocrflag: 是否开启OCR识别
        :param chrome: ChromeHelper
        :return: cookie、ua、message
        """
        if not url or not username or not password:
            return None, None, "参数错误"
        if not chrome:
            chrome = ChromeHelper()
            if not chrome.get_status():
                return None, None, "需要浏览器内核环境才能更新站点信息"
        # 全局锁
        with CHROME_LOCK:
            try:
                chrome.visit(url=url)
            except Exception as err:
                print(str(err))
                return None, None, "Chrome模拟访问失败"
            # 循环检测是否过cf
            cloudflare = False
            for i in range(0, 10):
                if chrome.get_title() != "Just a moment...":
                    cloudflare = True
                    break
                time.sleep(1)
            if not cloudflare:
                return None, None, "跳转站点失败，无法通过Cloudflare验证"
            # 登录页面代码
            html_text = chrome.get_html()
            if not html_text:
                return None, None, "获取源码失败"
            # 查找用户名输入框
            html = etree.HTML(html_text)
            username_xpath = None
            for xpath in SITE_LOGIN_XPATH.get("username"):
                if html.xpath(xpath):
                    username_xpath = xpath
                    break
            if not username_xpath:
                return None, None, "未找到用户名输入框"
            # 查找密码输入框
            password_xpath = None
            for xpath in SITE_LOGIN_XPATH.get("password"):
                if html.xpath(xpath):
                    password_xpath = xpath
                    break
            if not password_xpath:
                return None, None, "未找到密码输入框"
            # 查找验证码输入框
            captcha_xpath = None
            for xpath in SITE_LOGIN_XPATH.get("captcha"):
                if html.xpath(xpath):
                    captcha_xpath = xpath
                    break
            if captcha_xpath:
                # 查找验证码图片
                captcha_img_url = None
                for xpath in SITE_LOGIN_XPATH.get("captcha_img"):
                    if html.xpath(xpath):
                        captcha_img_url = html.xpath(xpath)[0]
                        break
                if not captcha_img_url:
                    return None, None, "未找到验证码图片"
            # 查找登录按钮
            submit_xpath = None
            for xpath in SITE_LOGIN_XPATH.get("submit"):
                if html.xpath(xpath):
                    submit_xpath = xpath
                    break
            if not submit_xpath:
                return None, None, "未找到登录按钮"
            # 点击登录按钮
            try:
                submit_obj = WebDriverWait(driver=chrome.browser,
                                           timeout=6).until(es.element_to_be_clickable((By.XPATH,
                                                                                        submit_xpath)))
                if submit_obj:
                    # 输入用户名
                    chrome.browser.find_element(By.XPATH, username_xpath).send_keys(username)
                    # 输入密码
                    chrome.browser.find_element(By.XPATH, password_xpath).send_keys(password)
                    # 识别验证码
                    if captcha_xpath:
                        if ocrflag:
                            # 自动OCR识别验证码
                            captcha = self.get_captcha_text(siteurl=url, imageurl=captcha_img_url)
                            if captcha:
                                log.info("【Sites】验证码地址为：%s，识别结果：%s" % (captcha_img_url, captcha))
                            else:
                                return None, None, "验证码识别失败"
                        else:
                            # 等待用户输入
                            captcha = None
                            codeurl = self.__get_captcha_url(url, captcha_img_url)
                            for sec in range(30, 0, -1):
                                if self.get_code(codeurl):
                                    # 用户输入了
                                    captcha = self.get_code(codeurl)
                                    log.info("【Sites】接收到验证码：%s" % captcha)
                                    break
                                else:
                                    self.progress.update(ptype='sitecookie',
                                                         text=f"{codeurl}|等待输入验证码，倒计时 %s 秒 ..." % sec)
                                    time.sleep(1)
                            if not captcha:
                                return None, None, "验证码输入超时"
                        # 输入验证码
                        chrome.browser.find_element(By.XPATH, captcha_xpath).send_keys(captcha)
                    # 提交登录
                    submit_obj.click()
                else:
                    return None, None, "未找到登录按钮"
            except Exception as e:
                return None, None, "仿真登录失败：%s" % str(e)
            # 登录后的源码
            html_text = chrome.get_html()
            if not html_text:
                return None, None, "获取源码失败"
            if self.sites.is_signin_success(html_text):
                cookie = chrome.get_cookies()
                ua = chrome.get_ua()
                return cookie, ua, ""
            else:
                # 读取错误信息
                error_xpath = None
                for xpath in SITE_LOGIN_XPATH.get("error"):
                    if html.xpath(xpath):
                        error_xpath = xpath
                        break
                if not error_xpath:
                    return None, None, "登录失败"
                else:
                    error_msg = html.xpath(error_xpath)[0]
                    return None, None, error_msg

    def get_captcha_text(self, siteurl, imageurl):
        """
        识别验证码图片的内容
        """
        if not siteurl or not imageurl:
            return ""
        return self.ocrhelper.get_captcha_text(image_url=self.__get_captcha_url(siteurl, imageurl))

    @staticmethod
    def __get_captcha_url(siteurl, imageurl):
        """
        获取验证码图片的URL
        """
        if not siteurl or not imageurl:
            return ""
        scheme, netloc = StringUtils.get_url_netloc(siteurl)
        return "%s://%s/%s" % (scheme, netloc, imageurl)

    def update_sites_cookie_ua(self, username, password, siteid=None, ocrflag=False):
        """
        更新所有站点Cookie和ua
        """
        chrome = ChromeHelper()
        if not chrome.get_status():
            return -1, ["需要浏览器内核环境才能更新站点信息"]
        # 获取站点列表
        sites = self.sites.get_sites(siteid=siteid)
        if siteid:
            sites = [sites]
        # 总数量
        site_num = len(sites)
        # 当前数量
        curr_num = 0
        # 返回码、返回消息
        retcode = 0
        messages = []
        # 开始进度
        self.progress.start('sitecookie')
        for site in sites:
            if not site.get("signurl") and not site.get("rssurl"):
                log.info("【Sites】%s 未设置地址，跳过" % site.get("name"))
                continue
            log.info("【Sites】开始更新 %s Cookie和User-Agent ..." % site.get("name"))
            self.progress.update(ptype='sitecookie',
                                 text="开始更新 %s Cookie和User-Agent ..." % site.get("name"))
            # 登录页面地址
            scheme, netloc = StringUtils.get_url_netloc(site.get("signurl") or site.get("rssurl"))
            login_url = "%s://%s/login.php" % (scheme, netloc)
            # 获取Cookie和User-Agent
            cookie, ua, msg = self.__get_site_cookie_ua(url=login_url,
                                                        username=username,
                                                        password=password,
                                                        ocrflag=ocrflag,
                                                        chrome=chrome)
            # 更新进度
            curr_num += 1
            if not cookie:
                log.error("【Sites】获取 %s 信息失败：%s" % (site.get("name"), msg))
                messages.append("%s %s" % (site.get("name"), msg))
                self.progress.update(ptype='sitecookie',
                                     value=round(100 * (curr_num / site_num)),
                                     text="%s %s" % (site.get("name"), msg))
                retcode = 1
            else:
                self.dbhelpter.update_site_cookie_ua(site.get("id"), cookie, ua)
                log.info("【Sites】更新 %s 的Cookie和User-Agent成功" % site.get("name"))
                messages.append("%s 更新Cookie和User-Agent成功" % site.get("name"))
                self.progress.update(ptype='sitecookie',
                                     value=round(100 * (curr_num / site_num)),
                                     text="%s 更新Cookie和User-Agent成功" % site.get("name"))
        self.progress.end('sitecookie')
        return retcode, messages
