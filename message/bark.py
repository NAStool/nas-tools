import requests

from config import Config


class Bark:
    __server = None
    __apikey = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        message = config.get_config('message')
        if message:
            self.__server = message.get('bark', {}).get('server')
            self.__apikey = message.get('bark', {}).get('apikey')

    # 发送Bark消息
    def send_bark_msg(self, title, text=""):
        if not title and not text:
            return -1, "标题和内容不能同时为空"
        try:
            if not self.__server or not self.__apikey:
                return False, "参数未配置"
            sc_url = "%s/%s/%s/%s" % (self.__server, self.__apikey, title, text)
            res = requests.get(sc_url, timeout=10)
            if res:
                ret_json = res.json()
                code = ret_json['code']
                message = ret_json['message']
                if code == 200:
                    return True, message
                else:
                    return False, message
            else:
                return False, "未获取到返回信息"
        except Exception as msg_e:
            return False, str(msg_e)
