import sys

import log
from config import get_config
from message.serverchan import ServerChan
from message.telegram import Telegram
from message.wechat import WeChat


class Message:
    __msg_channel = None

    def __init__(self):
        config = get_config()
        if config.get('message'):
            self.__msg_channel = config['message'].get('msg_channel')
            self.wechat = WeChat.get_instance()
            self.telegram = Telegram()
            self.serverchan = ServerChan()

    def sendmsg(self, title, text="", image=""):
        log.info("【MSG】发送%s消息：title=%s, text=%s" % (self.__msg_channel, title, text))
        if self.__msg_channel == "wechat":
            return self.wechat.send_wechat_msg(title, text, image)
        elif self.__msg_channel == "serverchan":
            return self.serverchan.send_serverchan_msg(title, text)
        elif self.__msg_channel == "telegram":
            return self.telegram.send_telegram_msg(title, text, image)
        else:
            return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        in_title = sys.argv[1]
    else:
        in_title = "标题"
    if len(sys.argv) > 2:
        in_text = sys.argv[2]
    else:
        in_text = "内容"
    Message().sendmsg(in_title, in_text)
