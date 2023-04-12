import os.path
import traceback
from threading import Thread

import log
from app.conf import SystemConfig
from app.helper import SubmoduleHelper
from app.plugins.event_manager import EventManager
from app.utils import SystemUtils, PathUtils
from app.utils.commons import singleton
from app.utils.types import SystemConfigKey
from config import Config


@singleton
class PluginManager:
    """
    插件管理器
    """
    systemconfig = None
    eventmanager = None

    # 用户插件目录
    user_plugin_path = None
    # 内部插件目录
    system_plugin_path = None

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
        # config/plugins 是插件py文件目录，config/plugins/xxx是插件数据目录
        self.user_plugin_path = Config().get_user_plugin_path()
        if not os.path.exists(self.user_plugin_path):
            os.makedirs(self.user_plugin_path)
        self.system_plugin_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "modules")
        if os.path.exists(self.user_plugin_path):
            for plugin_file in PathUtils.get_dir_level1_files(self.user_plugin_path, [".py"]):
                SystemUtils.copy(plugin_file, self.system_plugin_path)
        self.init_config()

    def init_config(self):
        self.systemconfig = SystemConfig()
        self.eventmanager = EventManager()
        # 停止已有插件
        self.stop_service()
        # 启动插件
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
                        log.error(f"事件处理出错：{str(e)} - {traceback.format_exc()}")

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
        if self._thread:
            self._thread.join()
        # 停止所有插件
        self.__stop_plugins()

    def __load_plugins(self):
        """
        加载所有插件
        """
        # 扫描插件目录
        plugins = SubmoduleHelper.import_submodules(
            "app.plugins.modules",
            filter_func=lambda _, obj: hasattr(obj, 'module_name')
        )
        # 排序
        plugins.sort(key=lambda x: x.module_order if hasattr(x, "module_order") else 0)
        # 用户已安装插件列表
        user_plugins = self.systemconfig.get(SystemConfigKey.UserInstalledPlugins) or []
        self._running_plugins = {}
        self._plugins = {}
        for plugin in plugins:
            module_id = plugin.__name__
            self._plugins[module_id] = plugin
            # 未安装的跳过加载
            if module_id not in user_plugins:
                continue
            self._running_plugins[module_id] = plugin()
            # 初始化配置
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
            print(str(err), traceback.format_exc())

    def reload_plugin(self, pid):
        """
        生效插件配置
        """
        if not pid:
            return
        if not self._running_plugins.get(pid):
            return
        if hasattr(self._running_plugins[pid], "init_config"):
            try:
                self._running_plugins[pid].init_config(self.get_plugin_config(pid))
                log.debug(f"生效插件配置：{pid}")
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
        return self.systemconfig.get(self._config_key % pid) or {}

    def get_plugin_page(self, pid):
        """
        获取插件额外页面数据
        """
        if not self._running_plugins.get(pid):
            return None
        if not hasattr(self._running_plugins[pid], "get_page"):
            return None
        title, html = self._running_plugins[pid].get_page()
        return title, html

    def get_plugin_script(self, pid):
        """
        获取插件额外脚本
        """
        if not self._running_plugins.get(pid):
            return None
        if not hasattr(self._running_plugins[pid], "get_script"):
            return None
        return self._running_plugins[pid].get_script()

    def get_plugin_state(self, pid):
        """
        获取插件状态
        """
        if not self._running_plugins.get(pid):
            return None
        if not hasattr(self._running_plugins[pid], "get_state"):
            return None
        return self._running_plugins[pid].get_state()

    def save_plugin_config(self, pid, conf):
        """
        保存插件配置
        """
        if not self._plugins.get(pid):
            return False
        return self.systemconfig.set(self._config_key % pid, conf)

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
            if hasattr(plugin, "module_config_prefix"):
                conf.update({"prefix": plugin.module_config_prefix})
            # 插件额外的页面
            if hasattr(plugin, "get_page"):
                title, _ = plugin.get_page()
                conf.update({"page": title})
            # 插件额外的脚本
            if hasattr(plugin, "get_script"):
                conf.update({"script": plugin.get_script()})
            # 配置项
            conf.update({"fields": plugin.get_fields() or {}})
            # 配置值
            conf.update({"config": self.get_plugin_config(pid)})
            # 状态
            conf.update({"state": plugin.get_state()})
            # 汇总
            all_confs[pid] = conf
        return all_confs

    def get_plugin_apps(self, auth_level):
        """
        获取所有插件
        """
        all_confs = {}
        installed_apps = self.systemconfig.get(SystemConfigKey.UserInstalledPlugins) or []
        for pid, plugin in self._plugins.items():
            # 基本属性
            conf = {}
            # 权限
            if hasattr(plugin, "auth_level") \
                    and plugin.auth_level > auth_level:
                continue
            conf.update({"id": pid})
            if pid in installed_apps:
                conf.update({"installed": True})
            else:
                conf.update({"installed": False})
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
            if hasattr(plugin, "author_url"):
                conf.update({"author_url": plugin.author_url})
            # 汇总
            all_confs[pid] = conf
        return all_confs
