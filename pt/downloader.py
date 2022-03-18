import log
from config import get_config
from message.send import Message
from pt.client.qbittorrent import Qbittorrent
from pt.client.transmission import Transmission

from utils.types import MediaType, DownloaderType


class Downloader:
    client = None
    __client_type = None
    __seeding_time = None
    media = None
    message = None

    def __init__(self):
        self.message = Message()
        config = get_config()
        if config.get('pt'):
            pt_client = config['pt'].get('pt_client')
            if pt_client == "qbittorrent":
                self.client = Qbittorrent()
                self.__client_type = DownloaderType.QB
            elif pt_client == "transmission":
                self.client = Transmission()
                self.__client_type = DownloaderType.TR
            self.__seeding_time = config['pt'].get('pt_seeding_time')

    # 添加下载任务
    def add_pt_torrent(self, url, mtype=MediaType.MOVIE):
        ret = None
        if self.client:
            try:
                ret = self.client.add_torrent(url, mtype)
                if ret and ret.find("Ok") != -1:
                    log.info("【PT】添加PT任务：%s" % url)
            except Exception as e:
                log.error("【PT】添加PT任务出错：" + str(e))
        return ret

    # 转移PT下载文人年
    def pt_transfer(self):
        if self.client:
            return self.client.transfer_task()

    # 做种清理
    def pt_removetorrents(self):
        if not self.client:
            return False
        return self.client.remove_torrents(self.__seeding_time)

    # 获取种子列表信息
    def get_pt_torrents(self, torrent_ids=None, status_filter=None):
        if not self.client:
            return None, []
        return self.__client_type, self.client.get_torrents(ids=torrent_ids, status=status_filter)

    # 下载控制：开始
    def start_torrents(self, ids):
        if not self.client:
            return False
        return self.client.start_torrents(ids)

    # 下载控制：停止
    def stop_torrents(self, ids):
        if not self.client:
            return False
        return self.client.stop_torrents(ids)

    # 下载控制：删除
    def delete_torrents(self, ids):
        if not self.client:
            return False
        return self.client.delete_torrents(delete_file=True, ids=ids)
