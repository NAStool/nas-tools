import time
from datetime import datetime
import requests
import log
from config import RMT_FAVTYPE, Config
from message.send import Message
from rmt.filetransfer import FileTransfer
from rmt.metainfo import MetaInfo
from utils.functions import get_local_time, get_location
from utils.types import MediaType

PLAY_LIST = []


class Emby:
    __config = None
    message = None
    media = None
    __apikey = None
    __host = None
    __library_info = []

    def __init__(self):
        self.message = Message()
        self.__config = Config()
        emby = self.__config.get_config('emby')
        if emby:
            self.__host = emby.get('host')
            if not self.__host.startswith('http://') and not self.__host.startswith('https://'):
                self.__host = "http://" + self.__host
            if not self.__host.endswith('/'):
                self.__host = self.__host + "/"
            self.__apikey = emby.get('api_key')
            self.__library_info = self.get_emby_librarys()

    # 获取Emby媒体库的信息
    def get_emby_librarys(self):
        if not self.__host or not self.__apikey:
            return []
        req_url = "%semby/Library/SelectableMediaFolders?api_key=%s" % (self.__host, self.__apikey)
        try:
            res = requests.get(req_url)
            if res:
                return res.json()
            else:
                log.error("【EMBY】Library/SelectableMediaFolders 未获取到返回数据")
                return []
        except Exception as e:
            log.error("【EMBY】连接Library/SelectableMediaFolders 出错：" + str(e))
            return []

    # 获得用户数量
    def get_emby_user_count(self):
        if not self.__host or not self.__apikey:
            return 0
        req_url = "%semby/Users/Query?api_key=%s" % (self.__host, self.__apikey)
        try:
            res = requests.get(req_url)
            if res:
                return res.json().get("TotalRecordCount")
            else:
                log.error("【EMBY】Users/Query 未获取到返回数据")
                return 0
        except Exception as e:
            log.error("【EMBY】连接Users/Query出错：" + str(e))
            return 0

    # 获取Emby活动记录
    def get_emby_activity_log(self, num):
        if not self.__host or not self.__apikey:
            return []
        req_url = "%semby/System/ActivityLog/Entries?api_key=%s&Limit=%s" % (self.__host, self.__apikey, num)
        ret_array = []
        try:
            res = requests.get(req_url)
            if res:
                ret_json = res.json()
                items = ret_json.get('Items')
                for item in items:
                    if item.get("Type") == "AuthenticationSucceeded":
                        event_type = "LG"
                        event_date = get_local_time(item.get("Date"))
                        event_str = "%s, %s" % (item.get("Name"), item.get("ShortOverview"))
                        activity = {"type": event_type, "event": event_str, "date": event_date}
                        ret_array.append(activity)
                    if item.get("Type") == "VideoPlayback":
                        event_type = "PL"
                        event_date = get_local_time(item.get("Date"))
                        event_str = item.get("Name")
                        activity = {"type": event_type, "event": event_str, "date": event_date}
                        ret_array.append(activity)
            else:
                log.error("【EMBY】System/ActivityLog/Entries 未获取到返回数据")
                return []
        except Exception as e:
            log.error("【EMBY】连接System/ActivityLog/Entries出错：" + str(e))
            return []
        return ret_array

    # 获得媒体数量
    def get_emby_medias_count(self):
        if not self.__host or not self.__apikey:
            return {}
        req_url = "%semby/Items/Counts?api_key=%s" % (self.__host, self.__apikey)
        try:
            res = requests.get(req_url)
            if res:
                return res.json()
            else:
                log.error("【EMBY】Items/Counts 未获取到返回数据")
                return {}
        except Exception as e:
            log.error("【EMBY】连接Items/Counts出错：" + str(e))
            return {}

    # 根据名称查询Emby中剧集的SeriesId
    def get_emby_series_id_by_name(self, name, year):
        if not self.__host or not self.__apikey:
            return None
        req_url = "%semby/Items?IncludeItemTypes=Series&Fields=ProductionYear&StartIndex=0&Recursive=true&SearchTerm=%s&Limit=10&IncludeSearchTypes=false&api_key=%s" % (
            self.__host, name, self.__apikey)
        try:
            res = requests.get(req_url)
            if res:
                res_items = res.json().get("Items")
                if res_items:
                    for res_item in res_items:
                        if res_item.get('Name') == name and (not year or str(res_item.get('ProductionYear')) == str(year)):
                            return res_item.get('Id')
        except Exception as e:
            log.error("【EMBY】连接Items出错：" + str(e))
            return None
        return None

    # 根据标题和年份，检查电影是否在Emby中存在，存在则返回列表
    def get_emby_movies(self, title, year=None):
        if not self.__host or not self.__apikey:
            return []
        req_url = "%semby/Items?IncludeItemTypes=Movie&Fields=ProductionYear&StartIndex=0&Recursive=true&SearchTerm=%s&Limit=10&IncludeSearchTypes=false&api_key=%s" % (
            self.__host, title, self.__apikey)
        try:
            res = requests.get(req_url)
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
            log.error("【EMBY】连接Items出错：" + str(e))
            return []
        return []

    # 根据标题和年份和季，返回Emby中的剧集列表
    def get_emby_tv_episodes(self, title, year=None, season=None):
        if not self.__host or not self.__apikey:
            return []
        # 电视剧
        item_id = self.get_emby_series_id_by_name(title, year)
        if not item_id:
            return []
        # /Shows/{Id}/Episodes 查集的信息
        if not season:
            season = 1
        req_url = "%semby/Shows/%s/Episodes?Season=%s&api_key=%s" % (
            self.__host, item_id, season, self.__apikey)
        try:
            res_json = requests.get(req_url)
            if res_json:
                res_items = res_json.json().get("Items")
                exists_episodes = []
                for res_item in res_items:
                    exists_episodes.append(int(res_item.get("IndexNumber")))
                return exists_episodes
        except Exception as e:
            log.error("【EMBY】连接Shows/{Id}/Episodes出错：" + str(e))
            return []

    # 判断Emby是否已存在
    def check_emby_exists(self, item):
        if item.type == MediaType.MOVIE:
            exists_movies = self.get_emby_movies(item.title, item.year)
            if exists_movies:
                return True
        else:
            seasons = item.get_season_list()
            for season in seasons:
                exists_episodes = self.get_emby_tv_episodes(item.title, item.year, season)
                if exists_episodes:
                    if not item.get_episode_list():
                        # 这一季本地存在，继续检查下一季
                        continue
                    elif set(exists_episodes).issuperset(set(item.get_episode_list())):
                        # 这一季种子中的所有集本地存在，继续检查下一季
                        continue
                    # 这一季不符合以上两个条件，以不存在返回
                    return False
                else:
                    # 这一季不存在
                    return False
            # 所有季检查完成，没有返回的，即都存在
            return True
        return False

    # 根据标题、年份、季、总集数，查询Emby中缺少哪几集
    def get_emby_no_exists_episodes(self, title, year, season, total_num):
        exists_episodes = self.get_emby_tv_episodes(title, year, season)
        total_episodes = [episode for episode in range(1, total_num + 1)]
        return set(total_episodes).difference(set(exists_episodes))

    # 根据ItemId从Emby查询图片地址
    def get_emby_image_by_id(self, item_id, image_type):
        if not self.__host or not self.__apikey:
            return None
        req_url = "%semby/Items/%s/RemoteImages?api_key=%s" % (self.__host, item_id, self.__apikey)
        try:
            res = requests.get(req_url)
            if res:
                images = res.json().get("Images")
                for image in images:
                    if image.get("ProviderName") == "TheMovieDb" and image.get("Type") == image_type:
                        return image.get("Url")
            else:
                log.error("【EMBY】Items/RemoteImages 未获取到返回数据")
                return None
        except Exception as e:
            log.error("【EMBY】连接Items/{Id}/RemoteImages出错：" + str(e))
            return None
        return None

    # 通知Emby刷新一个项目的媒体库
    def refresh_emby_library_by_id(self, item_id):
        if not self.__host or not self.__apikey:
            return False
        req_url = "%semby/Items/%s/Refresh?Recursive=true&api_key=%s" % (self.__host, item_id, self.__apikey)
        try:
            res = requests.post(req_url)
            if res:
                return True
        except Exception as e:
            log.error("【EMBY】连接Items/{Id}/Refresh出错：" + str(e))
            return False
        return False

    # 按名称来刷新媒体库
    def refresh_emby_library_by_names(self, names):
        if not names:
            return
        # 收集要刷新的媒体库信息
        log.info("【EMBY】开始刷新Emby媒体库...")
        library_ids = []
        for torrent in names:
            media_info = self.media.get_media_info(torrent)
            if not media_info or not media_info.tmdb_info:
                continue
            library_id = self.get_emby_library_id_by_metainfo(media_info)
            if library_id and library_id not in library_ids:
                library_ids.append(library_id)
        # 开始刷新媒体库
        for library_id in library_ids:
            self.refresh_emby_library_by_id(library_id)
        log.info("【EMBY】Emby媒体库刷新完成！")

    # 根据媒体信息查询在哪个媒体库，返回要刷新的位置的ID
    def get_emby_library_id_by_metainfo(self, media):
        if media.type == MediaType.TV:
            item_id = self.get_emby_series_id_by_name(media.title, media.year)
            if item_id:
                # 存在电视剧，则直接刷新这个电视剧就行
                return item_id
        else:
            if self.get_emby_movies(media.title, media.year):
                # 已存在，不用刷新
                return None
        # TODO 查找需要刷新的媒体库ID，这里还需要优化
        for library in self.__library_info:
            for folder in library.get("SubFolders"):
                if "/%s" % media.category in folder.get("Path"):
                    return library.get("Id")
        return None


