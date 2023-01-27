import random
from threading import Lock
from time import sleep

import zhconv

from app.utils.commons import singleton
from app.utils import ExceptionUtils, StringUtils

import log
from config import Config
from app.media.doubanapi import DoubanApi, DoubanWeb
from app.media.meta import MetaInfo
from app.utils import RequestUtils
from app.utils.types import MediaType

lock = Lock()


@singleton
class DouBan:
    cookie = None
    doubanapi = None
    doubanweb = None
    message = None
    _movie_num = 30
    _tv_num = 30

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.doubanapi = DoubanApi()
        self.doubanweb = DoubanWeb()
        douban = Config().get_config('douban')
        if douban:
            # Cookie
            self.cookie = douban.get('cookie')
            if not self.cookie:
                try:
                    res = RequestUtils(timeout=5).get_res("https://www.douban.com/")
                    if res:
                        self.cookie = StringUtils.str_from_cookiejar(res.cookies)
                except Exception as err:
                    ExceptionUtils.exception_traceback(err)
                    log.warn(f"【Douban】获取cookie失败：{format(err)}")

    def get_douban_detail(self, doubanid, mtype=None, wait=False):
        """
        根据豆瓣ID返回豆瓣详情，带休眠
        """
        log.info("【Douban】正在通过API查询豆瓣详情：%s" % doubanid)
        # 随机休眠
        if wait:
            time = round(random.uniform(1, 5), 1)
            log.info("【Douban】随机休眠：%s 秒" % time)
            sleep(time)
        if mtype == MediaType.MOVIE:
            douban_info = self.doubanapi.movie_detail(doubanid)
        elif mtype:
            douban_info = self.doubanapi.tv_detail(doubanid)
        else:
            douban_info = self.doubanapi.movie_detail(doubanid)
            if not douban_info:
                douban_info = self.doubanapi.tv_detail(doubanid)
        if not douban_info:
            log.warn("【Douban】%s 未找到豆瓣详细信息" % doubanid)
            return None
        if douban_info.get("localized_message"):
            log.warn("【Douban】查询豆瓣详情错误：%s" % douban_info.get("localized_message"))
            return None
        if not douban_info.get("title"):
            return None
        if douban_info.get("title") == "未知电影" or douban_info.get("title") == "未知电视剧":
            return None
        log.info("【Douban】查询到数据：%s" % douban_info.get("title"))
        return douban_info

    def __search_douban_id(self, metainfo):
        """
        给定名称和年份，查询一条豆瓣信息返回对应ID
        :param metainfo: 已进行识别过的媒体信息
        """
        if metainfo.year:
            year_range = [int(metainfo.year), int(metainfo.year) + 1, int(metainfo.year) - 1]
        else:
            year_range = []
        if metainfo.type == MediaType.MOVIE:
            search_res = self.doubanapi.movie_search(metainfo.title).get("items") or []
            if not search_res:
                return None
            for res in search_res:
                douban_meta = MetaInfo(title=res.get("target", {}).get("title"))
                if metainfo.title == douban_meta.get_name() \
                        and (int(res.get("target", {}).get("year")) in year_range or not year_range):
                    return res.get("target_id")
            return None
        elif metainfo.type == MediaType.TV:
            search_res = self.doubanapi.tv_search(metainfo.title).get("items") or []
            if not search_res:
                return None
            for res in search_res:
                douban_meta = MetaInfo(title=res.get("target", {}).get("title"))
                if metainfo.title == douban_meta.get_name() \
                        and (str(res.get("target", {}).get("year")) == str(metainfo.year) or not metainfo.year):
                    return res.get("target_id")
                if metainfo.title == douban_meta.get_name() \
                        and metainfo.get_season_string() == douban_meta.get_season_string():
                    return res.get("target_id")
            return search_res[0].get("target_id")

    def get_douban_info(self, metainfo):
        """
        查询附带演职人员的豆瓣信息
        :param metainfo: 已进行识别过的媒体信息
        """
        doubanid = self.__search_douban_id(metainfo)
        if not doubanid:
            return None
        if metainfo.type == MediaType.MOVIE:
            douban_info = self.doubanapi.movie_detail(doubanid)
            celebrities = self.doubanapi.movie_celebrities(doubanid)
            if douban_info and celebrities:
                douban_info["directors"] = celebrities.get("directors")
                douban_info["actors"] = celebrities.get("actors")
            return douban_info
        elif metainfo.type == MediaType.TV:
            douban_info = self.doubanapi.tv_detail(doubanid)
            celebrities = self.doubanapi.tv_celebrities(doubanid)
            if douban_info and celebrities:
                douban_info["directors"] = celebrities.get("directors")
                douban_info["actors"] = celebrities.get("actors")
            return douban_info

    def get_douban_wish(self, dtype, userid, start, wait=False):
        """
        获取豆瓣想看列表数据
        """
        if wait:
            time = round(random.uniform(1, 5), 1)
            log.info("【Douban】随机休眠：%s 秒" % time)
            sleep(time)
        if dtype == "do":
            web_infos = self.doubanweb.do(cookie=self.cookie, userid=userid, start=start)
        elif dtype == "collect":
            web_infos = self.doubanweb.collect(cookie=self.cookie, userid=userid, start=start)
        else:
            web_infos = self.doubanweb.wish(cookie=self.cookie, userid=userid, start=start)
        if not web_infos:
            return []
        for web_info in web_infos:
            web_info["id"] = web_info.get("url").split("/")[-2]
        return web_infos

    def get_user_info(self, userid, wait=False):
        if wait:
            time = round(random.uniform(1, 5), 1)
            log.info("【Douban】随机休眠：%s 秒" % time)
            sleep(time)
        return self.doubanweb.user(cookie=self.cookie, userid=userid)

    def search_douban_medias(self, keyword, mtype: MediaType = None, season=None, episode=None, page=1):
        """
        根据关键字搜索豆瓣，返回可能的标题和年份信息
        """
        if not keyword:
            return []
        result = self.doubanapi.search(keyword)
        if not result:
            return []
        ret_medias = []
        for item_obj in result.get("items"):
            if mtype and mtype.value != item_obj.get("type_name"):
                continue
            if item_obj.get("type_name") not in (MediaType.TV.value, MediaType.MOVIE.value):
                continue
            item = item_obj.get("target")
            meta_info = MetaInfo(title=item.get("title"))
            meta_info.title = item.get("title")
            if item_obj.get("type_name") == MediaType.MOVIE.value:
                meta_info.type = MediaType.MOVIE
            else:
                meta_info.type = MediaType.TV
            if season:
                if meta_info.type != MediaType.TV:
                    continue
                if season != 1 and meta_info.begin_season != season:
                    continue
            if episode and str(episode).isdigit():
                if meta_info.type != MediaType.TV:
                    continue
                meta_info.begin_episode = int(episode)
                meta_info.title = "%s 第%s集" % (meta_info.title, episode)
            meta_info.year = item.get("year")
            meta_info.tmdb_id = "DB:%s" % item.get("id")
            meta_info.douban_id = item.get("id")
            meta_info.overview = item.get("card_subtitle") or ""
            meta_info.poster_path = item.get("cover_url").split('?')[0]
            rating = item.get("rating", {}) or {}
            meta_info.vote_average = rating.get("value")
            if meta_info not in ret_medias:
                ret_medias.append(meta_info)

        return ret_medias[(page - 1) * 20:page * 20]

    def get_media_detail_from_web(self, doubanid):
        """
        从豆瓣详情页抓紧媒体信息
        :param doubanid: 豆瓣ID
        :return: {title, year, intro, cover_url, rating{value}, episodes_count}
        """
        log.info("【Douban】正在通过网页查询豆瓣详情：%s" % doubanid)
        web_info = self.doubanweb.detail(cookie=self.cookie, doubanid=doubanid)
        if not web_info:
            return {}
        ret_media = {}
        try:
            # 标题
            title = web_info.get("title")
            if title:
                title = title
                metainfo = MetaInfo(title=title)
                if metainfo.cn_name:
                    title = metainfo.cn_name
                    # 有中文的去掉日文和韩文
                    if title and StringUtils.is_chinese(title) and " " in title:
                        titles = title.split()
                        title = titles[0]
                        for _title in titles[1:]:
                            # 忽略繁体
                            if zhconv.convert(_title, 'zh-hans') == title:
                                break
                            # 忽略日韩文
                            if not StringUtils.is_japanese(_title) \
                                    and not StringUtils.is_korean(_title):
                                title = f"{title} {_title}"
                                break
                            else:
                                break
                else:
                    title = metainfo.en_name
                if not title:
                    return None
                ret_media['title'] = title
                ret_media['season'] = metainfo.begin_season
            else:
                return None
            # 年份
            year = web_info.get("year")
            if year:
                ret_media['year'] = year[1:-1]
            # 简介
            ret_media['intro'] = "".join(
                [str(x).strip() for x in web_info.get("intro") or []])
            # 封面图
            cover_url = web_info.get("cover")
            if cover_url:
                ret_media['cover_url'] = cover_url.replace("s_ratio_poster", "m_ratio_poster")
            # 评分
            rating = web_info.get("rate")
            if rating:
                ret_media['rating'] = {"value": float(rating)}
            # 季数
            season_num = web_info.get("season_num")
            if season_num:
                ret_media['season'] = int(season_num)
            # 集数
            episode_num = web_info.get("episode_num")
            if episode_num:
                ret_media['episodes_count'] = int(episode_num)
            # IMDBID
            imdbid = web_info.get('imdb')
            if imdbid:
                ret_media['imdbid'] = str(imdbid).strip()
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
        if ret_media:
            log.info("【Douban】查询到数据：%s" % ret_media.get("title"))
        else:
            log.warn("【Douban】%s 未查询到豆瓣数据：%s" % doubanid)
        return ret_media

    def get_douban_online_movie(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.movie_showing(start=(page - 1) * self._movie_num, count=self._movie_num)
        if not infos:
            return []
        return self.__refresh_movie(infos.get("subject_collection_items"))

    def get_douban_hot_movie(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.movie_hot_gaia(start=(page - 1) * self._movie_num, count=self._movie_num)
        if not infos:
            return []
        return self.__refresh_movie(infos.get("subject_collection_items"))

    def get_douban_hot_anime(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.tv_animation(start=(page - 1) * self._tv_num, count=self._tv_num)
        if not infos:
            return []
        return self.__refresh_tv(infos.get("subject_collection_items"))

    def get_douban_hot_tv(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.tv_hot(start=(page - 1) * self._tv_num, count=self._tv_num)
        if not infos:
            return []
        return self.__refresh_tv(infos.get("subject_collection_items"))

    def get_douban_new_movie(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.movie_soon(start=(page - 1) * self._movie_num, count=self._movie_num)
        if not infos:
            return []
        return self.__refresh_movie(infos.get("subject_collection_items"))

    def get_douban_hot_show(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.show_hot(start=(page - 1) * self._tv_num, count=self._tv_num)
        if not infos:
            return []
        return self.__refresh_tv(infos.get("subject_collection_items"))

    def get_douban_top250_movie(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.movie_top250(start=(page - 1) * self._movie_num, count=self._movie_num)
        if not infos:
            return []
        return self.__refresh_movie(infos.get("subject_collection_items"))

    @staticmethod
    def __refresh_movie(infos):
        if not infos:
            return []
        ret_list = []
        for info in infos:
            try:
                if not info:
                    continue
                # ID
                rid = info.get("id")
                # 评分
                rating = info.get('rating')
                if rating:
                    vote_average = float(rating.get("value"))
                else:
                    vote_average = 0
                # 年份
                year = info.get('year')
                # 海报
                poster_path = info.get('cover', {}).get("url")
                if not poster_path:
                    poster_path = info.get('cover_url')
                if poster_path:
                    poster_path = poster_path.replace("s_ratio_poster", "m_ratio_poster")
                # 标题
                title = info.get('title')
                if not title or not poster_path:
                    continue
                # 简介
                overview = info.get("card_subtitle") or ""
                if not year and overview:
                    if overview.split("/")[0].strip().isdigit():
                        year = overview.split("/")[0].strip()
                ret_list.append({
                    'id': "DB:%s" % rid,
                    'orgid': rid,
                    'title': title,
                    'type': 'MOV',
                    'year': year[:4] if year else "",
                    'vote': vote_average,
                    'image': poster_path,
                    'overview': overview
                })
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
        return ret_list

    @staticmethod
    def __refresh_tv(infos):
        if not infos:
            return []
        ret_list = []
        for info in infos:
            try:
                if not info:
                    continue
                # ID
                rid = info.get("id")
                # 评分
                rating = info.get('rating')
                if rating:
                    vote_average = float(rating.get("value"))
                else:
                    vote_average = 0
                # 年份
                year = info.get('year')
                # 海报
                poster_path = info.get('pic', {}).get("normal")
                if poster_path:
                    poster_path = poster_path.replace("s_ratio_poster", "m_ratio_poster")
                # 标题
                title = info.get('title')
                if not title or not poster_path:
                    continue
                # 简介
                overview = info.get("comment") or ""
                ret_list.append({
                    'id': "DB:%s" % rid,
                    'orgid': rid,
                    'title': title,
                    'type': 'TV',
                    'year': year[:4] if year else "",
                    'vote': vote_average,
                    'image': poster_path,
                    'overview': overview
                })
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
        return ret_list
