import os

import log
from app.helper import SubmoduleHelper
from app.utils.commons import singleton


@singleton
class PluginManager:
    """
    插件管理器
    """
    # 插件列表
    _plugins = {}

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.load_plugins()
        self.run_plugins()

    def load_plugins(self):
        """
        加载所有插件
        """
        plugins = SubmoduleHelper.import_submodules(
            "app.plugins.modules",
            filter_func=lambda _, obj: hasattr(obj, 'module_name')
        )
        for plugin in plugins:
            module_name = getattr(plugin, "module_name")
            if not module_name:
                continue
            log.info(f"加载插件：{module_name}")
            self._plugins[module_name] = plugin

    def run_plugin(self, plugin_name, *args, **kwargs):
        """
        运行插件
        """
        if not self._plugins.get(plugin_name):
            return None
        return self._plugins[plugin_name](*args, **kwargs)

    def run_plugins(self, *args, **kwargs):
        """
        运行所有插件
        """
        for plugin in self._plugins.values():
            plugin(*args, **kwargs)
