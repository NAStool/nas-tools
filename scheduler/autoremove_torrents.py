# 定时在DSM中执行命令清理qbittorrent的种子
from datetime import datetime

import log
from config import get_config
from message.send import Message
from pt.qbittorrent import Qbittorrent
from pt.transmission import Transmission


class AutoRemoveTorrents:
    qbittorrent = None
    transmission = None
    __pt_client = None
    __seeding_time = None
    message = None

    def __init__(self):
        self.message = Message()
        config = get_config()
        if config.get('pt'):
            self.__pt_client = config['pt'].get('pt_client')
            self.__seeding_time = config['pt'].get('pt_seeding_time')
            if self.__pt_client == "qbittorrent":
                self.qbittorrent = Qbittorrent()
            elif self.__pt_client == "transmission":
                self.transmission = Transmission()

    def run_schedule(self):
        try:
            if self.__pt_client == "qbittorrent":
                self.qb_removetorrents(self.__seeding_time)
            elif self.__pt_client == "transmission":
                self.tr_removetorrents(self.__seeding_time)
        except Exception as err:
            log.error("【RUN】执行任务autoremovetorrents出错：%s" % str(err))

    def qb_removetorrents(self, seeding_time):
        if not self.qbittorrent:
            return
        log.info("【REMOVETORRENTS】开始执行qBittorrent做种清理...")
        torrents = self.qbittorrent.get_qbittorrent_torrents()
        for torrent in torrents:
            log.debug("【REMOVETORRENTS】" + torrent.name + " ：" + torrent.state + " : " + str(torrent.seeding_time))
            # 只有标记为强制上传的才会清理（经过RMT处理的都是强制上传状态）
            if torrent.state == "forcedUP":
                if int(torrent.seeding_time) > int(seeding_time):
                    log.info("【REMOVETORRENTS】" + torrent.name + "做种时间：" + str(torrent.seeding_time) +
                             "（秒），已达清理条件，进行清理...")
                    # 同步删除文件
                    self.qbittorrent.delete_qbittorrent_torrents(True, torrent.hash)

    def tr_removetorrents(self, seeding_time):
        if not self.transmission:
            return
        log.info("【REMOVETORRENTS】开始执行transmission做种清理...")
        torrents = self.transmission.get_transmission_torrents()
        for torrent in torrents:
            log.debug("【REMOVETORRENTS】%s ：%s : %s" % (torrent.name, torrent.status, str(torrent.date_done)))
            date_done = torrent.date_done
            date_now = datetime.now().astimezone()
            # 只有标记为强制上传的才会清理（经过RMT处理的都是强制上传状态）
            if date_done and (torrent.status == "seeding" or torrent.status == "seed_pending"):
                if (date_now - date_done).seconds > int(seeding_time):
                    log.info("【REMOVETORRENTS】%s 做种时间：%s（秒），已达清理条件，进行清理..." % (torrent.name, torrent.seeding_time))
                    # 同步删除文件
                    self.transmission.delete_transmission_torrents(delete_file=True, ids=torrent.id)


if __name__ == "__main__":
    AutoRemoveTorrents().run_schedule()
