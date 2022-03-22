from enum import Enum

import log
from config import get_config
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
        config = get_config()
        if config.get('message'):
            self.__msg_channel = config['message'].get('msg_channel')
            self.__webhook_ignore = config['message'].get('webhook_ignore')
            self.wechat = WeChat.get_instance()
            self.telegram = Telegram()
            self.serverchan = ServerChan()
            self.bark = Bark()

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
        tt = can_item.title
        va = can_item.vote_average
        yr = can_item.year
        bp = can_item.backdrop_path if can_item.backdrop_path else can_item.poster_path
        tp = can_item.type
        se_str = can_item.get_season_episode_string()
        if isinstance(in_from, Enum):
            in_from = in_from.value
        if isinstance(tp, Enum):
            tp = tp.value

        if yr:
            msg_title = "%s (%s) 开始下载" % (tt, str(yr))
        else:
            msg_title = "%s 开始下载" % tt
        if se_str:
            msg_text = "来自 %s 的%s %s %s 已开始下载" % (in_from, tp, msg_title, se_str)
        else:
            msg_text = "来自 %s 的%s %s 已开始下载" % (in_from, tp, msg_title)
        if va and va != '0':
            msg_title = "%s 评分：%s" % (msg_title, str(va))
        self.sendmsg(msg_title, msg_text, bp)

    # 发送转移电影的消息
    def send_transfer_movie_message(self, in_from, media_info, media_filesize, exist_filenum):
        title_str = media_info.get_title_string()
        vote_average = media_info.vote_average
        media_pix = media_info.resource_pix
        backdrop_path = media_info.backdrop_path if media_info.backdrop_path else media_info.poster_path
        if vote_average:
            msg_title = "%s 转移完成 评分：%s" % (title_str, str(vote_average))
        else:
            msg_title = "%s 转移完成" % title_str
        if media_pix:
            msg_str = "电影 %s 转移完成，质量：%s，大小：%s，来自：%s" \
                      % (title_str, media_pix, str_filesize(media_filesize), in_from)
        else:
            msg_str = "电影 %s 转移完成, 大小：%s, 来自：%s" \
                      % (title_str, str_filesize(media_filesize), in_from)
        if exist_filenum != 0:
            msg_str = "%s，%s 个文件已存在" % (msg_str, str(exist_filenum))
        self.sendmsg(msg_title, msg_str, backdrop_path)

    # 发送转移电视剧的消息
    def send_transfer_tv_message(self, title_str, item_info, in_from):
        if item_info.get('Vote_Average'):
            msg_title = "%s 转移完成" % title_str
        else:
            msg_title = "%s 转移完成 评分：%s" % (title_str, item_info.get('Vote_Average'))
        if len(item_info.get('Episode_Ary')) == 1:
            # 只有一集
            msg_str = "电视剧 %s 第 %s 季第 %s 集 转移完成，大小：%s，来自：%s" \
                      % (msg_title,
                         item_info.get('Season_Ary')[0],
                         item_info.get('Episode_Ary')[0],
                         str_filesize(item_info.get('Total_Size')),
                         in_from)
        else:
            if item_info.get('Season_Ary'):
                se_string = " S".join("%s".rjust(2, '0') % season for season in item_info.get('Season_Ary'))
            else:
                se_string = ""
            msg_str = "电视剧 %s%s 转移完成，共 %s 季 %s 集，总大小：%s，来自：%s" % \
                      (msg_title,
                       se_string,
                       len(item_info.get('Season_Ary')),
                       len(item_info.get('Episode_Ary')),
                       str_filesize(item_info.get('Total_Size')),
                       in_from)
        if item_info.get('Exist_Files') != 0:
            msg_str = "%s，%s 个文件已存在" % (msg_str, str(item_info.get('Exist_Files')))
        msg_image = item_info.get('Backdrop_Path') if item_info.get('Backdrop_Path') else item_info.get('Poster_Path')
        self.sendmsg(msg_title, msg_str, msg_image)
