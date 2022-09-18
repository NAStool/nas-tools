from app.media.doubanv2api import DoubanApi
from app.utils.commons import singleton


@singleton
class DoubanHot:
    doubanapi = None
    __movie_num = 30
    __tv_num = 30

    def __init__(self):
        self.doubanapi = DoubanApi()

    def init_config(self):
        pass

    def get_douban_online_movie(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.movie_showing(start=(page - 1) * self.__movie_num, count=self.__movie_num)
        if not infos:
            return []
        return self.__refresh_movie(infos.get("subject_collection_items"))

    def get_douban_hot_movie(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.movie_hot_gaia(start=(page - 1) * self.__movie_num, count=self.__movie_num)
        if not infos:
            return []
        return self.__refresh_movie(infos.get("subject_collection_items"))

    def get_douban_hot_anime(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.tv_animation(start=(page - 1) * self.__tv_num, count=self.__tv_num)
        if not infos:
            return []
        return self.__refresh_tv(infos.get("subject_collection_items"))

    def get_douban_hot_tv(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.tv_hot(start=(page - 1) * self.__tv_num, count=self.__tv_num)
        if not infos:
            return []
        return self.__refresh_tv(infos.get("subject_collection_items"))

    def get_douban_new_movie(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.movie_soon(start=(page - 1) * self.__movie_num, count=self.__movie_num)
        if not infos:
            return []
        return self.__refresh_movie(infos.get("subject_collection_items"))

    def get_douban_hot_show(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.show_hot(start=(page - 1) * self.__tv_num, count=self.__tv_num)
        if not infos:
            return []
        return self.__refresh_tv(infos.get("subject_collection_items"))

    def get_douban_top250_movie(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.movie_top250(start=(page - 1) * self.__movie_num, count=self.__movie_num)
        if not infos:
            return []
        return self.__refresh_movie(infos.get("subject_collection_items"))

    def refresh_online_movie(self, page=1):
        if not self.doubanapi:
            return []
        infos = self.doubanapi.movie_showing(start=(page - 1) * self.__movie_num, count=self.__movie_num)
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
                # 标题
                title = info.get('title')
                if not title or not poster_path:
                    continue
                # 简介
                overview = info.get("card_subtitle") or ""
                if not year and overview:
                    if overview.split("/")[0].strip().isdigit():
                        year = overview.split("/")[0].strip()
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
                poster_path = info.get('pic', {}).get("normal")
                # 标题
                title = info.get('title')
                if not title or not poster_path:
                    continue
                # 简介
                overview = info.get("comment") or ""
                ret_list.append({'id': rid, 'name': title, 'first_air_date': year, 'vote_average': vote_average,
                                 'poster_path': poster_path, 'overview': overview})
            except Exception as e:
                print(str(e))
        return ret_list
