import os
import shutil

import ruamel.yaml

import log
from config import Config
from app.utils.commons import singleton


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
            self.__category_path = os.path.join(config.get_config_path(), "%s.yaml" % category)
            try:
                if not os.path.exists(self.__category_path):
                    shutil.copy(os.path.join(config.get_inner_config_path(), "default-category.yaml"),
                                self.__category_path)
                    log.console("【Config】分类配置文件 %s.yaml 不存在，已将配置文件模板复制到配置目录..." % category)
                with open(self.__category_path, mode='r', encoding='utf-8') as f:
                    try:
                        yaml = ruamel.yaml.YAML()
                        self.__categorys = yaml.load(f)
                    except Exception as e:
                        log.console("【Config】%s.yaml 分类配置文件格式出现严重错误！请检查：%s" % (category, str(e)))
                        self.__categorys = {}
            except Exception as err:
                log.console("【Config】加载 %s.yaml 配置出错：%s" % (category, str(err)))
                return False

            if self.__categorys:
                self.__movie_categorys = self.__categorys.get('movie')
                self.__tv_categorys = self.__categorys.get('tv')
                self.__anime_categorys = self.__categorys.get('anime')

    def get_movie_category_flag(self):
        """
        获取电影分类标志
        """
        if self.__movie_categorys:
            return True
        return False

    def get_tv_category_flag(self):
        """
        获取电视剧分类标志
        """
        if self.__tv_categorys:
            return True
        return False

    def get_anime_category_flag(self):
        """
        获取动漫分类标志
        """
        if self.__anime_categorys:
            return True
        return False

    def get_movie_categorys(self):
        """
        获取电影分类清单
        """
        if not self.__movie_categorys:
            return []
        return self.__movie_categorys.keys()

    def get_tv_categorys(self):
        """
        获取电视剧分类清单
        """
        if not self.__tv_categorys:
            return []
        return self.__tv_categorys.keys()

    def get_anime_categorys(self):
        """
        获取动漫分类清单
        """
        if not self.__anime_categorys:
            return []
        return self.__anime_categorys.keys()

    def get_movie_category(self, tmdb_info):
        """
        判断电影的分类
        :param tmdb_info: 识别的TMDB中的信息
        :return: 二级分类的名称
        """
        return self.get_category(self.__movie_categorys, tmdb_info)

    def get_tv_category(self, tmdb_info):
        """
        判断电视剧的分类
        :param tmdb_info: 识别的TMDB中的信息
        :return: 二级分类的名称
        """
        return self.get_category(self.__tv_categorys, tmdb_info)

    def get_anime_category(self, tmdb_info):
        """
        判断动漫的分类
        :param tmdb_info: 识别的TMDB中的信息
        :return: 二级分类的名称
        """
        return self.get_category(self.__anime_categorys, tmdb_info)

    @staticmethod
    def get_category(categorys, tmdb_info):
        """
        根据 TMDB信息与分类配置文件进行比较，确定所属分类
        :param categorys: 分类配置
        :param tmdb_info: TMDB信息
        :return: 分类的名称
        """
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
                elif attr == "production_countries":
                    info_values = [str(val.get("iso_3166_1")).upper() for val in info_value]
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
