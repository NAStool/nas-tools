from threading import Lock

import log
from config import Config
from message.send import Message
from utils.http_utils import RequestUtils
from utils.sqls import get_config_site

lock = Lock()


class PTSignin:
    __pt_sites = None
    __user_agent = None
    message = None

    def __init__(self):
        self.message = Message()
        self.init_config()

    def init_config(self):
        config = Config()
        app = config.get_config('app')
        pt = config.get_config('pt')
        if pt:
            self.__pt_sites = get_config_site()
            self.__user_agent = app.get('user_agent')

    def run_schedule(self):
        """
        运行PT站签到定时服务
        """
        try:
            lock.acquire()
            self.__signin()
        except Exception as err:
            log.error("【RUN】执行任务pt_signin出错：%s" % str(err))
        finally:
            lock.release()

    def __signin(self):
        """
        PT站签到入口，由定时服务调用
        """
        status = []
        if self.__pt_sites:
            for site_info in self.__pt_sites:
                if not site_info:
                    continue
                pt_task = site_info[1]
                try:
                    pt_url = site_info[4]
                    pt_cookie = site_info[5]
                    log.info("【PT】开始PT签到：%s" % pt_task)
                    if not pt_url or not pt_cookie:
                        log.warn("【PT】未配置 %s 的Url或Cookie，无法签到" % str(pt_task))
                        continue
                    res = RequestUtils(headers=self.__user_agent, cookies=pt_cookie).get_res(url=pt_url)
                    if res and res.status_code == 200:
                        status.append("%s 签到成功" % pt_task)
                    elif not res:
                        status.append("%s 签到失败，无法打开网站" % pt_task)
                    else:
                        status.append("%s 签到失败，状态码：%s" % (pt_task, res.status_code))
                except Exception as e:
                    log.error("【PT】%s 签到出错：%s" % (pt_task, str(e)))
        if not status:
            return
        else:
            msg_str = "\n".join(status)
        self.message.sendmsg(title=msg_str)
