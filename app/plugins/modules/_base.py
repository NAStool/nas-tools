from abc import ABCMeta, abstractmethod

from app.conf import SystemConfig


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
    # 主题色
    module_color = ""
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = ""
    # 插件配置项ID前缀：为了避免各插件配置表单相冲突，配置表单元素ID自动在前面加上此前缀
    module_config_prefix = "plugin_"
    # 显示顺序
    module_order = 0
    # 可使用的用户级别
    auth_level = 1

    @staticmethod
    @abstractmethod
    def get_fields():
        """
        获取配置字典，用于生成表单
        """
        pass

    @abstractmethod
    def get_state(self):
        """
        获取插件启用状态
        """
        pass

    @abstractmethod
    def init_config(self, config: dict):
        """
        生效配置信息
        :param config: 配置信息字典
        """
        pass

    @abstractmethod
    def stop_service(self):
        """
        停止插件
        """
        pass

    def update_config(self, config: dict):
        """
        更新配置信息
        :param config: 配置信息字典
        """
        return SystemConfig().set_system_config("plugin.%s" % self.__class__.__name__, config)
