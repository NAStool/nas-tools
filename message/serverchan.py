import sys
from urllib.parse import urlencode
import requests
from config import get_config
import log


# 发送ServerChan消息
def send_serverchan_msg(text, desp=""):
    if not text and not desp:
        return -1, "标题和内容不能同时为空！"
    values = {"title": text, "desp": desp}
    try:
        config = get_config()
        sckey = config['message'].get('serverchan', {}).get('sckey')
        if not sckey:
            log.error("【MSG】未配置sckey，无法发送ServerChan消息!")
            return False, None
        sc_url = "https://sctapi.ftqq.com/" + sckey + ".send?" + urlencode(values)
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
            return False, None
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
    send_serverchan_msg(in_title, in_text)
