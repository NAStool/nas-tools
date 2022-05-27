import os
import pickle
from threading import Lock

from config import Config
from utils.functions import singleton, json_serializable

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

    def __get_meta_data(self):
        return self.__meta_data

    def get_meta_data_by_key(self, key):
        with lock:
            return self.__get_meta_data().get(key)

    def dump_meta_data(self, search, page, num):
        """
        分页获取当前缓存列表
        @param search: 检索的缓存key
        @param page: 页码
        @param num: 单页大小
        @return: 总数, 缓存列表
        """
        if page == 1:
            begin_pos = 0
        else:
            begin_pos = (page - 1) * num

        with lock:
            search_metas = [(k, json_serializable(v)) for k, v in
                            self.__get_meta_data().items() if search.lower() in k.lower() and v.get("id") != 0]
            return len(search_metas), search_metas[begin_pos: begin_pos + num]

    def delete_meta_data(self, key):
        """
        删除缓存信息
        @param key: 缓存key
        @return: 被删除的缓存内容
        """
        with lock:
            return self.__meta_data.pop(key, None)

    @staticmethod
    def __load_meta_data(path):
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            return data
        except Exception as e:
            return {}

    def update_meta_data(self, meta_data):
        with lock:
            for key, item in meta_data.items():
                if not self.__meta_data.get(key):
                    self.__meta_data[key] = item

    def save_meta_data(self):
        with lock:
            meta_data = self.__load_meta_data(self.__meta_path)
            new_meta_data = {k: v for k, v in self.__meta_data.items() if v.get("id") != 0}

            if meta_data.keys() == new_meta_data.keys():
                return

            with open(self.__meta_path, 'wb') as f:
                pickle.dump(new_meta_data, f, pickle.HIGHEST_PROTOCOL)
