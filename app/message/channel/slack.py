from threading import Lock

import requests

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import log
from app.message.channel.channel import IMessageChannel
from config import Config

lock = Lock()


class Slack(IMessageChannel):
    _client_config = {}
    _interactive = False
    _ds_url = None
    _service = None
    _client = None

    def __init__(self, config, interactive=False):
        self._config = Config()
        self._client_config = config
        self._interactive = interactive
        self.init_config()

    def init_config(self):
        self._ds_url = "http://127.0.0.1:%s/slack" % self._config.get_config("app").get("web_port")
        if self._client_config:
            slack_app = App(token=self._client_config.get("bot_token"))
            self._client = slack_app.client

            # 注册消息响应
            @slack_app.event("message")
            def slack_message(message, say):
                local_res = requests.post(self._ds_url, json=message, timeout=10)
                log.debug("【Slack】message: %s processed, response is: %s" % (message, local_res.text))

            # 启动服务
            if self._interactive:
                self._service = SocketModeHandler(
                    slack_app,
                    self._client_config.get("app_token")
                )
                self._service.connect()
                log.info("【Slack】消息接收服务启动")

    def stop_service(self):
        if self._service:
            self._service.close()
            log.info("【Slack】消息接收服务停止")

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
        if not self._client:
            return False, "消息客户端未就绪"
        try:
            # TODO
            if user_id:
                # 按原会话返回
                result = self._client.chat_postMessage(
                    channel=user_id,
                    text=text
                )
                return True, result
            else:
                # 消息广播
                pass
        except Exception as msg_e:
            return False, str(msg_e)

    def send_list_msg(self, medias: list, user_id="", title="", url=""):
        """
        发送列表类消息
        """
        try:
            # TODO
            if user_id:
                # 按原会话返回
                result = self._client.chat_postMessage(
                    channel=user_id,
                    text="\n".join([media.get_title_string() for media in medias])
                )
                return True, result
            else:
                # 消息广播
                pass

        except Exception as msg_e:
            return False, str(msg_e)
