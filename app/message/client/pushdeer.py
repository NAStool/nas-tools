from pypushdeer import PushDeer

from app.message.client._base import _IMessageClient
from app.utils import StringUtils, ExceptionUtils


class PushDeerClient(_IMessageClient):
    schema = "pushdeer"

    _server = None
    _apikey = None
    _client_config = {}

    def __init__(self, config):
        self._client_config = config
        self.init_config()

    def init_config(self):
        if self._client_config:
            self._server = StringUtils.get_base_url(self._client_config.get('server'))
            self._apikey = self._client_config.get('apikey')

    @classmethod
    def match(cls, ctype):
        return True if ctype == cls.schema else False

    def send_msg(self, title, text="", image="", url="", user_id=""):
        """
        发送PushDeer消息
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
            pushdeer = PushDeer(server=self._server, pushkey=self._apikey)
            res = pushdeer.send_markdown(title, desp=text)
            if res:
                return True, "成功"
            else:
                return False, "失败"
        except Exception as msg_e:
            ExceptionUtils.exception_traceback(msg_e)
            return False, str(msg_e)

    def send_list_msg(self, **kwargs):
        pass
