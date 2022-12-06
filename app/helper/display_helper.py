import os

from pyvirtualdisplay import Display

from app.utils.commons import singleton


@singleton
class DisplayHelper(object):
    _display = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.quit()
        if self.can_display():
            os.environ["NASTOOL_DISPLAY"] = "YES"
            self._display = Display(visible=False, size=(1024, 768))
            self._display.start()

    def get_display(self):
        return self._display

    def quit(self):
        os.environ["NASTOOL_DISPLAY"] = ""
        if self._display:
            self._display.stop()

    @staticmethod
    def can_display():
        if os.path.exists("/usr/bin/Xvfb"):
            return True
        return False

    def __del__(self):
        self.quit()
