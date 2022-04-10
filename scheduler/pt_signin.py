from threading import Lock

import log
from pt.signin import SignIn

lock = Lock()


class PTSignin:
    signin = None

    def __init__(self):
        self.signin = SignIn()

    def run_schedule(self):
        try:
            lock.acquire()
            if self.signin:
                self.signin.signin()
        except Exception as err:
            log.error("【RUN】执行任务pt_signin出错：%s" % str(err))
        finally:
            lock.release()
