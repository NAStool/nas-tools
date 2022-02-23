# 发送telegram消息
import sys
from urllib.parse import urlencode
import requests
import log
from config import get_config


def send_telegram_msg(title, text=""):
    if not title and not text:
        return -1, "标题和内容不能同时为空！"
    try:
        config = get_config()
        telegram_token = config['message'].get('telegram', {}).get('telegram_token')
        telegram_chat_id = config['message'].get('telegram', {}).get('telegram_chat_id')
        if not telegram_token or not telegram_chat_id:
            log.error("【MSG】未配置telegram参数，无法发送telegram消息！")
            return False, None
        values = {"chat_id": telegram_chat_id, "text": title + "\n\n" + text}
        sc_url = "https://api.telegram.org/bot%s/sendMessage?" % telegram_token
        res = requests.get(sc_url + urlencode(values))
        if res:
            ret_json = res.json()
            errno = ret_json['ok']
            if errno == 0:
                return True, errno
            else:
                return False, errno
        else:
            return False, None
    except Exception as msg_e:
        return False, str(msg_e)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        in_title = sys.argv[1]
    else:
        in_title = "telegram标题"
    if len(sys.argv) > 2:
        in_text = sys.argv[2]
    else:
        in_text = "telegram内容"
    send_telegram_msg(in_title, in_text)
