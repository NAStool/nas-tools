import time

from app.message import Message
from app.mediaserver import MediaServer
from app.media import Media
from web.backend.web_utils import WebUtils


class WebhookEvent:
    message = None
    mediaserver = None
    media = None

    def __init__(self):
        self.message = Message()
        self.mediaserver = MediaServer()
        self.media = Media()

    @staticmethod
    def __parse_plex_msg(message):
        """
        解析Plex报文
        """
        eventItem = {'event': message.get('event', {}),
                     'item_name': message.get('Metadata', {}).get('title'),
                     'user_name': message.get('Account', {}).get('title')
                     }
        return eventItem

    @staticmethod
    def __parse_jellyfin_msg(message):
        """
        解析Jellyfin报文
        """
        eventItem = {'event': message.get('NotificationType', {}),
                     'item_name': message.get('Name'),
                     'user_name': message.get('NotificationUsername')
                     }
        return eventItem

    @staticmethod
    def __parse_emby_msg(message):
        """
        解析Emby报文
        """
        eventItem = {'event': message.get('Event', {})}
        if message.get('Item'):
            if message.get('Item', {}).get('Type') == 'Episode':
                eventItem['item_type'] = "TV"
                eventItem['item_name'] = "%s %s%s" % (
                    message.get('Item', {}).get('SeriesName'),
                    "S" + str(message.get('Item', {}).get('ParentIndexNumber')),
                    "E" + str(message.get('Item', {}).get('IndexNumber')))
                eventItem['item_id'] = message.get('Item', {}).get('SeriesId')
                eventItem['season_id'] = message.get('Item', {}).get('ParentIndexNumber')
                eventItem['episode_id'] = message.get('Item', {}).get('IndexNumber')
                eventItem['tmdb_id'] = message.get('Item', {}).get('ProviderIds', {}).get('Tmdb')
                if message.get('Item', {}).get('Overview') and len(message.get('Item', {}).get('Overview')) > 100:
                    eventItem['overview'] = str(message.get('Item', {}).get('Overview'))[:100] + "..."
                else:
                    eventItem['overview'] = message.get('Item', {}).get('Overview')
                eventItem['percentage'] = message.get('Item', {}).get('CompletionPercentage')
            else:
                eventItem['item_type'] = "MOV"
                eventItem['item_name'] = "%s %s" % (
                    message.get('Item', {}).get('Name'), "(" + str(message.get('Item', {}).get('ProductionYear')) + ")")
                eventItem['item_path'] = message.get('Item', {}).get('Path')
                eventItem['item_id'] = message.get('Item', {}).get('Id')
                eventItem['tmdb_id'] = message.get('Item', {}).get('ProviderIds', {}).get('Tmdb')
                if len(message.get('Item', {}).get('Overview')) > 100:
                    eventItem['overview'] = str(message.get('Item', {}).get('Overview'))[:100] + "..."
                else:
                    eventItem['overview'] = message.get('Item', {}).get('Overview')
                eventItem['percentage'] = message.get('Item', {}).get('CompletionPercentage')
        if message.get('Session'):
            eventItem['ip'] = message.get('Session').get('RemoteEndPoint')
            eventItem['device_name'] = message.get('Session').get('DeviceName')
            eventItem['client'] = message.get('Session').get('Client')
        if message.get("User"):
            eventItem['user_name'] = message.get("User").get('Name')

        return eventItem

    def plex_action(self, message):
        """
        执行Plex webhook动作
        """
        event_info = self.__parse_plex_msg(message)
        if event_info.get("event") in ["media.play", "media.stop"]:
            self.send_webhook_message(event_info, 'plex')

    def jellyfin_action(self, message):
        """
        执行Jellyfin webhook动作
        """
        event_info = self.__parse_jellyfin_msg(message)
        if event_info.get("event") in ["PlaybackStart", "PlaybackStop"]:
            self.send_webhook_message(event_info, 'jellyfin')

    def emby_action(self, message):
        """
        执行Emby webhook动作
        """
        event_info = self.__parse_emby_msg(message)
        if event_info.get("event") == "system.webhooktest":
            return
        elif event_info.get("event") in ["playback.start",
                                         "playback.stop",
                                         "user.authenticated",
                                         "user.authenticationfailed"]:
            self.send_webhook_message(event_info, 'emby')

    def send_webhook_message(self, event_info, channel):
        """
        发送消息
        """
        _webhook_actions = {
            "system.webhooktest": "测试",
            "playback.start": "开始播放",
            "playback.stop": "停止播放",
            "playback.pause": "暂停播放",
            "playback.unpause": "开始播放",
            "user.authenticated": "登录成功",
            "user.authenticationfailed": "登录失败",
            "media.play": "开始播放",
            "PlaybackStart": "开始播放",
            "PlaybackStop": "停止播放",
            "media.stop": "停止播放",
            "item.rate": "标记了",
        }
        _webhook_images = {
            "emby": "https://emby.media/notificationicon.png",
            "plex": "https://www.plex.tv/wp-content/uploads/2022/04/new-logo-process-lines-gray.png",
            "jellyfin": "https://play-lh.googleusercontent.com/SCsUK3hCCRqkJbmLDctNYCfehLxsS4ggD1ZPHIFrrAN1Tn9yhjmGMPep2D9lMaaa9eQi"
        }

        if self.is_ignore_webhook_message(event_info.get('user_name'), event_info.get('device_name')):
            return

        # 消息标题
        if event_info.get('item_type') == "TV":
            message_title = f"{_webhook_actions.get(event_info.get('event'))}剧集 {event_info.get('item_name')}"
        elif event_info.get('item_type') == "MOV":
            message_title = f"{_webhook_actions.get(event_info.get('event'))}电影 {event_info.get('item_name')}"
        else:
            message_title = f"{_webhook_actions.get(event_info.get('event'))}"

        # 消息内容
        if {event_info.get('user_name')}:
            message_texts = [f"用户：{event_info.get('user_name')}"]
        if event_info.get('device_name'):
            message_texts.append(f"设备：{event_info.get('client')} {event_info.get('device_name')}")
        if event_info.get('ip'):
            message_texts.append(f"位置：{event_info.get('ip')} {WebUtils.get_location(event_info.get('ip'))}")
        if event_info.get('percentage'):
            message_texts.append(f"进度：{event_info.get('percentage')}")
        if event_info.get('overview'):
            message_texts.append(f"剧情：{event_info.get('overview')}")
        message_texts.append(f"时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}")

        # 消息图片
        image_url = ''
        if event_info.get('item_id'):
            if event_info.get("item_type") == "TV":
                iteminfo = self.mediaserver.get_iteminfo(event_info.get('item_id'))
                tmdb_id = iteminfo.get('ProviderIds', {}).get('Tmdb')
                try:
                    # 从tmdb获取剧集某季某集图片
                    image_url = self.media.get_episode_images(tmdb_id, event_info.get('season_id'),
                                                              event_info.get('episode_id'))
                except IOError:
                    pass

            if not image_url:
                image_url = self.mediaserver.get_image_by_id(event_info.get('item_id'),
                                                             "Backdrop") or _webhook_images.get(channel)
        else:
            image_url = _webhook_images.get(channel)
        # 发送消息
        self.message.send_mediaserver_message(title=message_title, text="\n".join(message_texts), image=image_url)

    def is_ignore_webhook_message(self, user_name, device_name):
        """
        判断是否忽略通知
        """
        if not user_name and not device_name:
            return False
        webhook_ignore = self.message.get_webhook_ignore()
        if not webhook_ignore:
            return False
        if user_name in webhook_ignore or \
                device_name in webhook_ignore or \
                (user_name + ':' + device_name) in webhook_ignore:
            return True
        return False
