import time
from urllib.parse import urlencode

import log
from config import Config
from app.message.channel.channel import IMessageChannel
from app.utils import RequestUtils


class PushPlus(IMessageChannel):
    _token = None
    _topic = None
    _channel = None
    _webhook = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        message = config.get_config('message')
        if message:
            self._token = message.get('pushplus', {}).get('push_token')
            self._topic = message.get('pushplus', {}).get('push_topic')
            self._channel = message.get('pushplus', {}).get('push_channel')
            self._webhook = message.get('pushplus', {}).get('push_webhook')

    def get_status(self):
        """
        测试连通性
        """
        flag, msg = self.send_msg("测试", "这是一条测试消息")
        if not flag:
            log.error("【PushPlus】发送消息失败：%s" % msg)
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
        if not text:
            text = "无"
        if not self._token or not self._channel:
            return False, "参数未配置"
        try:
            values = {
                "token": self._token,
                "channel": self._channel,
                "topic": self._topic,
                "webhook": self._webhook,
                "title": title,
                "content": text,
                "timestamp": time.time_ns() + 60
            }
            sc_url = "http://www.pushplus.plus/send?%s" % urlencode(values)
            res = RequestUtils().get_res(sc_url)
            if res:
                ret_json = res.json()
                code = ret_json.get("code")
                msg = ret_json.get("msg")
                if code == 200:
                    return True, msg
                else:
                    return False, msg
            else:
                return False, "未获取到返回信息"
        except Exception as msg_e:
            return False, str(msg_e)

    def send_list_msg(self, title, medias: list, user_id=""):
        pass
