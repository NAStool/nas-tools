# 发送telegram消息
import sys
from urllib.parse import urlencode

import requests
import settings
from functions import mysql_exec_sql


def send_telegram_msg(title, text=""):
    if not title and not text:
        return -1, "标题和内容不能同时为空！"
    try:
        values = {"chat_id": settings.get("telegram.telegram_bot_id"), "text": title + "\n\n" + text}
        sc_url = "https://api.telegram.org/bot%s/sendMessage?" % settings.get("telegram.telegram_token")
        res = requests.get(sc_url + urlencode(values))
        if res:
            ret_json = res.json()
            errno = ret_json['ok']
            sql = "INSERT INTO message_log \
                        (TYPE, TITLE, TEXT, TIME, ERRCODE, ERRMSG) \
                        VALUES ('%s', '%s', '%s', now(), '%s', '%s')" % \
                  ("telegram", title, text, errno, '')
            # 登记数据库
            mysql_exec_sql(sql)
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
