import json
import os.path
import tempfile
from functools import reduce
from threading import Lock

from app.utils import SystemUtils, RequestUtils
from app.utils.commons import singleton
import undetected_chromedriver.v2 as uc

from app.utils.types import OsType
from config import Config

CHROME_LOCK = Lock()


@singleton
class ChromeHelper(object):

    _executable_path = "/usr/lib/chromium/chromedriver" if SystemUtils.is_docker() else None
    _chrome = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        if self._chrome:
            self._chrome.quit()
            self._chrome = None
        if not Config().get_config('laboratory').get('chrome_browser'):
            return
        if SystemUtils.get_system() == OsType.LINUX \
                and self._executable_path \
                and not os.path.exists(self._executable_path):
            return
        options = uc.ChromeOptions()
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument('--no-first-run --no-service-autorun --password-store=basic')
        if not os.environ.get("NASTOOL_DISPLAY"):
            options.add_argument('--headless')
        prefs = {
            "useAutomationExtension": False,
            "excludeSwitches": ["enable-automation"]
        }
        options.add_experimental_option("prefs", prefs)
        self._chrome = ChromeWithPrefs(options=options, driver_executable_path=self._executable_path)
        self._chrome.set_page_load_timeout(30)

    def get_browser(self):
        return self._chrome

    def visit(self, url, ua=None, cookie=None):
        if ua:
            self._chrome.execute_cdp_cmd("Emulation.setUserAgentOverride", {
                "userAgent": ua
            })
        self._chrome.get(url)
        if cookie:
            self._chrome.delete_all_cookies()
            for cookie in RequestUtils.cookie_parse(cookie, array=True):
                self._chrome.add_cookie(cookie)
            self._chrome.get(url)

    def get_title(self):
        return self._chrome.title

    def get_html(self):
        return self._chrome.page_source

    def get_cookies(self):
        cookie_str = ""
        for _cookie in self._chrome.get_cookies():
            if not _cookie:
                continue
            cookie_str += "%s=%s;" % (_cookie.get("name"), _cookie.get("value"))
        return cookie_str

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
