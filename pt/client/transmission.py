import os.path
import transmission_rpc
from datetime import datetime
import log
from config import Config
from utils.functions import singleton
from utils.types import MediaType


@singleton
class Transmission:
    __trhost = None
    __trport = None
    __trusername = None
    __trpassword = None
    __tv_save_path = None
    __tv_save_containerpath = None
    __movie_save_path = None
    __movie_save_containerpath = None
    __anime_save_path = None
    __anime_save_containerpath = None
    trc = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        transmission = config.get_config('transmission')
        if transmission:
            self.__trhost = transmission.get('trhost')
            self.__trport = int(transmission.get('trport'))
            self.__trusername = transmission.get('trusername')
            self.__trpassword = transmission.get('trpassword')
            # 解释下载目录
            save_path = transmission.get('save_path')
            if save_path:
                if isinstance(save_path, str):
                    self.__tv_save_path = save_path
                    self.__movie_save_path = save_path
                    self.__anime_save_path = save_path
                else:
                    self.__tv_save_path = save_path.get('tv')
                    self.__movie_save_path = save_path.get('movie')
                    self.__anime_save_path = save_path.get('anime')
                    if not self.__anime_save_path:
                        self.__anime_save_path = self.__tv_save_path
            save_containerpath = transmission.get('save_containerpath')
            if save_containerpath:
                if isinstance(save_containerpath, str):
                    self.__tv_save_containerpath = save_containerpath
                    self.__movie_save_containerpath = save_containerpath
                    self.__anime_save_containerpath = save_containerpath
                else:
                    self.__tv_save_containerpath = save_containerpath.get('tv')
                    self.__movie_save_containerpath = save_containerpath.get('movie')
                    self.__anime_save_containerpath = save_containerpath.get('anime')
                    # 没有配置anime目录则使用tv目录
                    if not self.__anime_save_containerpath:
                        self.__anime_save_containerpath = self.__tv_save_containerpath
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

    # 按条件读取种子信息
    def get_torrents(self, ids=None, status=None):
        if not self.trc:
            return []
        if isinstance(ids, list):
            ids = [int(x) for x in ids]
        elif ids:
            ids = int(ids)
        torrents = self.trc.get_torrents(ids=ids)
        if not status:
            return torrents
        else:
            if not isinstance(status, list):
                status = [status]
            ret_torrents = []
            for torrent in torrents:
                if torrent.status in status:
                    ret_torrents.append(torrent)
            return ret_torrents

    # 读取完成的种子信息
    def get_completed_torrents(self):
        if not self.trc:
            return []
        return self.get_torrents(status=["seeding", "seed_pending"])

    # 读取下载中的种子信息
    def get_downloading_torrents(self):
        if not self.trc:
            return []
        return self.get_torrents(status=["downloading", "download_pending", "stopped"])

    # 迁移完成后设置种子状态
    def set_torrents_status(self, ids):
        if not self.trc:
            return
        if isinstance(ids, list):
            ids = [int(x) for x in ids]
        elif ids:
            ids = int(ids)
        # 打标签
        self.trc.change_torrent(labels=["已整理"], ids=ids)
        log.info("【TR】设置transmission种子标签成功")

    # 处理transmission中的种子
    def get_transfer_task(self):
        # 处理所有任务
        torrents = self.get_completed_torrents()
        trans_tasks = []
        for torrent in torrents:
            try:
                # 3.0版本以下的Transmission没有labels
                labels = torrent.labels
            except Exception as e:
                log.warn("【TR】当前transmission版本可能过低，请安装3.0以上版本！错误：%s" % str(e))
                break
            if labels and "已整理" in labels:
                continue
            true_path = os.path.join(torrent.download_dir, torrent.name)
            if not true_path:
                continue
            if self.__tv_save_containerpath and true_path.startswith(self.__tv_save_path):
                true_path = true_path.replace(str(self.__tv_save_path), str(self.__tv_save_containerpath))
            if self.__movie_save_containerpath and true_path.startswith(self.__movie_save_path):
                true_path = true_path.replace(str(self.__movie_save_path), str(self.__movie_save_containerpath))
            if self.__anime_save_containerpath and true_path.startswith(self.__anime_save_path):
                true_path = true_path.replace(str(self.__anime_save_path), str(self.__anime_save_containerpath))
            trans_tasks.append({'path': true_path, 'id': torrent.id})
        return trans_tasks

    # 做种清理
    def get_remove_torrents(self, seeding_time):
        torrents = self.get_completed_torrents()
        remove_torrents = []
        for torrent in torrents:
            date_done = torrent.date_done
            date_now = datetime.now().astimezone()
            torrent_time = (date_now - date_done).seconds
            if torrent_time > int(seeding_time):
                log.info("【PT】%s 做种时间：%s（秒），已达清理条件，进行清理..." % (torrent.name, torrent_time))
                remove_torrents.append(torrent.id)
        return remove_torrents

    def add_torrent(self, turl, mtype):
        if mtype == MediaType.TV:
            return self.trc.add_torrent(torrent=turl, download_dir=self.__tv_save_path)
        elif mtype == MediaType.MOVIE:
            return self.trc.add_torrent(torrent=turl, download_dir=self.__movie_save_path)
        else:
            return self.trc.add_torrent(torrent=turl, download_dir=self.__anime_save_path)

    # 下载控制：开始
    def start_torrents(self, ids):
        if not self.trc:
            return False
        if isinstance(ids, list):
            ids = [int(x) for x in ids]
        elif ids:
            ids = int(ids)
        return self.trc.start_torrent(ids=ids)

    # 下载控制：停止
    def stop_torrents(self, ids):
        if not self.trc:
            return False
        if isinstance(ids, list):
            ids = [int(x) for x in ids]
        elif ids:
            ids = int(ids)
        return self.trc.stop_torrent(ids=ids)

    def delete_torrents(self, delete_file, ids):
        if not self.trc:
            return False
        if isinstance(ids, list):
            ids = [int(x) for x in ids]
        elif ids:
            ids = int(ids)
        return self.trc.remove_torrent(delete_data=delete_file, ids=ids)
