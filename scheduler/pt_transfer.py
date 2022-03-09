# 定时转移所有qbittorrent中下载完成的种子
import log
from message.send import Message
from pt.downloader import Downloader

PT_TRANS_RUNNING_FLAG = False


class PTTransfer:
    __pt_client = None
    message = None
    downloader = None

    def __init__(self):
        self.message = Message()
        self.downloader = Downloader()

    def run_schedule(self):
        global PT_TRANS_RUNNING_FLAG
        try:
            if PT_TRANS_RUNNING_FLAG:
                log.warn("【RUN】pt_transfer任务正在执行中...")
            else:
                if self.downloader:
                    PT_TRANS_RUNNING_FLAG = True
                    self.downloader.pt_transfer()
                    PT_TRANS_RUNNING_FLAG = False
        except Exception as err:
            PT_TRANS_RUNNING_FLAG = False
            log.error("【RUN】执行任务pt_transfer出错：%s" % str(err))


if __name__ == "__main__":
    PTTransfer().run_schedule()
