import json
import os.path
import tempfile
from functools import reduce
from threading import Lock

import undetected_chromedriver as uc
from webdriver_manager.chrome import ChromeDriverManager

import app.helper.cloudflare_helper as CloudflareHelper
from app.utils import SystemUtils, RequestUtils
from config import Config

lock = Lock()

driver_executable_path = None


class ChromeHelper(object):
    _executable_path = None

    _chrome = None
    _headless = False

    _proxy = None

    def __init__(self, headless=False):

        self._executable_path = SystemUtils.get_webdriver_path() or driver_executable_path

        if SystemUtils.is_windows() or SystemUtils.is_macos():
            self._headless = False
        elif not os.environ.get("NASTOOL_DISPLAY"):
            self._headless = True
        else:
            self._headless = headless

    def init_driver(self):
        if self._executable_path:
            return
        if not uc.find_chrome_executable():
            return
        global driver_executable_path
        driver_executable_path = ChromeDriverManager().install()

    @property
    def browser(self):
        with lock:
            if not self._chrome:
                self._chrome = self.__get_browser()
            return self._chrome

    def get_status(self):
        if self._executable_path \
                and not os.path.exists(self._executable_path):
            return False
        if not uc.find_chrome_executable():
            return False
        return True

    def __get_browser(self):
        if not self.get_status():
            return None
        options = uc.ChromeOptions()
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins-discovery")
        options.add_argument('--no-first-run')
        options.add_argument('--no-service-autorun')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--password-store=basic')
        if SystemUtils.is_windows() or SystemUtils.is_macos():
            options.add_argument("--window-position=-32000,-32000")
        if self._proxy:
            proxy = Config().get_proxies().get("https")
            if proxy:
                proxy = proxy.split('/')[-1]
            options.add_argument('--proxy-server=%s' % proxy or '')
        if self._headless:
            options.add_argument('--headless')
        prefs = {
            "useAutomationExtension": False,
            "profile.managed_default_content_settings.images": 2 if self._headless else 1,
            "excludeSwitches": ["enable-automation"]
        }
        options.add_argument('−−lang=zh-CN')
        options.add_experimental_option("prefs", prefs)
        chrome = ChromeWithPrefs(options=options, driver_executable_path=self._executable_path)
        chrome.set_page_load_timeout(30)
        return chrome

    def visit(self, url, ua=None, cookie=None, timeout=30, proxy=None):
        self._proxy = proxy
        if not self.browser:
            return False
        try:
            if ua:
                self._chrome.execute_cdp_cmd("Emulation.setUserAgentOverride", {
                    "userAgent": ua
                })
            if timeout:
                self._chrome.implicitly_wait(timeout)
            self._chrome.get(url)
            if cookie:
                self._chrome.delete_all_cookies()
                for cookie in RequestUtils.cookie_parse(cookie, array=True):
                    self._chrome.add_cookie(cookie)
                self._chrome.get(url)
            return True
        except Exception as err:
            print(str(err))
            return False

    def new_tab(self, url, ua=None, cookie=None):
        if not self._chrome:
            return False
        # 新开一个标签页
        try:
            self._chrome.switch_to.new_window('tab')
        except Exception as err:
            print(str(err))
            return False
        # 访问URL
        return self.visit(url=url, ua=ua, cookie=cookie)

    def close_tab(self):
        try:
            self._chrome.close()
            self._chrome.switch_to.window(self._chrome.window_handles[0])
        except Exception as err:
            print(str(err))
            return False

    def pass_cloudflare(self):
        challenge = CloudflareHelper.resolve_challenge(driver=self._chrome)
        return challenge

    def execute_script(self, script):
        if not self._chrome:
            return False
        try:
            return self._chrome.execute_script(script)
        except Exception as err:
            print(str(err))

    def get_title(self):
        if not self._chrome:
            return ""
        return self._chrome.title

    def get_html(self):
        if not self._chrome:
            return ""
        return self._chrome.page_source

    def get_cookies(self):
        if not self._chrome:
            return ""
        cookie_str = ""
        try:
            for _cookie in self._chrome.get_cookies():
                if not _cookie:
                    continue
                cookie_str += "%s=%s;" % (_cookie.get("name"), _cookie.get("value"))
        except Exception as err:
            print(str(err))
        return cookie_str

    def get_ua(self):
        try:
            return self._chrome.execute_script("return navigator.userAgent")
        except Exception as err:
            print(str(err))
            return None

    def quit(self):
        if self._chrome:
            self._chrome.close()
            self._chrome.quit()
            self._fixup_uc_pid_leak()
            self._chrome = None

    def _fixup_uc_pid_leak(self):
        """
        uc 在处理退出时为强制kill进程，没有调用wait，会导致出现僵尸进程，此处增加wait，确保系统正常回收
        :return:
        """
        try:
            # chromedriver 进程
            if hasattr(self._chrome, "service") and getattr(self._chrome.service, "process", None):
                self._chrome.service.process.wait(3)
            # chrome 进程
            os.waitpid(self._chrome.browser_pid, 0)
        except Exception as e:
            print(str(e))
            pass

    def __del__(self):
        self.quit()


class ChromeWithPrefs(uc.Chrome):
    def __init__(self, *args, options=None, **kwargs):
        if options:
            self._handle_prefs(options)
        super().__init__(*args, options=options, **kwargs)
        # remove the user_data_dir when quitting
        self.keep_user_data_dir = False

    @staticmethod
    def _handle_prefs(options):
        if prefs := options.experimental_options.get("prefs"):
            # turn a (dotted key, value) into a proper nested dict
            def undot_key(key, value):
                if "." in key:
                    key, rest = key.split(".", 1)
                    value = undot_key(rest, value)
                return {key: value}

            # undot prefs dict keys
            undot_prefs = reduce(
                lambda d1, d2: {**d1, **d2},  # merge dicts
                (undot_key(key, value) for key, value in prefs.items()),
            )

            # create a user_data_dir and add its path to the options
            user_data_dir = os.path.normpath(tempfile.mkdtemp())
            options.add_argument(f"--user-data-dir={user_data_dir}")

            # create the preferences json file in its default directory
            default_dir = os.path.join(user_data_dir, "Default")
            os.mkdir(default_dir)

            prefs_file = os.path.join(default_dir, "Preferences")
            with open(prefs_file, encoding="latin1", mode="w") as f:
                json.dump(undot_prefs, f)

            # pylint: disable=protected-access
            # remove the experimental_options to avoid an error
            del options._experimental_options["prefs"]


def init_chrome():
    """
    初始化chrome驱动
    """
    ChromeHelper().init_driver()
