# 定时转移所有qbittorrent中下载完成的种子
import log
from message.send import Message
from pt.downloader import Downloader


class PTTransfer:
    __running_flag = False
    __pt_client = None
    message = None
    downloader = None

    def __init__(self):
        self.message = Message()
        self.downloader = Downloader()

    def run_schedule(self):
        try:
            if self.__running_flag:
                log.warn("【RUN】pt_transfer任务正在执行中...")
            else:
                if self.downloader:
                    self.__running_flag = True
                    self.downloader.pt_transfer()
                    self.__running_flag = False
        except Exception as err:
            self.__running_flag = False
            log.error("【RUN】执行任务pt_transfer出错：%s" % str(err))


if __name__ == "__main__":
    PTTransfer().run_schedule()
