from app.conf.moduleconf import ModuleConf
from app.utils.types import *
from app.utils.commons import singleton


@singleton
class KVPrUtils:

    RMT_MODES_REVERSE = {}
    RmtMode_REVERSE = {}

    def __init__(self):
        self.init_config()

    def init_config(self):
        # 初始化反查
        self.RMT_MODES_REVERSE = self.__gen_dict_reverse(ModuleConf.RMT_MODES)
        self.RmtMode_REVERSE = self.__gen_enum_reverse(RmtMode)

    @staticmethod
    def __gen_dict_reverse(d: dict):
        return {v: k for k, v in d.items()}

    @staticmethod
    def __gen_enum_reverse(enum):
        return {e.value: e for e in enum}

