# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
from datetime import datetime
from functools import lru_cache
from random import choice
from urllib import parse

import requests

from app.utils import RequestUtils
from app.utils.commons import singleton


@singleton
class DoubanApi(object):
    _urls = {
        # 搜索类
        # sort=U:近期热门 T:标记最多 S:评分最高 R:最新上映
        # q=search_word&start=0&count=20&sort=U
        # 聚合搜索
        "search": "/search/weixin",
        "search_agg": "/search",

        # 电影探索
        # sort=U:综合排序 T:近期热度 S:高分优先 R:首播时间
        # tags='日本,动画,2022'&start=0&count=20&sort=U
        "movie_recommend": "/movie/recommend",
        # 电视剧探索
        "tv_recommend": "/tv/recommend",
        # 搜索
        "movie_tag": "/movie/tag",
        "tv_tag": "/tv/tag",
        # q=search_word&start=0&count=20
        "movie_search": "/search/movie",
        "tv_search": "/search/movie",
        "book_search": "/search/book",
        "group_search": "/search/group",

        # 各类主题合集
        # start=0&count=20
        # 正在上映
        "movie_showing": "/subject_collection/movie_showing/items",
        # 热门电影
        "movie_hot_gaia": "/subject_collection/movie_hot_gaia/items",
        # 即将上映
        "movie_soon": "/subject_collection/movie_soon/items",
        # TOP250
        "movie_top250": "/subject_collection/movie_top250/items",
        # 高分经典科幻片榜
        "movie_scifi": "/subject_collection/movie_scifi/items",
        # 高分经典喜剧片榜
        "movie_comedy": "/subject_collection/movie_comedy/items",
        # 高分经典动作片榜
        "movie_action": "/subject_collection/movie_action/items",
        # 高分经典爱情片榜
        "movie_love": "/subject_collection/movie_love/items",

        # 热门剧集
        "tv_hot": "/subject_collection/tv_hot/items",
        # 国产剧
        "tv_domestic": "/subject_collection/tv_domestic/items",
        # 美剧
        "tv_american": "/subject_collection/tv_american/items",
        # 本剧
        "tv_japanese": "/subject_collection/tv_japanese/items",
        # 韩剧
        "tv_korean": "/subject_collection/tv_korean/items",
        # 动画
        "tv_animation": "/subject_collection/tv_animation/items",
        # 综艺
        "tv_variety_show": "/subject_collection/tv_variety_show/items",
        # 华语口碑周榜
        "tv_chinese_best_weekly": "/subject_collection/tv_chinese_best_weekly/items",
        # 全球口碑周榜
        "tv_global_best_weekly": "/subject_collection/tv_global_best_weekly/items",

        # 执门综艺
        "show_hot": "/subject_collection/show_hot/items",
        # 国内综艺
        "show_domestic": "/subject_collection/show_domestic/items",
        # 国外综艺
        "show_foreign": "/subject_collection/show_foreign/items",

        "book_bestseller": "/subject_collection/book_bestseller/items",
        "book_top250": "/subject_collection/book_top250/items",
        # 虚构类热门榜
        "book_fiction_hot_weekly": "/subject_collection/book_fiction_hot_weekly/items",
        # 非虚构类热门
        "book_nonfiction_hot_weekly": "/subject_collection/book_nonfiction_hot_weekly/items",

        # 音乐
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

        # doulist
        "doulist": "/doulist/",
        "doulist_items": "/doulist/%s/items",
    }

    _user_agents = [
        "api-client/1 com.douban.frodo/7.22.0.beta9(231) Android/23 product/Mate 40 vendor/HUAWEI model/Mate 40 brand/HUAWEI  rom/android  network/wifi  platform/AndroidPad"
        "api-client/1 com.douban.frodo/7.18.0(230) Android/22 product/MI 9 vendor/Xiaomi model/MI 9 brand/Android  rom/miui6  network/wifi  platform/mobile nd/1",
        "api-client/1 com.douban.frodo/7.1.0(205) Android/29 product/perseus vendor/Xiaomi model/Mi MIX 3  rom/miui6  network/wifi  platform/mobile nd/1",
        "api-client/1 com.douban.frodo/7.3.0(207) Android/22 product/MI 9 vendor/Xiaomi model/MI 9 brand/Android  rom/miui6  network/wifi platform/mobile nd/1"]
    _api_secret_key = "bf7dddc7c9cfe6f7"
    _api_key = "0dad551ec0f84ed02907ff5c42e8ec70"
    _base_url = "https://frodo.douban.com/api/v2"
    _session = requests.Session()

    def __init__(self):
        pass

    @classmethod
    def __sign(cls, url: str, ts: int, method='GET') -> str:
        url_path = parse.urlparse(url).path
        raw_sign = '&'.join([method.upper(), parse.quote(url_path, safe=''), str(ts)])
        return base64.b64encode(hmac.new(cls._api_secret_key.encode(), raw_sign.encode(), hashlib.sha1).digest()
                                ).decode()

    @classmethod
    @lru_cache(maxsize=256)
    def __invoke(cls, url, **kwargs):
        req_url = cls._base_url + url

        params = {'apiKey': cls._api_key}
        if kwargs:
            params.update(kwargs)

        ts = params.pop('_ts', int(datetime.strftime(datetime.now(), '%Y%m%d')))
        params.update({'os_rom': 'android', 'apiKey': cls._api_key, '_ts': ts, '_sig': cls.__sign(url=req_url, ts=ts)})

        headers = {'User-Agent': choice(cls._user_agents)}
        resp = RequestUtils(headers=headers, session=cls._session).get_res(url=req_url, params=params)

        return resp.json() if resp else {}

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

    def movie_recommend(self, tags='', sort='T', start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["movie_recommend"], tags=tags, sort=sort, start=start, count=count, _ts=ts)

    def tv_recommend(self, tags='', sort='T', start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["tv_recommend"], tags=tags, sort=sort, start=start, count=count, _ts=ts)

    def tv_chinese_best_weekly(self, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["tv_chinese_best_weekly"], start=start, count=count, _ts=ts)

    def tv_global_best_weekly(self, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        return self.__invoke(self._urls["tv_global_best_weekly"], start=start, count=count, _ts=ts)

    def doulist_detail(self, subject_id):
        """
        豆列详情
        :param subject_id: 豆列id
        :return:
        {
            "is_follow": false,
            "screenshot_title": "分享海报",
            "playable_count": 1226,
            "screenshot_url": "douban:\/\/partial.douban.com\/screenshot\/doulist\/13712178\/_content",
            "create_time": "2014-10-05 10:41:22",
            "owner": {
                "kind": "user",
                "name": "依然饭特稀",
                "url": "https:\/\/www.douban.com\/people\/56698183\/",
                "uri": "douban:\/\/douban.com\/user\/56698183",
                "avatar": "https://img2.doubanio.com\/icon\/up56698183-12.jpg",
                "is_club": false,
                "type": "user",
                "id": "56698183",
                "uid": "yrftx"
            },
            "screenshot_type": "rexxar",
            "id": "13712178",
            "category": "movie",
            "is_merged_cover": false,
            "title": "评价人数超过十万的电影",
            "is_subject_selection": false,
            "followers_count": 53081,
            "is_private": false,
            "item_abstracts": [],
            "type": "doulist",
            "update_time": "2023-04-22 22:19:48",
            "list_type": "ugc_doulist",
            "tags": [],
            "syncing_note": null,
            "cover_url": "https://img9.doubanio.com\/view\/elanor_image\/raw\/public\/91314905.jpg",
            "header_bg_image": "",
            "doulist_type": "",
            "done_count": 0,
            "desc": "谢谢大家的关注和点赞，不过我更希望大家能在留言板上补充遗漏。\r\n看腻了豆瓣的评分排序，不如试试评价人数排序。评价人数并不代表作品的优劣，但是它起码说明了作品的存在感。这不一定是选电影最好的方法，却一定是选电影风险最小的方法。\r\n欢迎关注我关于读书的两个豆列： \r\n豆瓣评价人数超过一万的外文书籍 \r\nhttp:\/\/www.douban.com\/doulist\/37912871\/ \r\n豆瓣评价人数超过一万的中文书籍\r\nhttp:\/\/www.douban.com\/doulist\/36708212\/",
            "items_count": 1453,
            "wechat_timeline_share": "url",
            "url": "https:\/\/www.douban.com\/doulist\/13712178\/",
            "is_sys_private": false,
            "uri": "douban:\/\/douban.com\/doulist\/13712178",
            "sharing_url": "https:\/\/www.douban.com\/doulist\/13712178\/"
        }
        """
        return self.__invoke(self._urls["doulist"] + subject_id)

    def doulist_items(self, subject_id, start=0, count=20, ts=datetime.strftime(datetime.now(), '%Y%m%d')):
        """
        豆列列表
        :param subject_id: 豆列id
        :param start: 开始
        :param count: 数量
        :param ts: 时间戳
        :return:
        {
            "count": 3,
            "start": 0,
            "total": 1453,
            "items": [{
                "comment": "",
                "rating": {
                    "count": 2834097,
                    "max": 10,
                    "star_count": 5.0,
                    "value": 9.7
                },
                "subtitle": "1994 \/ 美国 \/ 剧情 犯罪 \/ 弗兰克·德拉邦特 \/ 蒂姆·罗宾斯 摩根·弗里曼",
                "title": "肖申克的救赎",
                "url": "https:\/\/movie.douban.com\/subject\/1292052\/",
                "target_id": "1292052",
                "uri": "douban:\/\/douban.com\/movie\/1292052",
                "cover_url": "https:\/\/qnmob3.doubanio.com\/view\/photo\/m_ratio_poster\/public\/p480747492.jpg?imageView2\/2\/q\/80\/w\/300\/h\/300\/format\/jpg",
                "create_time": "2014-10-05 10:41:51",
                "type": "movie",
                "id": "19877287"
            }, {
                "comment": "",
                "rating": {
                    "count": 2255839,
                    "max": 10,
                    "star_count": 4.5,
                    "value": 9.4
                },
                "subtitle": "1994 \/ 法国 美国 \/ 剧情 动作 犯罪 \/ 吕克·贝松 \/ 让·雷诺 娜塔莉·波特曼",
                "title": "这个杀手不太冷",
                "url": "https:\/\/movie.douban.com\/subject\/1295644\/",
                "target_id": "1295644",
                "uri": "douban:\/\/douban.com\/movie\/1295644",
                "cover_url": "https:\/\/qnmob3.doubanio.com\/view\/photo\/m_ratio_poster\/public\/p511118051.jpg?imageView2\/2\/q\/80\/w\/300\/h\/300\/format\/jpg",
                "create_time": "2014-10-05 10:42:34",
                "type": "movie",
                "id": "19877286"
            }, {
                "comment": "",
                "rating": {
                    "count": 2198702,
                    "max": 10,
                    "star_count": 4.5,
                    "value": 9.4
                },
                "subtitle": "2001 \/ 日本 \/ 剧情 动画 奇幻 \/ 宫崎骏 \/ 柊瑠美 入野自由",
                "title": "千与千寻",
                "url": "https:\/\/movie.douban.com\/subject\/1291561\/",
                "target_id": "1291561",
                "uri": "douban:\/\/douban.com\/movie\/1291561",
                "cover_url": "https:\/\/qnmob3.doubanio.com\/view\/photo\/m_ratio_poster\/public\/p2557573348.jpg?imageView2\/2\/q\/80\/w\/300\/h\/300\/format\/jpg",
                "create_time": "2014-10-05 10:47:12",
                "type": "movie",
                "id": "19877280"
            }]
        }
        """
        return self.__invoke(self._urls["doulist_items"] % subject_id, start=start, count=count, _ts=ts)
