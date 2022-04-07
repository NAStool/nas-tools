import log
from config import Config
from message.bark import Bark
from message.serverchan import ServerChan
from message.telegram import Telegram
from message.wechat import WeChat
from utils.functions import str_filesize


class Message:
    __msg_channel = None
    __webhook_ignore = None
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

    def get_webhook_ignore(self):
        return self.__webhook_ignore or []

    def sendmsg(self, title, text="", image=""):
        log.info("【MSG】发送%s消息：title=%s, text=%s" % (self.__msg_channel, title, text))
        if self.__msg_channel == "wechat":
            return self.wechat.send_wechat_msg(title, text, image)
        elif self.__msg_channel == "serverchan":
            return self.serverchan.send_serverchan_msg(title, text)
        elif self.__msg_channel == "telegram":
            return self.telegram.send_telegram_msg(title, text, image)
        elif self.__msg_channel == "bark":
            return self.bark.send_bark_msg(title, text)
        else:
            return None

    # 发送下载的消息
    def send_download_message(self, in_from, can_item):
        va = can_item.vote_average
        bp = can_item.get_backdrop_path()
        tp = can_item.type
        se_str = can_item.get_season_episode_string()
        msg_title = can_item.get_title_string()
        msg_text = f"来自{in_from.value}的{tp.value} {msg_title}{se_str} 已开始下载"
        if va:
            msg_title = f"{msg_title} 评分：{va}"

        self.sendmsg(msg_title, msg_text, bp)

    # 发送转移电影的消息
    def send_transfer_movie_message(self, in_from, media_info, media_filesize, exist_filenum, category_flag):
        msg_title = f"{media_info.get_title_string()} 转移完成"
        if media_info.vote_average:
            msg_str = f"评分：{media_info.vote_average}，类型：电影"
        else:
            msg_str = "类型：电影"
        if media_info.category:
            if category_flag:
                msg_str = f"{msg_str}，类别：{media_info.category}"
        if media_info.get_resource_type_string():
            msg_str = f"{msg_str}，质量：{media_info.get_resource_type_string()}"
        msg_str = f"{msg_str}，大小：{str_filesize(media_filesize)}，来自：{in_from.value}"
        if exist_filenum != 0:
            msg_str = f"{msg_str}，{exist_filenum}个文件已存在"
        self.sendmsg(msg_title, msg_str, media_info.get_backdrop_path())

    # 发送转移电视剧/动漫的消息
    def send_transfer_tv_message(self, message_medias, in_from):
        # 统计完成情况，发送通知
        for title_str, item_info in message_medias.items():
            if len(item_info.get('episodes')) == 1:
                msg_title = f"{title_str} 第{item_info.get('seasons')[0]}季第{item_info.get('episodes')[0]}集 转移完成"
            else:
                if item_info.get('seasons'):
                    se_string = " ".join("S%s" % str(season).rjust(2, '0') for season in item_info.get('seasons'))
                    msg_title = f"{title_str} {se_string} 转移完成"
                else:
                    msg_title = f"{title_str} 转移完成"

            if item_info.get('media').vote_average:
                msg_str = f"评分：{item_info.get('media').vote_average}，类型：{item_info.get('type')}"
            else:
                msg_str = f"类型：{item_info.get('type')}"

            if item_info.get('media').category and item_info.get('categoryflag'):
                msg_str = f"{msg_str}，类别：{item_info.get('media').category}"

            if len(item_info.get('episodes')) != 1:
                msg_str = f"{msg_str}，共{len(item_info.get('seasons'))}季{len(item_info.get('episodes'))}集，总大小：{str_filesize(item_info.get('totalsize'))}，来自：{in_from.value}"
            else:
                msg_str = f"{msg_str}，大小：{str_filesize(item_info.get('totalsize'))}，来自：{in_from.value}"

            self.sendmsg(msg_title, msg_str, item_info.get('media').backdrop_path if item_info.get('media').backdrop_path else item_info.get('media').poster_path)
