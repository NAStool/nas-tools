from app.message.message_client import IMessageClient
from app.utils import RequestUtils, StringUtils
from app.utils.exception_utils import ExceptionUtils


class Gotify(IMessageClient):
    _server = None
    _token = None
    _priority = None
    _client_config = {}

    def __init__(self, config):
        self._client_config = config
        self.init_config()

    def init_config(self):
        if self._client_config:
            self._server = StringUtils.get_base_url(self._client_config.get('server'))
            self._token = self._client_config.get('token')
            try:
                self._priority = int(self._client_config.get('priority'))
            except Exception as e:
                self._priority = 8
                ExceptionUtils.exception_traceback(e)

    def send_msg(self, title, text="", image="", url="", user_id=""):
        """
        发送Bark消息
        :param title: 消息标题
        :param text: 消息内容
        :param image: 未使用
        :param url: 点击消息跳转URL, 为空时则没有任何动作
        :param user_id: 未使用
        :return: 发送状态、错误信息
        """
        if not title and not text:
            return False, "标题和内容不能同时为空"
        try:
            if not self._server or not self._token:
                return False, "参数未配置"
            sc_url = "%s/message?token=%s" % (self._server, self._token)
            sc_data = {
                "title": title,
                "message": text,
                "priority": self._priority,
                "extras": {
                    "client::notification": {
                        "click": {
                            "url": url
                        }
                    },
                }
            }
            res = RequestUtils(content_type="application/json").post_res(sc_url, json=sc_data)
            message = res.json()
            if res.status_code == 200:
                return True, message
            else:
                return False, message
        except Exception as msg_e:
            ExceptionUtils.exception_traceback(msg_e)
            return False, str(msg_e)

    def send_list_msg(self, **kwargs):
        pass
