from urllib.parse import urlencode

import log
from app.message.channel.channel import IMessageChannel
from app.utils import RequestUtils


class ServerChan(IMessageChannel):
    _sckey = None
    _client_config = {}

    def __init__(self, config):
        self._client_config = config
        self.init_config()

    def init_config(self):
        if self._client_config:
            self._sckey = self._client_config.get('sckey')

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
        if not self._sckey:
            return False, "参数未配置"
        try:
            sc_url = "https://sctapi.ftqq.com/%s.send?%s" % (self._sckey, urlencode({"title": title, "desp": text}))
            res = RequestUtils().get_res(sc_url)
            if res:
                ret_json = res.json()
                errno = ret_json.get('code')
                error = ret_json.get('message')
                if errno == 0:
                    return True, error
                else:
                    return False, error
            else:
                return False, "未获取到返回信息"
        except Exception as msg_e:
            return False, str(msg_e)

    def send_list_msg(self, **kwargs):
        pass
