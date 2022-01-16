# 定时转移所有qbittorrent中下载完成的种子
import log
from message.send import sendmsg
from rmt.qbittorrent import transfer_qbittorrent_task

RUNING_FLAG = False


def run_qbtransfer():
    try:
        global RUNING_FLAG
        if RUNING_FLAG:
            log.error("【RUN】qbtransfer任务正在执行中...")
        else:
            RUNING_FLAG = True
            qbtransfer()
            RUNING_FLAG = False
    except Exception as err:
        RUNING_FLAG = False
        log.error("【RUN】执行任务qbtransfer出错：" + str(err))
        sendmsg("【NASTOOL】执行任务qbtransfer出错！", str(err))


def qbtransfer():
    log.info("【QB-TRANSFER】qb_transfer开始...")
    transfer_qbittorrent_task()
    log.info("【QB-TRANSFER】qb_transfer结束...")


if __name__ == "__main__":
    run_qbtransfer()
