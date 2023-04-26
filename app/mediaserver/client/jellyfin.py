import re

import log
from app.mediaserver.client._base import _IMediaClient
from app.utils import RequestUtils, SystemUtils, ExceptionUtils, IpUtils
from app.utils.types import MediaServerType, MediaType
from config import Config


class Jellyfin(_IMediaClient):
    # 媒体服务器ID
    client_id = "jellyfin"
    # 媒体服务器类型
    client_type = MediaServerType.JELLYFIN
    # 媒体服务器名称
    client_name = MediaServerType.JELLYFIN.value

    # 私有属性
    _client_config = {}
    _serverid = None
    _apikey = None
    _host = None
    _play_host = None
    _user = None

    def __init__(self, config=None):
        if config:
            self._client_config = config
        else:
            self._client_config = Config().get_config('jellyfin')
        self.init_config()

    def init_config(self):
        if self._client_config:
            self._host = self._client_config.get('host')
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
            self._apikey = self._client_config.get('api_key')
            if self._host and self._apikey:
                self._user = self.get_user(Config().current_user)
                self._serverid = self.get_server_id()

    @classmethod
    def match(cls, ctype):
        return True if ctype in [cls.client_id, cls.client_type, cls.client_name] else False

    def get_type(self):
        return self.client_type

    def get_status(self):
        """
        测试连通性
        """
        return True if self.get_medias_count() else False

    def __get_jellyfin_librarys(self):
        """
        获取Jellyfin媒体库的信息
        """
        if not self._host or not self._apikey:
            return []
        req_url = f"{self._host}Users/{self._user}/Views?api_key={self._apikey}"
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                return res.json().get("Items")
            else:
                log.error(f"【{self.client_name}】Users/Views 未获取到返回数据")
                return []
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接Users/Views 出错：" + str(e))
            return []

    def get_user_count(self):
        """
        获得用户数量
        """
        if not self._host or not self._apikey:
            return 0
        req_url = "%sUsers?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                return len(res.json())
            else:
                log.error(f"【{self.client_name}】Users 未获取到返回数据")
                return 0
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接Users出错：" + str(e))
            return 0

    def get_user(self, user_name=None):
        """
        获得管理员用户
        """
        if not self._host or not self._apikey:
            return None
        req_url = "%sUsers?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                users = res.json()
                # 先查询是否有与当前用户名称匹配的
                if user_name:
                    for user in users:
                        if user.get("Name") == user_name:
                            return user.get("Id")
                # 查询管理员
                for user in users:
                    if user.get("Policy", {}).get("IsAdministrator"):
                        return user.get("Id")
            else:
                log.error(f"【{self.client_name}】Users 未获取到返回数据")
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接Users出错：" + str(e))
        return None

    def get_server_id(self):
        """
        获得服务器信息
        """
        if not self._host or not self._apikey:
            return None
        req_url = "%sSystem/Info?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                return res.json().get("Id")
            else:
                log.error(f"【{self.client_name}】System/Info 未获取到返回数据")
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接System/Info出错：" + str(e))
        return None

    def get_activity_log(self, num):
        """
        获取Jellyfin活动记录
        """
        if not self._host or not self._apikey:
            return []
        req_url = "%sSystem/ActivityLog/Entries?api_key=%s&Limit=%s" % (self._host, self._apikey, num)
        ret_array = []
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                ret_json = res.json()
                items = ret_json.get('Items')
                for item in items:
                    if item.get("Type") == "SessionStarted":
                        event_type = "LG"
                        event_date = re.sub(r'\dZ', 'Z', item.get("Date"))
                        event_str = "%s, %s" % (item.get("Name"), item.get("ShortOverview"))
                        activity = {"type": event_type, "event": event_str,
                                    "date": SystemUtils.get_local_time(event_date)}
                        ret_array.append(activity)
                    if item.get("Type") in ["VideoPlayback", "VideoPlaybackStopped"]:
                        event_type = "PL"
                        event_date = re.sub(r'\dZ', 'Z', item.get("Date"))
                        activity = {"type": event_type, "event": item.get("Name"),
                                    "date": SystemUtils.get_local_time(event_date)}
                        ret_array.append(activity)
            else:
                log.error(f"【{self.client_name}】System/ActivityLog/Entries 未获取到返回数据")
                return []
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接System/ActivityLog/Entries出错：" + str(e))
            return []
        return ret_array

    def get_medias_count(self):
        """
        获得电影、电视剧、动漫媒体数量
        :return: MovieCount SeriesCount SongCount
        """
        if not self._host or not self._apikey:
            return None
        req_url = "%sItems/Counts?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                return res.json()
            else:
                log.error(f"【{self.client_name}】Items/Counts 未获取到返回数据")
                return {}
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接Items/Counts出错：" + str(e))
            return {}

    def __get_jellyfin_series_id_by_name(self, name, year):
        """
        根据名称查询Jellyfin中剧集的SeriesId
        """
        if not self._host or not self._apikey or not self._user:
            return None
        req_url = "%sUsers/%s/Items?api_key=%s&searchTerm=%s&IncludeItemTypes=Series&Limit=10&Recursive=true" % (
            self._host, self._user, self._apikey, name)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                res_items = res.json().get("Items")
                if res_items:
                    for res_item in res_items:
                        if res_item.get('Name') == name and (
                                not year or str(res_item.get('ProductionYear')) == str(year)):
                            return res_item.get('Id')
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接Items出错：" + str(e))
            return None
        return ""

    def get_movies(self, title, year=None):
        """
        根据标题和年份，检查电影是否在Jellyfin中存在，存在则返回列表
        :param title: 标题
        :param year: 年份，为空则不过滤
        :return: 含title、year属性的字典列表
        """
        if not self._host or not self._apikey or not self._user:
            return None
        req_url = "%sUsers/%s/Items?api_key=%s&searchTerm=%s&IncludeItemTypes=Movie&Limit=10&Recursive=true" % (
            self._host, self._user, self._apikey, title)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                res_items = res.json().get("Items")
                if res_items:
                    ret_movies = []
                    for res_item in res_items:
                        if res_item.get('Name') == title and (
                                not year or str(res_item.get('ProductionYear')) == str(year)):
                            ret_movies.append(
                                {'title': res_item.get('Name'), 'year': str(res_item.get('ProductionYear'))})
                            return ret_movies
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接Items出错：" + str(e))
            return None
        return []

    def get_tv_episodes(self,
                        item_id=None,
                        title=None,
                        year=None,
                        tmdb_id=None,
                        season=None):
        """
        根据标题和年份和季，返回Jellyfin中的剧集列表
        :param item_id: Jellyfin中的剧集ID
        :param title: 标题
        :param year: 年份
        :param tmdb_id: TMDBID
        :param season: 季
        :return: 集号的列表
        """
        if not self._host or not self._apikey or not self._user:
            return None
        if not item_id:
            # 查TVID
            item_id = self.__get_jellyfin_series_id_by_name(title, year)
            if item_id is None:
                return None
            if not item_id:
                return []
            # 验证tmdbid是否相同
            item_tmdbid = self.get_iteminfo(item_id).get("ProviderIds", {}).get("Tmdb")
            if tmdb_id and item_tmdbid:
                if str(tmdb_id) != str(item_tmdbid):
                    return []
        if not season:
            season = ""
        req_url = "%sShows/%s/Episodes?season=%s&&userId=%s&isMissing=false&api_key=%s" % (
            self._host, item_id, season, self._user, self._apikey)
        try:
            res_json = RequestUtils().get_res(req_url)
            if res_json:
                res_items = res_json.json().get("Items")
                exists_episodes = []
                for res_item in res_items:
                    exists_episodes.append({
                        "season_num": res_item.get("ParentIndexNumber") or 0,
                        "episode_num": res_item.get("IndexNumber") or 0
                    })
                return exists_episodes
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接Shows/Id/Episodes出错：" + str(e))
            return None
        return []

    def get_no_exists_episodes(self, meta_info, season, total_num):
        """
        根据标题、年份、季、总集数，查询Jellyfin中缺少哪几集
        :param meta_info: 已识别的需要查询的媒体信息
        :param season: 季号，数字
        :param total_num: 该季的总集数
        :return: 该季不存在的集号列表
        """
        if not self._host or not self._apikey:
            return None
        # 没有季默认为和1季
        if not season:
            season = 1
        exists_episodes = self.get_tv_episodes(title=meta_info.title,
                                               year=meta_info.year,
                                               tmdb_id=meta_info.tmdb_id,
                                               season=season)
        if not isinstance(exists_episodes, list):
            return None
        exists_episodes = [episode.get("episode_num") for episode in exists_episodes]
        total_episodes = [episode for episode in range(1, total_num + 1)]
        return list(set(total_episodes).difference(set(exists_episodes)))

    def get_episode_image_by_id(self, item_id, season_id, episode_id):
        """
        根据itemid、season_id、episode_id从Emby查询图片地址
        :param item_id: 在Emby中的ID
        :param season_id: 季
        :param episode_id: 集
        :return: 图片对应在TMDB中的URL
        """
        if not self._host or not self._apikey or not self._user:
            return None
        # 查询所有剧集
        req_url = "%sShows/%s/Episodes?season=%s&&userId=%s&isMissing=false&api_key=%s" % (
            self._host, item_id, season_id, self._user, self._apikey)
        try:
            res_json = RequestUtils().get_res(req_url)
            if res_json:
                res_items = res_json.json().get("Items")
                for res_item in res_items:
                    # 查询当前剧集的itemid
                    if res_item.get("IndexNumber") == episode_id:
                        # 查询当前剧集的图片
                        img_url = self.get_remote_image_by_id(res_item.get("Id"), "Primary")
                        # 没查到tmdb图片则判断播放地址是不是外网，使用jellyfin刮削的图片（直接挂载网盘场景）
                        if not img_url and not IpUtils.is_internal(self._play_host) \
                                and res_item.get('ImageTags', {}).get('Primary'):
                            return "%sItems/%s/Images/Primary?maxHeight=225&maxWidth=400&tag=%s&quality=90" % (
                                self._play_host, res_item.get("Id"), res_item.get('ImageTags', {}).get('Primary'))
                        return img_url
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接Shows/Id/Episodes出错：" + str(e))
            return None

    def get_remote_image_by_id(self, item_id, image_type):
        """
        根据ItemId从Jellyfin查询TMDB图片地址
        :param item_id: 在Emby中的ID
        :param image_type: 图片的类弄地，poster或者backdrop等
        :return: 图片对应在TMDB中的URL
        """
        if not self._host or not self._apikey:
            return None
        req_url = "%sItems/%s/RemoteImages?api_key=%s" % (self._host, item_id, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                images = res.json().get("Images")
                for image in images:
                    if image.get("ProviderName") == "TheMovieDb" and image.get("Type") == image_type:
                        return image.get("Url")
            else:
                log.error(f"【{self.client_name}】Items/RemoteImages 未获取到返回数据")
                return None
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接Items/Id/RemoteImages出错：" + str(e))
            return None
        return None

    def get_local_image_by_id(self, item_id, remote=True, inner=False):
        """
        根据ItemId从媒体服务器查询有声书图片地址
        :param: item_id: 在Emby中的ID
        :param: remote 是否远程使用，TG微信等客户端调用应为True
        :param: inner 是否NT内部调用，为True是会使用NT中转
        """
        if not self._host or not self._apikey:
            return None
        if not remote:
            image_url = "%sItems/%s/Images/Primary" % (self._host, item_id)
            if inner:
                return self.get_nt_image_url(image_url)
            return image_url
        else:
            host = self._play_host or self._host
            image_url = "%sItems/%s/Images/Primary" % (host, item_id)
            if IpUtils.is_internal(host):
                return self.get_nt_image_url(url=image_url, remote=True)
            return image_url

    def refresh_root_library(self):
        """
        通知Jellyfin刷新整个媒体库
        """
        if not self._host or not self._apikey:
            return False
        req_url = "%sLibrary/Refresh?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().post_res(req_url)
            if res:
                return True
            else:
                log.info(f"【{self.client_name}】刷新媒体库失败，无法连接Jellyfin！")
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接Library/Refresh出错：" + str(e))
            return False

    def refresh_library_by_items(self, items):
        """
        按类型、名称、年份来刷新媒体库，Jellyfin没有刷单个项目的API，这里直接刷新整个库
        :param items: 已识别的需要刷新媒体库的媒体信息列表
        """
        # 没找到单项目刷新的对应的API，先按全库刷新
        if not items:
            return False
        if not self._host or not self._apikey:
            return False
        return self.refresh_root_library()

    def get_libraries(self):
        """
        获取媒体服务器所有媒体库列表
        """
        if not self._host or not self._apikey:
            return []
        libraries = []
        for library in self.__get_jellyfin_librarys() or []:
            match library.get("CollectionType"):
                case "movies":
                    library_type = MediaType.MOVIE.value
                case "tvshows":
                    library_type = MediaType.TV.value
                case _:
                    continue
            image = self.get_local_image_by_id(library.get("Id"), remote=False, inner=True)
            link = f"{self._play_host or self._host}web/index.html#!" \
                   f"/movies.html?topParentId={library.get('Id')}" \
                if library_type == MediaType.MOVIE.value \
                else f"{self._play_host or self._host}web/index.html#!" \
                     f"/tv.html?topParentId={library.get('Id')}"
            libraries.append({
                "id": library.get("Id"),
                "name": library.get("Name"),
                "path": library.get("Path"),
                "type": library_type,
                "image": image,
                "link": link
            })
        return libraries

    def __get_backdrop_url(self, item_id, image_tag, remote=True, inner=False):
        """
        获取Backdrop图片地址
        :param: item_id: 在Emby中的ID
        :param: image_tag: 图片的tag
        :param: remote 是否远程使用，TG微信等客户端调用应为True
        :param: inner 是否NT内部调用，为True是会使用NT中转
        """
        if not self._host or not self._apikey:
            return ""
        if not image_tag or not item_id:
            return ""
        if not remote:
            image_url = f"{self._host}Items/{item_id}/"\
                        f"Images/Backdrop?tag={image_tag}&fillWidth=666&api_key={self._apikey}"
            if inner:
                return self.get_nt_image_url(image_url)
            return image_url
        else:
            host = self._play_host or self._host
            image_url = f"{host}Items/{item_id}/"\
                        f"Images/Backdrop?tag={image_tag}&fillWidth=666&api_key={self._apikey}"
            if IpUtils.is_internal(host):
                return self.get_nt_image_url(url=image_url, remote=True)
            return image_url

    def get_iteminfo(self, itemid):
        """
        获取单个项目详情
        """
        if not itemid:
            return {}
        if not self._host or not self._apikey:
            return {}
        req_url = "%sUsers/%s/Items/%s?api_key=%s" % (
            self._host, self._user, itemid, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res and res.status_code == 200:
                return res.json()
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {}

    def get_items(self, parent):
        """
        获取媒体服务器所有媒体库列表
        """
        if not parent:
            yield {}
        if not self._host or not self._apikey:
            yield {}
        req_url = "%sUsers/%s/Items?parentId=%s&api_key=%s" % (self._host, self._user, parent, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res and res.status_code == 200:
                results = res.json().get("Items") or []
                for result in results:
                    if not result:
                        continue
                    if result.get("Type") in ["Movie", "Series"]:
                        item_info = self.get_iteminfo(result.get("Id"))
                        yield {"id": result.get("Id"),
                               "library": item_info.get("ParentId"),
                               "type": item_info.get("Type"),
                               "title": item_info.get("Name"),
                               "originalTitle": item_info.get("OriginalTitle"),
                               "year": item_info.get("ProductionYear"),
                               "tmdbid": item_info.get("ProviderIds", {}).get("Tmdb"),
                               "imdbid": item_info.get("ProviderIds", {}).get("Imdb"),
                               "path": item_info.get("Path"),
                               "json": str(item_info)}
                    elif "Folder" in result.get("Type"):
                        for item in self.get_items(result.get("Id")):
                            yield item
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接Users/Items出错：" + str(e))
        yield {}

    def get_play_url(self, item_id):
        """
        拼装媒体播放链接
        :param item_id: 媒体的的ID
        """
        return f"{self._play_host or self._host}web/index.html#!/details?id={item_id}&serverId={self._serverid}"

    def get_playing_sessions(self):
        """
        获取正在播放的会话
        """
        if not self._host or not self._apikey:
            return []
        playing_sessions = []
        req_url = "%sSessions?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res and res.status_code == 200:
                sessions = res.json()
                for session in sessions:
                    if session.get("NowPlayingItem"):
                        playing_sessions.append(session)
            return playing_sessions
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return []

    def get_webhook_message(self, message):
        """
        解析Jellyfin报文
        """
        eventItem = {'event': message.get('NotificationType', ''),
                     'item_name': message.get('Name'),
                     'user_name': message.get('NotificationUsername')
                     }
        return eventItem

    def get_resume(self, num=12):
        """
        获得继续观看
        """
        if not self._host or not self._apikey:
            return None
        req_url = f"{self._host}Users/{self._user}/Items/Resume?Limit={num}&MediaTypes=Video&api_key={self._apikey}"
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                result = res.json().get("Items") or []
                ret_resume = []
                for item in result:
                    if item.get("Type") not in ["Movie", "Episode"]:
                        continue
                    item_type = MediaType.MOVIE.value if item.get("Type") == "Movie" else MediaType.TV.value
                    link = self.get_play_url(item.get("Id"))
                    if item.get("BackdropImageTags"):
                        image = self.__get_backdrop_url(item_id=item.get("Id"),
                                                        image_tag=item.get("BackdropImageTags")[0],
                                                        remote=False,
                                                        inner=True)
                    else:
                        image = self.get_local_image_by_id(item.get("Id"), remote=False, inner=True)
                    if item_type == MediaType.MOVIE.value:
                        title = item.get("Name")
                    else:
                        if item.get("ParentIndexNumber") == 1:
                            title = f'{item.get("SeriesName")} 第{item.get("IndexNumber")}集'
                        else:
                            title = f'{item.get("SeriesName")} 第{item.get("ParentIndexNumber")}季第{item.get("IndexNumber")}集'
                    ret_resume.append({
                        "id": item.get("Id"),
                        "name": title,
                        "type": item_type,
                        "image": image,
                        "link": link,
                        "percent": item.get("UserData", {}).get("PlayedPercentage")
                    })
                return ret_resume
            else:
                log.error(f"【{self.client_name}】Users/Items/Resume 未获取到返回数据")
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接Users/Items/Resume出错：" + str(e))
        return []

    def get_latest(self, num=20):
        """
        获得最近更新
        """
        if not self._host or not self._apikey:
            return None
        req_url = f"{self._host}Users/{self._user}/Items/Latest?Limit={num}&MediaTypes=Video&api_key={self._apikey}"
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                result = res.json() or []
                ret_latest = []
                for item in result:
                    if item.get("Type") not in ["Movie", "Series"]:
                        continue
                    item_type = MediaType.MOVIE.value if item.get("Type") == "Movie" else MediaType.TV.value
                    link = self.get_play_url(item.get("Id"))
                    image = self.get_local_image_by_id(item_id=item.get("Id"), remote=False, inner=True)
                    ret_latest.append({
                        "id": item.get("Id"),
                        "name": item.get("Name"),
                        "type": item_type,
                        "image": image,
                        "link": link
                    })
                return ret_latest
            else:
                log.error(f"【{self.client_name}】Users/Items/Latest 未获取到返回数据")
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.client_name}】连接Users/Items/Latest出错：" + str(e))
        return []
