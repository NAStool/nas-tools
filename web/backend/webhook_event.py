import time
from datetime import datetime
import requests

import log
from config import RMT_FAVTYPE
from message.send import Message
from rmt.filetransfer import FileTransfer
from rmt.media_server import MediaServer
from utils.types import MediaType

PLAY_LIST = []


class WebhookEvent:
    message = None
    mediaserver = None
    category = None
    filetransfer = None

    def __init__(self, input_json):
        if not input_json:
            return
        self.message = Message()
        self.mediaserver = MediaServer()
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

    @staticmethod
    def get_location(ip):
        url = 'https://sp0.baidu.com/8aQDcjqpAAV3otqbppnN2DJv/api.php?co=&resource_id=6006&t=1529895387942&ie=utf8' \
              '&oe=gbk&cb=op_aladdin_callback&format=json&tn=baidu&' \
              'cb=jQuery110203920624944751099_1529894588086&_=1529894588088&query=%s' % ip
        try:
            r = requests.get(url, timeout=10)
            r.encoding = 'gbk'
            html = r.text
            c1 = html.split('location":"')[1]
            c2 = c1.split('","')[0]
            return c2
        except requests.exceptions:
            return ''

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
                           + '\n位置：' + self.get_location(self.ip) \
                           + '\n时间：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        # 小红心事件
        if self.category == 'item':
            if self.action == 'rate':
                if self.media_type != MediaType.MOVIE:
                    return
                ret, org_type = self.filetransfer.transfer_embyfav(self.item_path)
                if ret:
                    # 刷新媒体库
                    self.mediaserver.refresh_root_library()
                    message_title = '电影 %s 已从 %s 转移到 %s' % (self.item_name, org_type, RMT_FAVTYPE)
                    message_text = '时间：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            else:
                return

        if message_title:
            image_url = None
            if self.item_id:
                image_url = self.mediaserver.get_image_by_id(self.item_id, "Backdrop")
            if not image_url:
                image_url = "https://emby.media/notificationicon.png"
            self.message.sendmsg(title=message_title, text=message_text, image=image_url)