class EmbyEvent:
    message = None
    emby = None
    category = None
    filetransfer = None

    def __init__(self, input_json):
        if not input_json:
            return
        self.message = Message()
        self.emby = Emby()
        self.filetransfer = FileTransfer()
        # 解析事件报文
        event = input_json.get('Event')
        if not event:
            return
        # 类型
        self.category = event.split('.')[0]
        # 事件
        self.action = event.split('.')[1]
        # 时间
        self.timestamp = datetime.now()
        if self.category == "system":
            return
        # 事件信息
        Item = input_json.get('Item', {})
        self.provider_ids = Item.get('ProviderIds', {})
        self.item_type = Item.get('Type')
        if self.item_type == 'Episode':
            self.media_type = MediaType.TV
            self.item_name = "%s %s" % (Item.get('SeriesName'), Item.get('Name'))
            self.item_id = Item.get('SeriesId')
            self.tmdb_id = None
        else:
            self.media_type = MediaType.MOVIE
            self.item_name = Item.get('Name')
            self.item_path = Item.get('Path')
            self.item_id = Item.get('Id')
            self.tmdb_id = self.provider_ids.get('Tmdb')
        Session = input_json.get('Session', {})
        User = input_json.get('User', {})
        if self.category == 'playback':
            self.user_name = User.get('Name')
            self.ip = Session.get('RemoteEndPoint')
            self.device_name = Session.get('DeviceName')
            self.client = Session.get('Client')

    # 处理Emby播放消息
    def report_to_discord(self):
        global PLAY_LIST
        if not self.category:
            return
        # 消息标题
        message_title = None
        message_text = None
        # 系统事件
        if self.category == 'system':
            if self.action == 'webhooktest':
                log.info("【EMBY】system.webhooktest")
            return
        # 播放事件
        webhook_ignore = self.message.get_webhook_ignore()
        if self.category == 'playback':
            if webhook_ignore:
                if self.user_name in webhook_ignore or \
                        self.device_name in webhook_ignore or \
                        (self.user_name + ':' + self.device_name) in webhook_ignore:
                    log.info('【EMBY】忽略的用户或设备，不通知：%s %s' % (self.user_name, self.device_name))
                    return
            list_id = self.user_name + self.item_name + self.ip + self.device_name + self.client
            if self.action == 'start':
                message_title = '用户 %s 开始播放 %s' % (self.user_name, self.item_name)
                log.info(message_title)
                if list_id not in PLAY_LIST:
                    PLAY_LIST.append(list_id)
            elif self.action == 'stop':
                if list_id in PLAY_LIST:
                    message_title = '用户 %s 停止播放 %s' % (self.user_name, self.item_name)
                    log.info(message_title)
                    PLAY_LIST.remove(list_id)
                else:
                    log.debug('【EMBY】重复Stop通知，丢弃：' + list_id)
                    return
            else:
                return
            message_text = '设备：' + self.device_name \
                           + '\n客户端：' + self.client \
                           + '\nIP地址：' + self.ip \
                           + '\n位置：' + get_location(self.ip) \
                           + '\n时间：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        # 小红心事件
        if self.category == 'item':
            if self.action == 'rate':
                ret, org_type = self.filetransfer.transfer_embyfav(self.item_path)
                if ret:
                    message_title = '电影 %s 已从 %s 转移到 %s' % (self.item_name, org_type, RMT_FAVTYPE.value)
                else:
                    message_title = '电影 %s 转移失败！' % self.item_name
                message_text = '时间：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            else:
                return

        if message_title:
            image_url = None
            if self.item_id:
                image_url = self.emby.get_emby_image_by_id(self.item_id, "Backdrop")
            if not image_url:
                image_url = MetaInfo.get_backdrop_image(search_type=self.media_type, backdrop_path=None,
                                                        tmdbid=self.tmdb_id,
                                                        default="https://emby.media/notificationicon.png")
            self.message.sendmsg(message_title, message_text, image_url)


if __name__ == "__main__":
    info = MetaInfo("国王排名 2021 S02 E06")
    info.type = MediaType.TV
    info.title = "国王排名"
    print(Emby().check_emby_exists(info))
