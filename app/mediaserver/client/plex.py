from app.utils import ExceptionUtils
from app.utils.types import MediaServerType

import log
from config import Config
from app.mediaserver.client._base import _IMediaClient
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
from plexapi import media


class Plex(_IMediaClient):
    # 媒体服务器ID
    client_id = "plex"
    # 媒体服务器类型
    client_type = MediaServerType.PLEX
    # 媒体服务器名称
    client_name = MediaServerType.PLEX.value

    # 私有属性
    _client_config = {}
    _host = None
    _token = None
    _username = None
    _password = None
    _servername = None
    _plex = None
    _libraries = []

    def __init__(self, config=None):
        if config:
            self._client_config = config
        else:
            self._client_config = Config().get_config('plex')
        self.init_config()

    def init_config(self):
        if self._client_config:
            self._host = self._client_config.get('host')
            self._token = self._client_config.get('token')
            if self._host:
                if not self._host.startswith('http'):
                    self._host = "http://" + self._host
                if not self._host.endswith('/'):
                    self._host = self._host + "/"
            self._username = self._client_config.get('username')
            self._password = self._client_config.get('password')
            self._servername = self._client_config.get('servername')
            if self._host and self._token:
                try:
                    self._plex = PlexServer(self._host, self._token)
                except Exception as e:
                    ExceptionUtils.exception_traceback(e)
                    self._plex = None
                    log.error(f"【{self.client_name}】Plex服务器连接失败：{str(e)}")
            elif self._username and self._password and self._servername:
                try:
                    self._plex = MyPlexAccount(self._username, self._password).resource(self._servername).connect()
                except Exception as e:
                    ExceptionUtils.exception_traceback(e)
                    self._plex = None
                    log.error(f"【{self.client_name}】Plex服务器连接失败：{str(e)}")

    @classmethod
    def match(cls, ctype):
        return True if ctype in [cls.client_id, cls.client_type, cls.client_name] else False

    def get_type(self):
        return self.client_type

    def get_status(self):
        """
        测试连通性
        """
        return True if self._plex else False

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
        if not self._plex:
            return []
        ret_array = []
        try:
            # type的含义: 1 电影 4 剧集单集
            # 根据最后播放时间倒序获取数据
            historys = self._plex.library.search(sort='lastViewedAt:desc', limit=num, type='1,4')
            for his in historys:
                # 过滤掉最后播放时间为空的
                if his.lastViewedAt:
                    if his.type == "episode":
                        event_title = "%s %s%s %s" % (
                            his.grandparentTitle,
                            "S" + str(his.parentIndex),
                            "E" + str(his.index),
                            his.title
                        )
                        event_str = "开始播放剧集 %s" % event_title
                    else:
                        event_title = "%s %s" % (
                            his.title, "(" + str(his.year) + ")")
                        event_str = "开始播放电影 %s" % event_title

                    event_type = "PL"
                    event_date = his.lastViewedAt.strftime('%Y-%m-%d %H:%M:%S')
                    activity = {"type": event_type, "event": event_str, "date": event_date}
                    ret_array.append(activity)
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接System/ActivityLog/Entries出错：" + str(e))
            return []
        if ret_array:
            ret_array = sorted(ret_array, key=lambda x: x['date'], reverse=True)
        return ret_array

    def get_medias_count(self):
        """
        获得电影、电视剧、动漫媒体数量
        :return: MovieCount SeriesCount SongCount
        """
        if not self._plex:
            return {}
        sections = self._plex.library.sections()
        MovieCount = SeriesCount = SongCount = EpisodeCount = 0
        for sec in sections:
            if sec.type == "movie":
                MovieCount += sec.totalSize
            if sec.type == "show":
                SeriesCount += sec.totalSize
                EpisodeCount += sec.totalViewSize(libtype='episode')
            if sec.type == "artist":
                SongCount += sec.totalSize
        return {
            "MovieCount": MovieCount,
            "SeriesCount": SeriesCount,
            "SongCount": SongCount,
            "EpisodeCount": EpisodeCount
        }

    def get_movies(self, title, year=None):
        """
        根据标题和年份，检查电影是否在Plex中存在，存在则返回列表
        :param title: 标题
        :param year: 年份，为空则不过滤
        :return: 含title、year属性的字典列表
        """
        if not self._plex:
            return None
        ret_movies = []
        if year:
            movies = self._plex.library.search(title=title, year=year, libtype="movie")
        else:
            movies = self._plex.library.search(title=title, libtype="movie")
        for movie in movies:
            ret_movies.append({'title': movie.title, 'year': movie.year})
        return ret_movies

    def get_tv_episodes(self,
                        item_id=None,
                        title=None,
                        year=None,
                        tmdbid=None,
                        season=None):
        """
        根据标题、年份、季查询电视剧所有集信息
        :param item_id: Plex中的ID
        :param title: 标题
        :param year: 年份，可以为空，为空时不按年份过滤
        :param tmdbid: TMDBID
        :param season: 季号，数字
        :return: 所有集的列表
        """
        if not self._plex:
            return []
        if not item_id:
            videos = self._plex.library.search(title=title, year=year, libtype="show")
            if not videos:
                return []
            episodes = videos[0].episodes()
        else:
            episodes = self._plex.fetchItem(item_id).episodes()
        ret_tvs = []
        for episode in episodes:
            if season and episode.seasonNumber != int(season):
                continue
            ret_tvs.append({
                "season_num": episode.seasonNumber,
                "episode_num": episode.index
            })
        return ret_tvs

    def get_no_exists_episodes(self, meta_info, season, total_num):
        """
        根据标题、年份、季、总集数，查询Plex中缺少哪几集
        :param meta_info: 已识别的需要查询的媒体信息
        :param season: 季号，数字
        :param total_num: 该季的总集数
        :return: 该季不存在的集号列表
        """
        if not self._plex:
            return None
        # 没有季默认为和1季
        if not season:
            season = 1
        episodes = self.get_tv_episodes(title=meta_info.title,
                                        year=meta_info.year,
                                        season=season)
        exists_episodes = [episode['episode_num'] for episode in episodes]
        total_episodes = [episode for episode in range(1, total_num + 1)]
        return list(set(total_episodes).difference(set(exists_episodes)))

    def get_episode_image_by_id(self, item_id, season_id, episode_id):
        """
        根据itemid、season_id、episode_id从Plex查询图片地址
        :param item_id: 在Plex中具体的一集的ID
        :param season_id: 季,目前没有使用
        :param episode_id: 集,目前没有使用
        :return: 图片对应在TMDB中的URL
        """
        if not self._plex:
            return None
        try:
            images = self._plex.fetchItems('/library/metadata/%s/posters' % item_id, cls=media.Poster)
            for image in images:
                if hasattr(image, 'key') and image.key.startswith('http'):
                    return image.key
            return None
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】获取剧集封面出错：" + str(e))
            return None

    def get_image_by_id(self, item_id, image_type):
        """
        根据ItemId从Plex查询图片地址
        :param item_id: 在Emby中的ID
        :param image_type: 图片的类型，Poster或者Backdrop等
        :return: 图片对应在TMDB中的URL
        """
        if not self._plex:
            return None
        try:
            if image_type == "Poster":
                images = self._plex.fetchItems('/library/metadata/%s/posters' % item_id, cls=media.Poster)
            else:
                images = self._plex.fetchItems('/library/metadata/%s/arts' % item_id, cls=media.Art)
            for image in images:
                if hasattr(image, 'key') and image.key.startswith('http'):
                    return image.key
            raise Exception("test")
            return None
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】获取封面出错：" + str(e))
            return None

    def refresh_root_library(self):
        """
        通知Plex刷新整个媒体库
        """
        if not self._plex:
            return False
        return self._plex.library.update()

    def refresh_library_by_items(self, items):
        """
        按类型、名称、年份来刷新媒体库，未找到对应的API，直接刷整个库
        """
        if not self._plex:
            return False
        return self._plex.library.update()

    def get_libraries(self):
        """
        获取媒体服务器所有媒体库列表
        """
        if not self._plex:
            return []
        try:
            self._libraries = self._plex.library.sections()
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return []
        libraries = []
        for library in self._libraries:
            libraries.append({"id": library.key, "name": library.title})
        return libraries

    def get_iteminfo(self, itemid):
        """
        获取单个项目详情
        """
        if not self._plex:
            return {}
        try:
            item = self._plex.fetchItem(itemid)
            ids = self.__get_ids(item.guids)
            return {'ProviderIds': {'Tmdb': ids['tmdb_id'], 'Imdb': ids['imdb_id']}}
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return {}

    def get_items(self, parent):
        """
        获取媒体服务器所有媒体库列表
        """
        if not parent:
            yield {}
        if not self._plex:
            yield {}
        try:
            section = self._plex.library.sectionByID(parent)
            if section:
                for item in section.all():
                    if not item:
                        continue
                    ids = self.__get_ids(item.guids)
                    path = None
                    if item.locations:
                        path = item.locations[0]
                    yield {"id": item.key,
                           "library": item.librarySectionID,
                           "type": item.type,
                           "title": item.title,
                           "originalTitle": item.originalTitle,
                           "year": item.year,
                           "tmdbid": ids['tmdb_id'],
                           "imdbid": ids['imdb_id'],
                           "tvdbid": ids['tvdb_id'],
                           "path": path}
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
        yield {}

    @staticmethod
    def __get_ids(guids):
        guid_mapping = {
            "imdb://": "imdb_id",
            "tmdb://": "tmdb_id",
            "tvdb://": "tvdb_id"
        }
        ids = {}
        for prefix, varname in guid_mapping.items():
            ids[varname] = None
        for guid in guids:
            for prefix, varname in guid_mapping.items():
                if isinstance(guid, dict):
                    if guid['id'].startswith(prefix):
                        # 找到匹配的ID
                        ids[varname] = guid['id'][len(prefix):]
                        break
                else:
                    if guid.id.startswith(prefix):
                        # 找到匹配的ID
                        ids[varname] = guid.id[len(prefix):]
                        break
        return ids

    def get_playing_sessions(self):
        """
        获取正在播放的会话
        """
        if not self._plex:
            return []
        sessions = self._plex.sessions()
        ret_sessions = []
        for session in sessions:
            ret_sessions.append({
                "type": session.TAG,
                "bitrate": sum([m.bitrate for m in session.media]),
                "address": session.player.address
            })
        return ret_sessions

    def get_webhook_message(self, message):
        """
        解析Plex报文
        eventItem  字段的含义
        event      事件类型
        item_type  媒体类型 TV,MOV
        item_name  TV:琅琊榜 S1E6 剖心明志 虎口脱险
                   MOV:猪猪侠大冒险(2001)
        overview   剧情描述
        """
        eventItem = {'event': message.get('event', '')}
        if message.get('Metadata'):
            if message.get('Metadata', {}).get('type') == 'episode':
                eventItem['item_type'] = "TV"
                eventItem['item_name'] = "%s %s%s %s" % (
                    message.get('Metadata', {}).get('grandparentTitle'),
                    "S" + str(message.get('Metadata', {}).get('parentIndex')),
                    "E" + str(message.get('Metadata', {}).get('index')),
                    message.get('Metadata', {}).get('title'))
                eventItem['item_id'] = message.get('Metadata', {}).get('ratingKey')
                eventItem['season_id'] = message.get('Metadata', {}).get('parentIndex')
                eventItem['episode_id'] = message.get('Metadata', {}).get('index')

                if message.get('Metadata', {}).get('summary') and len(message.get('Metadata', {}).get('summary')) > 100:
                    eventItem['overview'] = str(message.get('Metadata', {}).get('summary'))[:100] + "..."
                else:
                    eventItem['overview'] = message.get('Metadata', {}).get('summary')
            else:
                eventItem['item_type'] = "MOV"
                eventItem['item_name'] = "%s %s" % (
                    message.get('Metadata', {}).get('title'), "(" + str(message.get('Metadata', {}).get('year')) + ")")
                eventItem['item_id'] = message.get('Metadata', {}).get('ratingKey')
                if len(message.get('Metadata', {}).get('summary')) > 100:
                    eventItem['overview'] = str(message.get('Metadata', {}).get('summary'))[:100] + "..."
                else:
                    eventItem['overview'] = message.get('Metadata', {}).get('summary')
        if message.get('Player'):
            eventItem['ip'] = message.get('Player').get('publicAddress')
            eventItem['client'] = message.get('Player').get('title')
            # 这里给个空,防止拼消息的时候出现None
            eventItem['device_name'] = ' '
        if message.get('Account'):
            eventItem['user_name'] = message.get("Account").get('title')

        return eventItem
