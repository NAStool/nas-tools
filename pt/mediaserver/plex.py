from plexapi.myplex import MyPlexAccount

import log
from config import Config
from pt.mediaserver.server import IMediaServer
from rmt.meta.metabase import MetaBase
from utils.functions import singleton


@singleton
class Plex(IMediaServer):
    __host = None
    __username = None
    __password = None
    __servername = None
    __plex = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        plex = config.get_config('plex')
        if plex:
            self.__host = plex.get('host')
            if not self.__host.startswith('http://') and not self.__host.startswith('https://'):
                self.__host = "http://" + self.__host
            if not self.__host.endswith('/'):
                self.__host = self.__host + "/"
            self.__username = plex.get('username')
            self.__password = plex.get('password')
            self.__servername = plex.get('servername')
            try:
                self.__plex = MyPlexAccount(self.__username, self.__password).resource(self.__servername).connect()
            except Exception as e:
                self.__plex = None
                log.error("【PLEX】Plex服务器连接失败：%s" % str(e))

    def get_status(self):
        """
        测试连通性
        """
        return True if self.__plex else False

    @staticmethod
    def get_user_count(**kwargs):
        """
        获得用户数量，Plex只能配置一个用户，固定返回1
        """
        return 1

    def get_activity_log(self, num):
        """
        获取Plex活动记录
        """
        if not self.__plex:
            return []
        ret_array = []
        historys = self.__plex.library.history(num)
        for his in historys:
            event_type = "PL"
            event_date = his.viewedAt.strftime('%Y-%m-%d %H:%M:%S')
            event_str = "开始播放 %s" % his.title
            activity = {"type": event_type, "event": event_str, "date": event_date}
            ret_array.append(activity)
        return ret_array

    def get_medias_count(self):
        """
        获得电影、电视剧、动漫媒体数量
        :return: MovieCount SeriesCount SongCount
        """
        if not self.__plex:
            return {}
        sections = self.__plex.library.sections()
        MovieCount = SeriesCount = SongCount = 0
        for sec in sections:
            if sec.type == "movie":
                MovieCount += sec.totalSize
            if sec.type == "show":
                MovieCount += sec.totalSize
            if sec.type == "album":
                MovieCount += sec.totalSize
        return {"MovieCount": MovieCount, "SeriesCount": SeriesCount, "SongCount": SongCount, "EpisodeCount": 0}

    def get_movies(self, title, year=None):
        """
        根据标题和年份，检查电影是否在Plex中存在，存在则返回列表
        :param title: 标题
        :param year: 年份，为空则不过滤
        :return: 含title、year属性的字典列表
        """
        if not self.__plex:
            return None
        ret_movies = []
        if year:
            movies = self.__plex.library.search(title=title, year=year, libtype="movie")
        else:
            movies = self.__plex.library.search(title=title, libtype="movie")
        for movie in movies:
            ret_movies.append({'title': movie.title, 'year': movie.year})
        return ret_movies

    # 根据标题、年份、季、总集数，查询Plex中缺少哪几集
    def get_no_exists_episodes(self, meta_info: MetaBase, season, total_num):
        """
        根据标题、年份、季、总集数，查询Plex中缺少哪几集
        :param meta_info: 已识别的需要查询的媒体信息
        :param season: 季号，数字
        :param total_num: 该季的总集数
        :return: 该季不存在的集号列表
        """
        if not self.__plex:
            return None
        exists_episodes = []
        video = self.__plex.library.search(title=meta_info.title, year=meta_info.year, libtype="show")
        if video:
            for episode in video[0].episodes():
                if episode.seasonNumber == season:
                    exists_episodes.append(episode.index)
        total_episodes = [episode for episode in range(1, total_num + 1)]
        return list(set(total_episodes).difference(set(exists_episodes)))

    def get_image_by_id(self, item_id, image_type):
        """
        根据ItemId从Plex查询图片地址，该函数Plex下不使用
        """
        return None

    def refresh_root_library(self):
        """
        通知Plex刷新整个媒体库
        """
        return self.__plex.library.update()

    def refresh_library_by_items(self, items):
        """
        按类型、名称、年份来刷新媒体库，未找到对应的API，直接刷整库
        """
        return self.__plex.library.update()
