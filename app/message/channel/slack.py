from threading import Lock

import log
from app.message.channel.channel import IMessageChannel
from config import Config

lock = Lock()


class Slack(IMessageChannel):
    _client_config = {}
    _interactive = False
    _ds_url = None
    enabled = True

    def __init__(self, config, interactive=False):
        self._config = Config()
        self._client_config = config
        self._interactive = interactive
        self.init_config()

    def init_config(self):
        self._ds_url = "http://127.0.0.1:%s/slack" % self._config.get_config("app").get("web_port")
        if self._client_config:
            pass

    def get_status(self):
        """
        测试连通性
        """
        flag, msg = self.send_msg("测试", "这是一条测试消息")
        if not flag:
            log.error("【Slack】发送消息失败：%s" % msg)
        return flag

    def send_msg(self, title, text="", image="", url="", user_id=""):
        """
        发送Telegram消息
        :param title: 消息标题
        :param text: 消息内容
        :param image: 消息图片地址
        :param url: 点击消息转转的URL
        :param user_id: 用户ID，如有则只发消息给该用户
        :user_id: 发送消息的目标用户ID，为空则发给管理员
        """
        if not title and not text:
            return False, "标题和内容不能同时为空"
        try:
            pass

        except Exception as msg_e:
            return False, str(msg_e)

    def send_list_msg(self, medias: list, user_id="", title="", url=""):
        """
        发送列表类消息
        """
        try:
            pass

        except Exception as msg_e:
            return False, str(msg_e)
