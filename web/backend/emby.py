import os
import time
from datetime import datetime
from subprocess import call
import requests
import log
from config import get_config, RMT_FAVTYPE
from message.send import Message
from rmt.metainfo import MetaInfo
from utils.functions import get_local_time, get_location
from utils.types import MediaCatagory, MediaType

PLAY_LIST = []


class Emby:
    message = None
    __movie_path = None
    __tv_path = None
    __movie_subtypedir = True
    __apikey = None
    __host = None

    def __init__(self):
        self.message = Message()
        config = get_config()
        if config.get('media'):
            self.__movie_path = config['media'].get('movie_path')
            self.__movie_subtypedir = config['media'].get('movie_subtypedir', True)
            self.__tv_path = config['media'].get('tv_path')
        else:
            self.__movie_path = None
            self.__movie_subtypedir = True
        if config.get('emby'):
            self.__host = config['emby'].get('host')
            if not self.__host.startswith('http://') and not self.__host.startswith('https://'):
                self.__host = "http://" + self.__host
            if not self.__host.endswith('/'):
                self.__host = self.__host + "/"
            self.__apikey = config['emby'].get('api_key')

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
            for season in item.get_season_list():
                exists_episodes = self.get_emby_tv_episodes(item.title, item.year, season)
                if exists_episodes and not item.get_episode_list():
                    # 种子标题中没有集的信息，且本地又存在的，按存在处理
                    continue
                if not set(exists_episodes).issuperset(set(item.get_episode_list())):
                    # 本地存在的没有比标题中的集更多，按不存在处理
                    return False
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


class EmbyEvent:
    __webhook_ignore = None
    __movie_path = None
    __movie_subtypedir = True
    message = None
    emby = None
    category = None

    def __init__(self, input_json):
        if not input_json:
            return
        self.message = Message()
        self.emby = Emby()
        # 读取配置
        config = get_config()
        if config.get('media'):
            self.__movie_path = config['media'].get('movie_path')
            self.__movie_subtypedir = config['media'].get('movie_subtypedir', True)
        if config.get('message'):
            self.__webhook_ignore = config['message'].get('webhook_ignore')
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
        if self.category == 'playback':
            if self.__webhook_ignore:
                if self.user_name in self.__webhook_ignore or \
                        self.device_name in self.__webhook_ignore or \
                        (self.user_name + ':' + self.device_name) in self.__webhook_ignore:
                    log.info('【EMBY】忽略的用户或设备，不通知：%s %s' % (self.user_name, self.device_name))
                    return
            list_id = self.user_name + self.item_name + self.ip + self.device_name + self.client
            if self.action == 'start':
                message_title = '【EMBY】用户 %s 开始播放 %s' % (self.user_name, self.item_name)
                log.info(message_title)
                if list_id not in PLAY_LIST:
                    PLAY_LIST.append(list_id)
            elif self.action == 'stop':
                if list_id in PLAY_LIST:
                    message_title = '【EMBY】用户 %s 停止播放 %s' % (self.user_name, self.item_name)
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
                if not self.__movie_subtypedir or not self.__movie_path:
                    return
                if os.path.isdir(self.item_path):
                    movie_dir = self.item_path
                else:
                    movie_dir = os.path.dirname(self.item_path)
                if movie_dir.count(self.__movie_path) == 0:
                    return
                name = movie_dir.split('/')[-1]
                org_type = movie_dir.split('/')[-2]
                if org_type not in [MediaCatagory.HYDY.value, MediaCatagory.WYDY.value]:
                    return
                if org_type == MediaCatagory.JXDY.value:
                    return
                new_path = os.path.join(self.__movie_path, MediaCatagory.JXDY.value, name)
                log.info("【EMBY】开始转移文件 %s 到 %s ..." % (movie_dir, new_path))
                if os.path.exists(new_path):
                    log.info("【EMBY】目录 %s 已存在！" % new_path)
                    return
                ret = call(['mv', movie_dir, new_path])
                if ret == 0:
                    message_title = '【EMBY】电影 %s 已从 %s 转移到 %s' % (self.item_name, org_type, RMT_FAVTYPE.value)
                else:
                    message_title = '【EMBY】电影 %s 转移失败！' % self.item_name
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
