# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from functools import lru_cache

import requests

from app.utils.commons import singleton
from app.utils import RequestUtils

logger = logging.getLogger(__name__)


@singleton
class DoubanApi(object):
    _urls = {
        # 搜索类 sort=U:近期热门 T:标记最多 S:评分最高 R:最新上映
        # q=search_word&start=0&count=20&sort=U
        # 聚合搜索
        "search": "/search/weixin",
        "search_agg": "/search",

        # tags='日本,动画,2022'&start=0&count=20&sort=U
        "movie_recommend": "/movie/recommend",
        "movie_tag": "/movie/tag",
        "tv_tag": "/tv/tag",

        # q=search_word&start=0&count=20
        "movie_search": "/search/movie",
        "tv_search": "/search/movie",
        "book_search": "/search/book",
        "group_search": "/search/group",

        # 各类主题合集
        # start=0&count=20
        "movie_showing": "/subject_collection/movie_showing/items",
        "movie_hot_gaia": "/subject_collection/movie_hot_gaia/items",
        "movie_soon": "/subject_collection/movie_soon/items",
        "movie_top250": "/subject_collection/movie_top250/items",
        # 高分经典科幻片榜
        "movie_scifi": "/subject_collection/movie_scifi/items",
        # 高分经典喜剧片榜
        "movie_comedy": "/subject_collection/movie_comedy/items",
        # 高分经典动作片榜
        "movie_action": "/subject_collection/movie_action/items",
        # 高分经典爱情片榜
        "movie_love": "/subject_collection/movie_love/items",

        "tv_hot": "/subject_collection/tv_hot/items",
        "tv_domestic": "/subject_collection/tv_domestic/items",
        "tv_american": "/subject_collection/tv_american/items",
        "tv_japanese": "/subject_collection/tv_japanese/items",
        "tv_korean": "/subject_collection/tv_korean/items",
        "tv_animation": "/subject_collection/tv_animation/items",
        "tv_variety_show": "/subject_collection/tv_variety_show/items",
        "tv_chinese_best_weekly": "/subject_collection/tv_chinese_best_weekly/items",
        "tv_global_best_weekly": "/subject_collection/tv_global_best_weekly/items",

        # 综艺
        "show_hot": "/subject_collection/show_hot/items",
        "show_domestic": "/subject_collection/show_domestic/items",
        "show_foreign": "/subject_collection/show_foreign/items",

        "book_bestseller": "/subject_collection/book_bestseller/items",
        "book_top250": "/subject_collection/book_top250/items",
        # 虚构类热门榜
        "book_fiction_hot_weekly": "/subject_collection/book_fiction_hot_weekly/items",
        # 非虚构类热门
        "book_nonfiction_hot_weekly": "/subject_collection/book_nonfiction_hot_weekly/items",

        "music_single": "/subject_collection/music_single/items",

        # rank list
        "movie_rank_list": "/movie/rank_list",
        "movie_year_ranks": "/movie/year_ranks",
        "book_rank_list": "/book/rank_list",
        "tv_rank_list": "/tv/rank_list",

        # movie info
        "movie_detail": "/movie/",
        "movie_rating": "/movie/%s/rating",
        "movie_photos": "/movie/%s/photos",
        "movie_trailers": "/movie/%s/trailers",
        "movie_interests": "/movie/%s/interests",
        "movie_reviews": "/movie/%s/reviews",
        "movie_recommendations": "/movie/%s/recommendations",
        "movie_celebrities": "/movie/%s/celebrities",

        # tv info
        "tv_detail": "/tv/",
        "tv_rating": "/tv/%s/rating",
        "tv_photos": "/tv/%s/photos",
        "tv_trailers": "/tv/%s/trailers",
        "tv_interests": "/tv/%s/interests",
        "tv_reviews": "/tv/%s/reviews",
        "tv_recommendations": "/tv/%s/recommendations",
        "tv_celebrities": "/tv/%s/celebrities",

        # book info
        "book_detail": "/book/",
        "book_rating": "/book/%s/rating",
        "book_interests": "/book/%s/interests",
        "book_reviews": "/book/%s/reviews",
        "book_recommendations": "/book/%s/recommendations",

        # music info
        "music_detail": "/music/",
        "music_rating": "/music/%s/rating",
        "music_interests": "/music/%s/interests",
        "music_reviews": "/music/%s/reviews",
        "music_recommendations": "/music/%s/recommendations",
    }

    _user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.20(0x18001434) NetType/WIFI Language/en"
    _headers = {'User-Agent': _user_agent,
                'Referer': 'https://servicewechat.com/wx2f9b06c1de1ccfca/84/page-frame.html',
                'Accept-Encoding': 'gzip,compress,deflate',
                'content-type': 'application/json'}
    _api_key = "0ac44ae016490db2204ce0a042db2916"
    _base_url = "https://frodo.douban.com/api/v2"
    _req = RequestUtils(headers=_headers, session=requests.Session())

    def __init__(self):
        pass

    @classmethod
    @lru_cache(maxsize=128)
    def __invoke(cls, url, **kwargs):
        req_url = cls._base_url + url

        params = {'apiKey': cls._api_key}
        if kwargs:
            params.update(kwargs)

        resp = cls._req.get_res(url=req_url, params=params)
        return resp.json() if resp else None

    def search(self, keyword, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["search"], q=keyword, start=start, count=count, _ts=ts)

    def movie_search(self, keyword, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["movie_search"], q=keyword, start=start, count=count, _ts=ts)

    def tv_search(self, keyword, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["tv_search"], q=keyword, start=start, count=count, _ts=ts)

    def book_search(self, keyword, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["book_search"], q=keyword, start=start, count=count, _ts=ts)

    def group_search(self, keyword, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["group_search"], q=keyword, start=start, count=count, _ts=ts)

    def movie_showing(self, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["movie_showing"], start=start, count=count, _ts=ts)

    def movie_soon(self, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["movie_soon"], start=start, count=count, _ts=ts)

    def movie_hot_gaia(self, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["movie_hot_gaia"], start=start, count=count, _ts=ts)

    def tv_hot(self, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["tv_hot"], start=start, count=count, _ts=ts)

    def tv_animation(self, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["tv_animation"], start=start, count=count, _ts=ts)

    def tv_variety_show(self, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["tv_variety_show"], start=start, count=count, _ts=ts)

    def tv_rank_list(self, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["tv_rank_list"], start=start, count=count, _ts=ts)

    def show_hot(self, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["show_hot"], start=start, count=count, _ts=ts)

    def movie_detail(self, subject_id):
        return self.__invoke(self._urls["movie_detail"] + subject_id)

    def movie_celebrities(self, subject_id):
        return self.__invoke(self._urls["movie_celebrities"] % subject_id)

    def tv_detail(self, subject_id):
        return self.__invoke(self._urls["tv_detail"] + subject_id)

    def tv_celebrities(self, subject_id):
        return self.__invoke(self._urls["tv_celebrities"] % subject_id)

    def book_detail(self, subject_id):
        return self.__invoke(self._urls["book_detail"] + subject_id)

    def movie_top250(self, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["movie_top250"], start=start, count=count, _ts=ts)
