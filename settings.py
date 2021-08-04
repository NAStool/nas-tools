import os
import threading
from configparser import NoOptionError, RawConfigParser
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

lock = threading.Lock()


class ConfigFileModifyHandler(FileSystemEventHandler):
    def on_modified(self, event):
        Config.get_instance().load_config()


class Config(object):
    __instance = None

    def __init__(self, config_file_path=None):
        self.config = RawConfigParser()
        self.config_file_path = config_file_path or '/config/config.ini'
        self.load_config()
        self._init_config_file_observer()

    def _init_config_file_observer(self):
        event_handler = ConfigFileModifyHandler()
        observer = Observer()
        observer.schedule(event_handler, path=self.config_file_path, recursive=False)
        observer.setDaemon(True)
        observer.start()

    def get_config_path(self):
        return self.config_file_path

    @staticmethod
    def get_instance():
        if Config.__instance:
            return Config.__instance
        try:
            lock.acquire()
            if not Config.__instance:
                Config.__instance = Config()
        finally:
            lock.release()
        return Config.__instance

    def load_config(self):
        self.config.read(self.config_file_path, 'utf-8')

    def get(self, key, default=None):
        """
        获取配置
        :param str key: 格式 [section].[key] 如：app.name
        :param Any default: 默认值
        :return:
        """
        map_key = key.split('.')
        if len(map_key) < 2:
            return default
        section = map_key[0]
        if not self.config.has_section(section):
            return default
        option = '.'.join(map_key[1:])
        try:
            return self.config.get(section, option)
        except NoOptionError:
            return default


def get(key, default=None):
    """
    获取配置
    :param str key: 格式 [section].[key] 如：app.name
    :param Any default: 默认值
    :return:
    """
    return Config.get_instance().get(key, default)


def get_config_path():
    return Config.get_instance().get_config_path()
