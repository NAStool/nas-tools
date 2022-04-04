from threading import Lock

import requests
import log
from config import Config
from utils.functions import cookieParse, generateHeader, singleton
from message.send import Message

lock = Lock()


@singleton
class PTSignin:
    __pt_sites = None
    message = None

    def __init__(self):
        self.message = Message()
        self.init_config()

    def init_config(self):
        config = Config()
        pt = config.get_config('pt')
        if pt:
            self.__pt_sites = pt.get('sites')

    def run_schedule(self):
        try:
            lock.acquire()
            self.__ptsignin()
        except Exception as err:
            log.error("【RUN】执行任务ptsignin出错：%s" % str(err))
        finally:
            lock.release()

    @staticmethod
    def __signin(name, url, cookie):
        try:
            cookie_obj = cookieParse(cookie)
            header = generateHeader(url)
            # 设置请求头 、 cookie
            session = requests.session()
            session.headers.update(header)
            session.cookies.update(cookie_obj)
            res = session.get(url)
            if res:
                return "%s 签到成功" % name
        except Exception as err:
            return "%s 签到出错：%s" % (name, str(err))

    def __ptsignin(self):
        msg_str = ""
        if self.__pt_sites:
            for pt_task, task_info in self.__pt_sites.items():
                try:
                    log.info("【PT】开始PT签到：%s" % pt_task)
                    pt_url = task_info.get('signin_url')
                    pt_cooke = task_info.get('cookie')
                    if not pt_url or not pt_cooke:
                        log.error("【PT】未配置 %s 的Url或Cookie，无法签到！" % str(pt_task))
                        continue
                    log.debug("cookie: %s" % pt_cooke)
                    log.debug("url: %s" % pt_url)
                    res = self.__signin(pt_task, pt_url, pt_cooke)
                    if not msg_str:
                        msg_str = res
                    else:
                        msg_str = "%s\n%s" % (res, msg_str)
                except Exception as e:
                    log.error("【PT】%s 签到出错：%s" % (pt_task, str(e)))
        if msg_str == "":
            msg_str = "未配置任何有效PT站签到信息"
        self.message.sendmsg("【PT】每日签到", msg_str)
