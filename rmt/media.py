import os
import re
from threading import Lock
import log
from tmdbv3api import TMDb, Search, Movie, TV
from config import Config
from rmt.metainfo import MetaInfo
from utils.functions import xstr, is_anime
from utils.meta_helper import MetaHelper
from utils.types import MediaType, MatchMode

lock = Lock()


class Media:
    # TheMovieDB
    tmdb = None
    search = None
    movie = None
    tv = None
    meta = None
    __rmt_match_mode = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        app = config.get_config('app')
        if app:
            if app.get('rmt_tmdbkey'):
                self.tmdb = TMDb()
                self.tmdb.api_key = app.get('rmt_tmdbkey')
                self.tmdb.language = 'zh-CN'
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

    # 检索tmdb中的媒体信息，传入名字、年份、类型
    # 返回媒体信息对象
    def __search_tmdb(self, file_media_name, media_year, search_type, language=None):
        if not self.search:
            return None
        if not file_media_name:
            log.error("【META】检索关键字有误！")
            return None
        if language:
            self.tmdb.language = language
        else:
            self.tmdb.language = 'zh'
        # TMDB检索
        if search_type == MediaType.MOVIE:
            # 先按年份查，不行再不用年份查
            log.info("【META】正在检索%s：%s, 年份=%s ..." % (search_type.value, file_media_name, xstr(media_year)))
            try:
                if media_year:
                    movies = self.search.movies({"query": file_media_name, "year": media_year})
                else:
                    movies = self.search.movies({"query": file_media_name})
            except Exception as e:
                log.error("【META】连接TMDB出错：%s" % str(e))
                return None
            log.debug("【META】API返回：%s" % str(self.search.total_results))
            if len(movies) == 0:
                log.warn("【META】%s 未找到媒体信息!" % file_media_name)
                return None
            else:
                info = movies[0]
                for movie in movies:
                    if movie.get('release_date'):
                        if movie.get('title') == file_media_name or movie.get('release_date')[0:4] == media_year:
                            # 优先使用名称或者年份完全匹配的，匹配不到则取第一个
                            info = movie
                            break
                log.info(">%sID：%s, %s名称：%s, 上映日期：%s" % (
                    search_type.value, info.get('id'), search_type.value, info.get('title'), info.get('release_date')))
        else:
            # 先按年份查，不行再不用年份查
            log.info("【META】正在检索%s：%s, 年份=%s ..." % (search_type.value, file_media_name, xstr(media_year)))
            try:
                if media_year:
                    tvs = self.search.tv_shows({"query": file_media_name, "first_air_date_year": media_year})
                else:
                    tvs = self.search.tv_shows({"query": file_media_name})
            except Exception as e:
                log.error("【META】连接TMDB出错：%s" % str(e))
                return None
            log.debug("【META】API返回：%s" % str(self.search.total_results))
            if len(tvs) == 0:
                log.warn("【META】%s 未找到媒体信息!" % file_media_name)
                return None
            else:
                info = tvs[0]
                for tv in tvs:
                    if tv.get('first_air_date'):
                        if tv.get('name') == file_media_name and tv.get('first_air_date')[0:4] == media_year:
                            # 优先使用名称或者年份完全匹配的，匹配不到则取第一个
                            info = tv
                            break
                    elif tv.get('name') == file_media_name:
                        info = tv
                        break
                log.info(">%sID：%s, %s名称：%s, 上映日期：%s" % (
                    search_type.value, info.get('id'), search_type.value, info.get('name'), info.get('first_air_date')))
        # 补充类别信息
        if info:
            info['media_type'] = search_type
        return info

    # 给定名称和年份或者TMDB号，查询媒体信息
    def get_media_info_manual(self, mtype, title, year, tmdbid=None):
        if not tmdbid:
            if not mtype or not title or not year:
                return None
            tmdb_info = self.__search_tmdb(title, year, mtype)
        else:
            if mtype == MediaType.MOVIE:
                tmdb_info = self.get_tmdb_movie_info(tmdbid)
            else:
                tmdb_info = self.get_tmdb_tv_info(tmdbid)
        return tmdb_info

    # 只有名称信息，判别是电影还是电视剧并TMDB信息
    def get_media_info(self, title, subtitle=None):
        if not title:
            return None
        if not self.meta:
            return None
        if not is_anime(title):
            # 常规识别
            meta_info = MetaInfo(title, subtitle=subtitle)
            media_key = "%s%s" % (meta_info.get_name(), meta_info.year)
            try:
                lock.acquire()
                if not self.meta.get_meta_data().get(media_key):
                    # 缓存中没有开始查询
                    if meta_info.type == MediaType.TV:
                        # 确定是电视剧，直接按电视剧查
                        file_media_info = self.__search_tmdb(meta_info.get_name(), meta_info.year, MediaType.TV)
                        if meta_info.year and not file_media_info and self.__rmt_match_mode == MatchMode.NORMAL:
                            # 非严格模式去掉年份再查一遍
                            file_media_info = self.__search_tmdb(meta_info.get_name(), None, MediaType.TV)
                    else:
                        # 不能确定是电视剧，先按电影查
                        file_media_info = self.__search_tmdb(meta_info.get_name(), meta_info.year, MediaType.MOVIE)
                        if not file_media_info:
                            # 电影查不到再按电视剧查
                            file_media_info = self.__search_tmdb(meta_info.get_name(), meta_info.year, MediaType.TV)
                        if meta_info.year and not file_media_info and self.__rmt_match_mode == MatchMode.NORMAL:
                            # 非严格模式去掉年份再查一遍， 先查电视剧（一般电视剧年份出错的概率高）
                            file_media_info = self.__search_tmdb(meta_info.get_name(), None, MediaType.TV)
                            if not file_media_info:
                                # 不带年份查电影
                                file_media_info = self.__search_tmdb(meta_info.get_name(), None, MediaType.MOVIE)
                    # 加入缓存
                    if file_media_info:
                        self.meta.update_meta_data({media_key: file_media_info})
                    else:
                        # 标记为未找到，避免再次查询
                        self.meta.update_meta_data({media_key: {'id': 0}})
            finally:
                lock.release()
        else:
            # 动漫识别
            meta_info = MetaInfo(title, anime=True)
            media_key = "[ANIME]%s%s" % (meta_info.get_name(), meta_info.year)
            if meta_info.type != MediaType.UNKNOWN:
                try:
                    lock.acquire()
                    if not self.meta.get_meta_data().get(media_key):
                        file_media_info = self.__search_tmdb(meta_info.get_name(), meta_info.year, meta_info.type)
                        # 加入缓存
                        if file_media_info:
                            self.meta.update_meta_data({media_key: file_media_info})
                        else:
                            # 标记为未找到，避免再次查询
                            self.meta.update_meta_data({media_key: {'id': 0}})
                finally:
                    lock.release()
            else:
                self.meta.update_meta_data({media_key: {'id': 0}})
        # 赋值返回
        meta_info.set_tmdb_info(self.meta.get_meta_data().get(media_key))
        return meta_info

    # 搜刮媒体信息和类型，返回每个文件对应的媒体信息
    '''
    输入：file_list：文件路径清单, 可能是一个目录，也可能是一个文件清单
    输出：类型，文件路径：媒体信息的List
    '''

    def get_media_info_on_files(self, file_list, tmdb_info=None, media_type=None):
        # 存储文件路径与媒体的对应关系
        return_media_infos = {}
        if not self.meta:
            return return_media_infos
        # 不是list的转为list
        if not isinstance(file_list, list):
            file_list = [file_list]
        # 遍历每个文件，看得出来的名称是不是不一样，不一样的先搜索媒体信息
        for file_path in file_list:
            if not os.path.exists(file_path):
                log.error("【META】%s 不存在！" % file_path)
                continue
            # 解析媒体名称
            # 先用自己的名称
            file_name = os.path.basename(file_path)
            parent_name = os.path.basename(os.path.dirname(file_path))
            # 没有自带TMDB信息
            if not tmdb_info:
                if not is_anime(file_name):
                    # 常规识别
                    meta_info = MetaInfo(file_name)
                    # 识别不到则使用上级的名称
                    if not meta_info.get_name() or meta_info.get_name() == file_name or not meta_info.year:
                        parent_info = MetaInfo(parent_name)
                        if not meta_info.cn_name:
                            meta_info.cn_name = parent_info.cn_name
                        if not meta_info.en_name:
                            meta_info.en_name = parent_info.en_name
                        if not meta_info.year:
                            meta_info.year = parent_info.year
                        if parent_info.type != MediaType.MOVIE:
                            meta_info.type = parent_info.type
                    media_key = "%s%s" % (meta_info.get_name(), meta_info.year)
                    try:
                        lock.acquire()
                        if not self.meta.get_meta_data().get(media_key):
                            # 调用TMDB API
                            file_media_info = self.__search_tmdb(meta_info.get_name(), meta_info.year, meta_info.type)
                            if not file_media_info:
                                if self.__rmt_match_mode == MatchMode.NORMAL:
                                    # 去掉年份再查一次，有可能是年份错误
                                    file_media_info = self.__search_tmdb(meta_info.get_name(), None, meta_info.type)
                            if file_media_info:
                                self.meta.update_meta_data({media_key: file_media_info})
                            else:
                                # 标记为未找到避免再次查询
                                self.meta.update_meta_data({media_key: {'id': 0}})
                    finally:
                        lock.release()
                else:
                    # 动漫识别
                    meta_info = MetaInfo(file_name, anime=True)
                    # 识别不到则使用上级的名称
                    if not meta_info.get_name() or not meta_info.year or meta_info.type == MediaType.UNKNOWN:
                        parent_info = MetaInfo(parent_name, anime=True)
                        if parent_info.type != MediaType.UNKNOWN:
                            if meta_info.type == MediaType.UNKNOWN:
                                meta_info.type = parent_info.type
                            if not meta_info.cn_name:
                                meta_info.cn_name = parent_info.cn_name
                            if not meta_info.en_name:
                                meta_info.en_name = parent_info.en_name
                            if not meta_info.year:
                                meta_info.year = parent_info.year
                    media_key = "[ANIME]%s%s" % (meta_info.get_name(), meta_info.year)
                    # 动漫识别到了
                    if meta_info.type != MediaType.UNKNOWN:
                        try:
                            lock.acquire()
                            if not self.meta.get_meta_data().get(media_key):
                                file_media_info = self.__search_tmdb(meta_info.get_name(), meta_info.year,
                                                                     meta_info.type)
                                if file_media_info:
                                    self.meta.update_meta_data({media_key: file_media_info})
                                else:
                                    self.meta.update_meta_data({media_key: {'id': 0}})
                        finally:
                            lock.release()
                    else:
                        self.meta.update_meta_data({media_key: {'id': 0}})
                # 存入结果清单返回
                meta_info.set_tmdb_info(self.meta.get_meta_data().get(media_key))
            # 自带TMDB信息
            else:
                if media_type == MediaType.ANIME:
                    meta_info = MetaInfo(file_name, anime=True)
                else:
                    meta_info = MetaInfo(file_name)
                meta_info.set_tmdb_info(tmdb_info)
            return_media_infos[file_path] = meta_info

        return return_media_infos

    # 检查标题中是否匹配资源类型
    # 返回：是否匹配，匹配的序号，匹配的值
    @staticmethod
    def check_resouce_types(t_title, t_types, t_size=0):
        if not t_types:
            # 未配置默认不过滤
            return True, 0, ""
        if isinstance(t_types, list):
            # 如果是个列表，说明是旧配置
            c_seq = 100
            for t_type in t_types:
                c_seq = c_seq - 1
                t_type = str(t_type)
                if t_type.upper() == "BLURAY":
                    match_str = r'blu-?ray'
                elif t_type.upper() == "4K":
                    match_str = r'4k|2160p'
                else:
                    match_str = r'%s' % t_type
                re_res = re.search(match_str, t_title, re.IGNORECASE)
                if re_res:
                    return True, c_seq, t_type
            return False, 0, ""
        else:
            # 必须包括的项
            includes = t_types.get('include')
            if includes:
                if isinstance(includes, str):
                    includes = [includes]
                include_flag = True
                for include in includes:
                    if not include:
                        continue
                    re_res = re.search(r'%s' % include, t_title, re.IGNORECASE)
                    if not re_res:
                        include_flag = False
                if not include_flag:
                    return False, 0, ""

            # 不能包含的项
            excludes = t_types.get('exclude')
            if excludes:
                if isinstance(excludes, str):
                    excludes = [excludes]
                exclude_flag = False
                exclude_count = 0
                for exclude in excludes:
                    if not exclude:
                        continue
                    exclude_count += 1
                    re_res = re.search(r'%s' % exclude, t_title, re.IGNORECASE)
                    if not re_res:
                        exclude_flag = True
                if exclude_count != 0 and not exclude_flag:
                    return False, 0, ""

            # 大小
            if t_size:
                sizes = t_types.get('size')
                if sizes:
                    if sizes.find(',') != -1:
                        if sizes[0].isdigit():
                            begin_size = int(sizes[0].strip())
                        else:
                            begin_size = 0
                        if sizes[1].isdigit():
                            end_size = int(sizes[1].strip())
                        else:
                            end_size = 0
                    else:
                        begin_size = 0
                        if sizes.isdight():
                            end_size = int(sizes.strip())
                        else:
                            end_size = 0
                    if not begin_size * 1024 * 1024 * 1024 <= int(t_size) << end_size * 1024 * 1024 * 1024:
                        return False, 0, ""
            return True, 0, ""

    # 获取热门电影
    def get_tmdb_hot_movies(self, page):
        if not self.movie:
            return []
        return self.movie.popular(page)

    # 获取热门电视剧
    def get_tmdb_hot_tvs(self, page):
        if not self.tv:
            return []
        return self.tv.popular(page)

    # 获取最新电影
    def get_tmdb_new_movies(self, page):
        if not self.movie:
            return []
        return self.movie.now_playing(page)

    # 获取最新电视剧
    def get_tmdb_new_tvs(self, page):
        if not self.tv:
            return []
        return self.tv.on_the_air(page)

    # 获取电影的详情
    def get_tmdb_movie_info(self, tmdbid):
        if not self.movie:
            return {}
        try:
            return self.movie.details(tmdbid)
        except Exception as e:
            print(str(e))
            return {}

    # 获取电视剧的详情
    def get_tmdb_tv_info(self, tmdbid):
        if not self.tv:
            return {}
        try:
            return self.tv.details(tmdbid)
        except Exception as e:
            print(str(e))
            return {}
