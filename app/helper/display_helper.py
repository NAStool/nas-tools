import os

from pyvirtualdisplay import Display

from app.utils.commons import singleton
from app.utils import ExceptionUtils
from config import XVFB_PATH


@singleton
class DisplayHelper(object):
    _display = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.quit()
        if self.can_display():
            try:
                self._display = Display(visible=False, size=(1024, 768))
                self._display.start()
                os.environ["NASTOOL_DISPLAY"] = "true"
            except Exception as err:
                ExceptionUtils.exception_traceback(err)

    def get_display(self):
        return self._display

    def quit(self):
        os.environ["NASTOOL_DISPLAY"] = ""
        if self._display:
            self._display.stop()

    @staticmethod
    def can_display():
        for path in XVFB_PATH:
            if os.path.exists(path):
                return True
        return False

    def __del__(self):
        self.quit()
