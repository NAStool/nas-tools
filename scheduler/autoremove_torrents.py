from threading import Lock

import log
from pt.downloader import Downloader
from utils.functions import singleton

lock = Lock()


@singleton
class AutoRemoveTorrents:
    downloader = None

    def __init__(self):
        self.downloader = Downloader()

    def run_schedule(self):
        try:
            lock.acquire()
            if self.downloader:
                self.downloader.pt_removetorrents()
        except Exception as err:
            log.error("【RUN】执行任务autoremovetorrents出错：%s" % str(err))
        finally:
            lock.release()
