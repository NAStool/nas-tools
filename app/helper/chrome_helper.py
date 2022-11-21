import json
import os.path
import tempfile
from functools import reduce
from threading import Lock

from app.utils import SystemUtils, RequestUtils
import undetected_chromedriver.v2 as uc

CHROME_LOCK = Lock()
lock = Lock()


class ChromeHelper(object):

    _executable_path = "/usr/lib/chromium/chromedriver" if SystemUtils.is_docker() else None
    _chrome = None
    _headless = False

    def __init__(self, headless=False):
        if not os.environ.get("NASTOOL_DISPLAY"):
            self._headless = True
        else:
            self._headless = headless

    @property
    def browser(self):
        with lock:
            if not self._chrome:
                self._chrome = self.__get_browser()
            return self._chrome

    def get_status(self):
        if self._executable_path \
                and os.path.exists(self._executable_path):
            return True
        return False

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
        options.add_argument('--no-first-run --no-service-autorun --password-store=basic')
        if self._headless:
            options.add_argument('--headless')
        prefs = {
            "useAutomationExtension": False,
            "excludeSwitches": ["enable-automation"]
        }
        options.add_experimental_option("prefs", prefs)
        chrome = ChromeWithPrefs(options=options, driver_executable_path=self._executable_path)
        chrome.set_page_load_timeout(30)
        return chrome

    def visit(self, url, ua=None, cookie=None):
        if not self.browser:
            return
        if ua:
            self.browser.execute_cdp_cmd("Emulation.setUserAgentOverride", {
                "userAgent": ua
            })
        self.browser.get(url)
        if cookie:
            self.browser.delete_all_cookies()
            for cookie in RequestUtils.cookie_parse(cookie, array=True):
                self.browser.add_cookie(cookie)
            self.browser.get(url)

    def get_title(self):
        if not self.browser:
            return ""
        return self.browser.title

    def get_html(self):
        if not self.browser:
            return ""
        return self.browser.page_source

    def get_cookies(self):
        if not self.browser:
            return ""
        cookie_str = ""
        for _cookie in self.browser.get_cookies():
            if not _cookie:
                continue
            cookie_str += "%s=%s;" % (_cookie.get("name"), _cookie.get("value"))
        return cookie_str

    def get_ua(self):
        return self.browser.execute_script("return navigator.userAgent")

    def __del__(self):
        if self._chrome:
            self._chrome.quit()


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

            # create an user_data_dir and add its path to the options
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
