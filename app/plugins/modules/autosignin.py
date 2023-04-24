import re
import time
from datetime import datetime, timedelta
from multiprocessing.dummy import Pool as ThreadPool
from multiprocessing.pool import ThreadPool

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from lxml import etree
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as es
from selenium.webdriver.support.wait import WebDriverWait

from app.helper import ChromeHelper, SubmoduleHelper, SiteHelper
from app.helper.cloudflare_helper import under_challenge
from app.message import Message
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.sites.siteconf import SiteConf
from app.sites.sites import Sites
from app.utils import RequestUtils, ExceptionUtils, StringUtils
from app.utils.types import EventType
from config import Config


class AutoSignIn(_IPluginModule):
    # 插件名称
    module_name = "站点自动签到"
    # 插件描述
    module_desc = "站点自动签到保号，支持重试。"
    # 插件图标
    module_icon = "signin.png"
    # 主题色
    module_color = "#4179F4"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "thsrite"
    # 作者主页
    author_url = "https://github.com/thsrite"
    # 插件配置项ID前缀
    module_config_prefix = "autosignin_"
    # 加载顺序
    module_order = 0
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    siteconf = None
    _scheduler = None

    # 设置开关
    _enabled = False
    # 任务执行间隔
    _site_schema = []
    _cron = None
    _sign_sites = None
    _queue_cnt = None
    _retry_keyword = None
    _special_sites = None
    _onlyonce = False
    _notify = False

    @staticmethod
    def get_fields():
        sites = {site.get("id"): site for site in Sites().get_site_dict()}
        return [
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '开启定时签到',
                            'required': "",
                            'tooltip': '开启后会根据周期定时签到指定站点。',
                            'type': 'switch',
                            'id': 'enabled',
                        },
                        {
                            'title': '运行时通知',
                            'required': "",
                            'tooltip': '运行签到任务后会发送通知（需要打开插件消息通知）',
                            'type': 'switch',
                            'id': 'notify',
                        },
                        {
                            'title': '立即运行一次',
                            'required': "",
                            'tooltip': '打开后立即运行一次',
                            'type': 'switch',
                            'id': 'onlyonce',
                        }
                    ]
                ]
            },
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '签到周期',
                            'required': "",
                            'tooltip': '设置自动签到时间周期，支持5位cron表达式',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'cron',
                                    'placeholder': '0 0 0 ? *',
                                }
                            ]
                        },
                        {
                            'title': '签到队列',
                            'required': "",
                            'tooltip': '签到队列数量，默认10',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'queue_cnt',
                                    'placeholder': '10',
                                }
                            ]
                        },
                        {
                            'title': '重试关键词',
                            'required': "",
                            'tooltip': '重新签到关键词，支持正则表达式',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'retry_keyword',
                                    'placeholder': '失败|错误',
                                }
                            ]
                        },
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '签到站点',
                'tooltip': '只有选中的站点才会执行签到任务，不选则默认为全选',
                'content': [
                    # 同一行
                    [
                        {
                            'id': 'sign_sites',
                            'type': 'form-selectgroup',
                            'content': sites
                        },
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '特殊站点',
                'tooltip': '选中的站点无论是否匹配重试关键词都会进行重签',
                'content': [
                    # 同一行
                    [
                        {
                            'id': 'special_sites',
                            'type': 'form-selectgroup',
                            'content': sites
                        },
                    ]
                ]
            },
        ]

    def init_config(self, config=None):
        self.siteconf = SiteConf()

        # 读取配置
        if config:
            self._enabled = config.get("enabled")
            self._cron = config.get("cron")
            self._retry_keyword = config.get("retry_keyword")
            self._sign_sites = config.get("sign_sites")
            self._special_sites = config.get("special_sites") or []
            self._notify = config.get("notify")
            self._queue_cnt = config.get("queue_cnt")
            self._onlyonce = config.get("onlyonce")

        # 启动服务
        if self._enabled or self._onlyonce:
            # 加载模块
            self._site_schema = SubmoduleHelper.import_submodules('app.plugins.modules._autosignin',
                                                                  filter_func=lambda _, obj: hasattr(obj, 'match'))
            self.debug(f"加载站点签到：{self._site_schema}")

            # 定时服务
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())

            # 运行一次
            if self._onlyonce:
                self.info(f"签到服务启动，立即运行一次")
                self._scheduler.add_job(self.__sign_in, 'date',
                                        run_date=datetime.now(tz=pytz.timezone(Config().get_timezone())))
                # 关闭一次性开关
                self._onlyonce = False
                self.update_config({
                    "enabled": self._enabled,
                    "cron": self._cron,
                    "retry_keyword": self._retry_keyword,
                    "sign_sites": self._sign_sites,
                    "special_sites": self._special_sites,
                    "notify": self._notify,
                    "onlyonce": self._onlyonce,
                    "queue_cnt": self._queue_cnt,
                })

            # 周期运行
            if self._cron:
                self.info(f"定时签到服务启动，周期：{self._cron}")
                self._scheduler.add_job(self.__sign_in,
                                        CronTrigger.from_crontab(self._cron))

            # 启动任务
            if self._scheduler.get_jobs():
                self._scheduler.print_jobs()
                self._scheduler.start()

    @EventHandler.register(EventType.SiteSignin)
    def __sign_in(self, event=None):
        """
        自动签到
        """
        # 日期
        today = datetime.today()
        yesterday = today - timedelta(days=1)
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        # 删除昨天历史
        self.delete_history(yesterday_str)

        # 查看今天有没有签到历史
        today = today.strftime('%Y-%m-%d')
        today_history = self.get_history(key=today)
        if not today_history:
            sign_sites = self._sign_sites
            self.info(f"今日 {today} 未签到，开始签到已选站点")
        else:
            # 根据重试关键词查找重签站点
            sign_sites = today_history if isinstance(today_history, list) else [today_history]
            if sign_sites:
                self.info(f"今日 {today} 已签到，开始重签重试站点及特殊站点")
            else:
                self.info(f"今日 {today} 已签到，无重新签到站点")
                return

        # 查询签到站点
        sites = Sites().get_sites(siteids=sign_sites)
        if not sites:
            self.info("没有可签到站点，停止运行")
            return

        # 执行签到
        self.info("开始执行签到任务")
        with ThreadPool(min(len(sites), int(self._queue_cnt) or 10)) as p:
            status = p.map(self.signin_site, sites)

        if status:
            # 签到详细信息
            Message().send_site_signin_message(status)
            self.info("站点签到任务完成！")

            retry_sites = []
            # 记录本次命中重试关键词的站点
            if self._retry_keyword:
                sites = {site.get('name'): site.get("id") for site in Sites().get_site_dict()}
                for s in status:
                    match = re.search(self._retry_keyword, s)
                    if match:
                        result = re.findall(r'【(.*?)】', s)
                        if result:
                            site_id = sites.get(result[0])
                            if site_id:
                                self.debug(f"站点 {result[0]} 命中重试关键词 {self._retry_keyword}")
                                retry_sites.append(str(site_id))

                # 签到站点加入特殊站点
                retry_sites = retry_sites + self._special_sites
                # 站点去重
                if retry_sites:
                    retry_sites = list(set(retry_sites))
            else:
                # 没设置重试关键词则重试已选站点
                retry_sites = self._sign_sites
            self.debug(f"下次签到重试站点 {retry_sites}")

            # 存入历史
            if not today_history:
                self.history(today, retry_sites)
            else:
                self.update_history(today, retry_sites)

                # 发送通知
                if self._notify:
                    # 签到汇总信息
                    self.send_message(title="【自动签到任务完成】",
                                      text=f"本次签到站点数量: {len(sites)} \n"
                                           f"下次签到数量: {len(retry_sites)} \n"
                                           f"详见签到消息")
        else:
            self.error("站点签到任务失败！")

    def __build_class(self, url):
        for site_schema in self._site_schema:
            try:
                if site_schema.match(url):
                    return site_schema
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
        return None
            
    def signin_site(self, site_info):
        """
        签到一个站点
        """
        site_module = self.__build_class(site_info.get("signurl"))
        if site_module and hasattr(site_module, "signin"):
            try:
                status, msg = site_module().signin(site_info)
                # 特殊站点直接返回签到信息，防止仿真签到、模拟登陆有歧义
                return msg
            except Exception as e:
                return f"【{site_info.get('name')}】签到失败：{str(e)}"
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
                self.warn("未配置 %s 的站点地址或Cookie，无法签到" % str(site))
                return ""
            chrome = ChromeHelper()
            if site_info.get("chrome") and chrome.get_status():
                # 首页
                self.info("开始站点仿真签到：%s" % site)
                home_url = StringUtils.get_base_url(site_url)
                if not chrome.visit(url=home_url, ua=ua, cookie=site_cookie, proxy=site_info.get("proxy")):
                    self.warn("%s 无法打开网站" % site)
                    return f"【{site}】无法打开网站！"
                # 循环检测是否过cf
                cloudflare = chrome.pass_cloudflare()
                if not cloudflare:
                    self.warn("%s 跳转站点失败" % site)
                    return f"【{site}】跳转站点失败！"
                # 判断是否已签到
                html_text = chrome.get_html()
                if not html_text:
                    self.warn("%s 获取站点源码失败" % site)
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
                    self.info("%s 今日已签到" % site)
                    return f"【{site}】今日已签到"
                if not xpath_str:
                    if SiteHelper.is_logged_in(html_text):
                        self.warn("%s 未找到签到按钮，模拟登录成功" % site)
                        return f"【{site}】模拟登录成功"
                    else:
                        self.info("%s 未找到签到按钮，且模拟登录失败" % site)
                        return f"【{site}】模拟登录失败！"
                # 开始仿真
                try:
                    checkin_obj = WebDriverWait(driver=chrome.browser, timeout=6).until(
                        es.element_to_be_clickable((By.XPATH, xpath_str)))
                    if checkin_obj:
                        checkin_obj.click()
                        # 检测是否过cf
                        time.sleep(3)
                        if under_challenge(chrome.get_html()):
                            cloudflare = chrome.pass_cloudflare()
                            if not cloudflare:
                                self.info("%s 仿真签到失败，无法通过Cloudflare" % site)
                                return f"【{site}】仿真签到失败，无法通过Cloudflare！"
                        self.info("%s 仿真签到成功" % site)
                        return f"【{site}】仿真签到成功"
                except Exception as e:
                    ExceptionUtils.exception_traceback(e)
                    self.warn("%s 仿真签到失败：%s" % (site, str(e)))
                    return f"【{site}】签到失败！"
            # 模拟登录
            else:
                if site_url.find("attendance.php") != -1:
                    checkin_text = "签到"
                else:
                    checkin_text = "模拟登录"
                self.info(f"开始站点{checkin_text}：{site}")
                # 访问链接
                res = RequestUtils(cookies=site_cookie,
                                   headers=ua,
                                   proxies=Config().get_proxies() if site_info.get("proxy") else None
                                   ).get_res(url=site_url)
                if res and res.status_code in [200, 500, 403]:
                    if not SiteHelper.is_logged_in(res.text):
                        if under_challenge(res.text):
                            msg = "站点被Cloudflare防护，请开启浏览器仿真"
                        elif res.status_code == 200:
                            msg = "Cookie已失效"
                        else:
                            msg = f"状态码：{res.status_code}"
                        self.warn(f"{site} {checkin_text}失败，{msg}")
                        return f"【{site}】{checkin_text}失败，{msg}！"
                    else:
                        self.info(f"{site} {checkin_text}成功")
                        return f"【{site}】{checkin_text}成功"
                elif res is not None:
                    self.warn(f"{site} {checkin_text}失败，状态码：{res.status_code}")
                    return f"【{site}】{checkin_text}失败，状态码：{res.status_code}！"
                else:
                    self.warn(f"{site} {checkin_text}失败，无法打开网站")
                    return f"【{site}】{checkin_text}失败，无法打开网站！"
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            self.warn("%s 签到出错：%s" % (site, str(e)))
            return f"{site} 签到出错：{str(e)}！"

    def stop_service(self):
        pass

    def get_state(self):
        return self._enabled and self._cron
