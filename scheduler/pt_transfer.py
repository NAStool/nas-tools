# 定时转移所有qbittorrent中下载完成的种子
import log
from config import get_config
from message.send import sendmsg
from rmt.qbittorrent import transfer_qbittorrent_task
from rmt.transmission import transfer_transmission_task

RUNING_FLAG = False


def run_pttransfer():
    try:
        global RUNING_FLAG
        if RUNING_FLAG:
            log.error("【RUN】pt_transfer任务正在执行中...")
        else:
            RUNING_FLAG = True
            config = get_config()
            pt_client = config['pt']['pt_client']
            if pt_client == "qbittorrent":
                qb_transfer()
            elif pt_client == "transmission":
                tr_transfer()
            RUNING_FLAG = False
    except Exception as err:
        RUNING_FLAG = False
        log.error("【RUN】执行任务pt_transfer出错：" + str(err))
        sendmsg("【NASTOOL】执行任务pt_transfer出错！", str(err))


def qb_transfer():
    log.info("【QB-TRANSFER】qb_transfer开始...")
    transfer_qbittorrent_task()
    log.info("【QB-TRANSFER】qb_transfer结束...")


def tr_transfer():
    log.info("【TR-TRANSFER】tr_transfer开始...")
    transfer_transmission_task()
    log.info("【TR-TRANSFER】tr_transfer结束...")


if __name__ == "__main__":
    run_pttransfer()
