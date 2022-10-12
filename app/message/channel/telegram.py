from threading import Event, Lock
from urllib.parse import urlencode
from app.helper.thread_helper import ThreadHelper
import requests

import log
from config import Config
from app.message.channel.channel import IMessageChannel
from app.utils.commons import singleton
from app.utils import RequestUtils

lock = Lock()
WEBHOOK_STATUS = False


@singleton
class Telegram(IMessageChannel):
    __telegram_token = None
    __telegram_chat_id = None
    __webhook_url = None
    __telegram_user_ids = []
    __domain = None
    __config = None
    __message_proxy_event = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.__config = Config()
        app = self.__config.get_config('app')
        if app:
            self.__domain = app.get('domain')
            if self.__domain:
                if not self.__domain.startswith('http'):
                    self.__domain = "http://" + self.__domain
                if not self.__domain.endswith('/'):
                    self.__domain = self.__domain + "/"
        message = self.__config.get_config('message')
        if message:
            self.__telegram_token = message.get('telegram', {}).get('telegram_token')
            self.__telegram_chat_id = message.get('telegram', {}).get('telegram_chat_id')
            telegram_user_ids = message.get('telegram', {}).get('telegram_user_ids')
            if telegram_user_ids:
                self.__telegram_user_ids = telegram_user_ids.split(",")
            else:
                self.__telegram_user_ids = []
            if self.__telegram_token \
                    and self.__telegram_chat_id:
                if message.get('telegram', {}).get('webhook'):
                    if self.__domain:
                        self.__webhook_url = "%stelegram" % self.__domain
                        self.__set_bot_webhook()
                    if self.__message_proxy_event:
                        self.__message_proxy_event.set()
                        self.__message_proxy_event = None
                else:
                    self.__del_bot_webhook()
                    if not self.__message_proxy_event:
                        event = Event()
                        self.__message_proxy_event = event
                        ThreadHelper().start_thread(self.__start_telegram_message_proxy, [event])

    def get_status(self):
        """
        测试连通性
        """
        flag, msg = self.send_msg("测试", "这是一条测试消息")
        if not flag:
            log.error("【Telegram】发送消息失败：%s" % msg)
        return flag

    def get_admin_user(self):
        """
        获取Telegram配置文件中的ChatId，即管理员用户ID
        """
        return str(self.__telegram_chat_id)

    def send_msg(self, title, text="", image="", url="", user_id=""):
        """
        发送Telegram消息
        :param title: 消息标题
        :param text: 消息内容
        :param image: 消息图片地址
        :param url: 点击消息转转的URL
        :param user_id: 用户ID，如有则只发消息给该用户
        :user_id: 发送消息的目标用户ID，为空则发给管理员
        """
        if not title and not text:
            return False, "标题和内容不能同时为空"
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
            return self.__send_request(sc_url, values)

        except Exception as msg_e:
            return False, str(msg_e)

    def send_list_msg(self, title, medias: list, user_id=""):
        """
        发送列表类消息
        """
        try:
            if not self.__telegram_token or not self.__telegram_chat_id:
                return False, "参数未配置"
            if not title or not isinstance(medias, list):
                return False, "数据错误"
            index, image, caption = 1, "", "<b>%s</b>" % title
            for media in medias:
                if not image:
                    image = media.get_message_image()
                caption = "%s\n%s. %s" % (caption, index, media.get_title_vote_string())
                index += 1

            if user_id:
                chat_id = user_id
            else:
                chat_id = self.__telegram_chat_id

            # 发送图文消息
            values = {"chat_id": chat_id, "photo": image, "caption": caption, "parse_mode": "HTML"}
            sc_url = "https://api.telegram.org/bot%s/sendPhoto?" % self.__telegram_token
            return self.__send_request(sc_url, values)

        except Exception as msg_e:
            return False, str(msg_e)

    def __send_request(self, sc_url, values):
        """
        向Telegram发送报文
        """
        res = RequestUtils(proxies=self.__config.get_proxies()).get_res(sc_url + urlencode(values))
        if res:
            ret_json = res.json()
            status = ret_json.get("ok")
            if status:
                return True, ""
            else:
                return False, ret_json.get("description")
        else:
            return False, "未获取到返回信息"

    def __set_bot_webhook(self):
        """
        设置Telegram Webhook
        """
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

        status = self.__get_bot_webhook()
        if status and status != 1:
            if status == 2:
                self.__del_bot_webhook()
            values = {"url": self.__webhook_url, "allowed_updates": ["message"]}
            sc_url = "https://api.telegram.org/bot%s/setWebhook?" % self.__telegram_token
            res = RequestUtils(proxies=self.__config.get_proxies()).get_res(sc_url + urlencode(values))
            if res:
                json = res.json()
                if json.get("ok"):
                    log.info("【Telegram】Webhook 设置成功，地址为：%s" % self.__webhook_url)
                else:
                    log.error("【Telegram】Webhook 设置失败：" % json.get("description"))
            else:
                log.error("【Telegram】Webhook 设置失败：网络连接故障！")

    def __get_bot_webhook(self):
        """
        获取Telegram已设置的Webhook
        :return: 状态：1-存在且相等，2-存在不相等，3-不存在，0-网络出错
        """
        sc_url = "https://api.telegram.org/bot%s/getWebhookInfo" % self.__telegram_token
        res = RequestUtils(proxies=self.__config.get_proxies()).get_res(sc_url)
        if res and res.json():
            if res.json().get("ok"):
                result = res.json().get("result") or {}
                webhook_url = result.get("url") or ""
                if webhook_url:
                    log.info("【Telegram】Webhook 地址为：%s" % webhook_url)
                pending_update_count = result.get("pending_update_count")
                last_error_message = result.get("last_error_message")
                if pending_update_count and last_error_message:
                    log.warn("【Telegram】Webhook 有 %s 条消息挂起，最后一次失败原因为：%s" % (pending_update_count, last_error_message))
                if webhook_url == self.__webhook_url:
                    return 1
                else:
                    return 2
            else:
                return 3
        else:
            return 0

    def __del_bot_webhook(self):
        """
        删除Telegram Webhook
        :return: 是否成功
        """
        sc_url = "https://api.telegram.org/bot%s/deleteWebhook" % self.__telegram_token
        res = RequestUtils(proxies=self.__config.get_proxies()).get_res(sc_url)
        if res and res.json() and res.json().get("ok"):
            return True
        else:
            return False

    def get_users(self):
        """
        获取Telegram配置文件中的User Ids，即允许使用telegram机器人的user_id列表
        """
        return self.__telegram_user_ids

    @staticmethod
    def __start_telegram_message_proxy(event: Event):
        log.info("【Telegram】消息接收服务启动")

        long_poll_timeout = 5

        def consume_messages(_config, _offset, _sc_url, _ds_url):
            try:
                values = {"timeout": long_poll_timeout, "offset": _offset}
                res = RequestUtils(proxies=_config.get_proxies()).get_res(_sc_url + urlencode(values))
                if res and res.json():
                    for msg in res.json().get("result", []):
                        # 无论本地是否成功，先更新offset，即消息最多成功消费一次
                        _offset = msg["update_id"] + 1
                        log.info("【Telegram】接收到消息: %s" % msg)
                        local_res = requests.post(_ds_url, json=msg, timeout=10)
                        log.debug("【Telegram】message: %s processed, response is: %s" % (msg, local_res.text))
            except Exception as e:
                log.error("【Telegram】消息接收出现错误: %s" % e)
            return _offset

        offset = 0
        while True:
            # read config from config.yaml directly to make config.yaml changes aware 
            config = Config()
            message = config.get_config("message")
            channel = message.get("msg_channel")
            telegram_token = message.get('telegram', {}).get('telegram_token')
            web_port = config.get_config("app").get("web_port")
            sc_url = "https://api.telegram.org/bot%s/getUpdates?" % telegram_token
            ds_url = "http://127.0.0.1:%s/telegram" % web_port
            telegram_webhook = message.get('telegram', {}).get('webhook')
            if not channel == "telegram" or not telegram_token or telegram_webhook:
                log.info("【Telegram】消息接收服务已停止")
                break

            i = 0
            while i < 20 and not event.is_set():
                offset = consume_messages(config, offset, sc_url, ds_url)
                i = i + 1
