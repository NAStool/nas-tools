import json

from app.helper import DictHelper
from app.utils.commons import singleton


@singleton
class SystemConfig:

    # 系统设置
    systemconfig = {
        # 默认下载设置
        "DefaultDownloadSetting": None,
        # CookieCloud的设置
        "CookieCloud": {},
        # 自动获取Cookie的用户信息
        "CookieUserInfo": {},
        # 用户自定义CSS/JavsScript
        "CustomScript": {},
        # 播放限速设置
        "SpeedLimit": {}
    }

    def __init__(self):
        self.init_config()

    def init_config(self, key=None):
        """
        缓存系统设置
        """
        def __set_value(_key, _value):
            if isinstance(_value, dict) \
                    or isinstance(_value, list):
                dict_value = DictHelper().get("SystemConfig", _key)
                if dict_value:
                    self.systemconfig[_key] = json.loads(dict_value)
                else:
                    self.systemconfig[_key] = {}
            else:
                self.systemconfig[_key] = DictHelper().get("SystemConfig", _key)

        if key:
            __set_value(key, self.systemconfig.get(key))
        else:
            for key, value in self.systemconfig.items():
                __set_value(key, value)

    def set_system_config(self, key, value):
        """
        设置系统设置
        """
        if isinstance(value, dict) \
                or isinstance(value, list):
            if value:
                value = json.dumps(value)
            else:
                value = None
        DictHelper().set("SystemConfig", key, value)
        self.init_config(key)

    def get_system_config(self, key=None):
        """
        获取系统设置
        """
        if not key:
            return self.systemconfig
        return self.systemconfig.get(key)
