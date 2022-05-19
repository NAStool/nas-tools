from config import Config
from pt.mediaserver.emby import Emby
from pt.mediaserver.jellyfin import Jellyfin
from pt.mediaserver.plex import Plex


class MediaServer:
    server = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        media = config.get_config('media')
        if media:
            if media.get('media_server') == "jellyfin":
                self.server = Jellyfin()
            elif media.get('media_server') == "plex":
                self.server = Plex()
            else:
                self.server = Emby()

    def get_activity_log(self, limit):
        """
        获取媒体服务器的活动日志
        :param limit: 条数限制
        """
        if not self.server:
            return []
        return self.server.get_activity_log(limit)

    def get_user_count(self):
        """
        获取媒体服务器的总用户数
        """
        if not self.server:
            return 0
        return self.server.get_user_count()

    def get_medias_count(self):
        """
        获取媒体服务器各类型的媒体库
        :return: MovieCount SeriesCount SongCount
        """
        if not self.server:
            return None
        return self.server.get_medias_count()

    def refresh_root_library(self):
        """
        刷新媒体服务器整个媒体库
        """
        if not self.server:
            return
        return self.server.refresh_root_library()

    def get_image_by_id(self, item_id, image_type):
        """
        根据ItemId从媒体服务器查询图片地址
        :param item_id: 在Emby中的ID
        :param image_type: 图片的类弄地，poster或者backdrop等
        :return: 图片对应在TMDB中的URL
        """
        if not self.server:
            return None
        return self.server.get_image_by_id(item_id, image_type)

    def get_no_exists_episodes(self, meta_info,
                               season_number,
                               episode_count):
        """
        根据标题、年份、季、总集数，查询媒体服务器中缺少哪几集
        :param meta_info: 已识别的需要查询的媒体信息
        :param season_number: 季号，数字
        :param episode_count: 该季的总集数
        :return: 该季不存在的集号列表
        """
        if not self.server:
            return None
        return self.server.get_no_exists_episodes(meta_info,
                                                  season_number,
                                                  episode_count)

    def get_movies(self, title, year=None):
        """
        根据标题和年份，检查电影是否在媒体服务器中存在，存在则返回列表
        :param title: 标题
        :param year: 年份，可以为空，为空时不按年份过滤
        :return: 含title、year属性的字典列表
        """
        if not self.server:
            return None
        return self.server.get_movies(title, year)

    def refresh_library_by_items(self, items):
        """
        按类型、名称、年份来刷新媒体库
        :param items: 已识别的需要刷新媒体库的媒体信息列表
        """
        if not self.server:
            return
        return self.server.refresh_library_by_items(items)
