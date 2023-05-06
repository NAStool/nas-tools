import os

from app.downloader import Downloader
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils.types import EventType
from config import Config


class TorrentRemover(_IPluginModule):
    # 插件名称
    module_name = "下载任务联动删除"
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
    downloader = None
    _enable = False

    def __init__(self):
        self._ua = Config().get_ua()

    def init_config(self, config: dict = None):
        self.downloader = Downloader()
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
                            'tooltip': '在历史记录中选择删除源文件时联动删除下载器中的下载任务；只有NAStool添加的且被正确识别了的任务以及转种、辅种插件处理的任务才会被联动删除，其他工具辅种任务、非默认使用的下载器的任务等可通过建立自动删种任务等方式处理',
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
        source_path = event_info.get("path")
        source_filename = event_info.get("filename")
        media_title = event_info.get("media_info", {}).get("title")
        source_file = os.path.join(source_path, source_filename)
        # 同一标题的所有下载任务
        downloadinfos = Downloader().get_download_history_by_title(title=media_title)
        for info in downloadinfos:
            if not info.DOWNLOADER or not info.DOWNLOAD_ID:
                continue
            # 删除下载任务
            self.__del_torrent(source_file=source_file,
                               from_download=info.DOWNLOADER,
                               from_download_id=info.DOWNLOAD_ID)

    def __del_torrent(self, source_file, from_download, from_download_id):
        """
        删除下载任务
        """
        download = from_download
        download_id = from_download_id

        # 查询是否有转种记录
        history_key = "%s-%s" % (download, download_id)
        plugin_id = "TorrentTransfer"
        transfer_history = self.get_history(key=history_key,
                                            plugin_id=plugin_id)
        self.info(f"查询到 {history_key} 转种历史 {transfer_history}")

        del_history = False
        # 如果有转种记录，则删除转种后的下载任务
        if transfer_history and isinstance(transfer_history, dict):
            download = transfer_history['to_download']
            download_id = transfer_history['to_download_id']
            delete_source = transfer_history['delete_source']
            del_history = True

            # 转种后未删除源种时，同步删除源种
            if not delete_source:
                self.info(f"{history_key} 转种时未删除源下载任务，开始删除源下载任务…")
                # 删除标志
                delete_flag = False
                try:
                    dl_files = self.downloader.get_files(tid=from_download_id,
                                                         downloader_id=from_download)
                    if not dl_files:
                        return
                    for dl_file in dl_files:
                        dl_file_name = dl_file.get("name")
                        if os.path.normpath(source_file).endswith(os.path.normpath(dl_file_name)):
                            delete_flag = True
                            break
                    if delete_flag:
                        self.info(f"删除下载任务：{from_download} - {from_download_id}")
                        self.downloader.delete_torrents(downloader_id=from_download,
                                                        ids=from_download_id)
                except Exception as e:
                    self.error(f"删除源下载任务 {history_key} 失败: {str(e)}")

        # 删除标志
        delete_flag = False
        self.info(f"开始删除下载任务 {download} {download_id}")
        try:
            dl_files = self.downloader.get_files(tid=download_id,
                                                 downloader_id=download)
            if not dl_files:
                return
            for dl_file in dl_files:
                dl_file_name = dl_file.get("name")
                if os.path.normpath(source_file).endswith(os.path.normpath(dl_file_name)):
                    delete_flag = True
                    break
            if delete_flag:
                # 删除源下载任务或转种后下载任务
                self.info(f"删除下载任务：{download} - {download_id}")
                self.downloader.delete_torrents(downloader_id=download,
                                                ids=download_id)

                # 删除转种记录
                if del_history:
                    self.delete_history(key=history_key, plugin_id=plugin_id)

                # 处理辅种
                self.__del_seed(download=download, download_id=download_id)
        except Exception as e:
            self.error(f"删除转种辅种下载任务失败: {str(e)}")

    def __del_seed(self, download, download_id):
        """
        删除辅种
        """
        # 查询是否有辅种记录
        history_key = download_id
        plugin_id = "IYUUAutoSeed"
        seed_history = self.get_history(key=history_key,
                                        plugin_id=plugin_id) or []
        self.info(f"查询到 {history_key} 辅种历史 {seed_history}")

        # 有辅种记录则处理辅种
        if seed_history and isinstance(seed_history, list):
            for history in seed_history:
                downloader = history['downloader']
                torrents = history['torrents']
                if not downloader or not torrents:
                    return
                if not isinstance(torrents, list):
                    torrents = [torrents]

                # 删除辅种历史中与本下载器相同的辅种记录
                if int(downloader) == download:
                    for torrent in torrents:
                        # 删除辅种
                        self.info(f"删除辅种：{downloader} - {torrent}")
                        self.downloader.delete_torrents(downloader_id=downloader,
                                                        ids=torrent)
                    # 删除本下载器辅种历史
                    del history
                    break

            # 更新辅种历史
            if len(seed_history) > 0:
                self.update_history(key=history_key,
                                    value=seed_history,
                                    plugin_id=plugin_id)
            else:
                self.delete_history(key=history_key,
                                    plugin_id=plugin_id)
