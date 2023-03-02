import os.path
from threading import Thread

import log
from app.conf import SystemConfig
from app.helper import SubmoduleHelper
from app.plugins.event_manager import EventManager
from app.utils import SystemUtils, PathUtils
from app.utils.commons import singleton
from config import Config


@singleton
class PluginManager:
    """
    插件管理器
    """
    systemconfig = None
    eventmanager = None

    # 插件列表
    _plugins = {}
    # 运行态插件列表
    _running_plugins = {}
    # 配置Key
    _config_key = "plugin.%s"
    # 事件处理线程
    _thread = None
    # 开关
    _active = False

    def __init__(self):
        user_plugin_path = Config().get_plugin_path()
        system_plugin_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "modules")
        if os.path.exists(user_plugin_path):
            for plugin_file in PathUtils.get_dir_level1_files(user_plugin_path, [".py"]):
                SystemUtils.copy(plugin_file, system_plugin_path)
        self.init_config()

    def init_config(self):
        self.systemconfig = SystemConfig()
        self.eventmanager = EventManager()
        # 启动事件处理进程
        self.start_service()

    def __run(self):
        """
        事件处理线程
        """
        while self._active:
            event, handlers = self.eventmanager.get_event()
            if event:
                log.info(f"处理事件：{event.event_type} - {handlers}")
                for handler in handlers:
                    try:
                        names = handler.__qualname__.split(".")
                        self.run_plugin(names[0], names[1], event)
                    except Exception as e:
                        log.error(f"事件处理出错：{str(e)}")

    def start_service(self):
        """
        启动
        """
        # 加载插件
        self.__load_plugins()
        # 将事件管理器设为启动
        self._active = True
        self._thread = Thread(target=self.__run)
        # 启动事件处理线程
        self._thread.start()

    def stop_service(self):
        """
        停止
        """
        # 将事件管理器设为停止
        self._active = False
        # 等待事件处理线程退出
        self._thread.join()
        # 停止所有插件
        self.__stop_plugins()

    def __load_plugins(self):
        """
        加载所有插件
        """
        plugins = SubmoduleHelper.import_submodules(
            "app.plugins.modules",
            filter_func=lambda _, obj: hasattr(obj, 'module_name')
        )
        plugins.sort(key=lambda x: x.module_order if hasattr(x, "module_order") else 0)
        for plugin in plugins:
            module_id = plugin.__name__
            self._plugins[module_id] = plugin
            self._running_plugins[module_id] = plugin()
            self.reload_plugin(module_id)
            log.info(f"加载插件：{plugin}")

    def run_plugin(self, pid, method, *args, **kwargs):
        """
        运行插件
        """
        if not self._running_plugins.get(pid):
            return None
        if not hasattr(self._running_plugins[pid], method):
            return
        try:
            return getattr(self._running_plugins[pid], method)(*args, **kwargs)
        except Exception as err:
            print(str(err))

    def reload_plugin(self, pid):
        """
        生效插件配置
        """
        if not self._running_plugins.get(pid):
            return
        if hasattr(self._running_plugins[pid], "init_config"):
            try:
                self._running_plugins[pid].init_config(self.get_plugin_config(pid))
            except Exception as err:
                print(str(err))

    def __stop_plugins(self):
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
        return self.systemconfig.get_system_config(self._config_key % pid) or {}

    def save_plugin_config(self, pid, conf):
        """
        保存插件配置
        """
        if not self._plugins.get(pid):
            return False
        return self.systemconfig.set_system_config(self._config_key % pid, conf)

    def get_plugins_conf(self, auth_level):
        """
        获取所有插件配置
        """
        all_confs = {}
        for pid, plugin in self._running_plugins.items():
            # 基本属性
            conf = {}
            # 权限
            if hasattr(plugin, "auth_level") \
                    and plugin.auth_level > auth_level:
                continue
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
            # 状态
            conf.update({"state": plugin.get_state()})
            # 汇总
            all_confs[pid] = conf
        return all_confs
