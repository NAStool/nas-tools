import json
import threading
from datetime import datetime

from app.message.client._base import _IMessageClient
from app.utils import RequestUtils, ExceptionUtils
from config import DEFAULT_WECHAT_PROXY

lock = threading.Lock()


class WeChat(_IMessageClient):
    schema = "wechat"

    _instance = None
    _access_token = None
    _expires_in = None
    _access_token_time = None
    _default_proxy = False
    _client_config = {}
    _corpid = None
    _corpsecret = None
    _agent_id = None
    _interactive = False

    _send_msg_url = "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s"
    _token_url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=%s&corpsecret=%s"

    def __init__(self, config):
        self._client_config = config
        self._interactive = config.get("interactive")
        self.init_config()

    def init_config(self):
        if self._client_config:
            self._corpid = self._client_config.get('corpid')
            self._corpsecret = self._client_config.get('corpsecret')
            self._agent_id = self._client_config.get('agentid')
            self._default_proxy = self._client_config.get('default_proxy')
        if self._default_proxy:
            if isinstance(self._default_proxy, bool):
                self._send_msg_url = f"{DEFAULT_WECHAT_PROXY}/cgi-bin/message/send?access_token=%s"
                self._token_url = f"{DEFAULT_WECHAT_PROXY}/cgi-bin/gettoken?corpid=%s&corpsecret=%s"
            else:
                self._send_msg_url = f"{self._default_proxy}/cgi-bin/message/send?access_token=%s"
                self._token_url = f"{self._default_proxy}/cgi-bin/gettoken?corpid=%s&corpsecret=%s"
        if self._corpid and self._corpsecret and self._agent_id:
            self.__get_access_token()

    @classmethod
    def match(cls, ctype):
        return True if ctype == cls.schema else False

    def __get_access_token(self, force=False):
        """
        获取微信Token
        :return： 微信Token
        """
        token_flag = True
        if not self._access_token:
            token_flag = False
        else:
            if (datetime.now() - self._access_token_time).seconds >= self._expires_in:
                token_flag = False

        if not token_flag or force:
            if not self._corpid or not self._corpsecret:
                return None
            try:
                token_url = self._token_url % (self._corpid, self._corpsecret)
                res = RequestUtils().get_res(token_url)
                if res:
                    ret_json = res.json()
                    if ret_json.get('errcode') == 0:
                        self._access_token = ret_json.get('access_token')
                        self._expires_in = ret_json.get('expires_in')
                        self._access_token_time = datetime.now()
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                return None
        return self._access_token

    def __send_message(self, title, text, user_id=None):
        """
        发送文本消息
        :param title: 消息标题
        :param text: 消息内容
        :param user_id: 消息发送对象的ID，为空则发给所有人
        :return: 发送状态，错误信息
        """
        if not self.__get_access_token():
            return False, "参数未配置或配置不正确"
        message_url = self._send_msg_url % self.__get_access_token()
        if text:
            conent = "%s\n%s" % (title, text.replace("\n\n", "\n"))
        else:
            conent = title
        if not user_id:
            user_id = "@all"
        req_json = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": self._agent_id,
            "text": {
                "content": conent
            },
            "safe": 0,
            "enable_id_trans": 0,
            "enable_duplicate_check": 0
        }
        return self.__post_request(message_url, req_json)

    def __send_image_message(self, title, text, image_url, url, user_id=None):
        """
        发送图文消息
        :param title: 消息标题
        :param text: 消息内容
        :param image_url: 图片地址
        :param url: 点击消息跳转URL
        :param user_id: 消息发送对象的ID，为空则发给所有人
        :return: 发送状态，错误信息
        """
        if not self.__get_access_token():
            return False, "获取微信access_token失败，请检查参数配置"
        message_url = self._send_msg_url % self.__get_access_token()
        if text:
            text = text.replace("\n\n", "\n")
        if not user_id:
            user_id = "@all"
        req_json = {
            "touser": user_id,
            "msgtype": "news",
            "agentid": self._agent_id,
            "news": {
                "articles": [
                    {
                        "title": title,
                        "description": text,
                        "picurl": image_url,
                        "url": url
                    }
                ]
            }
        }
        return self.__post_request(message_url, req_json)

    def send_msg(self, title, text="", image="", url="", user_id=None):
        """
        微信消息发送入口，支持文本、图片、链接跳转、指定发送对象
        :param title: 消息标题
        :param text: 消息内容
        :param image: 图片地址
        :param url: 点击消息跳转URL
        :param user_id: 消息发送对象的ID，为空则发给所有人
        :return: 发送状态，错误信息
        """
        if not title and not text:
            return False, "标题和内容不能同时为空"
        if image:
            ret_code, ret_msg = self.__send_image_message(title, text, image, url, user_id)
        else:
            ret_code, ret_msg = self.__send_message(title, text, user_id)
        return ret_code, ret_msg

    def send_list_msg(self, medias: list, user_id="", title="", **kwargs):
        """
        发送列表类消息
        """
        if not self.__get_access_token():
            return False, "参数未配置或配置不正确"
        if not isinstance(medias, list):
            return False, "数据错误"
        message_url = self._send_msg_url % self.__get_access_token()
        if not user_id:
            user_id = "@all"
        articles = []
        index = 1
        for media in medias:
            if media.get_vote_string():
                title = f"{index}. {media.get_title_string()}\n{media.get_type_string()}，{media.get_vote_string()}"
            else:
                title = f"{index}. {media.get_title_string()}\n{media.get_type_string()}"
            articles.append({
                "title": title,
                "description": "",
                "picurl": media.get_message_image() if index == 1 else media.get_poster_image(),
                "url": media.get_detail_url()
            })
            index += 1
        req_json = {
            "touser": user_id,
            "msgtype": "news",
            "agentid": self._agent_id,
            "news": {
                "articles": articles
            }
        }
        return self.__post_request(message_url, req_json)

    def __post_request(self, message_url, req_json):
        """
        向微信发送请求
        """
        headers = {'content-type': 'application/json'}
        try:
            res = RequestUtils(headers=headers).post(message_url,
                                                     params=json.dumps(req_json, ensure_ascii=False).encode('utf-8'))
            if res:
                ret_json = res.json()
                if ret_json.get('errcode') == 0:
                    return True, ret_json.get('errmsg')
                else:
                    if ret_json.get('errcode') == 42001:
                        self.__get_access_token(force=True)
                    return False, ret_json.get('errmsg')
            else:
                return False, None
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return False, str(err)
