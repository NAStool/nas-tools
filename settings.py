import threading
from configparser import NoOptionError, RawConfigParser

lock = threading.Lock()
config_file_path = ""


class Config(object):
    __instance = None

    def __init__(self):
        self.config = RawConfigParser()
        self.load_config()

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
        self.config.read(config_file_path, 'utf-8')

    def get(self, key, default=None):
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
    return Config.get_instance().get(key, default)


def get_config_path():
    return Config.get_instance().get_config_path()


def reload_config():
    return Config.get_instance().load_config()
