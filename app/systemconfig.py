from app.helper import DictHelper


class SystemConfig:

    _dict = DictHelper()

    default_download_setting = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        # 缓存系统设置
        self.default_download_setting = self._dict.get("SystemConfig", "DefaultDownloadSetting")

    def set_system_config(self, key, value):
        return self._dict.set("SystemConfig", key, value)
