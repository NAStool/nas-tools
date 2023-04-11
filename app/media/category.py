import os
import shutil

import ruamel.yaml

import log
from app.utils import ExceptionUtils
from config import Config
from app.utils.commons import singleton


@singleton
class Category:
    _category_path = None
    _categorys = None
    _tv_categorys = None
    _movie_categorys = None
    _anime_categorys = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        self._category_path = Config().category_path
        if not self._category_path:
            return
        category_name, _ = os.path.splitext(os.path.basename(self._category_path))
        if category_name == "config":
            log.warn(f"【Config】二级分类策略 {category_name} 名称非法")
            return
        try:
            if not os.path.exists(self._category_path):
                shutil.copy(os.path.join(Config().get_inner_config_path(), "default-category.yaml"),
                            self._category_path)
                log.warn(f"【Config】二级分类策略 {category_name} 配置文件不存在，已按模板生成...")
            with open(self._category_path, mode='r', encoding='utf-8') as f:
                try:
                    yaml = ruamel.yaml.YAML()
                    self._categorys = yaml.load(f)
                except Exception as e:
                    ExceptionUtils.exception_traceback(e)
                    log.warn(f"【Config】二级分类策略 {category_name} 配置文件格式出现严重错误！请检查：{str(e)}")
                    self._categorys = {}
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            log.warn(f"【Config】二级分类策略 {category_name} 配置文件加载出错：{str(e)}")
            return False

        if self._categorys:
            self._movie_categorys = self._categorys.get('movie')
            self._tv_categorys = self._categorys.get('tv')
            self._anime_categorys = self._categorys.get('anime')
        log.info(f"【Config】已加载二级分类策略 {category_name}")

    @property
    def movie_category_flag(self):
        """
        获取电影分类标志
        """
        if self._movie_categorys:
            return True
        return False

    @property
    def tv_category_flag(self):
        """
        获取电视剧分类标志
        """
        if self._tv_categorys:
            return True
        return False

    @property
    def anime_category_flag(self):
        """
        获取动漫分类标志
        """
        if self._anime_categorys:
            return True
        return False

    @property
    def movie_categorys(self):
        """
        获取电影分类清单
        """
        if not self._movie_categorys:
            return []
        return self._movie_categorys.keys()

    @property
    def tv_categorys(self):
        """
        获取电视剧分类清单
        """
        if not self._tv_categorys:
            return []
        return self._tv_categorys.keys()

    @property
    def anime_categorys(self):
        """
        获取动漫分类清单
        """
        if not self._anime_categorys:
            return []
        return self._anime_categorys.keys()

    def get_movie_category(self, tmdb_info):
        """
        判断电影的分类
        :param tmdb_info: 识别的TMDB中的信息
        :return: 二级分类的名称
        """
        return self.get_category(self._movie_categorys, tmdb_info)

    def get_tv_category(self, tmdb_info):
        """
        判断电视剧的分类
        :param tmdb_info: 识别的TMDB中的信息
        :return: 二级分类的名称
        """
        return self.get_category(self._tv_categorys, tmdb_info)

    def get_anime_category(self, tmdb_info):
        """
        判断动漫的分类
        :param tmdb_info: 识别的TMDB中的信息
        :return: 二级分类的名称
        """
        return self.get_category(self._anime_categorys, tmdb_info)

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
