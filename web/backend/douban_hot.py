from datetime import datetime
from rmt.doubanv2api.doubanapi import DoubanApi
from utils.functions import singleton


@singleton
class DoubanHot:
    doubanapi = None
    __movie_num = 50
    __tv_num = 50
    __online_movies = []
    __hot_movies = []
    __hot_tvs = []
    __new_movies = []
    __hot_shows = []
    __hot_animes = []
    __hot_anime_time = datetime.now()
    __online_time = datetime.now()
    __hot_movie_time = datetime.now()
    __hot_tv_time = datetime.now()
    __new_movie_time = datetime.now()
    __hot_show_time = datetime.now()

    def __init__(self):
        self.doubanapi = DoubanApi()

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
    
    def get_douban_hot_anime(self):
        if not self.__hot_animes or (datetime.now() - self.__hot_anime_time).days >= 0.5:
            self.__hot_animes = self.refresh_hot_anime()
        return self.__hot_animes
    
    def get_douban_hot_tv(self):
        if not self.__hot_tvs or (datetime.now() - self.__hot_tv_time).days >= 0.5:
            self.__hot_tvs = self.refresh_hot_tv()
        return self.__hot_tvs

    def get_douban_new_movie(self):
        if not self.__new_movies or (datetime.now() - self.__new_movie_time).days >= 0.5:
            self.__new_movies = self.refresh_new_movie()
        return self.__new_movies

    def get_douban_hot_show(self):
        if not self.__hot_shows or (datetime.now() - self.__hot_show_time).days >= 0.5:
            self.__hot_shows = self.refresh_hot_show()
        return self.__hot_shows

    def refresh_online_movie(self):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.movie_showing(count=self.__movie_num)
        if not infos:
            return []
        self.__online_time = datetime.now()
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
                # 标题
                title = info.get('title')
                if not title or not poster_path:
                    continue
                # 简介
                overview = info.get("card_subtitle") or ""
                ret_list.append({'id': rid, 'title': title, 'release_date': year, 'vote_average': vote_average,
                                 'poster_path': poster_path, 'overview': overview})
            except Exception as e:
                print(str(e))
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
                poster_path = info.get('cover', {}).get("url")
                # 标题
                title = info.get('title')
                if not title or not poster_path:
                    continue
                # 简介
                overview = info.get("card_subtitle") or ""
                ret_list.append({'id': rid, 'name': title, 'first_air_date': year, 'vote_average': vote_average,
                                 'poster_path': poster_path, 'overview': overview})
            except Exception as e:
                print(str(e))
        return ret_list

    def refresh_hot_movie(self):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.movie_hot_gaia(count=self.__movie_num)
        if not infos:
            return []
        self.__hot_movie_time = datetime.now()
        return self.__refresh_movie(infos.get("subject_collection_items"))

    def refresh_hot_tv(self):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.tv_hot(count=self.__tv_num)
        if not infos:
            return []
        self.__hot_tv_time = datetime.now()
        return self.__refresh_tv(infos.get("subject_collection_items"))
    
    def refresh_hot_anime(self):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.tv_animation(count=self.__tv_num)
        if not infos:
            return []
        self.__hot_anime_time = datetime.now()
        return self.__refresh_tv(infos.get("subject_collection_items"))
    
    def refresh_new_movie(self):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.movie_soon(count=self.__movie_num)
        if not infos:
            return []
        self.__new_movie_time = datetime.now()
        return self.__refresh_movie(infos.get("subject_collection_items"))

    def refresh_hot_show(self):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.show_hot(count=self.__tv_num)
        if not infos:
            return []
        self.__hot_show_time = datetime.now()
        return self.__refresh_tv(infos.get("subject_collection_items"))
