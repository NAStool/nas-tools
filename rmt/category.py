import os
from subprocess import call

import yaml

from config import Config
from utils.functions import singleton


@singleton
class Category:
    __category_path = None
    __categorys = None
    __tv_categorys = None
    __movie_categorys = None
    __anime_categorys = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        media = config.get_config('media')
        if media:
            category = media.get('category')
            if not category:
                return
            self.__category_path = os.path.join(os.path.dirname(config.get_config_path()), "%s.yaml" % category)
            try:
                if not os.path.exists(self.__category_path):
                    cfg_tp_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../config", "default-category.yaml")
                    call(["cp", cfg_tp_path, self.__category_path])
                    print("【ERROR】分类配置文件 %s.yaml 不存在，已将配置文件模板复制到配置目录，请修改后重新启动..." % category)
                    self.__categorys = {}
                    return
                with open(self.__category_path, mode='r', encoding='utf-8') as f:
                    try:
                        self.__categorys = yaml.safe_load(f)
                    except yaml.YAMLError as e:
                        print("【ERROR】%s.yaml 分类配置文件格式出现严重错误！请检查：%s" % (category, str(e)))
                        self.__categorys = {}
            except Exception as err:
                print("【ERROR】加载 %s.yaml 配置出错：%s" % (category, str(err)))
                return False

            if self.__categorys:
                self.__movie_categorys = self.__categorys.get('movie')
                self.__tv_categorys = self.__categorys.get('tv')
                self.__anime_categorys = self.__categorys.get('anime')

    def get_movie_category_flag(self):
        if self.__movie_categorys:
            return True
        return False

    def get_tv_category_flag(self):
        if self.__tv_categorys:
            return True
        return False

    def get_anime_category_flag(self):
        if self.__anime_categorys:
            return True
        return False

    def get_movie_categorys(self):
        if not self.__movie_categorys:
            return []
        return self.__movie_categorys.keys()

    def get_tv_categorys(self):
        if not self.__tv_categorys:
            return []
        return self.__tv_categorys.keys()

    def get_anime_categorys(self):
        if not self.__anime_categorys:
            return []
        return self.__anime_categorys.keys()

    def get_movie_category(self, tmdb_info):
        return self.get_category(self.__movie_categorys, tmdb_info)

    def get_tv_category(self, tmdb_info):
        return self.get_category(self.__tv_categorys, tmdb_info)

    def get_anime_category(self, tmdb_info):
        return self.get_category(self.__anime_categorys, tmdb_info)

    @staticmethod
    def get_category(categorys, tmdb_info):
        if not tmdb_info:
            return ""
        if not categorys:
            return ""
        for key, item in categorys.items():
            if not item:
                return key
            match_flag = True
            for attr, value in item.items():
                if not value:
                    continue
                info_value = tmdb_info.get(attr)
                if not info_value:
                    match_flag = False
                    continue
                else:
                    if isinstance(info_value, list):
                        info_values = [str(val).upper() for val in info_value]
                    else:
                        info_values = [str(info_value).upper()]

                if value.find(",") != -1:
                    values = [str(val).upper() for val in value.split(",")]
                else:
                    values = [str(value).upper()]

                if not set(values).intersection(set(info_values)):
                    match_flag = False
            if match_flag:
                return key
        return ""
