import re
from threading import Lock

import requests
from slack_sdk.errors import SlackApiError

import log
from app.message.client._base import _IMessageClient
from app.utils import ExceptionUtils
from config import Config
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

lock = Lock()


class Slack(_IMessageClient):
    schema = "slack"

    _client_config = {}
    _interactive = False
    _ds_url = None
    _service = None
    _channel = None
    _client = None

    def __init__(self, config):
        self._config = Config()
        self._client_config = config
        self._interactive = config.get("interactive")
        self._channel = config.get("channel") or "全体"
        self.init_config()

    def init_config(self):
        self._ds_url = "http://127.0.0.1:%s/slack" % self._config.get_config("app").get("web_port")
        if self._client_config:
            try:
                slack_app = App(token=self._client_config.get("bot_token"))
            except Exception as err:
                ExceptionUtils.exception_traceback(err)
                return
            self._client = slack_app.client

            # 注册消息响应
            @slack_app.event("message")
            def slack_message(message):
                local_res = requests.post(self._ds_url, json=message, timeout=10)
                log.debug("【Slack】message: %s processed, response is: %s" % (message, local_res.text))

            @slack_app.action(re.compile(r"actionId-\d+"))
            def slack_action(ack, body):
                ack()
                local_res = requests.post(self._ds_url, json=body, timeout=60)
                log.debug("【Slack】message: %s processed, response is: %s" % (body, local_res.text))

            @slack_app.event("app_mention")
            def slack_mention(say, body):
                say(f"收到，请稍等... <@{body.get('event', {}).get('user')}>")
                local_res = requests.post(self._ds_url, json=body, timeout=10)
                log.debug("【Slack】message: %s processed, response is: %s" % (body, local_res.text))

            @slack_app.shortcut(re.compile(r"/*"))
            def slack_shortcut(ack, body):
                ack()
                local_res = requests.post(self._ds_url, json=body, timeout=10)
                log.debug("【Slack】message: %s processed, response is: %s" % (body, local_res.text))

            # 启动服务
            if self._interactive:
                try:
                    self._service = SocketModeHandler(
                        slack_app,
                        self._client_config.get("app_token")
                    )
                    self._service.connect()
                    log.info("Slack消息接收服务启动")
                except Exception as err:
                    ExceptionUtils.exception_traceback(err)
                    log.error("Slack消息接收服务启动失败: %s" % str(err))

    @classmethod
    def match(cls, ctype):
        return True if ctype == cls.schema else False

    def stop_service(self):
        if self._service:
            try:
                self._service.close()
            except Exception as err:
                print(str(err))
            log.info("Slack消息接收服务已停止")

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
            if user_id:
                channel = user_id
            else:
                # 消息广播
                channel = self.__find_public_channel()
            # 拼装消息内容
            titles = str(title).split('\n')
            if len(titles) > 1:
                title = titles[0]
                if not text:
                    text = "\n".join(titles[1:])
                else:
                    text = "%s\n%s" % ("\n".join(titles[1:]), text)
            block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{title}*\n{text}"
                }
            }
            # 消息图片
            if image:
                block['accessory'] = {
                    "type": "image",
                    "image_url": f"{image}",
                    "alt_text": f"{title}"
                }
            blocks = [block]
            # 链接
            if image and url:
                blocks.append({
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "查看详情",
                                "emoji": True
                            },
                            "value": "click_me_url",
                            "url": f"{url}",
                            "action_id": "actionId-url"
                        }
                    ]
                })
            # 发送
            result = self._client.chat_postMessage(
                channel=channel,
                blocks=blocks
            )
            return True, result
        except Exception as msg_e:
            ExceptionUtils.exception_traceback(msg_e)
            return False, str(msg_e)

    def send_list_msg(self, medias: list, user_id="", **kwargs):
        """
        发送列表类消息
        """
        if not medias:
            return False, "参数有误"
        if not self._client:
            return False, "消息客户端未就绪"
        try:
            if user_id:
                channel = user_id
            else:
                # 消息广播
                channel = self.__find_public_channel()
            title = f"共找到{len(medias)}条相关信息，请选择"
            # 消息主体
            title_section = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{title}*"
                }
            }
            blocks = [title_section]
            # 列表
            if medias:
                blocks.append({
                    "type": "divider"
                })
                index = 1
                for media in medias:
                    if media.get_poster_image():
                        if media.get_star_string():
                            text = f"{index}. *<{media.get_detail_url()}|{media.get_title_string()}>*" \
                                   f"\n{media.get_type_string()}" \
                                   f"\n{media.get_star_string()}" \
                                   f"\n{media.get_overview_string(50)}"
                        else:
                            text = f"{index}. *<{media.get_detail_url()}|{media.get_title_string()}>*" \
                                   f"\n{media.get_type_string()}" \
                                   f"\n{media.get_overview_string(50)}"
                        blocks.append(
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": text
                                },
                                "accessory": {
                                    "type": "image",
                                    "image_url": f"{media.get_poster_image()}",
                                    "alt_text": f"{media.get_title_string()}"
                                }
                            }
                        )
                        blocks.append(
                            {
                                "type": "actions",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "选择",
                                            "emoji": True
                                        },
                                        "value": f"{index}",
                                        "action_id": f"actionId-{index}"
                                    }
                                ]
                            }
                        )
                        index += 1
            # 发送
            result = self._client.chat_postMessage(
                channel=channel,
                blocks=blocks
            )
            return True, result
        except Exception as msg_e:
            ExceptionUtils.exception_traceback(msg_e)
            return False, str(msg_e)

    def __find_public_channel(self):
        """
        查找公共频道
        """
        if not self._client:
            return ""
        conversation_id = ""
        try:
            for result in self._client.conversations_list():
                if conversation_id:
                    break
                for channel in result["channels"]:
                    if channel.get("name") == self._channel:
                        conversation_id = channel.get("id")
                        break
        except SlackApiError as e:
            print(f"Slack Error: {e}")
        return conversation_id
