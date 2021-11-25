import sys

import log
from message.serverchan import send_serverchan_msg
from message.telegram import send_telegram_msg
from message.wechat import send_wechat_msg
import settings


def sendmsg(title, text=""):
    msg_channel = settings.get("webhook.msg_channel")
    log.info("【MSG】发送" + msg_channel + "消息：title=" + title + "，text=" + text)
    if msg_channel == "wechat":
        return send_wechat_msg(title, text)
    elif msg_channel == "serverchan":
        return send_serverchan_msg(title, text)
    else:
        return send_telegram_msg(title, text)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        in_title = sys.argv[1]
    else:
        in_title = "标题"
    if len(sys.argv) > 2:
        in_text = sys.argv[2]
    else:
        in_text = "内容"
    sendmsg(in_title, in_text)
