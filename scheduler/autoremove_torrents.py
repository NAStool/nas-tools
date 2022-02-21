# 定时在DSM中执行命令清理qbittorrent的种子
from datetime import datetime

import log
from config import get_config
from message.send import sendmsg
from rmt.qbittorrent import login_qbittorrent
from rmt.transmission import login_transmission


def run_autoremovetorrents():
    try:
        config = get_config()
        pt_client = config['pt']['pt_client']
        seeding_time = config['pt']['pt_seeding_time']
        if pt_client == "qbittorrent":
            qb_removetorrents(seeding_time)
        elif pt_client == "transmission":
            tr_removetorrents(seeding_time)
    except Exception as err:
        log.error("【RUN】执行任务autoremovetorrents出错：" + str(err))
        sendmsg("【NASTOOL】执行任务autoremovetorrents出错！", str(err))


def qb_removetorrents(seeding_time):
    log.info("【REMOVETORRENTS】开始执行qBittorrent做种清理...")
    qbc = login_qbittorrent()
    if not qbc:
        log.error("【REMOVETORRENTS】连接qbittorrent失败！")
        return
    torrents = qbc.torrents_info()
    for torrent in torrents:
        log.debug("【REMOVETORRENTS】" + torrent.name + " ：" + torrent.state + " : " + str(torrent.seeding_time))
        # 只有标记为强制上传的才会清理（经过RMT处理的都是强制上传状态）
        if torrent.state == "forcedUP":
            if int(torrent.seeding_time) > int(seeding_time):
                log.info("【REMOVETORRENTS】" + torrent.name + "做种时间：" + str(torrent.seeding_time) + "（秒），已达清理条件，进行清理...")
                # 同步删除文件
                qbc.torrents_delete(delete_files=True, torrent_hashes=torrent.hash)
    qbc.auth_log_out()


def tr_removetorrents(seeding_time):
    log.info("【REMOVETORRENTS】开始执行transmission做种清理...")
    trc = login_transmission()
    if not trc:
        log.error("【REMOVETORRENTS】连接transmission失败！")
        return
    torrents = trc.get_torrents()
    for torrent in torrents:
        log.debug("【REMOVETORRENTS】" + torrent.name + " ：" + torrent.status + " : " + str(torrent.date_done))
        date_done = torrent.date_done
        date_now = datetime.now().astimezone()
        # 只有标记为强制上传的才会清理（经过RMT处理的都是强制上传状态）
        if torrent.status == "seeding" or torrent.status == "seed_pending":
            if (date_now - date_done).seconds > int(seeding_time):
                log.info("【REMOVETORRENTS】" + torrent.name + "做种时间：" + str(torrent.seeding_time) + "（秒），已达清理条件，进行清理...")
                # 同步删除文件
                trc.remove_torrent(delete_data=True, idds=torrent.id)


if __name__ == "__main__":
    run_autoremovetorrents()
