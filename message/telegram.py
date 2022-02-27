# 发送telegram消息
import sys
from urllib.parse import urlencode
import requests
from config import get_config


class Telegram:

    __telegram_token = None
    __telegram_chat_id = None

    def __init__(self):
        config = get_config()
        if config.get('message'):
            self.__telegram_token = config['message'].get('telegram', {}).get('telegram_token')
            self.__telegram_chat_id = config['message'].get('telegram', {}).get('telegram_chat_id')

    def send_telegram_msg(self, title, text="", image=""):
        if not title and not text:
            return -1, "标题和内容不能同时为空"
        try:
            if not self.__telegram_token or not self.__telegram_chat_id:
                return False, "参数未配置"

            if image:
                # 发送图文消息
                text = text.replace("\n\n", "\n")
                values = {"chat_id": self.__telegram_chat_id, "photo": image, "caption": "【" + title + "】\n" + text}
                sc_url = "https://api.telegram.org/bot%s/sendPhoto?" % self.__telegram_token
            else:
                # 发送文本
                values = {"chat_id": self.__telegram_chat_id, "text": title + "\n\n" + text}
                sc_url = "https://api.telegram.org/bot%s/sendMessage?" % self.__telegram_token

            res = requests.get(sc_url + urlencode(values))
            if res:
                ret_json = res.json()
                errno = ret_json['ok']
                if errno == 0:
                    return True, errno
                else:
                    return False, errno
            else:
                return False, "未获取到返回信息"
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
    Telegram().send_telegram_msg(in_title, in_text)
