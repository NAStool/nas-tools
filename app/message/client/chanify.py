from urllib import parse

from app.message.client._base import _IMessageClient
from app.utils import RequestUtils, StringUtils, ExceptionUtils


class Chanify(_IMessageClient):
    schema = "chanify"

    _server = None
    _token = None
    _params = None
    _client_config = {}

    def __init__(self, config):
        self._client_config = config
        self.init_config()

    def init_config(self):
        if self._client_config:
            self._server = StringUtils.get_base_url(self._client_config.get('server'))
            self._token = self._client_config.get('token')
            self._params = self._client_config.get('params')

    @classmethod
    def match(cls, ctype):
        return True if ctype == cls.schema else False

    def send_msg(self, title, text="", image="", url="", user_id=""):
        """
        发送Chanify消息
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
            if not self._server or not self._token:
                return False, "参数未配置"
            sc_url = "%s/v1/sender/%s" % (self._server, self._token)
            params = parse.parse_qs(self._params or '')
            data = {key: value[0] for key, value in params.items()}
            data.update({'title': title, 'text': text})
            # 发送文本
            res = RequestUtils().post_res(sc_url, data=parse.urlencode(data).encode())
            if res and res.status_code == 200:
                return True, "发送成功"
            elif res is not None:
                return False, f"错误码：{res.status_code}，错误原因：{res.reason}"
            else:
                return False, "未获取到返回信息"
        except Exception as msg_e:
            ExceptionUtils.exception_traceback(msg_e)
            return False, str(msg_e)

    def send_list_msg(self, **kwargs):
        pass
