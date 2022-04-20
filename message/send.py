import re

import log
from config import Config
from message.bark import Bark
from message.serverchan import ServerChan
from message.telegram import Telegram
from message.wechat import WeChat
from utils.functions import str_filesize
from utils.types import SearchType


class Message:
    __msg_channel = None
    __webhook_ignore = None
    __domain = None
    wechat = None
    telegram = None
    serverchan = None
    bark = None

    def __init__(self):
        self.wechat = WeChat()
        self.telegram = Telegram()
        self.serverchan = ServerChan()
        self.bark = Bark()
        self.init_config()

    def init_config(self):
        config = Config()
        message = config.get_config('message')
        if message:
            self.__msg_channel = message.get('msg_channel')
            self.__webhook_ignore = message.get('webhook_ignore')
        app = config.get_config('app')
        if app:
            self.__domain = app.get('domain')
            if self.__domain:
                if not self.__domain.startswith('http://') and not self.__domain.startswith('https://'):
                    self.__domain = "http://" + self.__domain

    def get_webhook_ignore(self):
        return self.__webhook_ignore or []

    # 通用消息发送
    def sendmsg(self, title, text="", image="", url="", user_id=""):
        log.info("【MSG】发送%s消息：title=%s, text=%s" % (self.__msg_channel, title, text))
        if self.__domain:
            if url:
                url = "%s?next=%s" % (self.__domain, url)
            else:
                url = self.__domain
        else:
            url = ""
        if self.__msg_channel == "wechat":
            return self.wechat.send_wechat_msg(title, text, image, url, user_id)
        elif self.__msg_channel == "serverchan":
            return self.serverchan.send_serverchan_msg(title, text)
        elif self.__msg_channel == "telegram":
            return self.telegram.send_telegram_msg(title, text, image, url, user_id)
        elif self.__msg_channel == "bark":
            return self.bark.send_bark_msg(title, text)
        else:
            return None

    # 按渠道发送消息
    def send_channel_msg(self, channel, title, text="", image="", url="", user_id=""):
        if self.__domain:
            if url:
                url = "%s?next=%s" % (self.__domain, url)
            else:
                url = self.__domain
        else:
            url = ""
        if channel == SearchType.TG:
            return self.telegram.send_telegram_msg(title, text, image, url, user_id)
        elif channel == SearchType.WX:
            return self.wechat.send_wechat_msg(title, text, image, url, user_id)

    # 发送下载的消息
    def send_download_message(self, in_from, can_item):
        msg_title = can_item.get_title_vote_string()
        msg_text = f"{in_from.value}的{can_item.type.value} {can_item.get_title_string()}{can_item.get_season_episode_string()} 已开始下载"
        if can_item.site:
            msg_text = f"{msg_text}\n站点：{can_item.site}"
        if can_item.get_resource_type_string():
            msg_text = f"{msg_text}\n质量：{can_item.get_resource_type_string()}"
        if can_item.size:
            if str(can_item.size).isdigit():
                size = str_filesize(can_item.size)
            else:
                size = can_item.size
            msg_text = f"{msg_text}\n大小：{size}"
        if can_item.org_string:
            msg_text = f"{msg_text}\n种子：{can_item.org_string}"
        if can_item.description:
            html_re = re.compile(r'<[^>]+>', re.S)
            description = html_re.sub('', can_item.description)
            can_item.description = re.sub(r'<[^>]+>', '', description)
            msg_text = f"{msg_text}\n描述：{can_item.description}"
        self.sendmsg(title=msg_title, text=msg_text, image=can_item.get_message_image(), url='download')

    # 发送转移电影的消息
    def send_transfer_movie_message(self, in_from, media_info, exist_filenum, category_flag):
        msg_title = f"{media_info.get_title_string()} 转移完成"
        if media_info.vote_average:
            msg_str = f"{media_info.get_vote_string()}，类型：电影"
        else:
            msg_str = "类型：电影"
        if media_info.category:
            if category_flag:
                msg_str = f"{msg_str}，类别：{media_info.category}"
        if media_info.get_resource_type_string():
            msg_str = f"{msg_str}，质量：{media_info.get_resource_type_string()}"
        msg_str = f"{msg_str}，大小：{str_filesize(media_info.size)}，来自：{in_from.value}"
        if exist_filenum != 0:
            msg_str = f"{msg_str}，{exist_filenum}个文件已存在"
        self.sendmsg(title=msg_title, text=msg_str, image=media_info.get_message_image(), url='history')

    # 发送转移电视剧/动漫的消息
    def send_transfer_tv_message(self, message_medias, in_from):
        # 统计完成情况，发送通知
        for item_info in message_medias.values():
            if item_info.total_episodes == 1:
                msg_title = f"{item_info.get_title_string()} {item_info.get_season_episode_string()} 转移完成"
            else:
                msg_title = f"{item_info.get_title_string()} {item_info.get_season_string()} 转移完成"
            if item_info.vote_average:
                msg_str = f"{item_info.get_vote_string()}，类型：{item_info.type.value}"
            else:
                msg_str = f"类型：{item_info.type.value}"
            if item_info.category:
                msg_str = f"{msg_str}，类别：{item_info.category}"
            if item_info.total_episodes == 1:
                msg_str = f"{msg_str}，大小：{str_filesize(item_info.size)}，来自：{in_from.value}"
            else:
                msg_str = f"{msg_str}，共{item_info.total_episodes}集，总大小：{str_filesize(item_info.size)}，来自：{in_from.value}"
            self.sendmsg(title=msg_title, text=msg_str, image=item_info.get_message_image(), url='history')
