from app.helper import DictHelper
from app.utils.commons import singleton


@singleton
class SystemConfig:

    # 系统设置
    systemconfig = {
        "DefaultDownloadSetting": None
    }

    def __init__(self):
        self.init_config()

    def init_config(self):
        """
        缓存系统设置
        """
        for key, value in self.systemconfig.items():
            self.systemconfig[key] = DictHelper().get("SystemConfig", key)

    @staticmethod
    def set_system_config(key, value):
        """
        设置系统设置
        """
        return DictHelper().set("SystemConfig", key, value)

    def get_system_config(self, key=None):
        """
        获取系统设置
        """
        if not key:
            return self.systemconfig
        return self.systemconfig.get(key)
