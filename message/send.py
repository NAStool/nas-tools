import log
from config import get_config
from message.bark import Bark
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
