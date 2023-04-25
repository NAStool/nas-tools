import json
import os
from abc import ABCMeta, abstractmethod

import log
from app.conf import SystemConfig
from app.helper import DbHelper
from app.message import Message
from config import Config


class _IPluginModule(metaclass=ABCMeta):
    """
    插件模块基类，通过继续该类实现插件功能
    除内置属性外，还有以下方法可以扩展或调用：
    - get_fields() 获取配置字典，用于生成插件配置表单
    - get_state() 获取插件启用状态，用于展示运行状态
    - stop_service() 停止插件服务
    - get_config() 获取配置信息
    - update_config() 更新配置信息
    - init_config() 生效配置信息
    - info(msg) 记录INFO日志
    - warn(msg) 记录插件WARN日志
    - error(msg) 记录插件ERROR日志
    - debug(msg) 记录插件DEBUG日志
    - get_page() 插件额外页面数据，在插件配置页面左下解按钮展示
    - get_script() 插件额外脚本（Javascript），将会写入插件页面，可在插件元素中绑定使用
    - send_message() 发送消息
    - get_data_path() 获取插件数据保存目录
    - history() 记录插件运行数据，key需要唯一，value为对象
    - get_history() 获取插件运行数据
    - update_history() 更新插件运行数据
    - delete_history() 删除插件运行数据
    - get_command() 获取插件命令，使用消息机制通过远程控制

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
    # 作者主页
    author_url = ""
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
    def init_config(self, config: dict = None):
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

    @staticmethod
    def __is_obj(obj):
        if isinstance(obj, list) or isinstance(obj, dict):
            return True
        else:
            return str(obj).startswith("{") or str(obj).startswith("[")

    def update_config(self, config: dict, plugin_id=None):
        """
        更新配置信息
        :param config: 配置信息字典
        :param plugin_id: 插件ID
        """
        if not plugin_id:
            plugin_id = self.__class__.__name__
        return SystemConfig().set("plugin.%s" % plugin_id, config)

    def get_config(self, plugin_id=None):
        """
        获取配置信息
        :param plugin_id: 插件ID
        """
        if not plugin_id:
            plugin_id = self.__class__.__name__
        return SystemConfig().get("plugin.%s" % plugin_id)

    def get_data_path(self, plugin_id=None):
        """
        获取插件数据保存目录
        """
        if not plugin_id:
            plugin_id = self.__class__.__name__
        data_path = os.path.join(Config().get_user_plugin_path(), plugin_id)
        if not os.path.exists(data_path):
            os.makedirs(data_path)
        return data_path

    def history(self, key, value):
        """
        记录插件运行数据，key需要唯一，value为对象是自动转换为str，
        """
        if not key or not value:
            return
        if self.__is_obj(value):
            value = json.dumps(value)
        DbHelper().insert_plugin_history(plugin_id=self.__class__.__name__,
                                         key=key,
                                         value=value)

    def get_history(self, key=None, plugin_id=None):
        """
        获取插件运行数据，只返回一条，自动识别转换为对象
        """
        if not plugin_id:
            plugin_id = self.__class__.__name__

        historys = DbHelper().get_plugin_history(plugin_id=plugin_id, key=key)
        if not isinstance(historys, list):
            historys = [historys]
        result = []
        for history in historys:
            if not history:
                continue
            if self.__is_obj(history.VALUE):
                try:
                    if key:
                        return json.loads(history.VALUE)
                    else:
                        result.append(json.loads(history.VALUE))
                    continue
                except Exception as err:
                    print(str(err))
            if key:
                return history.VALUE
            else:
                result.append(history.VALUE)
        return None if key else result

    def update_history(self, key, value, plugin_id=None):
        """
        更新插件运行数据
        """
        if not key or not value:
            return False
        if not plugin_id:
            plugin_id = self.__class__.__name__
        if self.__is_obj(value):
            value = json.dumps(value)
        return DbHelper().update_plugin_history(plugin_id=plugin_id, key=key, value=value)

    def delete_history(self, key, plugin_id=None):
        """
        删除插件运行数据
        """
        if not key:
            return False
        if not plugin_id:
            plugin_id = self.__class__.__name__
        return DbHelper().delete_plugin_history(plugin_id=plugin_id, key=key)

    @staticmethod
    def send_message(title, text=None, image=None):
        """
        发送消息
        """
        return Message().send_plugin_message(title=title,
                                             text=text,
                                             image=image)

    def info(self, msg):
        """
        记录INFO日志
        :param msg: 日志信息
        """
        log.info(f"【Plugin】{self.module_name} - {msg}")

    def warn(self, msg):
        """
        记录插件WARN日志
        :param msg: 日志信息
        """
        log.warn(f"【Plugin】{self.module_name} - {msg}")

    def error(self, msg):
        """
        记录插件ERROR日志
        :param msg: 日志信息
        """
        log.error(f"【Plugin】{self.module_name} - {msg}")

    def debug(self, msg):
        """
        记录插件Debug日志
        :param msg: 日志信息
        """
        log.debug(f"【Plugin】{self.module_name} - {msg}")
