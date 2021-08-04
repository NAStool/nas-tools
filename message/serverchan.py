import sys
from urllib.parse import urlencode
import requests
import settings
from functions import mysql_exec_sql


# 发送ServerChan消息
def send_serverchan_msg(text, desp=""):
    if not text and not desp:
        return -1, "标题和内容不能同时为空！"
    values = {"title": text, "desp": desp}
    try:
        sc_url = "https://sctapi.ftqq.com/" + settings.get('serverchan.sckey') + ".send?" + urlencode(values)
        res = requests.get(sc_url)
        if res:
            ret_json = res.json()
            errno = ret_json['code']
            error = ret_json['message']
            sql = "INSERT INTO message_log \
                        (TYPE, TITLE, TEXT, TIME, ERRCODE, ERRMSG) \
                        VALUES ('%s', '%s', '%s', now(), '%s', '%s')" % \
                  ("ServerChan", text, desp, errno, error)
            # 登记数据库
            mysql_exec_sql(sql)
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
