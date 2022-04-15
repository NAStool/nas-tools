import log
from config import Config
from message.send import Message
from utils.http_utils import RequestUtils


class SignIn:
    __pt_sites = None
    __user_agent = None
    message = None

    def __init__(self):
        self.message = Message()
        self.init_config()

    def init_config(self):
        config = Config()
        pt = config.get_config('pt')
        if pt:
            self.__pt_sites = pt.get('sites')
            self.__user_agent = pt.get('user_agent')

    def signin(self):
        status = []
        if self.__pt_sites:
            for pt_task, task_info in self.__pt_sites.items():
                try:
                    log.info("【PT】开始PT签到：%s" % pt_task)
                    pt_url = task_info.get('signin_url')
                    pt_cookie = task_info.get('cookie')
                    if not pt_url or not pt_cookie:
                        log.warn("【PT】未配置 %s 的Url或Cookie，无法签到" % str(pt_task))
                        continue
                    res = RequestUtils(headers=self.__user_agent, cookies=pt_cookie).get_res(url=pt_url)
                    if res.status_code == 200:
                        status.append("%s 签到成功" % pt_task)
                    else:
                        status.append("%s 签到失败，状态码：%s" % (pt_task, res.status_code))
                except Exception as e:
                    log.error("【PT】%s 签到出错：%s" % (pt_task, str(e)))
        if not status:
            return
        else:
            msg_str = "\n".join(status)
        self.message.sendmsg(title="【PT】每日签到", text=msg_str)
