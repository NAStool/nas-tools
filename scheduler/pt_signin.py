# 定时进行PT签到
import re
import requests

import log
import settings
from functions import cookieParse, generateHeader
from message.send import sendmsg


def run_ptsignin():
    try:
        ptsignin()
    except Exception as err:
        log.error("【RUN】执行任务ptsignin出错：" + str(err))
        sendmsg("【NASTOOL】执行任务ptsignin出错！", str(err))


def signin(name, url, cookie):
    try:
        cookie_obj = cookieParse(cookie)
        header = generateHeader(url)
        # 设置请求头 、 cookie
        session = requests.session()
        session.headers.update(header)
        session.cookies.update(cookie_obj)

        with session.get(url) as res:
            if name == "mteam":
                r = re.search(r"魔力值（當前([\d,\.]+)）", res.text, re.IGNORECASE)
            elif name == "pthome":
                r = re.search(r": ([\d,\.]+)&nbsp;\(签到已得[\d]+\)", res.text, re.IGNORECASE)
            else:
                r = re.search(r"魔力值（当前([\d,\.]+)）", res.text, re.IGNORECASE)

        tip = r.group(1)
    except Exception as err:
        return name + "签到出错：" + str(err)

    return name + " 当前魔力值：" + tip


def ptsignin():
    pt_tasks = eval(settings.get("pt-signin.pt_tasks"))
    msg_str = "未配置任何PT站信息！"
    for pt_task in pt_tasks:
        log.info("【PT-SIGN】开始PT签到：" + pt_task)
        pt_url = settings.get("pt-signin." + pt_task + "_url")
        pt_cooke = settings.get("pt-signin." + pt_task + "_cookie")
        if not pt_url or not pt_cooke:
            log.error("【PT-SIGN】未配置" + str(pt_task) + "Url或Cookie，无法签到！")
            return
        log.debug("cookie: " + pt_cooke)
        log.debug("url: " + pt_url)
        res = signin(pt_task, pt_url, pt_cooke)
        if msg_str == "":
            msg_str = res
        else:
            msg_str = res + "\n" + msg_str
        log.debug(res)
    sendmsg("【PT-SIGN】每日签到", msg_str)


if __name__ == "__main__":
    run_ptsignin()
