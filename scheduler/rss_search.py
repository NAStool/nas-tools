from threading import Lock

import log
from pt.rss import Rss

lock = Lock()


class RssSearch:
    rss = None

    def __init__(self):
        self.rss = Rss()

    def run_schedule(self):
        """
        运行RSS队列中资源检索定时服务
        """
        try:
            lock.acquire()
            self.rss.rsssearch()
        except Exception as err:
            log.error("【RUN】执行任务rss_search出错：%s" % str(err))
        finally:
            lock.release()
