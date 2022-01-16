# 定时进行什么值得买签到
import re

import requests

import log
import settings
from message.send import sendmsg


def run_smzdmsignin():
    try:
        smzdmsignin()
    except Exception as err:
        log.error("【RUN】执行任务smzdmsignin出错：" + str(err))
        sendmsg("【NASTOOL】执行任务smzdmsignin出错！", str(err))


class SmzdmBot(object):
    def __init__(self):
        self.session = requests.Session()
        # 添加 headers
        self.session.headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Host': 'zhiyou.smzdm.com',
            'Referer': 'https://www.smzdm.com/',
            'Sec-Fetch-Dest': 'script',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36',
        }

    def load_cookie_str(self, cookie):
        """
        起一个什么值得买的，带cookie的session
        cookie 为浏览器复制来的字符串
        :param cookie: 登录过的社区网站 cookie
        """
        self.session.headers['Cookie'] = cookie

    def checkin(self):
        """
        签到函数
        """
        url = 'https://zhiyou.smzdm.com/user/checkin/jsonp_checkin'
        msg = self.session.get(url)
        return msg.json()


def smzdmsignin():
    sb = SmzdmBot()
    # sb.load_cookie_str(config.TEST_COOKIE)
    cookies = settings.get("smzdm.smzdm_cookie")
    try:
        sb.load_cookie_str(cookies)
        res = sb.checkin()
        log.info("【SMZDM-SIGN】登录返回结果：" + str(res))
        if res:
            data = res['data']
            err_code = res['error_code']
            if err_code == 0:
                slogan = re.sub(r'[a-zA-Z=_<>\"/]+', '', str(data['slogan'])).strip()
                send_msg = "签到次数：" + str(data['checkin_num']) \
                           + "\n\n积分：" + str(data['point']) \
                           + "\n\n经验：" + str(data['exp']) \
                           + "\n\n金币：" + str(data['gold']) \
                           + "\n\n" + slogan
            else:
                send_msg = "错误代码：" + str(err_code) \
                           + "\n\n错误信息：" + str(res['error_msg'])
        else:
            send_msg = "解析数据错误！"
        sendmsg(title='【SMZDM】每日签到', text=send_msg)
    except Exception as err:
        log.error("【SMZDM-SIGN】登录失败：" + str(err))
        sendmsg(title='【SMZDM】每日签到', text="登录失败：" + str(err))


if __name__ == "__main__":
    run_smzdmsignin()
