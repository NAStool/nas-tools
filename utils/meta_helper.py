import os
import pickle
from threading import Lock

lock = Lock()


class MetaHelper(object):
    __instance = None
    __meta_data = {}
    __meta_path = None

    def __init__(self):
        self.__meta_path = os.path.join(os.path.dirname(os.environ.get('NASTOOL_CONFIG')), 'meta.dat')
        self.__meta_data = self.__load_meta_data(self.__meta_path)

    @staticmethod
    def get_instance():
        if MetaHelper.__instance:
            return MetaHelper.__instance
        try:
            lock.acquire()
            if not MetaHelper.__instance:
                MetaHelper.__instance = MetaHelper()
        finally:
            lock.release()
        return MetaHelper.__instance

    def __get_meta_data(self):
        return self.__meta_data

    @staticmethod
    def __load_meta_data(path):
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            return data
        except Exception as e:
            return {}

    def __update_meta_data(self, meta_data):
        for key, item in meta_data.items():
            if not self.__meta_data.get(key):
                self.__meta_data[key] = item

    def __save_meta_data(self):
        meta_data = self.__load_meta_data(self.__meta_path)
        for key, item in self.__meta_data:
            if not meta_data.get(key) and item.get("id") != 0:
                meta_data[key] = item
        with open(self.__meta_path, 'wb') as f:
            pickle.dump(meta_data, f, pickle.HIGHEST_PROTOCOL)

    # 获取媒体信息
    def get_meta_data(self):
        return self.get_instance().__get_meta_data()

    # 保存媒体信息
    def save_meta_data(self):
        return self.get_instance().__save_meta_data()

    # 更新媒体信息
    def update_meta_data(self, meta_data):
        return self.get_instance().__update_meta_data(meta_data)
