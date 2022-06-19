from abc import ABCMeta, abstractmethod


class IDownloadClient(metaclass=ABCMeta):

    @abstractmethod
    def get_status(self):
        """
        检查连通性
        """
        pass

    @abstractmethod
    def get_torrents(self, ids, status, tag):
        """
        按条件读取种子信息
        """
        pass

    @abstractmethod
    def get_downloading_torrents(self, tag):
        """
        读取下载中的种子信息
        """
        pass

    @abstractmethod
    def set_torrents_status(self, ids):
        """
        迁移完成后设置种子标签为 已整理
        """
        pass

    @abstractmethod
    def get_transfer_task(self, tag):
        """
        获取需要转移的种子列表
        """
        pass

    @abstractmethod
    def get_remove_torrents(self, seeding_time, tag):
        """
        获取需要清理的种子清单
        """
        pass

    @abstractmethod
    def add_torrent(self, content, mtype, is_paused, tag):
        """
        添加下载任务
        """
        pass

    @abstractmethod
    def start_torrents(self, ids):
        """
        下载控制：开始
        """
        pass

    @abstractmethod
    def stop_torrents(self, ids):
        """
        下载控制：停止
        """
        pass

    @abstractmethod
    def delete_torrents(self, delete_file, ids):
        """
        删除种子
        """
        pass

    @abstractmethod
    def get_pt_data(self):
        """
        获取PT下载软件中当前上传和下载量
        """
        pass
