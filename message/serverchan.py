from urllib.parse import urlencode
import requests

from config import Config


class ServerChan:
    __sckey = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        message = config.get_config('message')
        if message:
            self.__sckey = message.get('serverchan', {}).get('sckey')

    # 发送ServerChan消息
    def send_serverchan_msg(self, text, desp=""):
        if not text and not desp:
            return -1, "标题和内容不能同时为空"
        values = {"title": text, "desp": desp}
        try:
            if not self.__sckey:
                return False, "参数未配置"
            sc_url = "https://sctapi.ftqq.com/%s.send?%s" % (self.__sckey, urlencode(values))
            res = requests.get(sc_url, timeout=10)
            if res:
                ret_json = res.json()
                errno = ret_json['code']
                error = ret_json['message']
                if errno == 0:
                    return True, error
                else:
                    return False, error
            else:
                return False, "未获取到返回信息"
        except Exception as msg_e:
            return False, str(msg_e)
