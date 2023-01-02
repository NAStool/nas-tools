import difflib
import os
import random
import re
import traceback
from functools import lru_cache

import zhconv
from lxml import etree

import log
from app.helper import MetaHelper
from app.media.meta.metainfo import MetaInfo
from app.media.tmdbv3api import TMDb, Search, Movie, TV, Person, Find, TMDbException
from app.utils import PathUtils, EpisodeFormat, RequestUtils, NumberUtils, StringUtils, cacheman
from app.utils.types import MediaType, MatchMode
from config import Config, KEYWORD_BLACKLIST, KEYWORD_SEARCH_WEIGHT_3, KEYWORD_SEARCH_WEIGHT_2, KEYWORD_SEARCH_WEIGHT_1, \
    KEYWORD_STR_SIMILARITY_THRESHOLD, KEYWORD_DIFF_SCORE_THRESHOLD, TMDB_IMAGE_ORIGINAL_URL, DEFAULT_TMDB_PROXY


class Media:
    # TheMovieDB
    tmdb = None
    search = None
    movie = None
    tv = None
    person = None
    find = None
    meta = None
    _rmt_match_mode = None
    _search_keyword = None
    _search_tmdbweb = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        app = Config().get_config('app')
        laboratory = Config().get_config('laboratory')
        if app:
            if app.get('rmt_tmdbkey'):
                self.tmdb = TMDb()
                if laboratory.get('tmdb_proxy'):
                    self.tmdb.domain = DEFAULT_TMDB_PROXY
                else:
                    self.tmdb.domain = app.get("tmdb_domain")
                self.tmdb.cache = True
                self.tmdb.api_key = app.get('rmt_tmdbkey')
                self.tmdb.language = 'zh-CN'
                self.tmdb.proxies = Config().get_proxies()
                self.tmdb.debug = True
                self.search = Search()
                self.movie = Movie()
                self.tv = TV()
                self.find = Find()
                self.person = Person()
                self.meta = MetaHelper()
            rmt_match_mode = app.get('rmt_match_mode', 'normal')
            if rmt_match_mode:
                rmt_match_mode = rmt_match_mode.upper()
            else:
                rmt_match_mode = "NORMAL"
            if rmt_match_mode == "STRICT":
                self._rmt_match_mode = MatchMode.STRICT
            else:
                self._rmt_match_mode = MatchMode.NORMAL
        laboratory = Config().get_config('laboratory')
        if laboratory:
            self._search_keyword = laboratory.get("search_keyword")
            self._search_tmdbweb = laboratory.get("search_tmdbweb")

    @staticmethod
    def __compare_tmdb_names(file_name, tmdb_names):
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
        file_name = StringUtils.handler_special_chars(file_name).upper()
        for tmdb_name in tmdb_names:
            tmdb_name = StringUtils.handler_special_chars(tmdb_name).strip().upper()
            if file_name == tmdb_name:
                return True
        return False

    def __search_tmdb_allnames(self, mtype: MediaType, tmdb_id):
        """
        检索tmdb中所有的标题和译名，用于名称匹配
        :param mtype: 类型：电影、电视剧、动漫
        :param tmdb_id: TMDB的ID
        :return: 所有译名的清单
        """
        if not mtype or not tmdb_id:
            return {}, []
        ret_names = []
        tmdb_info = self.get_tmdb_info(mtype=mtype, tmdbid=tmdb_id)
        if not tmdb_info:
            return tmdb_info, []
        if mtype == MediaType.MOVIE:
            alternative_titles = tmdb_info.get("alternative_titles", {}).get("titles", [])
            for alternative_title in alternative_titles:
                title = alternative_title.get("title")
                if title and title not in ret_names:
                    ret_names.append(title)
            translations = tmdb_info.get("translations", {}).get("translations", [])
            for translation in translations:
                title = translation.get("data", {}).get("title")
                if title and title not in ret_names:
                    ret_names.append(title)
        else:
            alternative_titles = tmdb_info.get("alternative_titles", {}).get("results", [])
            for alternative_title in alternative_titles:
                name = alternative_title.get("title")
                if name and name not in ret_names:
                    ret_names.append(name)
            translations = tmdb_info.get("translations", {}).get("translations", [])
            for translation in translations:
                name = translation.get("data", {}).get("name")
                if name and name not in ret_names:
                    ret_names.append(name)
        return tmdb_info, ret_names

    def __search_tmdb(self, file_media_name,
                      search_type,
                      first_media_year=None,
                      media_year=None,
                      season_number=None,
                      language=None):
        """
        检索tmdb中的媒体信息，匹配返回一条尽可能正确的信息
        :param file_media_name: 剑索的名称
        :param search_type: 类型：电影、电视剧、动漫
        :param first_media_year: 年份，如要是季集需要是首播年份(first_air_date)
        :param media_year: 当前季集年份
        :param season_number: 季集，整数
        :param language: 语言，默认是zh-CN
        :return: TMDB的INFO，同时会将search_type赋值到media_type中
        """
        if not self.search:
            return None
        if not file_media_name:
            return None
        if language:
            self.tmdb.language = language
        else:
            self.tmdb.language = 'zh-CN'
        # TMDB检索
        info = {}
        if search_type == MediaType.MOVIE:
            year_range = [first_media_year]
            if first_media_year:
                year_range.append(str(int(first_media_year) + 1))
                year_range.append(str(int(first_media_year) - 1))
            for year in year_range:
                log.debug(
                    f"【Meta】正在识别{search_type.value}：{file_media_name}, 年份={year} ...")
                info = self.__search_movie_by_name(file_media_name, year)
                if info:
                    info['media_type'] = MediaType.MOVIE
                    log.info("【Meta】%s 识别到 电影：TMDBID=%s, 名称=%s, 上映日期=%s" % (
                        file_media_name,
                        info.get('id'),
                        info.get('title'),
                        info.get('release_date')))
                    break
        else:
            # 有当前季和当前季集年份，使用精确匹配
            if media_year and season_number:
                log.debug(
                    f"【Meta】正在识别{search_type.value}：{file_media_name}, 季集={season_number}, 季集年份={media_year} ...")
                info = self.__search_tv_by_season(file_media_name,
                                                  media_year,
                                                  season_number)
            if not info:
                log.debug(
                    f"【Meta】正在识别{search_type.value}：{file_media_name}, 年份={StringUtils.xstr(first_media_year)} ...")
                info = self.__search_tv_by_name(file_media_name,
                                                first_media_year)
            if info:
                info['media_type'] = MediaType.TV
                log.info("【Meta】%s 识别到 电视剧：TMDBID=%s, 名称=%s, 首播日期=%s" % (
                    file_media_name,
                    info.get('id'),
                    info.get('name'),
                    info.get('first_air_date')))
        # 返回
        if info:
            return info
        else:
            log.info("【Meta】%s 以年份 %s 在TMDB中未找到%s信息!" % (
                file_media_name, StringUtils.xstr(first_media_year), search_type.value if search_type else ""))
            return info

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
        except TMDbException as err:
            log.error(f"【Meta】连接TMDB出错：{str(err)}")
            return None
        except Exception as e:
            log.error(f"【Meta】连接TMDB出错：{str(e)}")
            return None
        log.debug(f"【Meta】API返回：{str(self.search.total_results)}")
        if len(movies) == 0:
            log.debug(f"【Meta】{file_media_name} 未找到相关电影信息!")
            return {}
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
                index = 0
                for movie in movies:
                    if first_media_year:
                        if not movie.get('release_date'):
                            continue
                        if movie.get('release_date')[0:4] != str(first_media_year):
                            continue
                        index += 1
                        info, names = self.__search_tmdb_allnames(MediaType.MOVIE, movie.get("id"))
                        if self.__compare_tmdb_names(file_media_name, names):
                            return info
                    else:
                        index += 1
                        info, names = self.__search_tmdb_allnames(MediaType.MOVIE, movie.get("id"))
                        if self.__compare_tmdb_names(file_media_name, names):
                            return info
                    if index > 5:
                        break
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
        except TMDbException as err:
            log.error(f"【Meta】连接TMDB出错：{str(err)}")
            return None
        except Exception as e:
            log.error(f"【Meta】连接TMDB出错：{str(e)}")
            return None
        log.debug(f"【Meta】API返回：{str(self.search.total_results)}")
        if len(tvs) == 0:
            log.debug(f"【Meta】{file_media_name} 未找到相关剧集信息!")
            return {}
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
                index = 0
                for tv in tvs:
                    if first_media_year:
                        if not tv.get('first_air_date'):
                            continue
                        if tv.get('first_air_date')[0:4] != str(first_media_year):
                            continue
                        index += 1
                        info, names = self.__search_tmdb_allnames(MediaType.TV, tv.get("id"))
                        if self.__compare_tmdb_names(file_media_name, names):
                            return info
                    else:
                        index += 1
                        info, names = self.__search_tmdb_allnames(MediaType.TV, tv.get("id"))
                        if self.__compare_tmdb_names(file_media_name, names):
                            return info
                    if index > 5:
                        break
        return {}

    def __search_tv_by_season(self, file_media_name, media_year, season_number):
        """
        根据电视剧的名称和季的年份及序号匹配TMDB
        :param file_media_name: 识别的文件名或者种子名
        :param media_year: 季的年份
        :param season_number: 季序号
        :return: 匹配的媒体信息
        """

        def __season_match(tv_info, season_year):
            if not tv_info:
                return False
            try:
                seasons = self.get_tmdb_seasons_list(tv_info=tv_info)
                for season in seasons:
                    if season.get("air_date") and season.get("season_number"):
                        if season.get("air_date")[0:4] == str(season_year) \
                                and season.get("season_number") == int(season_number):
                            return True
            except Exception as e1:
                log.error(f"【Meta】连接TMDB出错：{e1}")
                return False
            return False

        try:
            tvs = self.search.tv_shows({"query": file_media_name})
        except TMDbException as err:
            log.error(f"【Meta】连接TMDB出错：{str(err)}")
            return None
        except Exception as e:
            log.error(f"【Meta】连接TMDB出错：{e}")
            return None

        if len(tvs) == 0:
            log.debug("【Meta】%s 未找到季%s相关信息!" % (file_media_name, season_number))
            return {}
        else:
            for tv in tvs:
                if (self.__compare_tmdb_names(file_media_name, tv.get('name'))
                    or self.__compare_tmdb_names(file_media_name, tv.get('original_name'))) \
                        and (tv.get('first_air_date') and tv.get('first_air_date')[0:4] == str(media_year)):
                    return tv

            for tv in tvs[:5]:
                info, names = self.__search_tmdb_allnames(MediaType.TV, tv.get("id"))
                if not self.__compare_tmdb_names(file_media_name, names):
                    continue
                if __season_match(tv_info=info, season_year=media_year):
                    return info
        return {}

    def __search_multi_tmdb(self, file_media_name):
        """
        根据名称同时查询电影和电视剧，不带年份
        :param file_media_name: 识别的文件名或种子名
        :return: 匹配的媒体信息
        """
        try:
            multis = self.search.multi({"query": file_media_name}) or []
        except TMDbException as err:
            log.error(f"【Meta】连接TMDB出错：{str(err)}")
            return None
        except Exception as e:
            log.error(f"【Meta】连接TMDB出错：{str(e)}")
            return None
        log.debug(f"【Meta】API返回：{str(self.search.total_results)}")
        if len(multis) == 0:
            log.debug(f"【Meta】{file_media_name} 未找到相关媒体息!")
            return {}
        else:
            info = {}
            for multi in multis:
                if multi.get("media_type") == "movie":
                    if self.__compare_tmdb_names(file_media_name, multi.get('title')) \
                            or self.__compare_tmdb_names(file_media_name, multi.get('original_title')):
                        info = multi
                elif multi.get("media_type") == "tv":
                    if self.__compare_tmdb_names(file_media_name, multi.get('name')) \
                            or self.__compare_tmdb_names(file_media_name, multi.get('original_name')):
                        info = multi
            if not info:
                for multi in multis[:5]:
                    if multi.get("media_type") == "movie":
                        movie_info, names = self.__search_tmdb_allnames(MediaType.MOVIE, multi.get("id"))
                        if self.__compare_tmdb_names(file_media_name, names):
                            info = movie_info
                    elif multi.get("media_type") == "tv":
                        tv_info, names = self.__search_tmdb_allnames(MediaType.TV, multi.get("id"))
                        if self.__compare_tmdb_names(file_media_name, names):
                            info = tv_info
        # 返回
        if info:
            info['media_type'] = MediaType.MOVIE if info.get('media_type') == 'movie' else MediaType.TV
            return info
        else:
            log.info("【Meta】%s 在TMDB中未找到媒体信息!" % file_media_name)
            return info

    @lru_cache(maxsize=128)
    def __search_tmdb_web(self, file_media_name, mtype: MediaType):
        """
        检索TMDB网站，直接抓取结果，结果只有一条时才返回
        :param file_media_name: 名称
        """
        if not file_media_name:
            return None
        if StringUtils.is_chinese(file_media_name):
            return {}
        log.info("【Meta】正在从TheDbMovie网站查询：%s ..." % file_media_name)
        tmdb_url = "https://www.themoviedb.org/search?query=%s" % file_media_name
        res = RequestUtils(timeout=5).get_res(url=tmdb_url)
        if res and res.status_code == 200:
            html_text = res.text
            if not html_text:
                return None
            try:
                tmdb_links = []
                html = etree.HTML(html_text)
                links = html.xpath("//a[@data-id]/@href")
                for link in links:
                    if not link or (not link.startswith("/tv") and not link.startswith("/movie")):
                        continue
                    if link not in tmdb_links:
                        tmdb_links.append(link)
                if len(tmdb_links) == 1:
                    tmdbinfo = self.get_tmdb_info(
                        mtype=MediaType.TV if tmdb_links[0].startswith("/tv") else MediaType.MOVIE,
                        tmdbid=tmdb_links[0].split("/")[-1])
                    if tmdbinfo:
                        if mtype == MediaType.TV and tmdbinfo.get('media_type') != MediaType.TV:
                            return {}
                        if tmdbinfo.get('media_type') == MediaType.MOVIE:
                            log.info("【Meta】%s 从WEB识别到 电影：TMDBID=%s, 名称=%s, 上映日期=%s" % (
                                file_media_name,
                                tmdbinfo.get('id'),
                                tmdbinfo.get('title'),
                                tmdbinfo.get('release_date')))
                        else:
                            log.info("【Meta】%s 从WEB识别到 电视剧：TMDBID=%s, 名称=%s, 首播日期=%s" % (
                                file_media_name,
                                tmdbinfo.get('id'),
                                tmdbinfo.get('name'),
                                tmdbinfo.get('first_air_date')))
                    return tmdbinfo
                elif len(tmdb_links) > 1:
                    log.info("【Meta】%s TMDB网站返回数据过多：%s" % (file_media_name, len(tmdb_links)))
                else:
                    log.info("【Meta】%s TMDB网站未查询到媒体信息！" % file_media_name)
            except Exception as err:
                print(str(err))
                return None
        return None

    def get_tmdb_info(self, mtype: MediaType,
                      tmdbid,
                      language=None,
                      append_to_response=None,
                      chinese=True):
        """
        给定TMDB号，查询一条媒体信息
        :param mtype: 类型：电影、电视剧、动漫，为空时都查（此时用不上年份）
        :param tmdbid: TMDB的ID，有tmdbid时优先使用tmdbid，否则使用年份和标题
        :param language: 语种
        :param append_to_response: 附加信息
        :param chinese: 是否转换中文标题
        """
        if not self.tmdb:
            log.error("【Meta】TMDB API Key 未设置！")
            return None
        if language:
            self.tmdb.language = language
        else:
            self.tmdb.language = 'zh-CN'
        if mtype == MediaType.MOVIE:
            tmdb_info = self.__get_tmdb_movie_detail(tmdbid, append_to_response)
            if tmdb_info:
                tmdb_info['media_type'] = MediaType.MOVIE
        else:
            tmdb_info = self.__get_tmdb_tv_detail(tmdbid, append_to_response)
            if tmdb_info:
                tmdb_info['media_type'] = MediaType.TV
        if tmdb_info:
            # 转换genreid
            tmdb_info['genre_ids'] = self.__get_genre_ids_from_detail(tmdb_info.get('genres'))
            # 转换中文标题
            if chinese:
                tmdb_info = self.__update_tmdbinfo_cn_title(tmdb_info)

        return tmdb_info

    def __update_tmdbinfo_cn_title(self, tmdb_info):
        """
        更新TMDB信息中的中文名称
        """
        # 查找中文名
        org_title = tmdb_info.get("title") if tmdb_info.get("media_type") == MediaType.MOVIE else tmdb_info.get(
            "name")
        if not StringUtils.is_chinese(org_title) and self.tmdb.language == 'zh-CN':
            cn_title = self.__get_tmdb_chinese_title(tmdbinfo=tmdb_info)
            if cn_title and cn_title != org_title:
                if tmdb_info.get("media_type") == MediaType.MOVIE:
                    tmdb_info['title'] = cn_title
                else:
                    tmdb_info['name'] = cn_title
        return tmdb_info

    def get_tmdb_infos(self, title, year=None, mtype: MediaType = None, num=6):
        """
        查询名称中有关键字的所有的TMDB信息并返回
        """
        if not self.tmdb:
            log.error("【Meta】TMDB API Key 未设置！")
            return []
        if not title:
            return []
        if not mtype and not year:
            results = self.__search_multi_tmdbinfos(title)
        else:
            if not mtype:
                results = list(
                    set(self.__search_movie_tmdbinfos(title, year)).union(set(self.__search_tv_tmdbinfos(title, year))))
                # 组合结果的情况下要排序
                results = sorted(results,
                                 key=lambda x: x.get("release_date") or x.get("first_air_date") or "0000-00-00",
                                 reverse=True)
            elif mtype == MediaType.MOVIE:
                results = self.__search_movie_tmdbinfos(title, year)
            else:
                results = self.__search_tv_tmdbinfos(title, year)
        return results[:num]

    def __search_multi_tmdbinfos(self, title):
        """
        同时查询模糊匹配的电影、电视剧TMDB信息
        """
        if not title:
            return []
        ret_infos = []
        multis = self.search.multi({"query": title}) or []
        for multi in multis:
            if multi.get("media_type") in ["movie", "tv"]:
                multi['media_type'] = MediaType.MOVIE if multi.get("media_type") == "movie" else MediaType.TV
                ret_infos.append(multi)
        return ret_infos

    def __search_movie_tmdbinfos(self, title, year):
        """
        查询模糊匹配的所有电影TMDB信息
        """
        if not title:
            return []
        ret_infos = []
        if year:
            movies = self.search.movies({"query": title, "year": year}) or []
        else:
            movies = self.search.movies({"query": title}) or []
        for movie in movies:
            if title in movie.get("title"):
                movie['media_type'] = MediaType.MOVIE
                ret_infos.append(movie)
        return ret_infos

    def __search_tv_tmdbinfos(self, title, year):
        """
        查询模糊匹配的所有电视剧TMDB信息
        """
        if not title:
            return []
        ret_infos = []
        if year:
            tvs = self.search.tv_shows({"query": title, "first_air_date_year": year}) or []
        else:
            tvs = self.search.tv_shows({"query": title}) or []
        for tv in tvs:
            if title in tv.get("name"):
                tv['media_type'] = MediaType.TV
                ret_infos.append(tv)
        return ret_infos

    @staticmethod
    def __make_cache_key(meta_info):
        """
        生成缓存的key
        """
        if not meta_info:
            return None
        return f"[{meta_info.type.value}]{meta_info.get_name()}-{meta_info.year}-{meta_info.begin_season}"

    def get_cache_info(self, meta_info):
        """
        根据名称查询是否已经有缓存
        """
        if not meta_info:
            return {}
        return self.meta.get_meta_data_by_key(self.__make_cache_key(meta_info))

    def get_media_info(self, title,
                       subtitle=None,
                       mtype=None,
                       strict=None,
                       cache=True,
                       chinese=True):
        """
        只有名称信息，判别是电影还是电视剧并搜刮TMDB信息，用于种子名称识别
        :param title: 种子名称
        :param subtitle: 种子副标题
        :param mtype: 类型：电影、电视剧、动漫
        :param strict: 是否严格模式，为true时，不会再去掉年份再查一次
        :param cache: 是否使用缓存，默认TRUE
        :param chinese: 原标题为英文时是否从别名中检索中文名称
        :return: 带有TMDB信息的MetaInfo对象
        """
        if not self.tmdb:
            log.error("【Meta】TMDB API Key 未设置！")
            return None
        if not title:
            return None
        # 识别
        meta_info = MetaInfo(title, subtitle=subtitle)
        if not meta_info.get_name() or not meta_info.type:
            log.warn("【Rmt】%s 未识别出有效信息！" % meta_info.org_string)
            return None
        if mtype:
            meta_info.type = mtype
        media_key = self.__make_cache_key(meta_info)
        if not cache or not self.meta.get_meta_data_by_key(media_key):
            # 缓存没有或者强制不使用缓存
            if meta_info.type != MediaType.TV and not meta_info.year:
                file_media_info = self.__search_multi_tmdb(file_media_name=meta_info.get_name())
            else:
                if meta_info.type == MediaType.TV:
                    # 确定是电视
                    file_media_info = self.__search_tmdb(file_media_name=meta_info.get_name(),
                                                         first_media_year=meta_info.year,
                                                         search_type=meta_info.type,
                                                         media_year=meta_info.year,
                                                         season_number=meta_info.begin_season
                                                         )
                    if not file_media_info and meta_info.year and self._rmt_match_mode == MatchMode.NORMAL and not strict:
                        # 非严格模式下去掉年份再查一次
                        file_media_info = self.__search_tmdb(file_media_name=meta_info.get_name(),
                                                             search_type=meta_info.type
                                                             )
                else:
                    # 有年份先按电影查
                    file_media_info = self.__search_tmdb(file_media_name=meta_info.get_name(),
                                                         first_media_year=meta_info.year,
                                                         search_type=MediaType.MOVIE
                                                         )
                    # 没有再按电视剧查
                    if not file_media_info:
                        file_media_info = self.__search_tmdb(file_media_name=meta_info.get_name(),
                                                             first_media_year=meta_info.year,
                                                             search_type=MediaType.TV
                                                             )
                    if not file_media_info and self._rmt_match_mode == MatchMode.NORMAL and not strict:
                        # 非严格模式下去掉年份和类型再查一次
                        file_media_info = self.__search_multi_tmdb(file_media_name=meta_info.get_name())
            if not file_media_info and self._search_tmdbweb:
                file_media_info = self.__search_tmdb_web(file_media_name=meta_info.get_name(),
                                                         mtype=meta_info.type)
            if not file_media_info and self._search_keyword:
                cache_name = cacheman["tmdb_supply"].get(meta_info.get_name())
                is_movie = False
                if not cache_name:
                    cache_name, is_movie = self.__search_engine(meta_info.get_name())
                    cacheman["tmdb_supply"].set(meta_info.get_name(), cache_name)
                if cache_name:
                    log.info("【Meta】开始辅助查询：%s ..." % cache_name)
                    if is_movie:
                        file_media_info = self.__search_tmdb(file_media_name=cache_name, search_type=MediaType.MOVIE)
                    else:
                        file_media_info = self.__search_multi_tmdb(file_media_name=cache_name)
            # 补充全量信息
            if file_media_info and not file_media_info.get("genres"):
                file_media_info = self.get_tmdb_info(mtype=file_media_info.get("media_type"),
                                                     tmdbid=file_media_info.get("id"),
                                                     chinese=chinese)
            # 保存到缓存
            if file_media_info is not None:
                self.__insert_media_cache(media_key=media_key,
                                          file_media_info=file_media_info)
        else:
            # 使用缓存信息
            cache_info = self.meta.get_meta_data_by_key(media_key)
            if cache_info.get("id"):
                file_media_info = self.get_tmdb_info(mtype=cache_info.get("type"),
                                                     tmdbid=cache_info.get("id"),
                                                     chinese=chinese)
            else:
                file_media_info = None
        # 赋值TMDB信息并返回
        meta_info.set_tmdb_info(file_media_info)
        return meta_info

    def __insert_media_cache(self, media_key, file_media_info):
        """
        将TMDB信息插入缓存
        """
        if file_media_info:
            # 缓存标题
            cache_title = file_media_info.get(
                "title") if file_media_info.get(
                "media_type") == MediaType.MOVIE else file_media_info.get("name")
            # 缓存年份
            cache_year = file_media_info.get('release_date') if file_media_info.get(
                "media_type") == MediaType.MOVIE else file_media_info.get('first_air_date')
            if cache_year:
                cache_year = cache_year[:4]
            self.meta.update_meta_data({
                media_key: {
                    "id": file_media_info.get("id"),
                    "type": file_media_info.get("media_type"),
                    "year": cache_year,
                    "title": cache_title,
                    "poster_path": file_media_info.get("poster_path"),
                    "backdrop_path": file_media_info.get("backdrop_path")
                }
            })
        else:
            self.meta.update_meta_data({media_key: {'id': 0}})

    def get_media_info_on_files(self,
                                file_list,
                                tmdb_info=None,
                                media_type=None,
                                season=None,
                                episode_format: EpisodeFormat = None,
                                chinese=True):
        """
        根据文件清单，搜刮TMDB信息，用于文件名称的识别
        :param file_list: 文件清单，如果是列表也可以是单个文件，也可以是一个目录
        :param tmdb_info: 如有传入TMDB信息则以该TMDB信息赋于所有文件，否则按名称从TMDB检索，用于手工识别时传入
        :param media_type: 媒体类型：电影、电视剧、动漫，如有传入以该类型赋于所有文件，否则按名称从TMDB检索并识别
        :param season: 季号，如有传入以该季号赋于所有文件，否则从名称中识别
        :param episode_format: EpisodeFormat
        :param chinese: 原标题为英文时是否从别名中检索中文名称
        :return: 带有TMDB信息的每个文件对应的MetaInfo对象字典
        """
        # 存储文件路径与媒体的对应关系
        if not self.tmdb:
            log.error("【Meta】TMDB API Key 未设置！")
            return {}
        return_media_infos = {}
        # 不是list的转为list
        if not isinstance(file_list, list):
            file_list = [file_list]
        # 遍历每个文件，看得出来的名称是不是不一样，不一样的先搜索媒体信息
        for file_path in file_list:
            try:
                if not os.path.exists(file_path):
                    log.warn("【Meta】%s 不存在" % file_path)
                    continue
                # 解析媒体名称
                # 先用自己的名称
                file_name = os.path.basename(file_path)
                parent_name = os.path.basename(os.path.dirname(file_path))
                parent_parent_name = os.path.basename(PathUtils.get_parent_paths(file_path, 2))
                # 过滤掉蓝光原盘目录下的子文件
                if not os.path.isdir(file_path) \
                        and PathUtils.get_bluray_dir(file_path):
                    log.info("【Meta】%s 跳过蓝光原盘文件：" % file_path)
                    continue
                # 没有自带TMDB信息
                if not tmdb_info:
                    # 识别名称
                    meta_info = MetaInfo(title=file_name)
                    # 识别不到则使用上级的名称
                    if not meta_info.get_name() or not meta_info.year:
                        parent_info = MetaInfo(parent_name)
                        if not parent_info.get_name() or not parent_info.year:
                            parent_parent_info = MetaInfo(parent_parent_name)
                            parent_info.type = parent_parent_info.type if parent_parent_info.type and parent_info.type != MediaType.TV else parent_info.type
                            parent_info.cn_name = parent_parent_info.cn_name if parent_parent_info.cn_name else parent_info.cn_name
                            parent_info.en_name = parent_parent_info.en_name if parent_parent_info.en_name else parent_info.en_name
                            parent_info.year = parent_parent_info.year if parent_parent_info.year else parent_info.year
                            parent_info.begin_season = NumberUtils.max_ele(parent_info.begin_season,
                                                                           parent_parent_info.begin_season)
                        if not meta_info.get_name():
                            meta_info.cn_name = parent_info.cn_name
                            meta_info.en_name = parent_info.en_name
                        if not meta_info.year:
                            meta_info.year = parent_info.year
                        if parent_info.type and parent_info.type == MediaType.TV \
                                and meta_info.type != MediaType.TV:
                            meta_info.type = parent_info.type
                        if meta_info.type == MediaType.TV:
                            meta_info.begin_season = NumberUtils.max_ele(parent_info.begin_season,
                                                                         meta_info.begin_season)
                    if not meta_info.get_name() or not meta_info.type:
                        log.warn("【Rmt】%s 未识别出有效信息！" % meta_info.org_string)
                        continue
                    # 区配缓存及TMDB
                    media_key = self.__make_cache_key(meta_info)
                    if not self.meta.get_meta_data_by_key(media_key):
                        # 没有缓存数据
                        file_media_info = self.__search_tmdb(file_media_name=meta_info.get_name(),
                                                             first_media_year=meta_info.year,
                                                             search_type=meta_info.type,
                                                             media_year=meta_info.year,
                                                             season_number=meta_info.begin_season)
                        if not file_media_info:
                            if self._rmt_match_mode == MatchMode.NORMAL:
                                # 去掉年份再查一次，有可能是年份错误
                                file_media_info = self.__search_tmdb(file_media_name=meta_info.get_name(),
                                                                     search_type=meta_info.type)
                        if not file_media_info and self._search_tmdbweb:
                            # 从网站查询
                            file_media_info = self.__search_tmdb_web(file_media_name=meta_info.get_name(),
                                                                     mtype=meta_info.type)
                        if not file_media_info and self._search_keyword:
                            cache_name = cacheman["tmdb_supply"].get(meta_info.get_name())
                            is_movie = False
                            if not cache_name:
                                cache_name, is_movie = self.__search_engine(meta_info.get_name())
                                cacheman["tmdb_supply"].set(meta_info.get_name(), cache_name)
                            if cache_name:
                                log.info("【Meta】开始辅助查询：%s ..." % cache_name)
                                if is_movie:
                                    file_media_info = self.__search_tmdb(file_media_name=cache_name,
                                                                         search_type=MediaType.MOVIE)
                                else:
                                    file_media_info = self.__search_multi_tmdb(file_media_name=cache_name)
                        # 补全TMDB信息
                        if file_media_info and not file_media_info.get("genres"):
                            file_media_info = self.get_tmdb_info(mtype=file_media_info.get("media_type"),
                                                                 tmdbid=file_media_info.get("id"),
                                                                 chinese=chinese)
                        # 保存到缓存
                        if file_media_info is not None:
                            self.__insert_media_cache(media_key=media_key,
                                                      file_media_info=file_media_info)
                    else:
                        # 使用缓存信息
                        cache_info = self.meta.get_meta_data_by_key(media_key)
                        if cache_info.get("id"):
                            file_media_info = self.get_tmdb_info(mtype=cache_info.get("type"),
                                                                 tmdbid=cache_info.get("id"),
                                                                 chinese=chinese)
                        else:
                            # 缓存为未识别
                            file_media_info = None
                    # 赋值TMDB信息
                    meta_info.set_tmdb_info(file_media_info)
                # 自带TMDB信息
                else:
                    meta_info = MetaInfo(title=file_name, mtype=media_type)
                    meta_info.set_tmdb_info(tmdb_info)
                    if season and meta_info.type != MediaType.MOVIE:
                        meta_info.begin_season = int(season)
                    if episode_format:
                        begin_ep, end_ep = episode_format.split_episode(file_name)
                        if begin_ep is not None:
                            meta_info.begin_episode = begin_ep
                        if end_ep is not None:
                            meta_info.end_episode = end_ep
                    # 加入缓存
                    self.save_rename_cache(file_name, tmdb_info)
                # 按文件路程存储
                return_media_infos[file_path] = meta_info
            except Exception as err:
                print(str(err))
                log.error("【Rmt】发生错误：%s - %s" % (str(err), traceback.format_exc()))
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

    def get_tmdb_upcoming_movies(self, page):
        """
        获取即将上映电影
        :param page: 第几页
        :return: TMDB信息列表
        """
        if not self.movie:
            return []
        return self.movie.upcoming(page)

    def __get_tmdb_movie_detail(self, tmdbid, append_to_response=None):
        """
        获取电影的详情
        :param tmdbid: TMDB ID
        :return: TMDB信息
        """
        if not self.movie:
            return {}
        try:
            log.info("【Meta】正在查询TMDB电影：%s ..." % tmdbid)
            tmdbinfo = self.movie.details(tmdbid, append_to_response)
            return tmdbinfo or {}
        except Exception as e:
            print(str(e))
            return None

    def __get_tmdb_tv_detail(self, tmdbid, append_to_response=None):
        """
        获取电视剧的详情
        :param tmdbid: TMDB ID
        :return: TMDB信息
        """
        if not self.tv:
            return {}
        try:
            log.info("【Meta】正在查询TMDB电视剧：%s ..." % tmdbid)
            tmdbinfo = self.tv.details(tmdbid, append_to_response)
            return tmdbinfo or {}
        except Exception as e:
            print(str(e))
            return None

    def get_tmdb_tv_season_detail(self, tmdbid, season):
        """
        获取电视剧季的详情
        :param tmdbid: TMDB ID
        :param season: 季，数字
        :return: TMDB信息
        """
        if not self.tv:
            return {}
        try:
            log.info("【Meta】正在查询TMDB电视剧：%s，季：%s ..." % (tmdbid, season))
            tmdbinfo = self.tv.season_details(tmdbid, season)
            return tmdbinfo or {}
        except Exception as e:
            print(str(e))
            return {}

    def get_tmdb_seasons_list(self, tv_info=None, tmdbid=None):
        """
        从TMDB的季集信息中获得季的组
        :param tv_info: TMDB 的季信息
        :param tmdbid: TMDB ID 没有tv_info且有tmdbid时，重新从TMDB查询季的信息
        :return: 带有season_number、episode_count 的每季总集数的字典列表
        """
        if not tv_info and not tmdbid:
            return []
        if not tv_info and tmdbid:
            tv_info = self.__get_tmdb_tv_detail(tmdbid, append_to_response="")
        if not tv_info:
            return []
        seasons = tv_info.get("seasons")
        if not seasons:
            return []
        total_seasons = []
        for season in seasons:
            if season.get("episode_count"):
                total_seasons.append(
                    {"season_number": season.get("season_number"),
                     "episode_count": season.get("episode_count"),
                     "air_date": season.get("air_date")})
        return total_seasons

    def get_tmdb_season_episodes_num(self, sea: int, tv_info=None, tmdbid=None):
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
            tv_info = self.__get_tmdb_tv_detail(tmdbid, append_to_response="")
        if not tv_info:
            return 0
        seasons = tv_info.get("seasons")
        if not seasons:
            return 0
        for season in seasons:
            if season.get("season_number") == sea:
                return int(season.get("episode_count"))
        return 0

    def get_tmdb_en_title(self, media_info):
        """
        获取TMDB的英文名称
        """
        en_info = self.get_tmdb_info(mtype=media_info.type,
                                     tmdbid=media_info.tmdb_id,
                                     language="en-US")
        if en_info:
            return en_info.get("title") if media_info.type == MediaType.MOVIE else en_info.get("name")
        return None

    def get_episode_title(self, media_info):
        """
        获取剧集的标题
        """
        if media_info.type == MediaType.MOVIE:
            return None
        if media_info.tmdb_id:
            if not media_info.begin_episode:
                return None
            tv_info = self.get_tmdb_tv_season_detail(tmdbid=media_info.tmdb_id,
                                                     season=int(media_info.get_season_seq()))
            if tv_info:
                for episode in tv_info.get("episodes") or []:
                    if episode.get("episode_number") == media_info.begin_episode:
                        return episode.get("name")
        return None

    def get_movie_discover(self, page=1):
        """
        发现电影
        """
        if not self.movie:
            return {}
        try:
            movies = self.movie.discover(page)
            return movies
        except Exception as e:
            print(str(e))
            return {}

    @staticmethod
    def __search_engine(feature_name):
        """
        辅助识别关键字
        """
        is_movie = False
        if not feature_name:
            return None, is_movie
        # 剔除不必要字符
        feature_name = re.compile(r"^\w+字幕[组社]?", re.IGNORECASE).sub("", feature_name)
        backlist = sorted(KEYWORD_BLACKLIST, key=lambda x: len(x), reverse=True)
        for single in backlist:
            feature_name = feature_name.replace(single, " ")
        if not feature_name:
            return None, is_movie

        def cal_score(strongs, r_dict):
            for i, s in enumerate(strongs):
                if len(strongs) < 5:
                    if i < 2:
                        score = KEYWORD_SEARCH_WEIGHT_3[0]
                    else:
                        score = KEYWORD_SEARCH_WEIGHT_3[1]
                elif len(strongs) < 10:
                    if i < 2:
                        score = KEYWORD_SEARCH_WEIGHT_2[0]
                    else:
                        score = KEYWORD_SEARCH_WEIGHT_2[1] if i < (len(strongs) >> 1) else KEYWORD_SEARCH_WEIGHT_2[2]
                else:
                    if i < 2:
                        score = KEYWORD_SEARCH_WEIGHT_1[0]
                    else:
                        score = KEYWORD_SEARCH_WEIGHT_1[1] if i < (len(strongs) >> 2) else KEYWORD_SEARCH_WEIGHT_1[
                            2] if i < (
                                len(strongs) >> 1) \
                            else KEYWORD_SEARCH_WEIGHT_1[3] if i < (len(strongs) >> 2 + len(strongs) >> 1) else \
                            KEYWORD_SEARCH_WEIGHT_1[
                                4]
                if r_dict.__contains__(s.lower()):
                    r_dict[s.lower()] += score
                    continue
                r_dict[s.lower()] = score

        bing_url = "https://www.cn.bing.com/search?q=%s&qs=n&form=QBRE&sp=-1" % feature_name
        baidu_url = "https://www.baidu.com/s?ie=utf-8&tn=baiduhome_pg&wd=%s" % feature_name
        res_bing = RequestUtils(timeout=5).get_res(url=bing_url)
        res_baidu = RequestUtils(timeout=5).get_res(url=baidu_url)
        ret_dict = {}
        if res_bing and res_bing.status_code == 200:
            html_text = res_bing.text
            if html_text:
                html = etree.HTML(html_text)
                strongs_bing = list(
                    filter(lambda x: (0 if not x else difflib.SequenceMatcher(None, feature_name,
                                                                              x).ratio()) > KEYWORD_STR_SIMILARITY_THRESHOLD,
                           map(lambda x: x.text, html.cssselect(
                               "#sp_requery strong, #sp_recourse strong, #tile_link_cn strong, .b_ad .ad_esltitle~div strong, h2 strong, .b_caption p strong, .b_snippetBigText strong, .recommendationsTableTitle+.b_slideexp strong, .recommendationsTableTitle+table strong, .recommendationsTableTitle+ul strong, .pageRecoContainer .b_module_expansion_control strong, .pageRecoContainer .b_title>strong, .b_rs strong, .b_rrsr strong, #dict_ans strong, .b_listnav>.b_ans_stamp>strong, #b_content #ans_nws .na_cnt strong, .adltwrnmsg strong"))))
                if strongs_bing:
                    title = html.xpath("//aside//h2[@class = \" b_entityTitle\"]/text()")
                    if len(title) > 0:
                        if title:
                            t = re.compile(r"\s*\(\d{4}\)$").sub("", title[0])
                            ret_dict[t] = 200
                            if html.xpath("//aside//div[@data-feedbk-ids = \"Movie\"]"):
                                is_movie = True
                    cal_score(strongs_bing, ret_dict)
        if res_baidu and res_baidu.status_code == 200:
            html_text = res_baidu.text
            if html_text:
                html = etree.HTML(html_text)
                ems = list(
                    filter(lambda x: (0 if not x else difflib.SequenceMatcher(None, feature_name,
                                                                              x).ratio()) > KEYWORD_STR_SIMILARITY_THRESHOLD,
                           map(lambda x: x.text, html.cssselect("em"))))
                if len(ems) > 0:
                    cal_score(ems, ret_dict)
        if not ret_dict:
            return None, False
        ret = sorted(ret_dict.items(), key=lambda d: d[1], reverse=True)
        log.info("【Meta】推断关键字为：%s ..." % ([k[0] for i, k in enumerate(ret) if i < 4]))
        if len(ret) == 1:
            keyword = ret[0][0]
        else:
            pre = ret[0]
            nextw = ret[1]
            if nextw[0].find(pre[0]) > -1:
                # 满分直接判定
                if int(pre[1]) >= 100:
                    keyword = pre[0]
                # 得分相差30 以上， 选分高
                elif int(pre[1]) - int(nextw[1]) > KEYWORD_DIFF_SCORE_THRESHOLD:
                    keyword = pre[0]
                # 重复的不选
                elif nextw[0].replace(pre[0], "").strip() == pre[0]:
                    keyword = pre[0]
                # 纯数字不选
                elif pre[0].isdigit():
                    keyword = nextw[0]
                else:
                    keyword = nextw[0]

            else:
                keyword = pre[0]
        log.info("【Meta】选择关键字为：%s " % keyword)
        return keyword, is_movie

    @staticmethod
    def __get_genre_ids_from_detail(genres):
        """
        从TMDB详情中获取genre_id列表
        """
        if not genres:
            return []
        genre_ids = []
        for genre in genres:
            genre_ids.append(genre.get('id'))
        return genre_ids

    def __get_tmdb_chinese_title(self, tmdbinfo=None, mtype: MediaType = None, tmdbid=None):
        """
        从别名中获取中文标题
        """
        if not tmdbinfo and not tmdbid:
            return None
        if tmdbinfo:
            if tmdbinfo.get("media_type") == MediaType.MOVIE:
                alternative_titles = tmdbinfo.get("alternative_titles", {}).get("titles", [])
            else:
                alternative_titles = tmdbinfo.get("alternative_titles", {}).get("results", [])
        else:
            try:
                if mtype == MediaType.MOVIE:
                    titles_info = self.movie.alternative_titles(tmdbid) or {}
                    alternative_titles = titles_info.get("titles", [])
                else:
                    titles_info = self.tv.alternative_titles(tmdbid) or {}
                    alternative_titles = titles_info.get("results", [])
            except Exception as err:
                print(str(err))
                return None
        for alternative_title in alternative_titles:
            iso_3166_1 = alternative_title.get("iso_3166_1")
            if iso_3166_1 == "CN":
                title = alternative_title.get("title")
                if title and StringUtils.is_chinese(title) and zhconv.convert(title, "zh-hans") == title:
                    return title
        if tmdbinfo:
            return tmdbinfo.get("title") if tmdbinfo.get("media_type") == MediaType.MOVIE else tmdbinfo.get("name")
        return None

    def get_tmdbperson_chinese_name(self, person_id):
        """
        查询TMDB人物中文名称
        """
        if not self.person:
            return ""
        alter_names = []
        name = ""
        try:
            aka_names = self.person.details(person_id).get("also_known_as", []) or []
        except Exception as err:
            print(str(err))
            return ""
        for aka_name in aka_names:
            if StringUtils.is_chinese(aka_name):
                alter_names.append(aka_name)
        if len(alter_names) == 1:
            name = alter_names[0]
        elif len(alter_names) > 1:
            for alter_name in alter_names:
                if alter_name == zhconv.convert(alter_name, 'zh-hans'):
                    name = alter_name
        return name

    def get_tmdbperson_aka_names(self, person_id):
        """
        查询人物又名
        """
        if not self.person:
            return []
        try:
            aka_names = self.person.details(person_id).get("also_known_as", []) or []
            return aka_names
        except Exception as err:
            print(str(err))
            return []

    def get_random_discover_backdrop(self):
        """
        获取TMDB热门电影随机一张背景图
        """
        movies = self.get_movie_discover()
        if movies:
            backdrops = [movie.get("backdrop_path") for movie in movies.get("results")]
            return TMDB_IMAGE_ORIGINAL_URL % backdrops[round(random.uniform(0, len(backdrops) - 1))]
        return ""

    def save_rename_cache(self, file_name, cache_info):
        """
        将手动识别的信息加入缓存
        """
        if not file_name or not cache_info:
            return
        meta_info = MetaInfo(title=file_name)
        self.__insert_media_cache(self.__make_cache_key(meta_info), cache_info)

    @staticmethod
    def merge_media_info(target, source):
        """
        将soruce中有效的信息合并到target中并返回
        """
        target.set_tmdb_info(source.tmdb_info)
        target.fanart_poster = source.get_poster_image()
        target.fanart_backdrop = source.get_backdrop_image()
        target.set_download_info(download_setting=source.download_setting,
                                 save_path=source.save_path)
        return target

    def get_tmdbid_by_imdbid(self, imdbid):
        """
        根据IMDBID查询TMDB信息
        """
        if not self.find:
            return None
        try:
            result = self.find.find_by_imdbid(imdbid) or {}
            tmdbinfo = result.get('movie_results') or result.get("tv_results")
            if tmdbinfo:
                tmdbinfo = tmdbinfo[0]
                return tmdbinfo.get("id")
        except Exception as err:
            print(str(err))
        return None

    @staticmethod
    def get_intersection_episodes(target, source, title):
        """
        对两个季集字典进行判重，有相同项目的取集的交集
        """
        if not source or not title:
            return target
        if not source.get(title):
            return target
        if not target.get(title):
            target[title] = source.get(title)
            return target
        index = -1
        for target_info in target.get(title):
            index += 1
            source_info = None
            for info in source.get(title):
                if info.get("season") == target_info.get("season"):
                    source_info = info
                    break
            if not source_info:
                continue
            if not source_info.get("episodes"):
                continue
            if not target_info.get("episodes"):
                target_episodes = source_info.get("episodes")
                target[title][index]["episodes"] = target_episodes
                continue
            target_episodes = list(set(target_info.get("episodes")).intersection(set(source_info.get("episodes"))))
            target[title][index]["episodes"] = target_episodes
        return target
