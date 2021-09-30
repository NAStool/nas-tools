# 定时在DSM中执行命令清理qbittorrent的种子
import log
import settings
from functions import system_exec_command, login_qbittorrent
from message.send import sendmsg

logger = log.Logger("scheduler").logger


def run_autoremovetorrents():
    seeding_time = settings.get("scheduler.autoremovetorrents_seeding_time")
    logger.info("开始执行qBittorrent做种清理...")
    qbc = login_qbittorrent()
    if not qbc:
        logger.error("连接qbittorrent失败！")
        return
    torrents = qbc.torrents_info()
    for torrent in torrents:
        logger.info(torrent.name + "：" + torrent.state)
        # 只有标记为强制上传的才会清理（经过RMT处理的都是强制上传状态）
        if torrent.state == "forcedUP":
            if torrent.seeding_time > seeding_time:
                logger.info(torrent.name + "做种时间：" + torrent.seeding_time + "（秒），已达清理条件，进行清理...")
                # 同步删除文件
                qbc.torrents_delete(delete_files=True, torrent_hashs=torrent.hash)
    qbc.auth_log_out()


if __name__ == "__main__":
    run_autoremovetorrents()
