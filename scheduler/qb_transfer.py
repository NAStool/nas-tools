# 定时转移所有qbittorrent中下载完成的种子
import log
from message.send import sendmsg
from rmt.qbittorrent import transfer_qbittorrent_task


def run_qbtransfer():
    try:
        qbtransfer()
    except Exception as err:
        log.error("【RUN】执行定时任务qbtransfer出错：" + str(err))
        sendmsg("【NASTOOL】执行定时任务qbtransfer出错！", str(err))


def qbtransfer():
    log.info("【QB-TRANSFER】qb_transfer开始...")
    transfer_qbittorrent_task()
    log.info("【QB-TRANSFER】qb_transfer结束...")


if __name__ == "__main__":
    run_qbtransfer()
