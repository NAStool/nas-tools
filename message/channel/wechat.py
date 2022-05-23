from datetime import datetime
import json
import threading
import requests

import log
from config import Config
from utils.functions import singleton

lock = threading.Lock()


@singleton
class WeChat(object):
    __instance = None
    __access_token = None
    __expires_in = None
    __access_token_time = None

    __corpid = None
    __corpsecret = None
    __agent_id = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        message = config.get_config('message')
        if message:
            self.__corpid = message.get('wechat', {}).get('corpid')
            self.__corpsecret = message.get('wechat', {}).get('corpsecret')
            self.__agent_id = message.get('wechat', {}).get('agentid')
        if self.__corpid and self.__corpsecret and self.__agent_id:
            self.__get_access_token()

    def __get_access_token(self):
        """
        获取微信Token
        :return： 微信Token
        """
        token_flag = True
        if not self.__access_token:
            token_flag = False
        else:
            cur_time = datetime.now()
            if (cur_time - self.__access_token_time).seconds >= self.__expires_in:
                token_flag = False

        if not token_flag:
            if not self.__corpid or not self.__corpsecret:
                return None
            try:
                token_url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=%s&corpsecret=%s" \
                            % (self.__corpid, self.__corpsecret)
                res = requests.get(token_url, timeout=10)
                if res:
                    ret_json = res.json()
                    if ret_json['errcode'] == 0:
                        self.__access_token = ret_json['access_token']
                        self.__expires_in = ret_json['expires_in']
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
        message_url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s' % self.__get_access_token()
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
        headers = {'content-type': 'application/json'}
        try:
            res = requests.post(message_url, data=json.dumps(req_json, ensure_ascii=False).encode('utf-8'),
                                headers=headers)
            if res:
                ret_json = res.json()
                if ret_json['errcode'] == 0:
                    return True, ret_json['errmsg']
                else:
                    return False, ret_json['errmsg']
            else:
                return False, None
        except Exception as err:
            return False, str(err)

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
        message_url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s' % self.__get_access_token()
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
        headers = {'content-type': 'application/json'}
        try:
            res = requests.post(message_url, data=json.dumps(req_json, ensure_ascii=False).encode('utf-8'),
                                headers=headers)
            if res:
                ret_json = res.json()
                if ret_json['errcode'] == 0:
                    return True, ret_json['errmsg']
                else:
                    return False, ret_json['errmsg']
            else:
                return False, None
        except Exception as err:
            return False, str(err)

    def send_msg(self, title, text, image, url, user_id=None):
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
