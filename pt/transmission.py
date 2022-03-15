import os.path
import transmission_rpc
import urllib3
import log
from config import get_config
from rmt.filetransfer import FileTransfer
from utils.types import DownloaderType, MediaType

urllib3.disable_warnings()


class Transmission:
    __trhost = None
    __trport = None
    __trusername = None
    __trpassword = None
    __tv_save_path = None
    __tv_save_containerpath = None
    __movie_save_path = None
    __movie_save_containerpath = None
    trc = None
    filetransfer = None

    def __init__(self):
        config = get_config()
        if config.get('transmission'):
            self.filetransfer = FileTransfer()
            self.__trhost = config['transmission'].get('trhost')
            self.__trport = config['transmission'].get('trport')
            self.__trusername = config['transmission'].get('trusername')
            self.__trpassword = config['transmission'].get('trpassword')
            # 解释下载目录
            save_path = config['transmission'].get('save_path')
            if save_path:
                if isinstance(save_path, str):
                    self.__tv_save_path = save_path
                    self.__movie_save_path = save_path
                else:
                    self.__tv_save_path = save_path.get('tv')
                    self.__movie_save_path = save_path.get('movie')
            save_containerpath = config['transmission'].get('save_containerpath')
            if save_containerpath:
                if isinstance(save_containerpath, str):
                    self.__tv_save_containerpath = save_containerpath
                    self.__movie_save_containerpath = save_containerpath
                else:
                    self.__tv_save_containerpath = save_containerpath.get('tv')
                    self.__movie_save_containerpath = save_containerpath.get('movie')
            if self.__trhost and self.__trport:
                self.trc = self.__login_transmission()

    # 连接transmission
    def __login_transmission(self):
        try:
            # 登录
            trt = transmission_rpc.Client(host=self.__trhost,
                                          port=self.__trport,
                                          username=self.__trusername,
                                          password=self.__trpassword,
                                          timeout=10)
            return trt
        except Exception as err:
            log.error("【TR】transmission连接出错：%s" % str(err))
            return None

    # 读取所有种子信息
    def get_transmission_torrents(self):
        # 读取transmission列表
        if not self.trc:
            return []
        torrents = self.trc.get_torrents()
        return torrents

    # 迁移完成后设置种子状态
    def set_tr_torrent_status(self, id_str):
        if not self.trc:
            return
        # 打标签
        self.trc.change_torrent(labels=["已整理"], ids=id_str)
        log.info("【TR】设置transmission种子标签成功！")

    # 处理transmission中的种子
    def transfer_transmission_task(self):
        # 处理所有任务
        torrents = self.get_transmission_torrents()
        for torrent in torrents:
            log.debug("【TR】" + torrent.get('name') + "：" + torrent.get('status'))
            # 3.0版本以下的Transmission没有labels
            handlered_flag = False
            labels = torrent.get('labels')
            if not isinstance(labels, list):
                log.warn("【TR】当前transmission版本可能过低，请安装3.0以上版本！")
            if labels and "已整理" in labels:
                handlered_flag = True
            if (torrent.get('status') == "seeding" or torrent.get('status') == "seed_pending") and not handlered_flag:
                # 查找根目录
                true_path = os.path.join(torrent.get('download_dir'), torrent.get('name'))
                if not true_path:
                    continue
                if self.__tv_save_containerpath:
                    true_path = true_path.replace(str(self.__tv_save_path), str(self.__tv_save_containerpath))
                if self.__movie_save_containerpath:
                    true_path = true_path.replace(str(self.__movie_save_path), str(self.__movie_save_containerpath))
                ret = self.filetransfer.transfer_media(in_from=DownloaderType.TR, in_path=true_path)
                if ret:
                    self.set_tr_torrent_status(torrent.get('id'))
                else:
                    log.error("【TR】%s 转移失败：" % torrent.get('name'))

    def add_transmission_torrent(self, turl, mtype):
        if mtype == MediaType.TV:
            return self.trc.add_torrent(torrent=turl, download_dir=self.__tv_save_path)
        else:
            return self.trc.add_torrent(torrent=turl, download_dir=self.__movie_save_path)

    def delete_transmission_torrents(self, delete_file, ids):
        if not self.trc:
            return False
        return self.trc.remove_torrent(delete_data=delete_file, ids=ids)
