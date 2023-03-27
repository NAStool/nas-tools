import re
from multiprocessing.dummy import Pool as ThreadPool
from threading import Lock

from lxml import etree
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as es
from selenium.webdriver.support.wait import WebDriverWait

import log
from app.helper import ChromeHelper, SubmoduleHelper, DbHelper, SiteHelper
from app.message import Message
from app.sites.siteconf import SiteConf
from app.sites.sites import Sites
from app.utils import RequestUtils, ExceptionUtils, StringUtils
from app.utils.commons import singleton
from config import Config

lock = Lock()


@singleton
class SiteSignin(object):
    sites = None
    dbhelper = None
    message = None
    siteconf = None

    _MAX_CONCURRENCY = 10

    def __init__(self):
        # 加载模块
        self._site_schema = SubmoduleHelper.import_submodules('app.sites.sitesignin',
                                                              filter_func=lambda _, obj: hasattr(obj, 'match'))
        log.debug(f"【Sites】加载站点签到：{self._site_schema}")
        self.init_config()

    def init_config(self):
        self.sites = Sites()
        self.dbhelper = DbHelper()
        self.message = Message()
        self.siteconf = SiteConf()

    def __build_class(self, url):
        for site_schema in self._site_schema:
            try:
                if site_schema.match(url):
                    return site_schema
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
        return None

    def signin(self):
        """
        站点并发签到
        """
        sites = self.sites.get_sites(signin=True)
        if not sites:
            return
        with ThreadPool(min(len(sites), self._MAX_CONCURRENCY)) as p:
            status = p.map(self.__signin_site, sites)
        if status:
            self.message.send_site_signin_message(status)

    def __signin_site(self, site_info):
        """
        签到一个站点
        """
        site_module = self.__build_class(site_info.get("signurl"))
        if site_module:
            return site_module.signin(site_info)
        else:
            return self.__signin_base(site_info)

    def __signin_base(self, site_info):
        """
        通用签到处理
        :param site_info: 站点信息
        :return: 签到结果信息
        """
        if not site_info:
            return ""
        site = site_info.get("name")
        try:
            site_url = site_info.get("signurl")
            site_cookie = site_info.get("cookie")
            ua = site_info.get("ua")
            if not site_url or not site_cookie:
                log.warn("【Sites】未配置 %s 的站点地址或Cookie，无法签到" % str(site))
                return ""
            chrome = ChromeHelper()
            if site_info.get("chrome") and chrome.get_status():
                # 首页
                log.info("【Sites】开始站点仿真签到：%s" % site)
                home_url = StringUtils.get_base_url(site_url)
                if not chrome.visit(url=home_url, ua=ua, cookie=site_cookie, proxy=site_info.get("proxy")):
                    log.warn("【Sites】%s 无法打开网站" % site)
                    return f"【{site}】无法打开网站！"
                # 循环检测是否过cf
                cloudflare = chrome.pass_cloudflare()
                if not cloudflare:
                    log.warn("【Sites】%s 跳转站点失败" % site)
                    return f"【{site}】跳转站点失败！"
                # 判断是否已签到
                html_text = chrome.get_html()
                if not html_text:
                    log.warn("【Sites】%s 获取站点源码失败" % site)
                    return f"【{site}】获取站点源码失败！"
                # 查找签到按钮
                html = etree.HTML(html_text)
                xpath_str = None
                for xpath in self.siteconf.get_checkin_conf():
                    if html.xpath(xpath):
                        xpath_str = xpath
                        break
                if re.search(r'已签|签到已得', html_text, re.IGNORECASE) \
                        and not xpath_str:
                    log.info("【Sites】%s 今日已签到" % site)
                    return f"【{site}】今日已签到"
                if not xpath_str:
                    if SiteHelper.is_logged_in(html_text):
                        log.warn("【Sites】%s 未找到签到按钮，模拟登录成功" % site)
                        return f"【{site}】模拟登录成功"
                    else:
                        log.info("【Sites】%s 未找到签到按钮，且模拟登录失败" % site)
                        return f"【{site}】模拟登录失败！"
                # 开始仿真
                try:
                    checkin_obj = WebDriverWait(driver=chrome.browser, timeout=6).until(
                        es.element_to_be_clickable((By.XPATH, xpath_str)))
                    if checkin_obj:
                        checkin_obj.click()
                        log.info("【Sites】%s 仿真签到成功" % site)
                        return f"【{site}】仿真签到成功"
                except Exception as e:
                    ExceptionUtils.exception_traceback(e)
                    log.warn("【Sites】%s 仿真签到失败：%s" % (site, str(e)))
                    return f"【{site}】签到失败！"
            # 模拟登录
            else:
                if site_url.find("attendance.php") != -1:
                    checkin_text = "签到"
                else:
                    checkin_text = "模拟登录"
                log.info(f"【Sites】开始站点{checkin_text}：{site}")
                # 访问链接
                res = RequestUtils(cookies=site_cookie,
                                   headers=ua,
                                   proxies=Config().get_proxies() if site_info.get("proxy") else None
                                   ).get_res(url=site_url)
                if res and res.status_code == 200:
                    if not SiteHelper.is_logged_in(res.text):
                        log.warn(f"【Sites】{site} {checkin_text}失败，请检查Cookie")
                        return f"【{site}】{checkin_text}失败，请检查Cookie！"
                    else:
                        log.info(f"【Sites】{site} {checkin_text}成功")
                        return f"【{site}】{checkin_text}成功"
                elif res is not None:
                    log.warn(f"【Sites】{site} {checkin_text}失败，状态码：{res.status_code}")
                    return f"【{site}】{checkin_text}失败，状态码：{res.status_code}！"
                else:
                    log.warn(f"【Sites】{site} {checkin_text}失败，无法打开网站")
                    return f"【{site}】{checkin_text}失败，无法打开网站！"
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.warn("【Sites】%s 签到出错：%s" % (site, str(e)))
            return f"{site} 签到出错：{str(e)}！"
