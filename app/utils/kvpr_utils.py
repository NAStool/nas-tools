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
        self.RMT_MODES_REVERSE = {v: k for k, v in ModuleConf.RMT_MODES.items()}
        self.RmtMode_REVERSE = {e.value: e for e in RmtMode}
