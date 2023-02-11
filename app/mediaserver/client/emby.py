import os
import re

import log
from config import Config
from app.mediaserver.client._base import _IMediaClient
from app.utils import RequestUtils, SystemUtils, ExceptionUtils
from app.utils.types import MediaType, MediaServerType


class Emby(_IMediaClient):
    schema = "emby"
    server_type = MediaServerType.EMBY.value
    _client_config = {}

    _apikey = None
    _host = None
    _user = None
    _libraries = []

    def __init__(self, config=None):
        if config:
            self._client_config = config
        else:
            self._client_config = Config().get_config('emby')
        self.init_config()

    def init_config(self):
        if self._client_config:
            self._host = self._client_config.get('host')
            if self._host:
                if not self._host.startswith('http'):
                    self._host = "http://" + self._host
                if not self._host.endswith('/'):
                    self._host = self._host + "/"
            self._apikey = self._client_config.get('api_key')
            if self._host and self._apikey:
                self._libraries = self.__get_emby_librarys()
                self._user = self.get_admin_user()

    @classmethod
    def match(cls, ctype):
        return True if ctype in [cls.schema, cls.server_type] else False

    def get_status(self):
        """
        测试连通性
        """
        return True if self.get_medias_count() else False

    def __get_emby_librarys(self):
        """
        获取Emby媒体库列表
        """
        if not self._host or not self._apikey:
            return []
        req_url = "%semby/Library/SelectableMediaFolders?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                return res.json()
            else:
                log.error(f"【{self.server_type}】Library/SelectableMediaFolders 未获取到返回数据")
                return []
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.server_type}】连接Library/SelectableMediaFolders 出错：" + str(e))
            return []

    def get_admin_user(self):
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
                for user in users:
                    if user.get("Policy", {}).get("IsAdministrator"):
                        return user.get("Id")
            else:
                log.error(f"【{self.server_type}】Users 未获取到返回数据")
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.server_type}】连接Users出错：" + str(e))
        return None

    def get_user_count(self):
        """
        获得用户数量
        """
        if not self._host or not self._apikey:
            return 0
        req_url = "%semby/Users/Query?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                return res.json().get("TotalRecordCount")
            else:
                log.error(f"【{self.server_type}】Users/Query 未获取到返回数据")
                return 0
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.server_type}】连接Users/Query出错：" + str(e))
            return 0

    def get_activity_log(self, num):
        """
        获取Emby活动记录
        """
        if not self._host or not self._apikey:
            return []
        req_url = "%semby/System/ActivityLog/Entries?api_key=%s&" % (self._host, self._apikey)
        ret_array = []
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                ret_json = res.json()
                items = ret_json.get('Items')
                for item in items:
                    if item.get("Type") == "AuthenticationSucceeded":
                        event_type = "LG"
                        event_date = SystemUtils.get_local_time(item.get("Date"))
                        event_str = "%s, %s" % (item.get("Name"), item.get("ShortOverview"))
                        activity = {"type": event_type, "event": event_str, "date": event_date}
                        ret_array.append(activity)
                    if item.get("Type") == "VideoPlayback":
                        event_type = "PL"
                        event_date = SystemUtils.get_local_time(item.get("Date"))
                        event_str = item.get("Name")
                        activity = {"type": event_type, "event": event_str, "date": event_date}
                        ret_array.append(activity)
            else:
                log.error(f"【{self.server_type}】System/ActivityLog/Entries 未获取到返回数据")
                return []
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.server_type}】连接System/ActivityLog/Entries出错：" + str(e))
            return []
        return ret_array[:num]

    def get_medias_count(self):
        """
        获得电影、电视剧、动漫媒体数量
        :return: MovieCount SeriesCount SongCount
        """
        if not self._host or not self._apikey:
            return {}
        req_url = "%semby/Items/Counts?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                return res.json()
            else:
                log.error(f"【{self.server_type}】Items/Counts 未获取到返回数据")
                return {}
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.server_type}】连接Items/Counts出错：" + str(e))
            return {}

    def __get_emby_series_id_by_name(self, name, year):
        """
        根据名称查询Emby中剧集的SeriesId
        :param name: 标题
        :param year: 年份
        :return: None 表示连不通，""表示未找到，找到返回ID
        """
        if not self._host or not self._apikey:
            return None
        req_url = "%semby/Items?IncludeItemTypes=Series&Fields=ProductionYear&StartIndex=0&Recursive=true&SearchTerm=%s&Limit=10&IncludeSearchTypes=false&api_key=%s" % (
            self._host, name, self._apikey)
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
            log.error(f"【{self.server_type}】连接Items出错：" + str(e))
            return None
        return ""

    def get_movies(self, title, year=None):
        """
        根据标题和年份，检查电影是否在Emby中存在，存在则返回列表
        :param title: 标题
        :param year: 年份，可以为空，为空时不按年份过滤
        :return: 含title、year属性的字典列表
        """
        if not self._host or not self._apikey:
            return None
        req_url = "%semby/Items?IncludeItemTypes=Movie&Fields=ProductionYear&StartIndex=0&Recursive=true&SearchTerm=%s&Limit=10&IncludeSearchTypes=false&api_key=%s" % (
            self._host, title, self._apikey)
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
            log.error(f"【{self.server_type}】连接Items出错：" + str(e))
            return None
        return []

    def __get_emby_tv_episodes(self, title, year, tmdb_id=None, season=None):
        """
        根据标题和年份和季，返回Emby中的剧集列表
        :param title: 标题
        :param year: 年份，可以为空，为空时不按年份过滤
        :param tmdb_id: TMDBID
        :param season: 季
        :return: 集号的列表
        """
        if not self._host or not self._apikey:
            return None
        # 电视剧
        item_id = self.__get_emby_series_id_by_name(title, year)
        if item_id is None:
            return None
        if not item_id:
            return []
        # 验证tmdbid是否相同
        item_tmdbid = self.get_iteminfo(item_id).get("ProviderIds", {}).get("Tmdb")
        if tmdb_id and item_tmdbid:
            if str(tmdb_id) != str(item_tmdbid):
                return []
        # /Shows/Id/Episodes 查集的信息
        if not season:
            season = 1
        req_url = "%semby/Shows/%s/Episodes?Season=%s&IsMissing=false&api_key=%s" % (
            self._host, item_id, season, self._apikey)
        try:
            res_json = RequestUtils().get_res(req_url)
            if res_json:
                res_items = res_json.json().get("Items")
                exists_episodes = []
                for res_item in res_items:
                    exists_episodes.append(int(res_item.get("IndexNumber")))
                return exists_episodes
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.server_type}】连接Shows/Id/Episodes出错：" + str(e))
            return None
        return []

    def get_no_exists_episodes(self, meta_info, season, total_num):
        """
        根据标题、年份、季、总集数，查询Emby中缺少哪几集
        :param meta_info: 已识别的需要查询的媒体信息
        :param season: 季号，数字
        :param total_num: 该季的总集数
        :return: 该季不存在的集号列表
        """
        if not self._host or not self._apikey:
            return None
        exists_episodes = self.__get_emby_tv_episodes(meta_info.title, meta_info.year, meta_info.tmdb_id, season)
        if not isinstance(exists_episodes, list):
            return None
        total_episodes = [episode for episode in range(1, total_num + 1)]
        return list(set(total_episodes).difference(set(exists_episodes)))

    def get_image_by_id(self, item_id, image_type):
        """
        根据ItemId从Emby查询图片地址
        :param item_id: 在Emby中的ID
        :param image_type: 图片的类弄地，poster或者backdrop等
        :return: 图片对应在TMDB中的URL
        """
        if not self._host or not self._apikey:
            return None
        req_url = "%semby/Items/%s/RemoteImages?api_key=%s" % (self._host, item_id, self._apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                images = res.json().get("Images")
                for image in images:
                    if image.get("ProviderName") == "TheMovieDb" and image.get("Type") == image_type:
                        return image.get("Url")
            else:
                log.error(f"【{self.server_type}】Items/RemoteImages 未获取到返回数据")
                return None
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.server_type}】连接Items/Id/RemoteImages出错：" + str(e))
            return None
        return None

    def __refresh_emby_library_by_id(self, item_id):
        """
        通知Emby刷新一个项目的媒体库
        """
        if not self._host or not self._apikey:
            return False
        req_url = "%semby/Items/%s/Refresh?Recursive=true&api_key=%s" % (self._host, item_id, self._apikey)
        try:
            res = RequestUtils().post_res(req_url)
            if res:
                return True
            else:
                log.info(f"【{self.server_type}】刷新媒体库对象 {item_id} 失败，无法连接Emby！")
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.server_type}】连接Items/Id/Refresh出错：" + str(e))
            return False
        return False

    def refresh_root_library(self):
        """
        通知Emby刷新整个媒体库
        """
        if not self._host or not self._apikey:
            return False
        req_url = "%semby/Library/Refresh?api_key=%s" % (self._host, self._apikey)
        try:
            res = RequestUtils().post_res(req_url)
            if res:
                return True
            else:
                log.info(f"【{self.server_type}】刷新媒体库失败，无法连接Emby！")
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.server_type}】连接Library/Refresh出错：" + str(e))
            return False
        return False

    def refresh_library_by_items(self, items):
        """
        按类型、名称、年份来刷新媒体库
        :param items: 已识别的需要刷新媒体库的媒体信息列表
        """
        if not items:
            return
        # 收集要刷新的媒体库信息
        log.info(f"【{self.server_type}】开始刷新Emby媒体库...")
        library_ids = []
        for item in items:
            if not item:
                continue
            library_id = self.__get_emby_library_id_by_item(item)
            if library_id and library_id not in library_ids:
                library_ids.append(library_id)
        # 开始刷新媒体库
        if "/" in library_ids:
            self.refresh_root_library()
            return
        for library_id in library_ids:
            if library_id != "/":
                self.__refresh_emby_library_by_id(library_id)
        log.info(f"【{self.server_type}】Emby媒体库刷新完成")

    def __get_emby_library_id_by_item(self, item):
        """
        根据媒体信息查询在哪个媒体库，返回要刷新的位置的ID
        :param item: 由title、year、type组成的字典
        """
        if not item.get("title") or not item.get("year") or not item.get("type"):
            return None
        if item.get("type") == MediaType.TV:
            item_id = self.__get_emby_series_id_by_name(item.get("title"), item.get("year"))
            if item_id:
                # 存在电视剧，则直接刷新这个电视剧就行
                return item_id
        else:
            if self.get_movies(item.get("title"), item.get("year")):
                # 已存在，不用刷新
                return None
        # 查找需要刷新的媒体库ID
        for library in self._libraries:
            # 找同级路径最多的媒体库（要求容器内映射路径与实际一致）
            max_equal_path_id = None
            max_path_len = 0
            equal_path_num = 0
            for folder in library.get("SubFolders"):
                path_list = re.split(pattern='/+|\\\\+', string=folder.get("Path"))
                if item.get("category") != path_list[-1]:
                    continue
                try:
                    path_len = len(os.path.commonpath([item.get("target_path"), folder.get("Path")]))
                    if path_len >= max_path_len:
                        max_path_len = path_len
                        max_equal_path_id = folder.get("Id")
                        equal_path_num += 1
                except Exception as err:
                    ExceptionUtils.exception_traceback(err)
                    continue
            if max_equal_path_id:
                return max_equal_path_id if equal_path_num == 1 else library.get("Id")
            # 如果找不到，只要路径中有分类目录名就命中
            for folder in library.get("SubFolders"):
                if folder.get("Path") and re.search(r"[/\\]%s" % item.get("category"), folder.get("Path")):
                    return library.get("Id")
        # 刷新根目录
        return "/"

    def get_libraries(self):
        """
        获取媒体服务器所有媒体库列表
        """
        if self._host and self._apikey:
            self._libraries = self.__get_emby_librarys()
        libraries = []
        for library in self._libraries:
            libraries.append({"id": library.get("Id"), "name": library.get("Name")})
        return libraries

    def get_iteminfo(self, itemid):
        """
        获取单个项目详情
        """
        if not itemid:
            return {}
        if not self._host or not self._apikey:
            return {}
        req_url = "%semby/Users/%s/Items/%s?api_key=%s" % (self._host, self._user, itemid, self._apikey)
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
        req_url = "%semby/Users/%s/Items?ParentId=%s&api_key=%s" % (self._host, self._user, parent, self._apikey)
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
                        for item in self.get_items(parent=result.get('Id')):
                            yield item
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error(f"【{self.server_type}】连接Users/Items出错：" + str(e))
        yield {}

    def get_playing_sessions(self):
        """
        获取正在播放的会话
        """
        if not self._host or not self._apikey:
            return []
        playing_sessions = []
        req_url = "%semby/Sessions?api_key=%s" % (self._host, self._apikey)
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
