# 定时转移所有qbittorrent中下载完成的种子
import log
from config import get_config
from message.send import Message
from pt.qbittorrent import Qbittorrent
from pt.transmission import Transmission


class PTTransfer:
    __running_flag = False
    __pt_client = None

    qbittorrent = None
    transmission = None
    message = None

    def __init__(self):
        self.message = Message()
        config = get_config()
        if config.get('pt'):
            self.__pt_client = config['pt'].get('pt_client')
            if self.__pt_client == "qbittorrent":
                self.qbittorrent = Qbittorrent()
            elif self.__pt_client == "transmission":
                self.transmission = Transmission()

    def run_schedule(self):
        try:
            if self.__running_flag:
                log.warn("【RUN】pt_transfer任务正在执行中...")
            else:
                if not self.__pt_client:
                    return
                if self.__pt_client == "qbittorrent":
                    self.__qb_transfer()
                elif self.__pt_client == "transmission":
                    self.__tr_transfer()
        except Exception as err:
            self.__running_flag = False
            log.error("【RUN】执行任务pt_transfer出错：%s" % str(err))
            self.message.sendmsg("【NASTOOL】执行任务pt_transfer出错！", str(err))

    def __qb_transfer(self):
        log.info("【QB-TRANSFER】qb_transfer开始...")
        self.__running_flag = True
        if self.qbittorrent:
            self.qbittorrent.transfer_qbittorrent_task()
        self.__running_flag = False
        log.info("【QB-TRANSFER】qb_transfer结束...")

    def __tr_transfer(self):
        log.info("【TR-TRANSFER】tr_transfer开始...")
        self.__running_flag = True
        if self.transmission:
            self.transmission.transfer_transmission_task()
        self.__running_flag = False
        log.info("【TR-TRANSFER】tr_transfer结束...")


if __name__ == "__main__":
    PTTransfer().run_schedule()
