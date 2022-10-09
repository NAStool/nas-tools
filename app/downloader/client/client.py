import os.path
from abc import ABCMeta, abstractmethod

from config import Config


class IDownloadClient(metaclass=ABCMeta):
    user_config = None
    host = None
    port = None
    username = None
    password = None
    secret = None

    def __init__(self, user_config=None):
        if user_config:
            self.user_config = user_config
        self.init_config()

    def init_config(self):
        """
        检查连通性
        """
        self.get_config()
        self.set_user_config()
        self.connect()

    @abstractmethod
    def get_config(self):
        """
        获取配置
        """
        pass

    @abstractmethod
    def connect(self):
        """
        连接
        """
        pass

    def set_user_config(self):
        if self.user_config:
            # 使用输入配置
            self.host = self.user_config.get("host")
            self.port = self.user_config.get("port")
            self.username = self.user_config.get("username")
            self.password = self.user_config.get("password")

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
        :param ids: 种子ID，单个ID或者ID列表
        :param status: 种子状态过滤
        :param tag: 种子标签过滤
        :return: 种子信息列表
        """
        pass

    @abstractmethod
    def get_downloading_torrents(self, tag):
        """
        读取下载中的种子信息
        """
        pass

    @abstractmethod
    def get_completed_torrents(self, tag):
        """
        读取下载完成的种子信息
        """
        pass

    @abstractmethod
    def set_torrents_status(self, ids):
        """
        迁移完成后设置种子标签为 已整理
        :param ids: 种子ID列表
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
        :param seeding_time: 保种时间，单位秒
        :param tag: 种子标签
        :return: 种子ID列表
        """
        pass

    @abstractmethod
    def add_torrent(self, content, is_paused, tag, download_dir):
        """
        添加下载任务
        :param content: 种子数据或链接
        :param is_paused: 是否默认暂停，只有需要进行下一步控制时，才会添加种子时默认暂停
        :param tag: 下载时对种子的TAG标记
        :param download_dir: 指定下载目录
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
    def get_download_dirs(self):
        """
        获取下载目录清单
        """
        pass

    @staticmethod
    def get_replace_path(true_path):
        """
        对目录路径进行转换
        """
        if not true_path:
            return ""
        downloaddir = Config().get_config('downloaddir') or {}
        for path, attr in downloaddir.items():
            if not path or not attr.get("path"):
                continue
            if os.path.normpath(path) == os.path.normpath(true_path):
                return attr.get("path")
        return true_path
