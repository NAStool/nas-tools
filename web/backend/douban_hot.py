import json
from datetime import datetime

import log
from pt.douban import DouBan
from utils.functions import singleton


@singleton
class DoubanHot:
    douban = None
    __soup = None
    __movie_num = 50
    __tv_num = 50
    __online_movies = []
    __hot_movies = []
    __hot_tvs = []
    __new_movies = []
    __new_tvs = []
    __online_time = datetime.now()
    __hot_movie_time = datetime.now()
    __hot_tv_time = datetime.now()
    __new_movie_time = datetime.now()
    __new_tv_time = datetime.now()

    def __init__(self):
        self.douban = DouBan()
        self.__soup = self.douban.get_html_soup(url="https://movie.douban.com/")
        self.__online_time = datetime.now()

    def init_config(self):
        pass

    def get_douban_online_movie(self):
        if not self.__online_movies or (datetime.now() - self.__online_time).days >= 0.5:
            self.__online_movies = self.refresh_online_movie()
        return self.__online_movies

    def get_douban_hot_movie(self):
        if not self.__hot_movies or (datetime.now() - self.__hot_movie_time).days >= 0.5:
            self.__hot_movies = self.refresh_hot_movie()
        return self.__hot_movies

    def get_douban_hot_tv(self):
        if not self.__hot_tvs or (datetime.now() - self.__hot_tv_time).days >= 0.5:
            self.__hot_tvs = self.refresh_hot_tv()
        return self.__hot_tvs

    def get_douban_new_movie(self):
        if not self.__new_movies or (datetime.now() - self.__new_movie_time).days >= 0.5:
            self.__new_movies = self.refresh_new_movie()
        return self.__new_movies

    def get_douban_new_tv(self):
        if not self.__new_tvs or (datetime.now() - self.__new_tv_time).days >= 0.5:
            self.__new_tvs = self.refresh_new_tv()
        return self.__new_tvs

    def refresh_online_movie(self):
        if not self.__soup:
            return []
        infos = self.__soup.select('.ui-slide-item')
        ret_list = []
        for info in infos:
            try:
                if not info:
                    continue
                # 评分
                vote_average = info.get('data-rate')
                if vote_average:
                    vote_average = float(vote_average)
                else:
                    vote_average = 0
                # 年份
                release_date = info.get('data-release')
                if not info.img:
                    continue
                # 海报
                poster_path = info.img.get('src')
                # 标题
                title = info.img.get('alt')
                if not title or not poster_path:
                    continue
                # 演员
                actors = info.get('data-actors') or ""
                # 导演
                director = info.get('data-director') or ""
                # 时长
                duration = info.get('data-duration') or ""
                # 国家/地区
                region = info.get('data-region') or ""
                if not region or not actors or not duration or not director:
                    continue
                # 简介
                overview = "国家/地区：%s 主演：%s，导演：%s，时长：%s" % (region, actors, director, duration)
                # ID
                ticket = info.get('data-ticket') or ""
                rid = ticket.split("=")[-1]
                ret_list.append({'id': rid, 'title': title, 'release_date': release_date, 'vote_average': vote_average, 'poster_path': poster_path, 'overview': overview})
            except Exception as e:
                log.error("【DOUBAN】DoubanHot出错：%s" % str(e))
        self.__online_time = datetime.now()
        return ret_list

    @staticmethod
    def __refresh_movie(html):
        movies = json.loads(html)
        ret_list = []
        if movies and 'subjects' in movies.keys():
            for item in movies.get('subjects'):
                if item.get('rate'):
                    vote_average = float(item.get('rate'))
                else:
                    vote_average = 0
                film = {
                    'id': item.get('id'),
                    'vote_average': vote_average,
                    'release_date': '',
                    'title': item.get('title'),
                    'overview': item.get('title'),
                    'poster_path': item.get('cover')
                }
                ret_list.append(film)
        return ret_list

    @staticmethod
    def __refresh_tv(html):
        tvs = json.loads(html)
        ret_list = []
        if tvs and 'subjects' in tvs.keys():
            for item in tvs.get('subjects'):
                if item.get('rate'):
                    vote_average = float(item.get('rate'))
                else:
                    vote_average = 0
                overview = item.get('episodes_info')
                if not overview:
                    overview = item.get('title')
                else:
                    overview = "%s %s" % (item.get('title'), item.get('episodes_info'))
                tv = {
                    'id': item.get('id'),
                    'vote_average': vote_average,
                    'first_air_date': '',
                    'name': item.get('title'),
                    'overview': overview,
                    'poster_path': item.get('cover')
                }
                ret_list.append(tv)
        return ret_list

    def refresh_hot_movie(self):
        html = self.douban.get_douban_hot_json('movie', self.__movie_num)
        if not html:
            return []
        self.__hot_movie_time = datetime.now()
        return self.__refresh_movie(html)

    def refresh_hot_tv(self):
        html = self.douban.get_douban_hot_json('tv', self.__tv_num)
        if not html:
            return []
        self.__hot_tv_time = datetime.now()
        return self.__refresh_tv(html)

    def refresh_new_movie(self):
        html = self.douban.get_douban_new_json('movie', self.__movie_num)
        if not html:
            return []
        self.__new_movie_time = datetime.now()
        return self.__refresh_movie(html)

    def refresh_new_tv(self):
        html = self.douban.get_douban_new_json('tv', self.__tv_num)
        if not html:
            return []
        self.__new_tv_time = datetime.now()
        return self.__refresh_tv(html)
