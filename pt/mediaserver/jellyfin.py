import re
import log
from config import Config
from pt.mediaserver.server import IMediaServer
from rmt.meta.metabase import MetaBase
from utils.functions import singleton, get_local_time
from utils.http_utils import RequestUtils
from utils.types import MediaType


@singleton
class Jellyfin(IMediaServer):
    __apikey = None
    __host = None
    __user = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        jellyfin = config.get_config('jellyfin')
        if jellyfin:
            self.__host = jellyfin.get('host')
            if self.__host:
                if not self.__host.startswith('http://') and not self.__host.startswith('https://'):
                    self.__host = "http://" + self.__host
                if not self.__host.endswith('/'):
                    self.__host = self.__host + "/"
            self.__apikey = jellyfin.get('api_key')
            if self.__host and self.__apikey:
                self.__user = self.get_admin_user()

    def get_status(self):
        """
        测试连通性
        """
        return True if self.get_medias_count() else False

    def __get_jellyfin_librarys(self):
        """
        获取Jellyfin媒体库的信息
        """
        if not self.__host or not self.__apikey:
            return []
        req_url = "%sLibrary/MediaFolders?api_key=%s" % (self.__host, self.__apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                return res.json().get("Items")
            else:
                log.error("【JELLYFIN】Library/MediaFolders 未获取到返回数据")
                return []
        except Exception as e:
            log.error("【JELLYFIN】连接Library/MediaFolders 出错：" + str(e))
            return []

    def get_user_count(self):
        """
        获得用户数量
        """
        if not self.__host or not self.__apikey:
            return 0
        req_url = "%sUsers?api_key=%s" % (self.__host, self.__apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                return len(res.json())
            else:
                log.error("【JELLYFIN】Users 未获取到返回数据")
                return 0
        except Exception as e:
            log.error("【JELLYFIN】连接Users出错：" + str(e))
            return 0

    def get_admin_user(self):
        """
        获得管理员用户
        """
        if not self.__host or not self.__apikey:
            return None
        req_url = "%sUsers?api_key=%s" % (self.__host, self.__apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                users = res.json()
                for user in users:
                    if user.get("Policy", {}).get("IsAdministrator"):
                        return user.get("Id")
            else:
                log.error("【JELLYFIN】Users 未获取到返回数据")
        except Exception as e:
            log.error("【JELLYFIN】连接Users出错：" + str(e))
        return None

    def get_activity_log(self, num):
        """
        获取Jellyfin活动记录
        """
        if not self.__host or not self.__apikey:
            return []
        req_url = "%sSystem/ActivityLog/Entries?api_key=%s&Limit=%s" % (self.__host, self.__apikey, num)
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
                        activity = {"type": event_type, "event": event_str, "date": get_local_time(event_date)}
                        ret_array.append(activity)
                    if item.get("Type") == "VideoPlayback":
                        event_type = "PL"
                        event_date = re.sub(r'\dZ', 'Z', item.get("Date"))
                        activity = {"type": event_type, "event": item.get("Name"), "date": get_local_time(event_date)}
                        ret_array.append(activity)
            else:
                log.error("【JELLYFIN】System/ActivityLog/Entries 未获取到返回数据")
                return []
        except Exception as e:
            log.error("【JELLYFIN】连接System/ActivityLog/Entries出错：" + str(e))
            return []
        return ret_array

    def get_medias_count(self):
        """
        获得电影、电视剧、动漫媒体数量
        :return: MovieCount SeriesCount SongCount
        """
        if not self.__host or not self.__apikey:
            return None
        req_url = "%sItems/Counts?api_key=%s" % (self.__host, self.__apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                return res.json()
            else:
                log.error("【JELLYFIN】Items/Counts 未获取到返回数据")
                return {}
        except Exception as e:
            log.error("【JELLYFIN】连接Items/Counts出错：" + str(e))
            return {}

    def __get_jellyfin_series_id_by_name(self, name, year):
        """
        根据名称查询Jellyfin中剧集的SeriesId
        """
        if not self.__host or not self.__apikey or not self.__user:
            return None
        req_url = "%sUsers/%s/Items?api_key=%s&searchTerm=%s&IncludeItemTypes=Series&Limit=10&Recursive=true" % (
            self.__host, self.__user, self.__apikey, name)
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
            log.error("【JELLYFIN】连接Items出错：" + str(e))
            return None
        return ""

    def __get_jellyfin_season_id_by_name(self, name, year, season):
        """
        根据名称查询Jellyfin中剧集和季对应季的Id
        """
        if not self.__host or not self.__apikey or not self.__user:
            return None, None
        series_id = self.__get_jellyfin_series_id_by_name(name, year)
        if series_id is None:
            return None, None
        if not series_id:
            return "", ""
        if not season:
            season = 1
        req_url = "%sShows/%s/Seasons?api_key=%s&userId=%s" % (
            self.__host, series_id, self.__apikey, self.__user)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                res_items = res.json().get("Items")
                if res_items:
                    for res_item in res_items:
                        if int(res_item.get('IndexNumber')) == int(season):
                            return series_id, res_item.get('Id')
        except Exception as e:
            log.error("【JELLYFIN】连接Shows/{Id}/Seasons出错：" + str(e))
            return None, None
        return "", ""

    def get_movies(self, title, year=None):
        """
        根据标题和年份，检查电影是否在Jellyfin中存在，存在则返回列表
        :param title: 标题
        :param year: 年份，为空则不过滤
        :return: 含title、year属性的字典列表
        """
        if not self.__host or not self.__apikey or not self.__user:
            return None
        req_url = "%sUsers/%s/Items?api_key=%s&searchTerm=%s&IncludeItemTypes=Movie&Limit=10&Recursive=true" % (
            self.__host, self.__user, self.__apikey, title)
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
            log.error("【JELLYFIN】连接Items出错：" + str(e))
            return None
        return []

    def __get_jellyfin_tv_episodes(self, title, year=None, season=None):
        """
        根据标题和年份和季，返回Jellyfin中的剧集列表
        :param title: 标题
        :param year: 年份，可以为空，为空时不按年份过滤
        :return: 集号的列表
        """
        if not self.__host or not self.__apikey or not self.__user:
            return None
        # 电视剧
        series_id, season_id = self.__get_jellyfin_season_id_by_name(title, year, season)
        if series_id is None or season_id is None:
            return None
        if not series_id or not season_id:
            return []
        req_url = "%sShows/%s/Episodes?seasonId=%s&&userId=%s&isMissing=false&api_key=%s" % (
            self.__host, series_id, season_id, self.__user, self.__apikey)
        try:
            res_json = RequestUtils().get_res(req_url)
            if res_json:
                res_items = res_json.json().get("Items")
                exists_episodes = []
                for res_item in res_items:
                    exists_episodes.append(int(res_item.get("IndexNumber")))
                return exists_episodes
        except Exception as e:
            log.error("【JELLYFIN】连接Shows/{Id}/Episodes出错：" + str(e))
            return None
        return []

    def get_no_exists_episodes(self, meta_info: MetaBase, season, total_num):
        """
        根据标题、年份、季、总集数，查询Jellyfin中缺少哪几集
        :param meta_info: 已识别的需要查询的媒体信息
        :param season: 季号，数字
        :param total_num: 该季的总集数
        :return: 该季不存在的集号列表
        """
        if not self.__host or not self.__apikey:
            return None
        exists_episodes = self.__get_jellyfin_tv_episodes(meta_info.title, meta_info.year, season)
        if not isinstance(exists_episodes, list):
            return None
        total_episodes = [episode for episode in range(1, total_num + 1)]
        return list(set(total_episodes).difference(set(exists_episodes)))

    def get_image_by_id(self, item_id, image_type):
        """
        根据ItemId从Jellyfin查询图片地址
        :param item_id: 在Emby中的ID
        :param image_type: 图片的类弄地，poster或者backdrop等
        :return: 图片对应在TMDB中的URL
        """
        if not self.__host or not self.__apikey:
            return None
        req_url = "%sItems/%s/RemoteImages?api_key=%s" % (self.__host, item_id, self.__apikey)
        try:
            res = RequestUtils().get_res(req_url)
            if res:
                images = res.json().get("Images")
                for image in images:
                    if image.get("ProviderName") == "TheMovieDb" and image.get("Type") == image_type:
                        return image.get("Url")
            else:
                log.error("【JELLYFIN】Items/RemoteImages 未获取到返回数据")
                return None
        except Exception as e:
            log.error("【JELLYFIN】连接Items/{Id}/RemoteImages出错：" + str(e))
            return None
        return None

    def refresh_root_library(self):
        """
        通知Jellyfin刷新整个媒体库
        """
        if not self.__host or not self.__apikey:
            return False
        req_url = "%sLibrary/Refresh?api_key=%s" % (self.__host, self.__apikey)
        try:
            res = RequestUtils().post_res(req_url)
            if res:
                return True
        except Exception as e:
            log.error("【JELLYFIN】连接Library/Refresh出错：" + str(e))
            return False

    def refresh_library_by_items(self, items):
        """
        按类型、名称、年份来刷新媒体库，Jellyfin没有刷单个项目的API，这里直接刷新整库
        :param items: 已识别的需要刷新媒体库的媒体信息列表
        """
        # 没找到单项目刷新的对应的API，先按全库刷新
        if not items:
            return False
        if not self.__host or not self.__apikey:
            return False
        return self.refresh_root_library()

    def __get_jellyfin_library_id_by_item(self, item):
        """
        根据媒体信息查询在哪个媒体库，返回要刷新的位置的ID
        :param item: 由title、year、type组成的字典
        """
        if not item.get("title") or not item.get("year") or not item.get("type"):
            return None
        if item.get("type") == MediaType.TV:
            item_id = self.__get_jellyfin_series_id_by_name(item.get("title"), item.get("year"))
            if item_id:
                # 存在电视剧，则直接刷新这个电视剧就行
                return item_id
        else:
            if self.get_movies(item.get("title"), item.get("year")):
                # 已存在，不用刷新
                return None
        # 查找需要刷新的媒体库ID
        for library in self.__get_jellyfin_librarys():
            for folder in library.get("Path"):
                if "/%s" % item.get("category") in folder.get("Path"):
                    return library.get("Id")
        # 刷新根目录
        return "/"
