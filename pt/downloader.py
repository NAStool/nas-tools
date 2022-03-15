import log
from config import get_config
from message.send import Message
from pt.qbittorrent import Qbittorrent
from pt.transmission import Transmission
from datetime import datetime

from utils.types import MediaType


class Downloader:
    qbittorrent = None
    transmission = None
    __pt_client = None
    __seeding_time = None
    media = None
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
            self.__seeding_time = config['pt'].get('pt_seeding_time')

    # 添加下载任务
    def add_pt_torrent(self, url, mtype=MediaType.MOVIE):
        ret = None
        if self.__pt_client == "qbittorrent":
            if self.qbittorrent:
                try:
                    ret = self.qbittorrent.add_qbittorrent_torrent(url, mtype)
                    if ret and ret.find("Ok") != -1:
                        log.info("【PT】添加qBittorrent任务：%s" % url)
                except Exception as e:
                    log.error("【PT】添加qBittorrent任务出错：" + str(e))
        elif self.__pt_client == "transmission":
            if self.transmission:
                try:
                    ret = self.transmission.add_transmission_torrent(url, mtype)
                    if ret:
                        log.info("【PT】添加transmission任务：%s" % url)
                except Exception as e:
                    log.error("【PT】添加transmission任务出错：" + str(e))
        return ret

    # 转移PT下载文人年
    def pt_transfer(self):
        if not self.__pt_client:
            return
        if self.__pt_client == "qbittorrent":
            log.info("【PT】qb_transfer开始...")
            if self.qbittorrent:
                self.qbittorrent.transfer_qbittorrent_task()
            log.info("【PT】qb_transfer结束...")
        elif self.__pt_client == "transmission":
            log.info("【PT】tr_transfer开始...")
            if self.transmission:
                self.transmission.transfer_transmission_task()
            log.info("【PT】tr_transfer结束...")

    # 做种清理
    def pt_removetorrents(self):
        if self.__pt_client == "qbittorrent":
            if not self.qbittorrent:
                return
            log.info("【PT】开始执行qBittorrent做种清理...")
            torrents = self.qbittorrent.get_qbittorrent_torrents()
            for torrent in torrents:
                log.debug("【PT】" + torrent.name + " ：" + torrent.state + " : " + str(torrent.seeding_time))
                # 只有标记为强制上传的才会清理（经过RMT处理的都是强制上传状态）
                if torrent.state == "forcedUP":
                    if int(torrent.seeding_time) > int(self.__seeding_time):
                        log.info("【PT】" + torrent.name + "做种时间：" + str(torrent.seeding_time) +
                                 "（秒），已达清理条件，进行清理...")
                        # 同步删除文件
                        self.qbittorrent.delete_qbittorrent_torrents(True, torrent.hash)
            log.info("【PT】qBittorrent做种清理完成！")

        elif self.__pt_client == "transmission":
            if not self.transmission:
                return
            log.info("【PT】开始执行transmission做种清理...")
            torrents = self.transmission.get_transmission_torrents()
            for torrent in torrents:
                log.debug("【PT】%s ：%s : %s" % (torrent.name, torrent.status, str(torrent.date_done)))
                date_done = torrent.date_done
                date_now = datetime.now().astimezone()
                # 只有标记为强制上传的才会清理（经过RMT处理的都是强制上传状态）
                if date_done and (torrent.status == "seeding" or torrent.status == "seed_pending"):
                    if (date_now - date_done).seconds > int(self.__seeding_time):
                        log.info("【PT】%s 做种时间：%s（秒），已达清理条件，进行清理..." % (torrent.name, torrent.seeding_time))
                        # 同步删除文件
                        self.transmission.delete_transmission_torrents(delete_file=True, ids=torrent.id)
            log.info("【PT】transmission做种清理完成！")
