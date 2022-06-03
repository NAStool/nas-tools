import os
import re
import traceback
import parse

import log
from config import Config, SPLIT_CHARS
from rmt.metainfo import MetaInfo
from rmt.tmdbv3api import TMDb, Search, Movie, TV
from utils.functions import xstr
from utils.meta_helper import MetaHelper
from utils.types import MediaType, MatchMode


class Media:
    # TheMovieDB
    tmdb = None
    search = None
    movie = None
    tv = None
    meta = None
    __rmt_match_mode = None
    __space_chars = r"\.|-|/|:"
    __empty_chars = r"'"

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        app = config.get_config('app')
        if app:
            if app.get('rmt_tmdbkey'):
                self.tmdb = TMDb()
                self.tmdb.cache = True
                self.tmdb.api_key = app.get('rmt_tmdbkey')
                self.tmdb.language = 'zh-CN'
                self.tmdb.proxies = config.get_proxies()
                self.tmdb.debug = True
                self.search = Search()
                self.movie = Movie()
                self.tv = TV()
                self.meta = MetaHelper()
            rmt_match_mode = app.get('rmt_match_mode', 'normal')
            if rmt_match_mode:
                rmt_match_mode = rmt_match_mode.upper()
            else:
                rmt_match_mode = "NORMAL"
            if rmt_match_mode == "STRICT":
                self.__rmt_match_mode = MatchMode.STRICT
            else:
                self.__rmt_match_mode = MatchMode.NORMAL

    def __compare_tmdb_names(self, file_name, tmdb_names):
        """
        比较文件名是否匹配，忽略大小写和特殊字符
        :param file_name: 识别的文件名或者种子名
        :param tmdb_names: TMDB返回的译名
        :return: True or False
        """
        if not file_name or not tmdb_names:
            return False
        if not isinstance(tmdb_names, list):
            tmdb_names = [tmdb_names]
        file_name = re.sub(r'\s+', ' ', re.sub(r"%s" % self.__empty_chars, '', re.sub(r"%s" % self.__space_chars, ' ', file_name))).strip().upper()
        for tmdb_name in tmdb_names:
            tmdb_name = re.sub(r'\s+', ' ', re.sub(r"%s" % self.__empty_chars, '', re.sub(r"%s" % self.__space_chars, ' ', tmdb_name))).strip().upper()
            if file_name == tmdb_name:
                return True
        return False

    def __search_tmdb_names(self, mtype, tmdb_id):
        """
        检索tmdb中所有的译名，用于名称匹配
        :param mtype: 类型：电影、电视剧、动漫
        :param tmdb_id: TMDB的ID
        :return: 所有译名的清单
        """
        if not mtype or not tmdb_id:
            return []
        ret_names = []
        try:
            if mtype == MediaType.MOVIE:
                tmdb_info = self.movie.translations(tmdb_id)
                if tmdb_info:
                    translations = tmdb_info.get("translations", [])
                    for translation in translations:
                        data = translation.get("data", {})
                        title = data.get("title")
                        if title and title not in ret_names:
                            ret_names.append(title)
            else:
                tmdb_info = self.tv.translations(tmdb_id)
                if tmdb_info:
                    translations = tmdb_info.get("translations", [])
                    for translation in translations:
                        data = translation.get("data", {})
                        name = data.get("name")
                        if name and name not in ret_names:
                            ret_names.append(name)
        except Exception as e:
            log.error("【META】连接TMDB出错：%s" % str(e))
        return ret_names

    def __search_tmdb(self, file_media_name, first_media_year, search_type,
                      media_year=None, season_number=None, language=None):
        """
        检索tmdb中的媒体信息
        :param file_media_name: 剑索的名称
        :param first_media_year: 年份，如要是季集需要是首播年份(first_air_date)
        :param media_year: 当前季集年份
        :param season_number: 季集，整数
        :param search_type: 类型：电影、电视剧、动漫
        :param language: 语言，默认是zh-CN
        :return: TMDB的INFO，同时会将search_type赋值到media_type中
        """
        if not self.search:
            return None
        if not file_media_name:
            log.error("【META】识别关键字有误！")
            return None
        if language:
            self.tmdb.language = language
        else:
            self.tmdb.language = 'zh'
        # TMDB检索
        info = {}
        if search_type == MediaType.MOVIE:
            log.info(f"【META】正在识别{search_type.value}：{file_media_name}, 年份={xstr(first_media_year)} ...")
            info = self.__search_movie_by_name(file_media_name, first_media_year)
            if info:
                log.info(">%sID：%s, %s名称：%s, 上映日期：%s" % (
                    search_type.value, info.get('id'), search_type.value, info.get('title'), info.get('release_date')))
        else:
            # 有当前季和当前季集年份，使用精确匹配
            if media_year and season_number:
                log.info(f"【META】正在识别{search_type.value}：{file_media_name}, 季集={season_number}, 季集年份={media_year} ...")
                info = self.__search_tv_by_season(file_media_name, media_year, season_number)
            if not info:
                log.info(f"【META】正在识别{search_type.value}：{file_media_name}, 年份={xstr(first_media_year)} ...")
                info = self.__search_tv_by_name(file_media_name, first_media_year)
            if info:
                log.info(">%sID：%s, %s名称：%s, 首播日期：%s" % (
                    search_type.value, info.get('id'), search_type.value, info.get('name'), info.get('first_air_date')))
        # 补充类别信息
        if info:
            info['media_type'] = search_type
            return info
        else:
            log.warn("【META】%s 未匹配到媒体信息!" % file_media_name)
            return None

    def __search_movie_by_name(self, file_media_name, first_media_year):
        """
        根据名称查询电影TMDB匹配
        :param file_media_name: 识别的文件名或种子名
        :param first_media_year: 电影上映日期
        :return: 匹配的媒体信息
        """
        try:
            if first_media_year:
                movies = self.search.movies({"query": file_media_name, "year": first_media_year})
            else:
                movies = self.search.movies({"query": file_media_name})
        except Exception as e:
            log.error(f"【META】连接TMDB出错：{str(e)}")
            return None
        log.debug(f"【META】API返回：{str(self.search.total_results)}")
        if len(movies) == 0:
            log.warn(f"【META】{file_media_name} 未找到媒体信息!")
            return None
        elif len(movies) == 1:
            return movies[0]
        else:
            info = {}
            if first_media_year:
                for movie in movies:
                    if movie.get('release_date'):
                        if self.__compare_tmdb_names(file_media_name, movie.get('title')) \
                                and movie.get('release_date')[0:4] == str(first_media_year):
                            return movie
                        if self.__compare_tmdb_names(file_media_name, movie.get('original_title')) \
                                and movie.get('release_date')[0:4] == str(first_media_year):
                            return movie
            else:
                for movie in movies:
                    if self.__compare_tmdb_names(file_media_name, movie.get('title')) \
                            or self.__compare_tmdb_names(file_media_name, movie.get('original_title')):
                        return movie
            if not info:
                for movie in movies:
                    if first_media_year:
                        if not movie.get('release_date'):
                            continue
                        if movie.get('release_date')[0:4] != str(first_media_year):
                            continue
                        if self.__compare_tmdb_names(file_media_name,
                                                     self.__search_tmdb_names(MediaType.MOVIE, movie.get("id"))):
                            return movie
                    else:
                        if self.__compare_tmdb_names(file_media_name,
                                                     self.__search_tmdb_names(MediaType.MOVIE, movie.get("id"))):
                            return movie
        return {}

    def __search_tv_by_name(self, file_media_name, first_media_year):
        """
        根据名称查询电视剧TMDB匹配
        :param file_media_name: 识别的文件名或者种子名
        :param first_media_year: 电视剧的首播年份
        :return: 匹配的媒体信息
        """
        try:
            if first_media_year:
                tvs = self.search.tv_shows({"query": file_media_name, "first_air_date_year": first_media_year})
            else:
                tvs = self.search.tv_shows({"query": file_media_name})
        except Exception as e:
            log.error(f"【META】连接TMDB出错：{str(e)}")
            return None
        log.debug(f"【META】API返回：{str(self.search.total_results)}")
        if len(tvs) == 0:
            log.warn(f"【META】{file_media_name} 未找到媒体信息!")
            return None
        elif len(tvs) == 1:
            return tvs[0]
        else:
            info = {}
            if first_media_year:
                for tv in tvs:
                    if tv.get('first_air_date'):
                        if self.__compare_tmdb_names(file_media_name, tv.get('name')) \
                                and tv.get('first_air_date')[0:4] == str(first_media_year):
                            return tv
                        if self.__compare_tmdb_names(file_media_name, tv.get('original_name')) \
                                and tv.get('first_air_date')[0:4] == str(first_media_year):
                            return tv
            else:
                for tv in tvs:
                    if self.__compare_tmdb_names(file_media_name, tv.get('name')) \
                            or self.__compare_tmdb_names(file_media_name, tv.get('original_name')):
                        return tv
            if not info:
                for tv in tvs:
                    if first_media_year:
                        if not tv.get('first_air_date'):
                            continue
                        if tv.get('first_air_date')[0:4] != str(first_media_year):
                            continue
                        if self.__compare_tmdb_names(file_media_name,
                                                     self.__search_tmdb_names(MediaType.TV, tv.get("id"))):
                            return tv
                    else:
                        if self.__compare_tmdb_names(file_media_name,
                                                     self.__search_tmdb_names(MediaType.TV, tv.get("id"))):
                            return tv
        return {}

    def __search_tv_by_season(self, file_media_name, media_year, season_number):
        """
        根据电视剧的名称和季的年份及序号匹配TMDB
        :param file_media_name: 识别的文件名或者种子名
        :param media_year: 季的年份
        :param season_number: 季序号
        :return: 匹配的媒体信息
        """
        def __season_match(tmdb_id):
            try:
                seasons = self.get_tmdb_seasons_info(tmdbid=tmdb_id)
                for season in seasons:
                    if season.get("air_date") and season.get("season_number"):
                        if season.get("air_date")[0:4] == str(media_year) \
                                and season.get("season_number") == int(season_number):
                            return True
            except Exception as err:
                log.error(f"【META】连接TMDB出错：{err}")
                return False
            return False

        try:
            tvs = self.search.tv_shows({"query": file_media_name})
        except Exception as e:
            log.error(f"【META】连接TMDB出错：{e}")
            return None

        if len(tvs) == 0:
            log.warn("【META】%s 未找到媒体信息!" % file_media_name)
            return None
        else:
            for tv in tvs:
                if not self.__compare_tmdb_names(file_media_name, tv.get('name')) \
                        and not self.__compare_tmdb_names(file_media_name, tv.get('original_name')):
                    continue
                # compare seasons
                if __season_match(tv.id):
                    return tv

            # 按照翻译名称再次查询
            for tv in tvs:
                if not self.__compare_tmdb_names(file_media_name, self.__search_tmdb_names(MediaType.TV, tv.get("id"))):
                    continue
                # compare seasons
                if __season_match(tv.id):
                    return tv
        return {}

    def get_media_info_manual(self, mtype, title, year, tmdbid=None):
        """
        给定名称和年份或者TMDB号，查询媒体信息
        :param mtype: 类型：电影、电视剧、动漫
        :param title: 标题
        :param year: 年份
        :param tmdbid: TMDB的ID，有tmdbid时优先使用tmdbid，否则使用年份和标题
        """
        if not tmdbid:
            if not mtype or not title:
                return None
            media_info = self.get_media_info(title="%s %s" % (title, year), mtype=mtype, strict=True)
            tmdb_info = media_info.tmdb_info
        else:
            if mtype == MediaType.MOVIE:
                tmdb_info = self.get_tmdb_movie_info(tmdbid)
            else:
                tmdb_info = self.get_tmdb_tv_info(tmdbid)
        if tmdb_info:
            tmdb_info['media_type'] = mtype
        return tmdb_info

    def get_media_info(self, title, subtitle=None, mtype=None, strict=None):
        """
        只有名称信息，判别是电影还是电视剧并搜刮TMDB信息，用于种子名称识别
        :param title: 种子名称
        :param subtitle: 种子副标题
        :param mtype: 类型：电影、电视剧、动漫
        :param strict: 是否严格模式，为true时，不会再去掉年份再查一次
        :return: 带有TMDB信息的MetaInfo对象
        """
        if not title:
            return None
        if not self.meta:
            return None
        # 识别
        meta_info = MetaInfo(title, subtitle=subtitle)
        if not meta_info.get_name():
            return None
        if mtype:
            meta_info.type = mtype
        media_key = "[%s]%s-%s-%s" % (meta_info.type.value, meta_info.get_name(), meta_info.year, meta_info.begin_season)
        if not self.meta.get_meta_data_by_key(media_key):
            # 缓存中没有开始查询
            if meta_info.type in [MediaType.TV, MediaType.ANIME]:
                # 确定是电视剧或动漫，直接按电视剧查
                file_media_info = self.__search_tmdb(file_media_name=meta_info.get_name(),
                                                     first_media_year=meta_info.year,
                                                     search_type=meta_info.type,
                                                     media_year=meta_info.year,
                                                     season_number=meta_info.begin_season
                                                     )
                if meta_info.year and not file_media_info and self.__rmt_match_mode == MatchMode.NORMAL and not strict:
                    # 非严格模式去掉年份再查一遍
                    file_media_info = self.__search_tmdb(file_media_name=meta_info.get_name(),
                                                         first_media_year=None,
                                                         search_type=meta_info.type)
            else:
                # 先按电影查
                file_media_info = self.__search_tmdb(file_media_name=meta_info.get_name(),
                                                     first_media_year=meta_info.year,
                                                     search_type=MediaType.MOVIE)
                # 电影查不到，又没有指定类型时再按电视剧查
                if not file_media_info and not mtype:
                    file_media_info = self.__search_tmdb(file_media_name=meta_info.get_name(),
                                                         first_media_year=meta_info.year,
                                                         search_type=MediaType.TV,
                                                         media_year=meta_info.year,
                                                         season_number=meta_info.begin_season)
                # 非严格模式去掉年份再查一遍， 先查电视剧（一般电视剧年份出错的概率高）
                if meta_info.year and not file_media_info and self.__rmt_match_mode == MatchMode.NORMAL and not strict:
                    file_media_info = self.__search_tmdb(file_media_name=meta_info.get_name(),
                                                         first_media_year=None,
                                                         search_type=MediaType.TV)
                    # 不带年份查电影
                    if not file_media_info and not mtype:
                        file_media_info = self.__search_tmdb(file_media_name=meta_info.get_name(),
                                                             first_media_year=None,
                                                             search_type=MediaType.MOVIE)
            # 加入缓存
            if file_media_info:
                self.meta.update_meta_data({media_key: file_media_info})
            else:
                # 标记为未找到，避免再次查询
                self.meta.update_meta_data({media_key: {'id': 0}})
        # 赋值返回
        meta_info.set_tmdb_info(self.meta.get_meta_data_by_key(media_key))
        return meta_info

    def get_media_info_on_files(self, file_list, tmdb_info=None, media_type=None, season=None, episode_format=None):
        """
        根据文件清单，搜刮TMDB信息，用于文件名称的识别
        :param file_list: 文件清单，如果是列表也可以是单个文件，也可以是一个目录
        :param tmdb_info: 如有传入TMDB信息则以该TMDB信息赋于所有文件，否则按名称从TMDB检索，用于手工识别时传入
        :param media_type: 媒体类型：电影、电视剧、动漫，如有传入以该类型赋于所有文件，否则按名称从TMDB检索并识别
        :param season: 季号，如有传入以该季号赋于所有文件，否则从名称中识别
        :param episode_format: 手动识别轩发金时传入的集数位置
        :return: 带有TMDB信息的每个文件对应的MetaInfo对象字典
        """
        # 存储文件路径与媒体的对应关系
        return_media_infos = {}
        if not self.meta:
            return return_media_infos
        # 不是list的转为list
        if not isinstance(file_list, list):
            file_list = [file_list]
        # 遍历每个文件，看得出来的名称是不是不一样，不一样的先搜索媒体信息
        for file_path in file_list:
            try:
                if not os.path.exists(file_path):
                    log.warn("【META】%s 不存在" % file_path)
                    continue
                # 解析媒体名称
                # 先用自己的名称
                file_name = os.path.basename(file_path)
                parent_name = os.path.basename(os.path.dirname(file_path))
                parent_parent_name = os.path.basename(os.path.dirname(os.path.dirname(file_path)))
                # 没有自带TMDB信息
                if not tmdb_info:
                    # 识别
                    meta_info = MetaInfo(file_name)
                    # 识别不到则使用上级的名称
                    if not meta_info.get_name() or not meta_info.year or meta_info.type == MediaType.UNKNOWN:
                        parent_info = MetaInfo(parent_name)
                        if not parent_info.get_name() or not parent_info.year:
                            parent_parent_info = MetaInfo(parent_parent_name)
                            parent_info.type = parent_parent_info.type if parent_info.type in [MediaType.MOVIE,
                                                                                               MediaType.UNKNOWN] else parent_info.type
                            parent_info.cn_name = parent_parent_info.cn_name if parent_parent_info.cn_name else parent_info.cn_name
                            parent_info.en_name = parent_parent_info.en_name if parent_parent_info.en_name else parent_info.en_name
                            parent_info.year = parent_parent_info.year if parent_parent_info.year else parent_info.year
                            parent_info.begin_season = self.max_ele(parent_info.begin_season,
                                                                    parent_parent_info.begin_season)
                            parent_info.end_season = self.max_ele(parent_info.end_season, parent_parent_info.end_season)
                        if not meta_info.get_name():
                            meta_info.cn_name = parent_info.cn_name
                            meta_info.en_name = parent_info.en_name
                        if not meta_info.year:
                            meta_info.year = parent_info.year
                        if parent_info.type not in [MediaType.MOVIE, MediaType.UNKNOWN] \
                                and meta_info.type in [MediaType.MOVIE, MediaType.UNKNOWN]:
                            meta_info.type = parent_info.type
                        if meta_info.type in [MediaType.TV, MediaType.ANIME]:
                            meta_info.begin_season = self.max_ele(parent_info.begin_season, meta_info.begin_season)
                            meta_info.end_season = self.max_ele(parent_info.end_season, meta_info.end_season)
                    if not meta_info.get_name():
                        continue
                    media_key = "[%s]%s-%s-%s" % (
                        meta_info.type.value, meta_info.get_name(), meta_info.year, meta_info.begin_season)
                    if not self.meta.get_meta_data_by_key(media_key):
                        # 调用TMDB API
                        file_media_info = self.__search_tmdb(file_media_name=meta_info.get_name(),
                                                             first_media_year=meta_info.year,
                                                             search_type=meta_info.type,
                                                             media_year=meta_info.year,
                                                             season_number=meta_info.begin_season)
                        if not file_media_info:
                            if self.__rmt_match_mode == MatchMode.NORMAL:
                                # 去掉年份再查一次，有可能是年份错误
                                file_media_info = self.__search_tmdb(file_media_name=meta_info.get_name(),
                                                                     first_media_year=None,
                                                                     search_type=meta_info.type)
                        if file_media_info:
                            self.meta.update_meta_data({media_key: file_media_info})
                        else:
                            # 标记为未找到避免再次查询
                            self.meta.update_meta_data({media_key: {'id': 0}})
                    # 存入结果清单返回
                    meta_info.set_tmdb_info(self.meta.get_meta_data_by_key(media_key))
                # 自带TMDB信息
                else:
                    meta_info = MetaInfo(file_name, mtype=media_type)
                    meta_info.set_tmdb_info(tmdb_info)
                    meta_info.type = media_type
                    if season and media_type != MediaType.MOVIE:
                        meta_info.begin_season = int(season)
                    if episode_format:
                        meta_info.begin_episode, meta_info.end_episode = self.split_episode(file_name, episode_format)
                return_media_infos[file_path] = meta_info
            except Exception as err:
                log.error("【RMT】发生错误：%s - %s" % (str(err), traceback.format_exc()))
        # 循环结束
        return return_media_infos

    def get_tmdb_hot_movies(self, page):
        """
        获取热门电影
        :param page: 第几页
        :return: TMDB信息列表
        """
        if not self.movie:
            return []
        return self.movie.popular(page)

    def get_tmdb_hot_tvs(self, page):
        """
        获取热门电视剧
        :param page: 第几页
        :return: TMDB信息列表
        """
        if not self.tv:
            return []
        return self.tv.popular(page)

    def get_tmdb_new_movies(self, page):
        """
        获取最新电影
        :param page: 第几页
        :return: TMDB信息列表
        """
        if not self.movie:
            return []
        return self.movie.now_playing(page)

    def get_tmdb_new_tvs(self, page):
        """
        获取最新电视剧
        :param page: 第几页
        :return: TMDB信息列表
        """
        if not self.tv:
            return []
        return self.tv.on_the_air(page)

    def get_tmdb_movie_info(self, tmdbid):
        """
        获取电影的详情
        :param tmdbid: TMDB ID
        :return: TMDB信息
        """
        if not self.movie:
            return {}
        try:
            log.info("【META】正在查询TMDB：%s ..." % tmdbid)
            tmdbinfo = self.movie.details(tmdbid)
            return tmdbinfo
        except Exception as e:
            log.console(str(e))
            return {}

    def get_tmdb_tv_info(self, tmdbid):
        """
        获取电视剧的详情
        :param tmdbid: TMDB ID
        :return: TMDB信息
        """
        if not self.tv:
            return {}
        try:
            log.info("【META】正在查询TMDB：%s ..." % tmdbid)
            tmdbinfo = self.tv.details(tmdbid)
            return tmdbinfo
        except Exception as e:
            log.console(str(e))
            return {}

    def get_tmdb_seasons_info(self, tv_info=None, tmdbid=None):
        """
        从TMDB的季集信息中获得季的组
        :param tv_info: TMDB 的季信息
        :param tmdbid: TMDB ID 没有tv_info且有tmdbid时，重新从TMDB查询季的信息
        :return: 带有season_number、episode_count 的每季总集数的字典列表
        """
        if not tv_info and not tmdbid:
            return []
        if not tv_info and tmdbid:
            tv_info = self.get_tmdb_tv_info(tmdbid)
        if not tv_info:
            return []
        seasons = tv_info.get("seasons")
        if not seasons:
            return []
        total_seasons = []
        for season in seasons:
            if season.get("season_number") != 0:
                total_seasons.append(
                    {"season_number": season.get("season_number"),
                     "episode_count": season.get("episode_count"),
                     "air_date": season.get("air_date")})
        return total_seasons

    def get_tmdb_season_episodes_num(self, sea, tv_info=None, tmdbid=None):
        """
        从TMDB的季信息中获得具体季有多少集
        :param sea: 季号，数字
        :param tv_info: 已获取的TMDB季的信息
        :param tmdbid: TMDB ID，没有tv_info且有tmdbid时，重新从TMDB查询季的信息
        :return: 该季的总集数
        """
        if not tv_info and not tmdbid:
            return 0
        if not tv_info and tmdbid:
            tv_info = self.get_tmdb_tv_info(tmdbid)
        if not tv_info:
            return 0
        seasons = tv_info.get("seasons")
        if not seasons:
            return 0
        for season in seasons:
            if season.get("season_number") == sea:
                return season.get("episode_count")
        return 0

    @staticmethod
    def max_ele(a, b):
        if not a:
            return b
        if not b:
            return a
        return max(a, b)

    @staticmethod
    def split_episode(file_name, episode_format):
        ret = parse.parse(episode_format, file_name)
        if ret:
            episodes = ret.__getitem__('episode')
            episode_splits = list(filter(lambda x: re.compile(r'[a-zA-Z]*\d{1,4}', re.IGNORECASE).match(x), re.split(r'%s' % SPLIT_CHARS, episodes)))
            if len(episode_splits) == 1:
                return int(re.compile(r'[a-zA-Z]*', re.IGNORECASE).sub("", episode_splits[0])), None
            else:
                return int(re.compile(r'[a-zA-Z]*', re.IGNORECASE).sub("", episode_splits[0])), int(
                    re.compile(r'[a-zA-Z]*', re.IGNORECASE).sub("", episode_splits[1]))
        else:
            return 1, None
