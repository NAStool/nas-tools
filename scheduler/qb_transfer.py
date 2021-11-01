# 定时转移所有qbittorrent中下载完成的种子
import log
from rmt.qbittorrent import transfer_qbittorrent_task

logger = log.Logger("scheduler").logger


def run_qbtransfer():
    logger.info("【QB-TRANSFER】qb_transfer开始...")
    transfer_qbittorrent_task()
    logger.info("【QB-TRANSFER】qb_transfer结束...")


if __name__ == "__main__":
    run_qbtransfer()
