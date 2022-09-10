import os
import pickle
import random
import time
from threading import RLock
from app.utils import JsonUtils, ThreadHelper
from config import Config
from app.utils.commons import singleton
from app.utils.types import MediaType

lock = RLock()

CACHE_EXPIRE_TIMESTAMP_STR = "cache_expire_timestamp"
EXPIRE_TIMESTAMP = 7 * 24 * 3600


@singleton
class MetaHelper(object):
    __meta_data = {}
    __meta_path = None
    __tmdb_cache_expire = False

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        laboratory = config.get_config('laboratory')
        if laboratory:
            self.__tmdb_cache_expire = laboratory.get("tmdb_cache_expire")
        self.__meta_path = os.path.join(config.get_config_path(), 'meta.dat')
        self.__meta_data = self.__load_meta_data(self.__meta_path)

    def clear_meta_data(self):
        """
        清空所有TMDB缓存
        """
        with lock:
            self.__meta_data = {}

    def get_meta_data_path(self):
        """
        返回TMDB缓存文件路径
        """
        return self.__meta_path

    def get_meta_data_by_key(self, key):
        """
        根据KEY值获取缓存值
        """
        with lock:
            info: dict = self.__meta_data.get(key)
            if info:
                expire = info.get(CACHE_EXPIRE_TIMESTAMP_STR)
                if not expire or int(time.time()) < expire:
                    info[CACHE_EXPIRE_TIMESTAMP_STR] = int(time.time()) + EXPIRE_TIMESTAMP
                    ThreadHelper().start_thread(self.update_meta_data, ({key: info}))
                elif expire and self.__tmdb_cache_expire:
                    ThreadHelper().start_thread(self.delete_meta_data, (key,))
            return info

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
            search_metas = [(k, JsonUtils.json_serializable(v),
                             str(k).replace("[电影]", "").replace("[电视剧]", "").replace("[未知]", "").replace("-None", ""))
                            for k, v in
                            self.__meta_data.items() if search.lower() in k.lower() and v.get("id") != 0]
            return len(search_metas), search_metas[begin_pos: begin_pos + num]

    def delete_meta_data(self, key):
        """
        删除缓存信息
        @param key: 缓存key
        @return: 被删除的缓存内容
        """
        with lock:
            return self.__meta_data.pop(key, None)

    def delete_meta_data_by_tmdbid(self, tmdbid):
        """
        清空对应TMDBID的所有缓存记录，以强制更新TMDB中最新的数据
        """
        for key in list(self.__meta_data):
            if str(self.__meta_data.get(key, {}).get("id")) == str(tmdbid):
                with lock:
                    self.__meta_data.pop(key)

    def delete_unknown_meta(self):
        """
        清除未识别的缓存记录，以便重新检索TMDB
        """
        for key in list(self.__meta_data):
            if str(self.__meta_data.get(key, {}).get("id")) == '0':
                with lock:
                    self.__meta_data.pop(key)

    def modify_meta_data(self, key, title):
        """
        删除缓存信息
        @param key: 缓存key
        @param title: 标题
        @return: 被修改后缓存内容
        """
        with lock:
            if self.__meta_data.get(key):
                if self.__meta_data[key]['media_type'] == MediaType.MOVIE:
                    self.__meta_data[key]['title'] = title
                else:
                    self.__meta_data[key]['name'] = title
                self.__meta_data[key][CACHE_EXPIRE_TIMESTAMP_STR] = int(time.time()) + EXPIRE_TIMESTAMP
            return self.__meta_data.get(key)

    @staticmethod
    def __load_meta_data(path):
        """
        从文件中加载缓存
        """
        try:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    data = pickle.load(f)
                return data
            return {}
        except Exception as e:
            print(str(e))
            return {}

    def update_meta_data(self, meta_data):
        """
        新增或更新缓存条目
        """
        if not meta_data:
            return
        with lock:
            for key, item in meta_data.items():
                if not self.__meta_data.get(key):
                    item[CACHE_EXPIRE_TIMESTAMP_STR] = int(time.time()) + EXPIRE_TIMESTAMP
                    self.__meta_data[key] = item

    def save_meta_data(self, force=False):
        """
        保存缓存数据到文件
        """
        meta_data = self.__load_meta_data(self.__meta_path)
        new_meta_data = {k: v for k, v in self.__meta_data.items() if str(v.get("id")) != '0'}

        if not force and not self._random_sample(new_meta_data) and meta_data.keys() == new_meta_data.keys():
            return

        with open(self.__meta_path, 'wb') as f:
            pickle.dump(new_meta_data, f, pickle.HIGHEST_PROTOCOL)

    def _random_sample(self, new_meta_data):
        """
        采样分析是否需要保存
        """
        ret = False
        if len(new_meta_data) < 25:
            keys = list(new_meta_data.keys())
            for k in keys:
                info = new_meta_data.get(k)
                expire = info.get(CACHE_EXPIRE_TIMESTAMP_STR)
                if not expire:
                    ret = True
                    info[CACHE_EXPIRE_TIMESTAMP_STR] = int(time.time()) + EXPIRE_TIMESTAMP
                elif int(time.time()) >= expire:
                    ret = True
                    if self.__tmdb_cache_expire:
                        new_meta_data.pop(k)
        else:
            count = 0
            keys = random.sample(new_meta_data.keys(), 25)
            for k in keys:
                info = new_meta_data.get(k)
                expire = info.get(CACHE_EXPIRE_TIMESTAMP_STR)
                if not expire:
                    ret = True
                    info[CACHE_EXPIRE_TIMESTAMP_STR] = int(time.time()) + EXPIRE_TIMESTAMP
                elif int(time.time()) >= expire:
                    ret = True
                    if self.__tmdb_cache_expire:
                        new_meta_data.pop(k)
                        count += 1
            if count >= 5:
                ret |= self._random_sample(new_meta_data)
        return ret

    def get_cache_title(self, key):
        """
        获取缓存的标题
        """
        cache_media_info = self.__meta_data.get(key)
        if not cache_media_info or not cache_media_info.get("id"):
            return None
        return cache_media_info.get("title") if cache_media_info.get(
            "media_type") == MediaType.MOVIE else cache_media_info.get("name")

    def set_cache_title(self, key, cn_title):
        """
        重新设置缓存标题
        """
        cache_media_info = self.__meta_data.get(key)
        if not cache_media_info:
            return
        if cache_media_info.get("media_type") == MediaType.MOVIE:
            self.__meta_data[key]['title'] = cn_title
        else:
            self.__meta_data[key]['name'] = cn_title
