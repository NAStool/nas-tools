import json

from app.helper import DictHelper
from app.utils.commons import singleton
from app.utils.types import SystemConfigKey


@singleton
class SystemConfig:
    # 系统设置
    systemconfig = {}

    def __init__(self):
        self.dicthelper = DictHelper()
        self.init_config()

    def init_config(self):
        """
        缓存系统设置
        """
        for item in self.dicthelper.list("SystemConfig"):
            if not item:
                continue
            if self.__is_obj(item.VALUE):
                self.systemconfig[item.KEY] = json.loads(item.VALUE)
            else:
                self.systemconfig[item.KEY] = item.VALUE

    @staticmethod
    def __is_obj(obj):
        if isinstance(obj, list) or isinstance(obj, dict):
            return True
        else:
            return str(obj).startswith("{") or str(obj).startswith("[")

    def set(self, key: [SystemConfigKey, str], value):
        """
        设置系统设置
        """
        if isinstance(key, SystemConfigKey):
            key = key.value
        # 更新内存
        self.systemconfig[key] = value
        # 写入数据库
        if self.__is_obj(value):
            if value is not None:
                value = json.dumps(value)
            else:
                value = ''
        self.dicthelper.set("SystemConfig", key, value)

    def get(self, key: [SystemConfigKey, str] = None):
        """
        获取系统设置
        """
        if not key:
            return self.systemconfig
        if isinstance(key, SystemConfigKey):
            key = key.value
        return self.systemconfig.get(key)
