import os
from collections import OrderedDict
from functools import lru_cache
from urllib.parse import quote_plus
import log
from app.mediaserver.client._base import _IMediaClient
from app.utils import ExceptionUtils
from app.utils.types import MediaServerType, MediaType
from config import Config
from plexapi import media
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer


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
    _play_host = None
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
            self._play_host = self._client_config.get('play_host')
            if not self._play_host:
                self._play_host = self._host
            else:
                if not self._play_host.startswith('http'):
                    self._play_host = "http://" + self._play_host
                if not self._play_host.endswith('/'):
                    self._play_host = self._play_host + "/"
            if "app.plex.tv" in self._play_host:
                self._play_host = self._play_host + "desktop/"
            else:
                self._play_host = self._play_host + "web/index.html"
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
            # type的含义: 1 电影 4 剧集单集 详见 plexapi/utils.py中SEARCHTYPES的定义
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

    def get_remote_image_by_id(self, item_id, image_type):
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
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】获取封面出错：" + str(e))
        return None

    def get_local_image_by_id(self, item_id, remote=True):
        """
        根据ItemId从媒体服务器查询有声书图片地址
        :param item_id: 在Emby中的ID
        :param remote: 是否远程使用
        """
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
        按路径刷新媒体库
        """
        if not self._plex:
            return False
        # _libraries可能未初始化,初始化一下
        if not self._libraries:
            try:
                self._libraries = self._plex.library.sections()
            except Exception as err:
                ExceptionUtils.exception_traceback(err)
        result_dict = {}
        for item in items:
            file_path = item.get("file_path")
            lib_key, path = self.__find_librarie(file_path, self._libraries)
            # 如果存在同一剧集的多集,key(path)相同会合并
            result_dict[path] = lib_key
        if "" in result_dict:
            # 如果有匹配失败的,刷新整个库
            self._plex.library.update()
        else:
            # 否则一个一个刷新
            for path, lib_key in result_dict.items():
                log.info(f"【{self.client_name}】刷新媒体库：{lib_key} : {path}")
                self._plex.query(f'/library/sections/{lib_key}/refresh?path={quote_plus(path)}')

    @staticmethod
    def __find_librarie(path, libraries):
        """
        判断这个path属于哪个媒体库
        多个媒体库配置的目录不应有重复和嵌套,
        使用os.path.commonprefix([path, location]) == location应该没问题
        """
        if path is None:
            return "", ""
        # 只要路径,不要文件名
        dir_path = os.path.dirname(path)
        try:
            for lib in libraries:
                if hasattr(lib, "locations") and lib.locations:
                    for location in lib.locations:
                        if os.path.commonprefix([dir_path, location]) == location:
                            return lib.key, dir_path
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
        return "", ""

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
            match library.type:
                case "movie":
                    library_type = MediaType.MOVIE.value
                    image_list_str = self.get_libraries_image(library.key, 1)
                case "show":
                    library_type = MediaType.TV.value
                    image_list_str = self.get_libraries_image(library.key, 2)
                case _:
                    continue
            libraries.append({
                "id": library.key,
                "name": library.title,
                "paths": library.locations,
                "type": library_type,
                "image_list": image_list_str,
                "link": f"{self._play_host or self._host}#!/media/{self._plex.machineIdentifier}"
                        f"/com.plexapp.plugins.library?source={library.key}"
            })
        return libraries

    @lru_cache(maxsize=10)
    def get_libraries_image(self, library_key, type):
        """
        获取媒体服务器最近添加的媒体的图片列表
        param: library_key
        param: type type的含义: 1 电影 2 剧集 详见 plexapi/utils.py中SEARCHTYPES的定义
        """
        if not self._plex:
            return ""
        # 返回结果
        poster_urls = {}
        # 页码计数
        container_start = 0
        # 需要的总条数/每页的条数
        total_size = 4

        # 如果总数不足,接续获取下一页
        while len(poster_urls) < total_size:
            items = self._plex.fetchItems(f"/hubs/home/recentlyAdded?type={type}&sectionID={library_key}",
                                          container_size=total_size,
                                          container_start=container_start)
            for item in items:
                if item.type == 'episode':
                    # 如果是剧集的单集,则去找上级的图片
                    if item.parentThumb is not None:
                        poster_urls[item.parentThumb] = None
                else:
                    # 否则就用自己的图片
                    if item.thumb is not None:
                        poster_urls[item.thumb] = None
                if len(poster_urls) == total_size:
                    break
            if len(items) < total_size:
                break
            container_start += total_size
        image_list_str = ", ".join(
            [f"{self.get_nt_image_url(self._host.rstrip('/') + url)}?X-Plex-Token={self._token}" for url in
             list(poster_urls.keys())[:total_size]])
        return image_list_str

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

    def get_play_url(self, item_id):
        """
        拼装媒体播放链接
        :param item_id: 媒体的的ID
        """
        return f'{self._play_host or self._host}#!/server/{self._plex.machineIdentifier}/details?key={item_id}'

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
            bitrate = sum([m.bitrate or 0 for m in session.media])
            ret_sessions.append({
                "type": session.TAG,
                "bitrate": bitrate,
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

    def get_resume(self, num=12):
        """
        获取继续观看的媒体
        """
        if not self._plex:
            return []
        items = self._plex.fetchItems('/hubs/continueWatching/items', container_start=0, container_size=num)
        ret_resume = []
        for item in items:
            item_type = MediaType.MOVIE.value if item.TYPE == "movie" else MediaType.TV.value
            if item_type == MediaType.MOVIE.value:
                name = item.title
            else:
                if item.parentIndex == 1:
                    name = "%s 第%s集" % (item.grandparentTitle, item.index)
                else:
                    name = "%s 第%s季第%s集" % (item.grandparentTitle, item.parentIndex, item.index)
            link = self.get_play_url(item.key)
            image = self.get_nt_image_url(item.artUrl)
            ret_resume.append({
                "id": item.key,
                "name": name,
                "type": item_type,
                "image": image,
                "link": link,
                "percent": item.viewOffset / item.duration * 100 if item.viewOffset and item.duration else 0
            })
        return ret_resume

    def get_latest(self, num=20):
        """
        获取最近添加媒体
        """
        if not self._plex:
            return []
        items = self._plex.fetchItems('/library/recentlyAdded', container_start=0, container_size=num)
        ret_resume = []
        for item in items:
            item_type = MediaType.MOVIE.value if item.TYPE == "movie" else MediaType.TV.value
            link = self.get_play_url(item.key)
            title = item.title if item_type == MediaType.MOVIE.value else \
                "%s 第%s季" % (item.parentTitle, item.index)
            image = self.get_nt_image_url(item.posterUrl)
            ret_resume.append({
                "id": item.key,
                "name": title,
                "type": item_type,
                "image": image,
                "link": link
            })
        return ret_resume
