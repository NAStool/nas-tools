import os.path

from app.utils import SystemUtils
from app.utils.commons import singleton
from pyvirtualdisplay import Display
import undetected_chromedriver as uc

from app.utils.types import OsType


@singleton
class ChromeHelper(object):

    _executable_path = "/usr/lib/chromium/chromedriver" if SystemUtils.get_system() == OsType.LINUX else None
    _chrome = None
    _display = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        if SystemUtils.get_system() == OsType.LINUX \
                and self._executable_path \
                and not os.path.exists(self._executable_path):
            return
        if SystemUtils.get_system() == OsType.LINUX:
            self._display = Display(visible=False, size=(1920, 1080))
            self._display.start()
        options = uc.ChromeOptions()
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        self._chrome = uc.Chrome(options=options, driver_executable_path=self._executable_path)

    def get_browser(self):
        self.check_browser()
        return self._chrome

    def check_browser(self):
        if self._chrome:
            try:
                self._chrome.execute_script('javascript:void(0);')
            except Exception as e:
                self.init_config()

    def __del__(self):
        if self._chrome:
            self._chrome.quit()
        if self._display:
            self._display.stop()
