import os
import qbittorrentapi
import log
from config import Config
from utils.functions import singleton
from utils.types import MediaType


@singleton
class Qbittorrent:
    __qbhost = None
    __qbport = None
    __qbusername = None
    __qbpassword = None
    __force_upload = False
    __tv_save_path = None
    __tv_save_containerpath = None
    __tv_category = None
    __movie_save_path = None
    __movie_save_containerpath = None
    __movie_category = None
    __anime_save_path = None
    __anime_save_containerpath = None
    __anime_category = None
    qbc = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        qbittorrent = config.get_config('qbittorrent')
        if qbittorrent:
            self.__qbhost = qbittorrent.get('qbhost')
            self.__qbport = int(qbittorrent.get('qbport'))
            self.__qbusername = qbittorrent.get('qbusername')
            self.__qbpassword = qbittorrent.get('qbpassword')
            # 强制做种开关
            self.__force_upload = qbittorrent.get('force_upload')
            # 解释下载目录
            save_path = qbittorrent.get('save_path')
            if save_path:
                if isinstance(save_path, str):
                    self.__tv_save_path = save_path
                    self.__movie_save_path = save_path
                    self.__anime_save_path = save_path
                else:
                    if save_path.get('tv'):
                        tv_save_path = save_path.get('tv').split("|")
                        self.__tv_save_path = tv_save_path[0]
                        if len(tv_save_path) > 1:
                            self.__tv_category = tv_save_path[1]
                    if save_path.get('movie'):
                        movie_save_path = save_path.get('movie').split("|")
                        self.__movie_save_path = movie_save_path[0]
                        if len(movie_save_path) > 1:
                            self.__movie_category = movie_save_path[1]
                    if save_path.get('anime'):
                        anime_save_path = save_path.get('anime').split("|")
                        self.__anime_save_path = anime_save_path[0]
                        if len(anime_save_path) > 1:
                            self.__anime_category = anime_save_path[1]
                    if not self.__anime_save_path:
                        self.__anime_save_path = self.__tv_save_path
                        self.__anime_category = self.__tv_category
            save_containerpath = qbittorrent.get('save_containerpath')
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

    # 按条件读取种子信息
    def get_torrents(self, ids=None, status=None):
        if not self.qbc:
            return []
        self.qbc.auth_log_in()
        torrents = self.qbc.torrents_info(torrent_hashes=ids, status_filter=status)
        self.qbc.auth_log_out()
        if not status:
            return torrents
        else:
            if not isinstance(status, list):
                status = [status]
            ret_torrents = []
            for torrent in torrents:
                if torrent.get("state") in status:
                    ret_torrents.append(torrent)
            return ret_torrents

    # 读取完成的种子信息
    def get_completed_torrents(self):
        if not self.qbc:
            return []
        return self.get_torrents(status=["forcedUP", "stalledUP", "queuedUP", "pausedUP", "uploading"])

    # 读取下载中的种子信息
    def get_downloading_torrents(self):
        if not self.qbc:
            return []
        return self.get_torrents(status=["downloading", "forcedDL", "stalledDL", "queuedDL", "pausedDL"])

    # 迁移完成后设置种子状态
    def set_torrents_status(self, ids):
        if not self.qbc:
            return
        self.qbc.auth_log_in()
        # 打标签
        self.qbc.torrents_add_tags(tags="已整理", torrent_hashes=ids)
        # 超级做种
        if self.__force_upload:
            self.qbc.torrents_set_force_start(enable=True, torrent_hashes=ids)
        log.info("【QB】设置qBittorrent种子状态成功")
        self.qbc.auth_log_out()

    # 处理qbittorrent中的种子
    def get_transfer_task(self):
        # 处理下载完成的任务
        torrents = self.get_completed_torrents()
        trans_tasks = []
        for torrent in torrents:
            # 判断标签是否包含已整理
            if torrent.get("tags") and "已整理" in torrent.get("tags"):
                continue
            true_path = torrent.get('content_path', os.path.join(torrent.get('save_path'), torrent.get('name')))
            if not true_path:
                continue
            if self.__tv_save_containerpath and true_path.startswith(self.__tv_save_path):
                true_path = true_path.replace(str(self.__tv_save_path), str(self.__tv_save_containerpath))
            if self.__movie_save_containerpath and true_path.startswith(self.__movie_save_path):
                true_path = true_path.replace(str(self.__movie_save_path), str(self.__movie_save_containerpath))
            if self.__anime_save_containerpath and true_path.startswith(self.__anime_save_path):
                true_path = true_path.replace(str(self.__anime_save_path), str(self.__anime_save_containerpath))
            trans_tasks.append({'path': true_path, 'id': torrent.get('hash')})
        return trans_tasks

    # 做种清理
    def get_remove_torrents(self, seeding_time):
        torrents = self.get_completed_torrents()
        remove_torrents = []
        for torrent in torrents:
            if int(torrent.get('seeding_time')) > int(seeding_time):
                log.info("【PT】%s 做种时间：%s（秒），已达清理条件，进行清理..." % (torrent.get('name'), torrent.get('seeding_time')))
                remove_torrents.append(torrent.get('hash'))
        return remove_torrents

    # 添加qbittorrent任务
    def add_torrent(self, turl, mtype):
        if not self.qbc:
            return False
        self.qbc.auth_log_in()
        if mtype == MediaType.TV:
            qbc_ret = self.qbc.torrents_add(urls=turl, save_path=self.__tv_save_path, category=self.__tv_category)
        elif mtype == MediaType.MOVIE:
            qbc_ret = self.qbc.torrents_add(urls=turl, save_path=self.__movie_save_path, category=self.__movie_category)
        else:
            qbc_ret = self.qbc.torrents_add(urls=turl, save_path=self.__anime_save_path, category=self.__anime_category)
        self.qbc.auth_log_out()
        return qbc_ret

    # 下载控制：开始
    def start_torrents(self, ids):
        if not self.qbc:
            return False
        return self.qbc.torrents_resume(torrent_hashes=ids)

    # 下载控制：停止
    def stop_torrents(self, ids):
        if not self.qbc:
            return False
        return self.qbc.torrents_pause(torrent_hashes=ids)

    # 删除种子
    def delete_torrents(self, delete_file, ids):
        if not self.qbc:
            return False
        self.qbc.auth_log_in()
        ret = self.qbc.torrents_delete(delete_files=delete_file, torrent_hashes=ids)
        self.qbc.auth_log_out()
        return ret
