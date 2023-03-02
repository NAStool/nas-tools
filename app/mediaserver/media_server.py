import json
import threading

import log
from app.conf import SystemConfig
from app.db import MediaDb
from app.helper import ProgressHelper, SubmoduleHelper
from app.media import Media
from app.message import Message
from app.utils import ExceptionUtils
from app.utils.commons import singleton
from app.utils.types import MediaServerType, MovieTypes, SystemConfigKey
from app.utils.types import MediaType
from config import Config

lock = threading.Lock()
server_lock = threading.Lock()


@singleton
class MediaServer:

    _mediaserver_schemas = []

    _server_type = None
    _server = None
    mediadb = None
    progress = None
    message = None
    media = None
    systemconfig = None

    def __init__(self):
        self._mediaserver_schemas = SubmoduleHelper.import_submodules(
            'app.mediaserver.client',
            filter_func=lambda _, obj: hasattr(obj, 'client_id')
        )
        log.debug(f"【MediaServer】加载媒体服务器：{self._mediaserver_schemas}")
        self.init_config()

    def init_config(self):
        self.mediadb = MediaDb()
        self.message = Message()
        self.progress = ProgressHelper()
        self.media = Media()
        self.systemconfig = SystemConfig()
        # 当前使用的媒体库服务器
        self._server_type = Config().get_config('media').get('media_server') or 'emby'
        self._server = None

    def __build_class(self, ctype, conf):
        for mediaserver_schema in self._mediaserver_schemas:
            try:
                if mediaserver_schema.match(ctype):
                    return mediaserver_schema(conf)
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
        return None

    @property
    def server(self):
        with server_lock:
            if not self._server:
                self._server = self.__get_server(self._server_type)
            return self._server

    def __get_server(self, ctype: [MediaServerType, str], conf=None):
        return self.__build_class(ctype=ctype, conf=conf)

    def get_type(self):
        """
        当前使用的媒体库服务器
        """
        return self.server.get_type()

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
        if not item_id:
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

    def get_libraries(self):
        """
        获取媒体服务器所有媒体库列表
        """
        if not self.server:
            return []
        return self.server.get_libraries()

    def get_items(self, parent):
        """
        获取媒体库中的所有媒体
        :param parent: 上一级的ID
        """
        if not self.server:
            return []
        return self.server.get_items(parent)

    def get_tv_episodes(self, item_id):
        """
        获取电视剧的所有集数信息
        :param item_id: 电视剧的ID
        """
        if not self.server:
            return []
        return self.server.get_tv_episodes(item_id=item_id)

    def sync_mediaserver(self):
        """
        同步媒体库所有数据到本地数据库
        """
        if not self.server:
            return
        with lock:
            # 开始进度条
            log.info("【MediaServer】开始同步媒体库数据...")
            self.progress.start("mediasync")
            self.progress.update(ptype="mediasync", text="请稍候...")
            # 获取需同步的媒体库
            librarys = self.systemconfig.get_system_config(SystemConfigKey.SyncLibrary) or []
            # 汇总统计
            medias_count = self.get_medias_count()
            total_media_count = medias_count.get("MovieCount") + medias_count.get("SeriesCount")
            total_count = 0
            movie_count = 0
            tv_count = 0
            # 清空登记薄
            self.mediadb.empty()
            for library in self.get_libraries():
                if str(library.get("id")) not in librarys:
                    continue
                # 获取媒体库所有项目
                self.progress.update(ptype="mediasync",
                                     text="正在获取 %s 数据..." % (library.get("name")))
                for item in self.get_items(library.get("id")):
                    if not item:
                        continue
                    # 更新进度
                    seasoninfo = []
                    total_count += 1
                    if item.get("type") in ['Movie', 'movie']:
                        movie_count += 1
                    elif item.get("type") in ['Series', 'show']:
                        tv_count += 1
                        # 查询剧集信息
                        seasoninfo = self.get_tv_episodes(item.get("id"))
                    self.progress.update(ptype="mediasync",
                                         text="正在同步 %s，已完成：%s / %s ..." % (
                                             library.get("name"), total_count, total_media_count),
                                         value=round(100 * total_count / total_media_count, 1))
                    # 插入数据
                    self.mediadb.insert(server_type=self._server_type,
                                        iteminfo=item,
                                        seasoninfo=seasoninfo)

            # 更新总体同步情况
            self.mediadb.statistics(server_type=self._server_type,
                                    total_count=total_count,
                                    movie_count=movie_count,
                                    tv_count=tv_count)
            # 结束进度条
            self.progress.update(ptype="mediasync",
                                 value=100,
                                 text="媒体库数据同步完成，同步数量：%s" % total_count)
            self.progress.end("mediasync")
            log.info("【MediaServer】媒体库数据同步完成，同步数量：%s" % total_count)

    def check_item_exists(self,
                          mtype,
                          title=None,
                          year=None,
                          tmdbid=None,
                          season=None,
                          episode=None):
        """
        检查媒体库是否已存在某项目，非实时同步数据，仅用于展示
        :param mtype: 媒体类型
        :param title: 标题
        :param year: 年份
        :param tmdbid: TMDB ID
        :param season: 季号
        :param episode: 集号
        """
        media = self.mediadb.query(server_type=self._server_type,
                                   title=title,
                                   year=year,
                                   tmdbid=tmdbid)
        if not media:
            return False

        # 剧集没有季时默认为第1季
        if mtype not in MovieTypes:
            if not season:
                season = 1
        if season:
            # 匹配剧集是否存在
            seasoninfos = json.loads(media.JSON or "[]")
            for seasoninfo in seasoninfos:
                if seasoninfo.get("season_num") == int(season):
                    if not episode:
                        return True
                    elif seasoninfo.get("episode_num") == int(episode):
                        return True
            return False
        else:
            return True

    def get_mediasync_status(self):
        """
        获取当前媒体库同步状态
        """
        status = self.mediadb.get_statistics(server_type=self._server_type)
        if not status:
            return {}
        else:
            return {"movie_count": status.MOVIE_COUNT, "tv_count": status.TV_COUNT, "time": status.UPDATE_TIME}

    def get_iteminfo(self, itemid):
        """
        根据ItemId从媒体服务器查询项目详情
        :param itemid: 在Emby中的ID
        :return: 图片对应在TMDB中的URL
        """
        if not self.server:
            return None
        if not itemid:
            return None
        return self.server.get_iteminfo(itemid)

    def get_playing_sessions(self):
        """
        获取正在播放的会话
        """
        if not self.server:
            return None
        return self.server.get_playing_sessions()

    def webhook_message_handler(self, message: str, channel: MediaServerType):
        """
        处理Webhook消息
        """
        if not self.server:
            return
        if channel != self.server.get_type():
            return
        event_info = self.server.get_webhook_message(message)
        if event_info:
            # 获取消息图片
            image_url = None
            if event_info.get("item_type") == "TV":
                item_info = self.get_iteminfo(event_info.get('item_id'))
                if item_info:
                    image_url = self.media.get_episode_images(tv_id=item_info.get('ProviderIds', {}).get('Tmdb'),
                                                              season_id=event_info.get('season_id'),
                                                              episode_id=event_info.get('episode_id'))
            else:
                if self._server_type == "plex":
                    # Plex:根据返回的tmdb_id去调用tmdb获取
                    image_url = self.media.get_tmdb_backdrop(mtype=MediaType.MOVIE,
                                                             tmdbid=event_info.get('tmdb_id'))
                else:
                    # Emby,Jellyfin:根据返回的item_id去调用媒体服务器获取
                    image_url = self.get_image_by_id(item_id=event_info.get('item_id'),
                                                     image_type="Backdrop")
            self.message.send_mediaserver_message(event_info=event_info,
                                                  channel=channel.value,
                                                  image_url=image_url)
