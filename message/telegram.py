from urllib.parse import urlencode
import requests

from config import Config


class Telegram:
    __telegram_token = None
    __telegram_chat_id = None
    config = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.config = Config()
        message = self.config.get_config('message')
        if message:
            self.__telegram_token = message.get('telegram', {}).get('telegram_token')
            self.__telegram_chat_id = message.get('telegram', {}).get('telegram_chat_id')

    def send_telegram_msg(self, title, text="", image="", url=""):
        if not title and not text:
            return -1, "标题和内容不能同时为空"
        try:
            if not self.__telegram_token or not self.__telegram_chat_id:
                return False, "参数未配置"

            if text:
                caption = "<strong>%s</strong>\n%s" % (title, text.replace("\n\n", "\n"))
            else:
                caption = title
            if url:
                caption = "%s\n\n<a href='%s'>查看详情</a>" % (caption, url)
            if image:
                # 发送图文消息
                values = {"chat_id": self.__telegram_chat_id, "photo": image, "caption": caption, "parse_mode": "HTML"}
                sc_url = "https://api.telegram.org/bot%s/sendPhoto?" % self.__telegram_token
            else:
                # 发送文本
                values = {"chat_id": self.__telegram_chat_id, "text": caption, "parse_mode": "HTML"}
                sc_url = "https://api.telegram.org/bot%s/sendMessage?" % self.__telegram_token

            res = requests.get(sc_url + urlencode(values), timeout=10, proxies=self.config.get_proxies())
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
