import qbittorrentapi
import urllib3
import log
from config import get_config

# 全局设置
from rmt.media import Media

urllib3.disable_warnings()


class Qbittorrent:
    __qbhost = None
    __qbport = None
    __qbusername = None
    __qbpassword = None
    __save_path = None
    __save_containerpath = None
    qbc = None
    media = None

    def __init__(self):
        self.media = Media()
        config = get_config()
        if config.get('qbittorrent'):
            self.__qbhost = config['qbittorrent'].get('qbhost')
            self.__qbport = config['qbittorrent'].get('qbport')
            self.__qbusername = config['qbittorrent'].get('qbusername')
            self.__qbpassword = config['qbittorrent'].get('qbpassword')
            self.__save_path = config['qbittorrent'].get('save_path')
            self.__save_containerpath = config['qbittorrent'].get('save_containerpath')
            if self.__qbhost and self.__qbport:
                self.qbc = self.__login_qbittorrent()

    # 连接qbittorrent
    def __login_qbittorrent(self):
        try:
            # 登录
            qbt = qbittorrentapi.Client(host=self.__qbhost,
                                        port=self.__qbport,
                                        username=self.__qbusername,
                                        password=self.__qbpassword,
                                        VERIFY_WEBUI_CERTIFICATE=False)
            return qbt
        except Exception as err:
            log.error("【QB】qBittorrent连接出错：%s" % str(err))
            return None

    # 读取所有种子信息
    def get_qbittorrent_torrents(self):
        # 读取qBittorrent列表
        if not self.qbc:
            return []
        self.qbc.auth_log_in()
        torrents = self.qbc.torrents_info()
        self.qbc.auth_log_out()
        return torrents

    # 删除种子
    def delete_qbittorrent_torrents(self, delete_file, thash):
        if not self.qbc:
            return False
        self.qbc.auth_log_in()
        ret = self.qbc.torrents_delete(delete_file=delete_file, torrent_hashes=thash)
        self.qbc.auth_log_out()
        return ret

    # 迁移完成后设置种子状态
    def set_qb_torrent_status(self, hash_str):
        if not self.qbc:
            return
        self.qbc.auth_log_in()
        # 打标签
        self.qbc.torrents_add_tags("已整理", hash_str)
        # 超级做种
        self.qbc.torrents_set_force_start(True, hash_str)
        log.info("【QB】设置qBittorrent种类状态成功！")
        self.qbc.auth_log_out()

    # 处理qbittorrent中的种子
    def transfer_qbittorrent_task(self):
        # 处理所有任务
        torrents = self.get_qbittorrent_torrents()
        for torrent in torrents:
            log.debug("【QB】" + torrent.name + "：" + torrent.state)
            if torrent.state == "uploading" or torrent.state == "stalledUP":
                true_path = torrent.content_path
                if self.__save_containerpath:
                    true_path = true_path.replace(str(self.__save_path), str(self.__save_containerpath))
                done_flag = self.media.transfer_media(in_from="Qbittorrent", in_path=true_path)
                if done_flag:
                    self.set_qb_torrent_status(torrent.hash)
                else:
                    log.error("【QB】%s 转移失败！" % torrent.name)

    # 添加qbittorrent任务
    def add_qbittorrent_torrent(self, turl):
        if not self.qbc:
            return False
        self.qbc.auth_log_in()
        qbc_ret = self.qbc.torrents_add(turl, None, self.__save_path)
        self.qbc.auth_log_out()
        return qbc_ret
