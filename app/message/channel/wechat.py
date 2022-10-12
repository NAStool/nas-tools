import json
import threading
from datetime import datetime

import log
from config import Config, DEFAULT_WECHAT_PROXY
from app.message.channel.channel import IMessageChannel
from app.utils.commons import singleton
from app.utils import RequestUtils

lock = threading.Lock()


@singleton
class WeChat(IMessageChannel):
    __instance = None
    __access_token = None
    __expires_in = None
    __access_token_time = None
    __default_proxy = False

    __corpid = None
    __corpsecret = None
    __agent_id = None

    __send_msg_url = "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s"
    __token_url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=%s&corpsecret=%s"

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        message = config.get_config('message')
        if message:
            self.__corpid = message.get('wechat', {}).get('corpid')
            self.__corpsecret = message.get('wechat', {}).get('corpsecret')
            self.__agent_id = message.get('wechat', {}).get('agentid')
            self.__default_proxy = message.get('wechat', {}).get('default_proxy')
        if self.__default_proxy:
            if isinstance(self.__default_proxy, bool):
                self.__send_msg_url = f"{DEFAULT_WECHAT_PROXY}/cgi-bin/message/send?access_token=%s"
                self.__token_url = f"{DEFAULT_WECHAT_PROXY}/cgi-bin/gettoken?corpid=%s&corpsecret=%s"
            else:
                self.__send_msg_url = f"{self.__default_proxy}/cgi-bin/message/send?access_token=%s"
                self.__token_url = f"{self.__default_proxy}/cgi-bin/gettoken?corpid=%s&corpsecret=%s"
        if self.__corpid and self.__corpsecret and self.__agent_id:
            self.__get_access_token()

    def __get_access_token(self, force=False):
        """
        获取微信Token
        :return： 微信Token
        """
        token_flag = True
        if not self.__access_token:
            token_flag = False
        else:
            if (datetime.now() - self.__access_token_time).seconds >= self.__expires_in:
                token_flag = False

        if not token_flag or force:
            if not self.__corpid or not self.__corpsecret:
                return None
            try:
                token_url = self.__token_url % (self.__corpid, self.__corpsecret)
                res = RequestUtils().get_res(token_url)
                if res:
                    ret_json = res.json()
                    if ret_json.get('errcode') == 0:
                        self.__access_token = ret_json.get('access_token')
                        self.__expires_in = ret_json.get('expires_in')
                        self.__access_token_time = datetime.now()
            except Exception as e:
                log.console(str(e))
                return None
        return self.__access_token

    def get_status(self):
        """
        测试连通性
        """
        flag, msg = self.__send_message("测试", "这是一条测试消息")
        if not flag:
            log.error("【WeChat】发送消息失败：%s" % msg)
        return flag

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
        message_url = self.__send_msg_url % self.__get_access_token()
        if text:
            conent = "%s\n%s" % (title, text.replace("\n\n", "\n"))
        else:
            conent = title
        if not user_id:
            user_id = "@all"
        req_json = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": self.__agent_id,
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
            return False, "参数未配置或配置不正确"
        message_url = self.__send_msg_url % self.__get_access_token()
        if text:
            text = text.replace("\n\n", "\n")
        if not user_id:
            user_id = "@all"
        req_json = {
            "touser": user_id,
            "msgtype": "news",
            "agentid": self.__agent_id,
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

    def send_list_msg(self, medias: list, url="", user_id=""):
        """
        发送列表类消息
        """
        if not self.__get_access_token():
            return False, "参数未配置或配置不正确"
        if not isinstance(medias, list):
            return False, "数据错误"
        message_url = self.__send_msg_url % self.__get_access_token()
        if not user_id:
            user_id = "@all"
        articles = []
        index = 1
        for media in medias:
            articles.append({
                "title": "%s. %s" % (index, media.get_title_vote_string()),
                "description": "",
                "picurl": media.get_message_image() if index == 1 else media.get_poster_image(),
                "url": url
            })
            index += 1
        req_json = {
            "touser": user_id,
            "msgtype": "news",
            "agentid": self.__agent_id,
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
            return False, str(err)
