import os
import pickle
from threading import Lock

from config import Config
from utils.functions import singleton

lock = Lock()


@singleton
class MetaHelper(object):
    __meta_data = {}
    __meta_path = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        self.__meta_path = os.path.join(os.path.dirname(config.get_config_path()), 'meta.dat')
        self.__meta_data = self.__load_meta_data(self.__meta_path)

    def get_meta_data(self):
        return self.__meta_data

    @staticmethod
    def __load_meta_data(path):
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            return data
        except Exception as e:
            return {}

    def update_meta_data(self, meta_data):
        for key, item in meta_data.items():
            if not self.__meta_data.get(key):
                self.__meta_data[key] = item

    def save_meta_data(self):
        try:
            lock.acquire()
            meta_data = self.__load_meta_data(self.__meta_path)
            save_flag = False
            for key, item in self.__meta_data.items():
                if not meta_data.get(key) and item.get("id") != 0:
                    save_flag = True
                    meta_data[key] = item
            if not save_flag:
                return
            with open(self.__meta_path, 'wb') as f:
                pickle.dump(meta_data, f, pickle.HIGHEST_PROTOCOL)
        finally:
            lock.release()
