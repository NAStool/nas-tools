import json
from urllib.parse import quote
from threading import Lock

from app.message.client._base import _IMessageClient
from app.utils import ExceptionUtils, RequestUtils, StringUtils
from config import Config

lock = Lock()


class SynologyChat(_IMessageClient):
    schema = "synologychat"

    _client_config = {}
    _interactive = False
    _domain = None
    _webhook_url = None
    _token = None
    _client = None
    _req = None

    def __init__(self, config):
        self._config = Config()
        self._client_config = config
        self._interactive = config.get("interactive")
        self._req = RequestUtils(content_type="application/x-www-form-urlencoded")
        self.init_config()

    def init_config(self):
        if self._client_config:
            self._webhook_url = self._client_config.get("webhook_url")
            if self._webhook_url:
                self._domain = StringUtils.get_base_url(self._webhook_url)
            self._token = self._client_config.get('token')

    @classmethod
    def match(cls, ctype):
        return True if ctype == cls.schema else False

    def check_token(self, token):
        return True if token == self._token else False

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
        if not self._webhook_url or not self._token:
            return False, "参数未配置"
        try:
            # 拼装消息内容
            titles = str(title).split('\n')
            if len(titles) > 1:
                title = titles[0]
                if not text:
                    text = "\n".join(titles[1:])
                else:
                    text = f"%s\n%s" % ("\n".join(titles[1:]), text)

            if text:
                caption = "*%s*\n%s" % (title, text.replace("\n\n", "\n"))
            else:
                caption = title
            if url and image:
                caption = f"{caption}\n\n<{url}|查看详情>"
            payload_data = {'text': quote(caption)}
            if image:
                payload_data['file_url'] = quote(image)
            if user_id:
                payload_data['user_ids'] = [int(user_id)]
            else:
                userids = self.__get_bot_users()
                if not userids:
                    return False, "机器人没有对任何用户可见"
                payload_data['user_ids'] = userids
            return self.__send_request(payload_data)

        except Exception as msg_e:
            ExceptionUtils.exception_traceback(msg_e)
            return False, str(msg_e)

    def send_list_msg(self, medias: list, user_id="", title="", **kwargs):
        """
        发送列表类消息
        """
        if not medias:
            return False, "参数有误"
        if not self._webhook_url or not self._token:
            return False, "参数未配置"
        try:
            if not title or not isinstance(medias, list):
                return False, "数据错误"
            index, image, caption = 1, "", "*%s*" % title
            for media in medias:
                if not image:
                    image = media.get_message_image()
                if media.get_vote_string():
                    caption = "%s\n%s. <%s|%s>\n%s，%s" % (caption,
                                                          index,
                                                          media.get_detail_url(),
                                                          media.get_title_string(),
                                                          media.get_type_string(),
                                                          media.get_vote_string())
                else:
                    caption = "%s\n%s. <%s|%s>\n%s" % (caption,
                                                       index,
                                                       media.get_detail_url(),
                                                       media.get_title_string(),
                                                       media.get_type_string())
                index += 1

            if user_id:
                user_ids = [int(user_id)]
            else:
                user_ids = self.__get_bot_users()
            payload_data = {
                "text": quote(caption),
                "file_url": quote(image),
                "user_ids": user_ids
            }
            return self.__send_request(payload_data)
        except Exception as msg_e:
            ExceptionUtils.exception_traceback(msg_e)
            return False, str(msg_e)

    def __get_bot_users(self):
        """
        查询机器人可见的用户列表
        """
        if not self._domain or not self._token:
            return []
        req_url = f"{self._domain}" \
                  f"/webapi/entry.cgi?api=SYNO.Chat.External&method=user_list&version=2&token=" \
                  f"{self._token}"
        ret = self._req.get_res(url=req_url)
        if ret and ret.status_code == 200:
            users = ret.json().get("data", {}).get("users", []) or []
            return [user.get("user_id") for user in users]
        else:
            return []

    def __send_request(self, payload_data):
        """
        发送消息请求
        """
        payload = f"payload={json.dumps(payload_data)}"
        ret = self._req.post_res(url=self._webhook_url, params=payload)
        if ret and ret.status_code == 200:
            result = ret.json()
            if result:
                errno = result.get('error', {}).get('code')
                errmsg = result.get('error', {}).get('errors')
                if not errno:
                    return True, ""
                return False, f"{errno}-{errmsg}"
            else:
                return False, f"{ret.text}"
        elif ret:
            return False, f"错误码：{ret.status_code}"
        else:
            return False, "未获取到返回信息"
