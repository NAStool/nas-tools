import os.path

from app.utils import SystemUtils
from app.utils.commons import singleton
from pyvirtualdisplay import Display
import undetected_chromedriver as uc

from app.utils.types import OsType


@singleton
class ChromeHelper(object):

    _default_options = uc.ChromeOptions()
    _executable_path = "/usr/lib/chromium/chromedriver"
    _chrome = None
    _display = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        if SystemUtils.get_system() == OsType.LINUX \
                and not os.path.exists(self._executable_path):
            return
        self._display = Display(visible=False, size=(1920, 1080))
        self._display.start()
        self._default_options.add_argument('--disable-gpu')
        self._default_options.add_argument('--no-sandbox')
        self._default_options.add_argument('--ignore-certificate-errors')
        self._chrome = uc.Chrome(options=self._default_options, driver_executable_path=self._executable_path)

    def get_browser(self):
        return self._chrome

    def __del__(self):
        self._chrome.quit()
        self._display.stop()

    @staticmethod
    def cookie_parse(cookies_str):
        if not cookies_str:
            return {}
        cookie_dict = {}
        cookies = cookies_str.split(';')
        for cookie in cookies:
            cstr = cookie.split('=')
            if len(cstr) > 1:
                cookie_dict[cstr[0]] = cstr[1]
        return cookie_dict
