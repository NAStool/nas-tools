from abc import ABCMeta, abstractmethod


class IDownloadClient(metaclass=ABCMeta):
    user_config = None
    host = None
    port = None
    username = None
    password = None
    save_path = None
    save_containerpath = None
    tv_save_path = None
    tv_save_containerpath = None
    tv_category = None
    movie_save_path = None
    movie_save_containerpath = None
    movie_category = None
    anime_save_path = None
    anime_save_containerpath = None
    anime_category = None

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
            self.movie_save_path = self.tv_save_path = self.anime_save_path = self.user_config.get("save_dir")
        else:
            if self.save_path:
                if isinstance(self.save_path, str):
                    self.tv_save_path = self.save_path
                    self.movie_save_path = self.save_path
                    self.anime_save_path = self.save_path
                else:
                    if self.save_path.get('tv'):
                        tv_save_path = self.save_path.get('tv').split("|")
                        self.tv_save_path = tv_save_path[0]
                        if len(tv_save_path) > 1:
                            self.tv_category = tv_save_path[1]
                    if self.save_path.get('movie'):
                        movie_save_path = self.save_path.get('movie').split("|")
                        self.movie_save_path = movie_save_path[0]
                        if len(movie_save_path) > 1:
                            self.movie_category = movie_save_path[1]
                    if self.save_path.get('anime'):
                        anime_save_path = self.save_path.get('anime').split("|")
                        self.anime_save_path = anime_save_path[0]
                        if len(anime_save_path) > 1:
                            self.anime_category = anime_save_path[1]
                    if not self.anime_save_path:
                        self.anime_save_path = self.tv_save_path
                        self.anime_category = self.tv_category
            if self.save_containerpath:
                if isinstance(self.save_containerpath, str):
                    self.tv_save_containerpath = self.save_containerpath
                    self.movie_save_containerpath = self.save_containerpath
                    self.anime_save_containerpath = self.save_containerpath
                else:
                    self.tv_save_containerpath = self.save_containerpath.get('tv')
                    self.movie_save_containerpath = self.save_containerpath.get('movie')
                    self.anime_save_containerpath = self.save_containerpath.get('anime')
                    # 没有配置anime目录则使用tv目录
                    if not self.anime_save_containerpath:
                        self.anime_save_containerpath = self.tv_save_containerpath

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
    def get_completed_torrents(self, tag):
        """
        读取下载完成的种子信息
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

    def get_replace_path(self, true_path):
        """
        对目录路径进行转换
        """
        if self.tv_save_containerpath and true_path.startswith(self.tv_save_path):
            true_path = true_path.replace(str(self.tv_save_path), str(self.tv_save_containerpath))
        if self.movie_save_containerpath and true_path.startswith(self.movie_save_path):
            true_path = true_path.replace(str(self.movie_save_path), str(self.movie_save_containerpath))
        if self.anime_save_containerpath and true_path.startswith(self.anime_save_path):
            true_path = true_path.replace(str(self.anime_save_path), str(self.anime_save_containerpath))
        return true_path
