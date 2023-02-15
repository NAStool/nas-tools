import json

import log
from app.conf import SystemConfig
from app.helper import SubmoduleHelper
from app.utils.commons import singleton


@singleton
class PluginManager:
    """
    插件管理器
    """
    systemconfig = None

    # 插件列表
    _plugins = {}
    # 运行态插件列表
    _running_plugins = {}

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.systemconfig = SystemConfig()
        self.load_plugins()
        self.run_plugins()

    def load_plugins(self):
        """
        加载所有插件
        """
        plugins = SubmoduleHelper.import_submodules(
            "app.plugins.modules",
            filter_func=lambda _, obj: hasattr(obj, 'module_id')
        )
        for plugin in plugins:
            module_id = getattr(plugin, "module_id")
            if not module_id:
                continue
            log.info(f"加载插件：{module_id}")
            self._plugins[module_id] = plugin

    def run_plugin(self, pid, *args, **kwargs):
        """
        运行插件
        """
        if not self._plugins.get(pid):
            return None
        return self._plugins[pid](*args, **kwargs)

    def run_plugins(self, *args, **kwargs):
        """
        运行所有插件
        """
        for pid, plugin in self._plugins.items():
            self._running_plugins[pid] = self.run_plugin(pid, *args, **kwargs)
            self.reload_plugin(pid)

    def reload_plugin(self, pid):
        if not self._running_plugins.get(pid):
            return
        if hasattr(self._running_plugins[pid], "init_config"):
            self._running_plugins[pid].init_config(self.get_plugin_config(pid))

    def stop_plugins(self):
        """
        停止所有插件
        """
        for plugin in self._running_plugins.values():
            if hasattr(plugin, "stop_service"):
                plugin.stop_service()

    def get_plugin_config(self, pid):
        """
        获取插件配置
        """
        if not self._plugins.get(pid):
            return {}
        return self.systemconfig.get_system_config(f"plugin.{pid}") or {}

    def save_plugin_config(self, pid, conf):
        """
        保存插件配置
        """
        if not self._plugins.get(pid):
            return False
        return self.systemconfig.set_system_config(f"plugin.{pid}", conf)

    def get_plugins_conf(self):
        """
        获取所有插件配置
        """
        all_confs = {}
        for pid, plugin in self._plugins.items():
            # 基本属性
            conf = {}
            if hasattr(plugin, "module_name"):
                conf.update({"name": plugin.module_name})
            if hasattr(plugin, "module_desc"):
                conf.update({"desc": plugin.module_desc})
            if hasattr(plugin, "module_version"):
                conf.update({"version": plugin.module_version})
            if hasattr(plugin, "module_icon"):
                conf.update({"icon": plugin.module_icon})
            if hasattr(plugin, "module_color"):
                conf.update({"color": plugin.module_color})
            if hasattr(plugin, "module_author"):
                conf.update({"author": plugin.module_author})
            if hasattr(plugin, "module_config_prefix"):
                conf.update({"prefix": plugin.module_config_prefix})
            # 配置项
            conf.update({"fields": plugin.get_fields() or {}})
            # 配置值
            conf.update({"config": self.get_plugin_config(pid)})
            # 汇总
            all_confs[pid] = conf
        return all_confs
