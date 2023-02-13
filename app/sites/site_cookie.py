import base64
import time

from lxml import etree
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as es
from selenium.webdriver.support.wait import WebDriverWait

import log
from app.helper import ChromeHelper, ProgressHelper, DbHelper, OcrHelper, SiteHelper
from app.sites.sites import Sites
from app.conf import SiteConf
from app.utils import StringUtils, RequestUtils, ExceptionUtils
from app.utils.commons import singleton


@singleton
class SiteCookie(object):
    progress = None
    sites = None
    ocrhelper = None
    dbhelpter = None
    captcha_code = {}

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.dbhelpter = DbHelper()
        self.progress = ProgressHelper()
        self.sites = Sites()
        self.ocrhelper = OcrHelper()
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

    def __get_site_cookie_ua(self,
                             url,
                             username,
                             password,
                             twostepcode=None,
                             ocrflag=False):
        """
        获取站点cookie和ua
        :param url: 站点地址
        :param username: 用户名
        :param password: 密码
        :param twostepcode: 两步验证
        :param ocrflag: 是否开启OCR识别
        :return: cookie、ua、message
        """
        if not url or not username or not password:
            return None, None, "参数错误"
        # 全局锁
        chrome = ChromeHelper()
        if not chrome.get_status():
            return None, None, "需要浏览器内核环境才能更新站点信息"
        if not chrome.visit(url=url):
            return None, None, "Chrome模拟访问失败"
        # 循环检测是否过cf
        cloudflare = chrome.pass_cloudflare()
        if not cloudflare:
            return None, None, "跳转站点失败，无法通过Cloudflare验证"
        # 登录页面代码
        html_text = chrome.get_html()
        if not html_text:
            return None, None, "获取源码失败"
        if SiteHelper.is_logged_in(html_text):
            return chrome.get_cookies(), chrome.get_ua(), "已经登录过且Cookie未失效"
        # 查找用户名输入框
        html = etree.HTML(html_text)
        username_xpath = None
        for xpath in SiteConf.SITE_LOGIN_XPATH.get("username"):
            if html.xpath(xpath):
                username_xpath = xpath
                break
        if not username_xpath:
            return None, None, "未找到用户名输入框"
        # 查找密码输入框
        password_xpath = None
        for xpath in SiteConf.SITE_LOGIN_XPATH.get("password"):
            if html.xpath(xpath):
                password_xpath = xpath
                break
        if not password_xpath:
            return None, None, "未找到密码输入框"
        # 查找两步验证码
        twostepcode_xpath = None
        for xpath in SiteConf.SITE_LOGIN_XPATH.get("twostep"):
            if html.xpath(xpath):
                twostepcode_xpath = xpath
                break
        # 查找验证码输入框
        captcha_xpath = None
        for xpath in SiteConf.SITE_LOGIN_XPATH.get("captcha"):
            if html.xpath(xpath):
                captcha_xpath = xpath
                break
        # 查找验证码图片
        captcha_img_url = None
        if captcha_xpath:
            for xpath in SiteConf.SITE_LOGIN_XPATH.get("captcha_img"):
                if html.xpath(xpath):
                    captcha_img_url = html.xpath(xpath)[0]
                    break
            if not captcha_img_url:
                return None, None, "未找到验证码图片"
        # 查找登录按钮
        submit_xpath = None
        for xpath in SiteConf.SITE_LOGIN_XPATH.get("submit"):
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
                # 输入两步验证码
                if twostepcode and twostepcode_xpath:
                    twostepcode_element = chrome.browser.find_element(By.XPATH, twostepcode_xpath)
                    if twostepcode_element.is_displayed():
                        twostepcode_element.send_keys(twostepcode)
                # 识别验证码
                if captcha_xpath:
                    captcha_element = chrome.browser.find_element(By.XPATH, captcha_xpath)
                    if captcha_element.is_displayed():
                        code_url = self.__get_captcha_url(url, captcha_img_url)
                        if ocrflag:
                            # 自动OCR识别验证码
                            captcha = self.get_captcha_text(chrome, code_url)
                            if captcha:
                                log.info("【Sites】验证码地址为：%s，识别结果：%s" % (code_url, captcha))
                            else:
                                return None, None, "验证码识别失败"
                        else:
                            # 等待用户输入
                            captcha = None
                            code_key = StringUtils.generate_random_str(5)
                            for sec in range(30, 0, -1):
                                if self.get_code(code_key):
                                    # 用户输入了
                                    captcha = self.get_code(code_key)
                                    log.info("【Sites】接收到验证码：%s" % captcha)
                                    self.progress.update(ptype='sitecookie',
                                                         text="接收到验证码：%s" % captcha)
                                    break
                                else:
                                    # 获取验证码图片base64
                                    code_bin = self.get_captcha_base64(chrome, code_url)
                                    if not code_bin:
                                        return None, None, "获取验证码图片数据失败"
                                    else:
                                        code_bin = f"data:image/png;base64,{code_bin}"
                                    # 推送到前端
                                    self.progress.update(ptype='sitecookie',
                                                         text=f"{code_bin}|{code_key}")
                                    time.sleep(1)
                            if not captcha:
                                return None, None, "验证码输入超时"
                        # 输入验证码
                        captcha_element.send_keys(captcha)
                    else:
                        # 不可见元素不处理
                        pass
                # 提交登录
                submit_obj.click()
            else:
                return None, None, "未找到登录按钮"
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return None, None, "仿真登录失败：%s" % str(e)
        # 登录后的源码
        html_text = chrome.get_html()
        if not html_text:
            return None, None, "获取源码失败"
        if SiteHelper.is_logged_in(html_text):
            return chrome.get_cookies(), chrome.get_ua(), ""
        else:
            # 读取错误信息
            error_xpath = None
            for xpath in SiteConf.SITE_LOGIN_XPATH.get("error"):
                if html.xpath(xpath):
                    error_xpath = xpath
                    break
            if not error_xpath:
                return None, None, "登录失败"
            else:
                error_msg = html.xpath(error_xpath)[0]
                return None, None, error_msg

    def get_captcha_text(self, chrome, code_url):
        """
        识别验证码图片的内容
        """
        code_b64 = self.get_captcha_base64(chrome=chrome,
                                           image_url=code_url)
        if not code_b64:
            return ""
        return self.ocrhelper.get_captcha_text(image_b64=code_b64)

    @staticmethod
    def __get_captcha_url(siteurl, imageurl):
        """
        获取验证码图片的URL
        """
        if not siteurl or not imageurl:
            return ""
        if imageurl.startswith("/"):
            imageurl = imageurl[1:]
        return "%s/%s" % (StringUtils.get_base_url(siteurl), imageurl)

    def update_sites_cookie_ua(self,
                               username,
                               password,
                               twostepcode=None,
                               siteid=None,
                               ocrflag=False):
        """
        更新所有站点Cookie和ua
        """
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
            baisc_url = StringUtils.get_base_url(site.get("signurl") or site.get("rssurl"))
            site_conf = self.sites.get_grapsite_conf(url=baisc_url)
            if site_conf.get("LOGIN"):
                login_url = "%s/%s" % (baisc_url, site_conf.get("LOGIN"))
            else:
                login_url = "%s/login.php" % baisc_url
            # 获取Cookie和User-Agent
            cookie, ua, msg = self.__get_site_cookie_ua(url=login_url,
                                                        username=username,
                                                        password=password,
                                                        twostepcode=twostepcode,
                                                        ocrflag=ocrflag)
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
                messages.append("%s %s" % (site.get("name"), msg or "更新Cookie和User-Agent成功"))
                self.progress.update(ptype='sitecookie',
                                     value=round(100 * (curr_num / site_num)),
                                     text="%s %s" % (site.get("name"), msg or "更新Cookie和User-Agent成功"))
        self.progress.end('sitecookie')
        return retcode, messages

    @staticmethod
    def get_captcha_base64(chrome, image_url):
        """
        根据图片地址，获取验证码图片base64编码
        """
        if not image_url:
            return ""
        ret = RequestUtils(headers=chrome.get_ua(),
                           cookies=chrome.get_cookies()).get_res(image_url)
        if ret:
            return base64.b64encode(ret.content).decode()
        return ""
