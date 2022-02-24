import sys

import log
from config import get_config
from message.serverchan import send_serverchan_msg
from message.telegram import send_telegram_msg
from message.wechat import send_wechat_msg


def sendmsg(title, text="", image=""):
    config = get_config()
    if not config.get('message'):
        return None
    msg_channel = config['message'].get('msg_channel')
    if not msg_channel:
        return None
    log.info("【MSG】发送" + msg_channel + "消息：title=" + title + "，text=" + text)
    if msg_channel == "wechat":
        return send_wechat_msg(title, text, image)
    elif msg_channel == "serverchan":
        return send_serverchan_msg(title, text)
    elif msg_channel == "telegram":
        return send_telegram_msg(title, text, image)
    else:
        return None


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
