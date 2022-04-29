from threading import Lock
import log
from pt.rss import Rss

lock = Lock()


class RSSDownloader:
    rss = None

    def __init__(self):
        self.rss = Rss()

    def run_schedule(self):
        try:
            lock.acquire()
            self.rss.rssdownload()
        except Exception as err:
            log.error("【RUN】执行任务rssdownload出错：%s" % str(err))
        finally:
            lock.release()
