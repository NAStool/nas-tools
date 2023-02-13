from urllib.parse import quote_plus

from app.message.client._base import _IMessageClient
from app.utils import RequestUtils, StringUtils, ExceptionUtils


class Bark(_IMessageClient):
    schema = "bark"

    _server = None
    _apikey = None
    _params = None
    _client_config = {}

    def __init__(self, config):
        self._client_config = config
        self.init_config()

    def init_config(self):
        if self._client_config:
            self._server = StringUtils.get_base_url(self._client_config.get('server'))
            self._apikey = self._client_config.get('apikey')
            self._params = self._client_config.get('params')

    @classmethod
    def match(cls, ctype):
        return True if ctype == cls.schema else False

    def send_msg(self, title, text="", image="", url="", user_id=""):
        """
        发送Bark消息
        :param title: 消息标题
        :param text: 消息内容
        :param image: 未使用
        :param url: 未使用
        :param user_id: 未使用
        :return: 发送状态、错误信息
        """
        if not title and not text:
            return False, "标题和内容不能同时为空"
        try:
            if not self._server or not self._apikey:
                return False, "参数未配置"
            sc_url = "%s/%s/%s/%s" % (self._server, self._apikey, quote_plus(title), quote_plus(text))
            if self._params:
                sc_url = "%s?%s" % (sc_url, self._params)
            res = RequestUtils().post_res(sc_url)
            if res:
                ret_json = res.json()
                code = ret_json['code']
                message = ret_json['message']
                if code == 200:
                    return True, message
                else:
                    return False, message
            else:
                return False, "未获取到返回信息"
        except Exception as msg_e:
            ExceptionUtils.exception_traceback(msg_e)
            return False, str(msg_e)

    def send_list_msg(self, **kwargs):
        pass
