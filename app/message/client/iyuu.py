from urllib.parse import urlencode

from app.message.client._base import _IMessageClient
from app.utils import RequestUtils, ExceptionUtils


class IyuuMsg(_IMessageClient):
    schema = "iyuu"

    _token = None
    _client_config = {}

    def __init__(self, config):
        self._client_config = config
        self.init_config()

    def init_config(self):
        if self._client_config:
            self._token = self._client_config.get('token')

    @classmethod
    def match(cls, ctype):
        return True if ctype == cls.schema else False

    def send_msg(self, title, text="", image="", url="", user_id=""):
        """
        发送爱语飞飞消息
        :param title: 消息标题
        :param text: 消息内容
        :param image: 未使用
        :param url: 未使用
        :param user_id: 未使用
        """
        if not title and not text:
            return False, "标题和内容不能同时为空"
        if not self._token:
            return False, "参数未配置"
        try:
            sc_url = "http://iyuu.cn/%s.send?%s" % (self._token, urlencode({"text": title, "desp": text}))
            res = RequestUtils().get_res(sc_url)
            if res:
                ret_json = res.json()
                errno = ret_json.get('errcode')
                error = ret_json.get('errmsg')
                if errno == 0:
                    return True, error
                else:
                    return False, error
            else:
                return False, "未获取到返回信息"
        except Exception as msg_e:
            ExceptionUtils.exception_traceback(msg_e)
            return False, str(msg_e)

    def send_list_msg(self, **kwargs):
        pass
