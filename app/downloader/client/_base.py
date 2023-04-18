import os.path
from abc import ABCMeta, abstractmethod

from app.utils import PathUtils


class _IDownloadClient(metaclass=ABCMeta):

    # 下载器ID
    client_id = ""
    # 下载器类型
    client_type = ""
    # 下载器名称
    client_name = ""

    @abstractmethod
    def match(self, ctype):
        """
        匹配实例
        """
        pass

    @abstractmethod
    def get_type(self):
        """
        获取下载器类型
        """
        pass

    @abstractmethod
    def connect(self):
        """
        连接
        """
        pass

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
        :return: 种子信息列表，是否发生错误
        """
        pass

    @abstractmethod
    def get_downloading_torrents(self, ids, tag):
        """
        读取下载中的种子信息，发生错误时需返回None
        """
        pass

    @abstractmethod
    def get_completed_torrents(self, ids, tag):
        """
        读取下载完成的种子信息，发生错误时需返回None
        """
        pass

    @abstractmethod
    def get_files(self, tid):
        """
        读取种子文件列表
        """
        pass

    @abstractmethod
    def set_torrents_status(self, ids, tags=None):
        """
        迁移完成后设置种子标签为 已整理
        :param ids: 种子ID列表
        :param tags: 种子标签列表
        """
        pass

    @abstractmethod
    def get_transfer_task(self, tag, match_path=None):
        """
        获取需要转移的种子列表
        """
        pass

    @abstractmethod
    def get_remove_torrents(self, config):
        """
        获取需要清理的种子清单
        :param config: 删种策略
        :return: 种子ID列表
        """
        pass

    @abstractmethod
    def add_torrent(self, **kwargs):
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
    def get_download_dirs(self):
        """
        获取下载目录清单
        """
        pass

    @staticmethod
    def get_replace_path(path, downloaddir) -> (str, bool):
        """
        对目录路径进行转换
        :param path: 需要转换的路径
        :param downloaddir: 下载目录清单
        :return: 转换后的路径, 是否进行转换
        """
        if not path or not downloaddir:
            return "", False
        path = os.path.normpath(path)
        for attr in downloaddir:
            save_path = attr.get("save_path")
            if not save_path:
                continue
            save_path = os.path.normpath(save_path)
            container_path = attr.get("container_path")
            # 没有访问目录，视为与下载保存目录相同
            if not container_path:
                container_path = save_path
            else:
                container_path = os.path.normpath(container_path)
            if PathUtils.is_path_in_path(save_path, path):
                return path.replace(save_path, container_path), True
        return path, False

    @abstractmethod
    def change_torrent(self, **kwargs):
        """
        修改种子状态
        """
        pass

    @abstractmethod
    def get_downloading_progress(self):
        """
        获取下载进度
        """
        pass

    @abstractmethod
    def set_speed_limit(self, **kwargs):
        """
        设置速度限制
        """
        pass

    @abstractmethod
    def recheck_torrents(self, ids):
        """
        下载控制：重新校验
        """
        pass
