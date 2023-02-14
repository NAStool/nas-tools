from abc import ABCMeta, abstractmethod


class _IPluginModule(metaclass=ABCMeta):
    """
    插件模块基类
    """
    # 插件ID
    module_id = ""
    # 插件名称
    module_name = ""
    # 插件描述
    module_desc = ""
    # 插件图标
    module_icon = ""
    # 主题色
    module_color = ""
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = ""

    @staticmethod
    @abstractmethod
    def get_fields():
        """
        获取配置字典，用于生成表单
        """
        pass

    @abstractmethod
    def init_config(self, conf: dict):
        """
        生效配置信息
        :param conf: 配置信息字典
        """
        pass

    @abstractmethod
    def stop_service(self):
        """
        停止插件
        """
        pass
