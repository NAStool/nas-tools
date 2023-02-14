from abc import ABCMeta, abstractmethod


class _IPluginModule(metaclass=ABCMeta):
    """
    插件模块基类
    """

    # 插件名称
    module_name = ""
    # 插件描述
    module_desc = ""
    # 插件图标
    module_icon = ""
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = ""

    @abstractmethod
    def get_fields(self, ctype):
        """
        获取配置字典，用于生成表单
        """
        pass

    @abstractmethod
    def save_config(self, conf):
        """
        保存配置信息，可通过SystemConfig保存配置数据
        :param conf: 配置信息
        :return:
        """
        pass
