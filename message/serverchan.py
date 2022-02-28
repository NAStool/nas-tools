import sys
from urllib.parse import urlencode
import requests
from config import get_config


class ServerChan:
    __sckey = None

    def __init__(self):
        config = get_config()
        if config.get('message'):
            self.__sckey = config['message'].get('serverchan', {}).get('sckey')

    # 发送ServerChan消息
    def send_serverchan_msg(self, text, desp=""):
        if not text and not desp:
            return -1, "标题和内容不能同时为空"
        values = {"title": text, "desp": desp}
        try:
            if not self.__sckey:
                return False, "参数未配置"
            sc_url = "https://sctapi.ftqq.com/%s.send?%s" % (self.__sckey, urlencode(values))
            res = requests.get(sc_url)
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


if __name__ == "__main__":
    if len(sys.argv) > 1:
        in_title = sys.argv[1]
    else:
        in_title = "ServerChan标题"
    if len(sys.argv) > 2:
        in_text = sys.argv[2]
    else:
        in_text = "ServerChan内容"
    ServerChan().send_serverchan_msg(in_title, in_text)
