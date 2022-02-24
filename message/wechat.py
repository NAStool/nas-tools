import sys
from datetime import datetime
import threading
import requests

from config import get_config

lock = threading.Lock()


class WeChat(object):
    __instance = None
    __access_token = None
    __expires_in = None
    __access_token_time = None

    def __init__(self):
        self.get_access_token()

    @staticmethod
    def get_instance():
        if WeChat.__instance:
            return WeChat.__instance
        try:
            lock.acquire()
            if not WeChat.__instance:
                WeChat.__instance = WeChat()
        finally:
            lock.release()
        return WeChat.__instance

    def get_access_token(self):
        token_flag = True
        if not self.__access_token:
            token_flag = False
        else:
            cur_time = datetime.now()
            if (cur_time - self.__access_token_time).seconds >= self.__expires_in:
                token_flag = False

        if not token_flag:
            config = get_config()
            corpid = config['message'].get('wechat', {}).get('corpid')
            corpsecret = config['message'].get('wechat', {}).get('corpsecret')
            if not corpid or not corpsecret:
                return None
            token_url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=%s&corpsecret=%s" % (corpid, corpsecret)
            res = requests.get(token_url)
            if res:
                ret_json = res.json()
                if ret_json['errcode'] == 0:
                    self.__access_token = ret_json['access_token']
                    self.__expires_in = ret_json['expires_in']
                    self.__access_token_time = datetime.now()
        return self.__access_token

    # 发送文本消息
    def send_message(self, title, text):
        message_url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s' % self.get_access_token()
        config = get_config()
        agent_id = config['message'].get('wechat', {}).get('agentid')
        if not agent_id:
            return False, "未配置wechat.agentid，无法发送消息！"
        if text:
            text = text.replace("\n\n", "\n")
        req_json = {
            "touser": "@all",
            "msgtype": "text",
            "agentid": agent_id,
            "text": {
                "content": title + "\n\n" + text
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
    def send_image_message(self, title, text, image_url):
        message_url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s' % self.get_access_token()
        config = get_config()
        agent_id = config['message'].get('wechat', {}).get('agentid')
        if not agent_id:
            return False, "未配置wechat.agentid，无法发送消息！"
        if text:
            text = text.replace("\n\n", "\n")

        req_json = {
            "touser": "@all",
            "msgtype": "news",
            "agentid": agent_id,
            "news": {
                "articles": [
                    {
                        "title": title,
                        "description": text,
                        "url": "URL",
                        "picurl": image_url
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


def send_wechat_msg(title, text, image):
    if not title and not text:
        return -1, "标题和内容不能同时为空！"
    if image:
        ret_code, ret_msg = WeChat.get_instance().send_image_message(title, text, image)
    else:
        ret_code, ret_msg = WeChat.get_instance().send_message(title, text)
    return ret_code, ret_msg


if __name__ == "__main__":
    if len(sys.argv) > 1:
        in_title = sys.argv[1]
    else:
        in_title = "WeChat标题"
    if len(sys.argv) > 2:
        in_text = sys.argv[2]
    else:
        in_text = "WeChat内容"
    send_wechat_msg(in_title, in_text)
