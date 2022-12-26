import time
from urllib.parse import urlencode

from app.message.message_client import IMessageClient
from app.utils import RequestUtils
from app.utils.exception_utils import ExceptionUtils


class PushPlus(IMessageClient):
    _token = None
    _topic = None
    _channel = None
    _webhook = None
    _client_config = {}

    def __init__(self, config):
        self._client_config = config
        self.init_config()

    def init_config(self):
        if self._client_config:
            self._token = self._client_config.get('token')
            self._topic = self._client_config.get('topic')
            self._channel = self._client_config.get('channel')
            self._webhook = self._client_config.get('webhook')

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
            ExceptionUtils.exception_traceback(msg_e)
            return False, str(msg_e)

    def send_list_msg(self, **kwargs):
        pass
