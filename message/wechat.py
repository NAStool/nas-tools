from datetime import datetime
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
            self.get_access_token()

    def get_access_token(self):
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

    # 发送文本消息
    def send_message(self, title, text, user_id):
        message_url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s' % self.get_access_token()
        if not self.__agent_id:
            return False, "参数未配置"
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
        headers = {'content-type': 'charset=utf8'}
        try:
            res = requests.post(message_url, json=req_json, headers=headers)
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

    # 发送图文消息
    def send_image_message(self, title, text, image_url, url, user_id):
        message_url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s' % self.get_access_token()
        if not self.__agent_id:
            return False, "参数未配置"
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
        headers = {'content-type': 'charset=utf8'}
        try:
            res = requests.post(message_url, json=req_json, headers=headers)
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

    def send_wechat_msg(self, title, text, image, url, user_id):
        if not title and not text:
            return -1, "标题和内容不能同时为空"
        if image:
            ret_code, ret_msg = self.send_image_message(title, text, image, url, user_id)
        else:
            ret_code, ret_msg = self.send_message(title, text, user_id)
        return ret_code, ret_msg
