# 定时进行PT签到
import re
import requests
import log
from config import get_config
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

        res = session.get(url)
        if res:
            return name + " 签到成功！"
    except Exception as err:
        return name + " 签到出错：" + str(err)


def ptsignin():
    config = get_config()
    sites = config['pt']['sites']
    msg_str = ""
    for pt_task, task_info in sites.items():
        log.info("【PT-SIGN】开始PT签到：" + pt_task)
        pt_url = task_info['signin_url']
        pt_cooke = task_info['cookie']
        if not pt_url or not pt_cooke:
            log.error("【PT-SIGN】未配置" + str(pt_task) + "Url或Cookie，无法签到！")
            continue
        log.debug("cookie: " + pt_cooke)
        log.debug("url: " + pt_url)
        res = signin(pt_task, pt_url, pt_cooke)
        if msg_str == "":
            msg_str = res
        else:
            msg_str = res + "\n" + msg_str
        log.debug(res)
    if msg_str == "":
        msg_str = "未配置任何有效PT签到信息！"
    sendmsg("【PT-SIGN】每日签到", msg_str)


if __name__ == "__main__":
    run_ptsignin()
