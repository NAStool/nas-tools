# 定时转移所有qbittorrent中下载完成的种子
import threading

import log
from message.send import Message
from pt.downloader import Downloader

lock = threading.Lock()


class PTTransfer:
    __pt_client = None
    message = None
    downloader = None

    def __init__(self):
        self.message = Message()
        self.downloader = Downloader()

    def run_schedule(self):
        try:
            lock.acquire()
            if self.downloader:
                self.downloader.pt_transfer()
        except Exception as err:
            log.error("【RUN】执行任务pt_transfer出错：%s" % str(err))
        finally:
            lock.release()


if __name__ == "__main__":
    PTTransfer().run_schedule()
