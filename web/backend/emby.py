import os
import time
from datetime import datetime
from subprocess import call

import requests

import log
from config import get_config, RMT_FAVTYPE
from message.send import Message
from rmt.metainfo import MetaInfo
from utils.functions import get_location, get_local_time
from utils.types import MediaCatagory, MediaType

PLAY_LIST = []


class Emby:
    message = None
    __movie_path = None
    __tv_path = None
    __movie_subtypedir = True
    __webhook_ignore = []
    __apikey = None
    __host = None

    class EmbyEvent:
        def __init__(self, input_json):
            event = input_json['Event']
            self.category = event.split('.')[0]
            self.action = event.split('.')[1]
            self.timestamp = datetime.now()
            User = input_json.get('User', {})
            Item = input_json.get('Item', {})
            Session = input_json.get('Session', {})
            Server = input_json.get('Server', {})
            Status = input_json.get('Status', {})

            if self.category == 'playback':
                self.user_name = User.get('Name')
                self.item_type = Item.get('Type')
                self.provider_ids = Item.get('ProviderIds')
                if self.item_type == 'Episode':
                    self.media_type = MediaType.TV
                    self.item_name = "%s %s" % (Item.get('SeriesName'), Item.get('Name'))
                    self.tmdb_id = Item.get('SeriesId')
                else:
                    self.item_name = Item.get('Name')
                    self.tmdb_id = self.provider_ids.get('Tmdb')
                    self.media_type = MediaType.MOVIE
                self.ip = Session.get('RemoteEndPoint')
                self.device_name = Session.get('DeviceName')
                self.client = Session.get('Client')

            if self.category == 'user':
                if self.action == 'login':
                    self.user_name = User.get('user_name')
                    self.user_name = User.get('user_name')
                    self.device_name = User.get('device_name')
                    self.ip = User.get('device_ip')
                    self.server_name = Server.get('server_name')
                    self.status = Status

            if self.category == 'item':
                if self.action == 'rate':
                    self.movie_name = Item.get('Name')
                    self.movie_path = Item.get('Path')
                    self.item_type = Item.get('Type')
                    self.provider_ids = Item.get('ProviderIds')
                    if self.item_type == 'Episode':
                        self.media_type = MediaType.TV
                        self.tmdb_id = Item.get('SeriesId')
                    else:
                        self.tmdb_id = self.provider_ids.get('Tmdb')
                        self.media_type = MediaType.MOVIE

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
        if config.get('message'):
            self.__webhook_ignore = config['message'].get('webhook_ignore')
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
            log.error("【EMBY】连接Emby出错：" + str(e))
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
                        event_date = get_local_time(item.get("Date").replace('0000', ''))
                        event_str = "%s, %s" % (item.get("Name"), item.get("ShortOverview"))
                        activity = {"type": event_type, "event": event_str, "date": event_date}
                        ret_array.append(activity)
                    if item.get("Type") == "VideoPlayback":
                        event_type = "PL"
                        event_date = get_local_time(item.get("Date").replace('0000', ''))
                        event_str = item.get("Name")
                        activity = {"type": event_type, "event": event_str, "date": event_date}
                        ret_array.append(activity)
            else:
                log.error("【EMBY】System/ActivityLog/Entries 未获取到返回数据")
                return []
        except Exception as e:
            log.error("【EMBY】连接Emby出错：" + str(e))
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
            log.error("【EMBY】连接Emby出错：" + str(e))
            return {}

    # 判断Emby是否已存在
    def check_emby_exists(self, item):
        if not self.__host or not self.__apikey:
            return False
        # TODO 调用EMBY API 检查是否已存在

        return False

    # 处理Emby播放消息
    def report_to_discord(self, event):
        global PLAY_LIST
        message_title = None
        tmdb_id = None
        media_type = None
        # System
        if event.category == 'system':
            if event.action == 'webhooktest':
                log.info("【EMBY】system.webhooktest")
                return ""
        if event.category == 'playback':
            media_type = event.media_type
            if self.__webhook_ignore:
                if event.user_name in self.__webhook_ignore or \
                        event.device_name in self.__webhook_ignore or \
                        (event.user_name + ':' + event.device_name) in self.__webhook_ignore:
                    log.info('【EMBY】忽略的用户或设备，不通知：%s %s' % (event.user_name, event.device_name))
            list_id = event.user_name + event.item_name + event.ip + event.device_name + event.client
            if event.action == 'start':
                message_title = '【EMBY】用户 %s 开始播放 %s' % (event.user_name, event.item_name)
                tmdb_id = event.tmdb_id
                if list_id not in PLAY_LIST:
                    PLAY_LIST.append(list_id)
            elif event.action == 'stop':
                if list_id in PLAY_LIST:
                    message_title = '【EMBY】用户 %s 停止播放 %s' % (event.user_name, event.item_name)
                    tmdb_id = event.tmdb_id
                    PLAY_LIST.remove(list_id)
                else:
                    log.debug('【EMBY】重复Stop通知，丢弃：' + list_id)
        elif event.category == 'user':
            if event.action == 'login':
                if event.status.upper() == 'F':
                    message_title = '【EMBY】用户 %s 登录 %s 失败！' % (event.user_name, event.server_name)
                else:
                    message_title = '【EMBY】用户 %s 登录了 %s' % (event.user_name, event.server_name)
        elif event.category == 'item':
            if event.action == 'rate':
                media_type = event.media_type
                tmdb_id = event.tmdb_id
                if not self.__movie_subtypedir or not self.__movie_path:
                    return
                if os.path.isdir(event.movie_path):
                    movie_dir = event.movie_path
                else:
                    movie_dir = os.path.dirname(event.movie_path)
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
                    message_title = '【EMBY】电影 %s 已从 %s 转移到 %s' % (event.movie_name, org_type, RMT_FAVTYPE.value)
                else:
                    message_title = '【EMBY】电影 %s 转移失败！' % event.movie_name

        if message_title:
            desp = ""
            if event.category == 'playback':
                address = get_location(event.ip)
                desp = '设备：' + event.device_name \
                       + '\n客户端：' + event.client \
                       + '\nIP地址：' + event.ip \
                       + '\n位置：' + address \
                       + '\n时间：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            elif event.category == 'user':
                if event.action == 'login':
                    address = get_location(event.ip)
                    desp = '设备：' + event.device_name \
                           + '\nIP地址：' + event.ip \
                           + '\n位置：' + address \
                           + '\n时间：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            elif event.category == 'item':
                if event.action == 'rate':
                    desp = '时间：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            # Report Message
            if tmdb_id:
                image_url = MetaInfo.get_backdrop_image(media_type, None, tmdb_id,
                                                        "https://emby.media/notificationicon.png")
            else:
                image_url = ""
            self.message.sendmsg(message_title, desp, image_url)


if __name__ == "__main__":
    print(Emby().get_emby_medias_count())
