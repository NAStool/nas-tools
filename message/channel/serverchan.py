from urllib.parse import urlencode
import requests

from config import Config
from message.channel.channel import IMessageChannel


class ServerChan(IMessageChannel):
    __sckey = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        message = config.get_config('message')
        if message:
            self.__sckey = message.get('serverchan', {}).get('sckey')

    def get_status(self):
        """
        测试连通性
        """
        flag, msg = self.send_msg("测试", "这是一条测试消息")
        return flag

    def send_msg(self, title, text="", image="", url="", user_id=""):
        """
        发送ServerChan消息
        :param title: 消息标题
        :param text: 消息内容
        :param image: 未使用
        :param url: 未使用
        :param user_id: 未使用
        """
        if not title and not text:
            return False, "标题和内容不能同时为空"
        values = {"title": title, "desp": text}
        try:
            if not self.__sckey:
                return False, "参数未配置"
            sc_url = "https://sctapi.ftqq.com/%s.send?%s" % (self.__sckey, urlencode(values))
            res = requests.get(sc_url, timeout=10)
            if res:
                ret_json = res.json()
                errno = ret_json['code']
                error = ret_json['message']
                if errno == 0:
                    return True, error
                else:
                    return False, error
            else:
                return False, "未获取到返回信息"
        except Exception as msg_e:
            return False, str(msg_e)
