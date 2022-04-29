from threading import Lock
from urllib.parse import urlencode
import requests

import log
from config import Config
from utils.functions import singleton

lock = Lock()
WEBHOOK_STATUS = False


@singleton
class Telegram:
    __telegram_token = None
    __telegram_chat_id = None
    __webhook_url = None
    __domain = None
    __config = None

    def __init__(self):
        self.init_config()
        self.set_bot_webhook()

    def init_config(self):
        self.__config = Config()
        app = self.__config.get_config('app')
        if app:
            self.__domain = app.get('domain')
            if self.__domain:
                if not self.__domain.startswith('http://') and not self.__domain.startswith('https://'):
                    self.__domain = "http://" + self.__domain
                if not self.__domain.endswith('/'):
                    self.__domain = self.__domain + "/"
        message = self.__config.get_config('message')
        if message:
            self.__telegram_token = message.get('telegram', {}).get('telegram_token')
            self.__telegram_chat_id = message.get('telegram', {}).get('telegram_chat_id')
            if self.__telegram_token \
                    and self.__telegram_chat_id \
                    and message.get('telegram', {}).get('webhook') \
                    and self.__domain:
                self.__webhook_url = "%stelegram" % self.__domain

    def get_admin_user(self):
        return str(self.__telegram_chat_id)

    def send_telegram_msg(self, title, text="", image="", url="", user_id=""):
        if not title and not text:
            return -1, "标题和内容不能同时为空"
        try:
            if not self.__telegram_token or not self.__telegram_chat_id:
                return False, "参数未配置"

            if text:
                caption = "<b>%s</b>\n%s" % (title, text.replace("\n\n", "\n"))
            else:
                caption = title
            if image and url:
                caption = "%s\n\n<a href='%s'>查看详情</a>" % (caption, url)
            if user_id:
                chat_id = user_id
            else:
                chat_id = self.__telegram_chat_id
            if image:
                # 发送图文消息
                values = {"chat_id": chat_id, "photo": image, "caption": caption, "parse_mode": "HTML"}
                sc_url = "https://api.telegram.org/bot%s/sendPhoto?" % self.__telegram_token
            else:
                # 发送文本
                values = {"chat_id": chat_id, "text": caption, "parse_mode": "HTML"}
                sc_url = "https://api.telegram.org/bot%s/sendMessage?" % self.__telegram_token

            res = requests.get(sc_url + urlencode(values), timeout=10, proxies=self.__config.get_proxies())
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

    def set_bot_webhook(self):
        if not self.__webhook_url:
            return

        try:
            lock.acquire()
            global WEBHOOK_STATUS
            if not WEBHOOK_STATUS:
                WEBHOOK_STATUS = True
            else:
                return
        finally:
            lock.release()

        status = self.get_bot_webhook()
        if status and status != 1:
            if status == 2:
                self.del_bot_webhook()
            values = {"url": self.__webhook_url, "allowed_updates": ["message"]}
            sc_url = "https://api.telegram.org/bot%s/setWebhook?" % self.__telegram_token
            res = requests.get(sc_url + urlencode(values), timeout=10, proxies=self.__config.get_proxies())
            if res:
                json = res.json()
                if json.get("ok"):
                    log.console("TelegramBot Webhook 设置成功，地址为：%s" % self.__webhook_url)
                else:
                    log.console("TelegramBot Webhook 设置失败：" % json.get("description"))
            else:
                log.console("TelegramBot Webhook 设置失败：网络连接故障！")

    # 1-存在且相等，2-存在不相等，3-不存在，0-网络出错
    def get_bot_webhook(self):
        sc_url = "https://api.telegram.org/bot%s/getWebhookInfo" % self.__telegram_token
        res = requests.get(sc_url, timeout=10, proxies=self.__config.get_proxies())
        if res and res.json():
            if res.json().get("ok"):
                webhook_url = res.json().get("result", {}).get("url") or ""
                if webhook_url:
                    log.console("TelegramBot Webhook 地址为：%s" % webhook_url)
                if webhook_url == self.__webhook_url:
                    return 1
                else:
                    return 2
            else:
                return 3
        else:
            return 0

    def del_bot_webhook(self):
        sc_url = "https://api.telegram.org/bot%s/deleteWebhook" % self.__telegram_token
        res = requests.get(sc_url, timeout=10, proxies=self.__config.get_proxies())
        if res and res.json() and res.json().get("ok"):
            return True
        else:
            return False
