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

    def __init__(self):
        config = get_config()
        if config.get('message'):
            self.__msg_channel = config['message'].get('msg_channel')
            self.wechat = WeChat.get_instance()
            self.telegram = Telegram()
            self.serverchan = ServerChan()
            self.bark = Bark()

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
    def send_download_message(self, in_from, can_item, se_str):
        tt = can_item.get('title')
        va = can_item.get('vote_average')
        yr = can_item.get('year')
        bp = can_item.get('backdrop_path')
        tp = can_item.get('type')
        if isinstance(tp, Enum):
            tp = tp.value
        msg_title = tt
        if yr:
            msg_title = "%s (%s)" % (tt, str(yr))
        if se_str:
            msg_text = "来自%s的%s %s %s 已开始下载" % (in_from, tp, msg_title, se_str)
        else:
            msg_text = "来自%s的%s %s 已开始下载" % (in_from, tp, msg_title)
        if va and va != '0':
            msg_title = msg_title + " 评分：%s" % str(va)
        self.sendmsg(msg_title, msg_text, bp)

    # 发送转移电影的消息
    def send_transfer_movie_message(self, in_from, media_info, media_filesize, exist_filenum):
        title_str = media_info.get_title_string()
        vote_average = media_info.vote_average
        media_pix = media_info.resource_pix
        backdrop_path = media_info.backdrop_path
        msg_title = title_str
        if vote_average:
            msg_title = title_str + " 评分：%s" % str(vote_average)
        if media_pix:
            msg_str = "电影 %s 转移完成，质量：%s，大小：%s，来自：%s" \
                      % (title_str, media_pix, str_filesize(media_filesize), in_from)
        else:
            msg_str = "电影 %s 转移完成, 大小：%s, 来自：%s" \
                      % (title_str, str_filesize(media_filesize), in_from)
        if exist_filenum != 0:
            msg_str = msg_str + "，%s 个文件已存在" % str(exist_filenum)
        self.sendmsg(msg_title, msg_str, backdrop_path)

    # 发送转移电视剧的消息
    def send_transfer_tv_message(self, title_str, item_info, in_from):
        if len(item_info['Episode_Ary']) == 1:
            # 只有一集
            msg_str = "电视剧 %s 第 %s 季第 %s 集 转移完成，大小：%s，来自：%s" \
                      % (title_str,
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
                      (title_str,
                       se_string,
                       len(item_info.get('Season_Ary')),
                       len(item_info.get('Episode_Ary')),
                       str_filesize(item_info.get('Total_Size')),
                       in_from)
        if item_info.get('Exist_Files') != 0:
            msg_str = msg_str + "，%s 个文件已存在" % str(item_info.get('Exist_Files'))

        msg_title = title_str
        if item_info.get('Vote_Average'):
            msg_title = title_str + " 评分：%s" % str(item_info.get('Vote_Average'))
        self.sendmsg(msg_title, msg_str, item_info.get('Backdrop_Path'))
