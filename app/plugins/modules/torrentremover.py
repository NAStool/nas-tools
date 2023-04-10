import os

from app.downloader import Downloader
from app.helper import DbHelper, IyuuHelper
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils.types import EventType
from config import Config


class TorrentRemover(_IPluginModule):
    # 插件名称
    module_name = "删除下载任务"
    # 插件描述
    module_desc = "历史记录中源文件被删除时，同步删除下载器中的下载任务。"
    # 插件图标
    module_icon = "torrentremover.png"
    # 主题色
    module_color = "#F44336"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "torrentremover_"
    # 加载顺序
    module_order = 9
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    dbhelper = None
    _enable = False

    def __init__(self):
        self._ua = Config().get_ua()

    def init_config(self, config: dict = None):
        self.dbhelper = DbHelper()
        if config:
            self._enable = config.get("enable")

    def get_state(self):
        return self._enable

    @staticmethod
    def get_fields():
        return [
            # 同一板块
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '下载任务联动删除',
                            'required': "",
                            'tooltip': '在历史记录中选择删除源文件时联动删除下载器中的下载任务；只有NAStool添加的且被正确识别了的任务才会被联动删除，辅种任务、非默认使用的下载器的任务等可通过建立自动删种任务等方式处理',
                            'type': 'switch',
                            'id': 'enable',
                        }
                    ]
                ]
            }
        ]

    def stop_service(self):
        pass

    @EventHandler.register(EventType.SourceFileDeleted)
    def deletetorrent(self, event):
        """
        联动删除下载器中的下载任务
        """
        if not self._enable:
            return
        event_info = event.event_data
        if not event_info:
            return
        # 删除下载记录
        DownloaderHandler = Downloader()
        source_path = event_info.get("path")
        source_filename = event_info.get("filename")
        media_title = event_info.get("media_info", {}).get("title")
        source_file = os.path.join(source_path, source_filename)
        # 同一标题的所有下载任务
        downloadinfos = self.dbhelper.get_download_history_by_title(title=media_title) or []
        for info in downloadinfos:
            if not info.DOWNLOADER or not info.DOWNLOAD_ID:
                continue
            # 删除标志
            delete_flag = False
            dl_files = DownloaderHandler.get_files(tid=info.DOWNLOAD_ID,
                                                   downloader_id=info.DOWNLOADER)
            if not dl_files:
                continue
            for dl_file in dl_files:
                dl_file_name = dl_file.get("name")
                if os.path.normpath(source_file).endswith(os.path.normpath(dl_file_name)):
                    delete_flag = True
                    break
            if delete_flag:
                download = info.DOWNLOADER
                download_id = info.DOWNLOAD_ID

                # 查询是否有自动转移做种记录
                torrent_transfer = self.dbhelper.get_torrent_transfer_history(from_download=download,
                                                                              from_download_id=download_id)
                # 如果有转种则删除转种后的种子任务
                if torrent_transfer:
                    download = torrent_transfer.TO_DOWNLOAD
                    download_id = torrent_transfer.TO_DOWNLOAD_ID
                    if not bool(torrent_transfer.DELETE_SOURCE):
                        # 转种后未删除源种时，同步删除源种
                        self.info(f"删除下载任务：{info.DOWNLOADER} - {info.DOWNLOAD_ID}")
                        DownloaderHandler.delete_torrents(downloader_id=info.DOWNLOADER,
                                                          ids=info.DOWNLOAD_ID)
                self.info(f"删除下载任务：{download} - {download_id}")
                DownloaderHandler.delete_torrents(downloader_id=download,
                                                  ids=download_id)
                # 处理辅种
                auto_seed_config = self.get_config(plugin_id="IYUUAutoSeed")
                # 只处理开启了转种任务且填写iyuu token的情况
                if auto_seed_config and auto_seed_config.get('enable') and auto_seed_config.get('token'):
                    # 查询可辅种数据
                    seed_list, msg = IyuuHelper(token=auto_seed_config.get('token')).get_seed_info([download_id])
                    if isinstance(seed_list, dict):
                        # 遍历
                        for current_hash, seed_info in seed_list.items():
                            if not seed_info:
                                continue
                            seed_torrents = seed_info.get("torrent")
                            if not isinstance(seed_torrents, list):
                                seed_torrents = [seed_torrents]
                            for seed in seed_torrents:
                                if not seed:
                                    continue
                                if not isinstance(seed, dict):
                                    continue
                                if not seed.get("sid") or not seed.get("info_hash"):
                                    continue
                                download_id = seed.get("info_hash")
                                # 查询hash值是否已经在目的下载器中
                                torrent_info = DownloaderHandler.get_torrents(downloader_id=download,
                                                                              ids=download_id)
                                # 删除辅种
                                if torrent_info:
                                    self.info(f"删除辅种：{download} - {download_id}")
                                    DownloaderHandler.delete_torrents(downloader_id=download,
                                                                      ids=download_id)