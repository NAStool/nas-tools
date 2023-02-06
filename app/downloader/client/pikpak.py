import asyncio

from pikpakapi import PikPakApi, DownloadStatus

import log
from app.downloader.client._base import _IDownloadClient
from app.utils.types import DownloaderType
from config import Config


class PikPak(_IDownloadClient):
    schema = "pikpak"
    client_type = DownloaderType.PikPak.value
    _client_config = {}

    downclient = None
    lasthash = None

    def __init__(self, config=None):
        if config:
            self._client_config = config
        else:
            self._client_config = Config().get_config('pikpak')
        self.init_config()
        self.connect()

    def init_config(self):
        if self._client_config:
            self.downclient = PikPakApi(
                username=self._client_config.get("username"),
                password=self._client_config.get("password"),
                proxy=self._client_config.get("proxy"),
            )

    @classmethod
    def match(cls, ctype):
        return True if ctype in [cls.schema, cls.client_type] else False

    def connect(self):
        try:
            asyncio.run(self.downclient.login())
        except Exception as err:
            print(str(err))
            return

    def get_status(self):
        if not self.downclient:
            return False
        try:
            asyncio.run(self.downclient.login())
            if self.downclient.user_id is None:
                log.info("PikPak 登录失败")
                return False
        except Exception as err:
            log.error("PikPak 登录出错：%s" % str(err))
            return False

        return True

    def get_torrents(self, ids=None, status=None, **kwargs):
        rv = []
        if self.downclient.user_id is None:
            if self.get_status():
                return [], False

        if ids is not None:
            for id in ids:
                status = asyncio.run(self.downclient.get_task_status(id, ''))
                if status == DownloadStatus.downloading:
                    rv.append({"id": id, "finish": False})
                if status == DownloadStatus.done:
                    rv.append({"id": id, "finish": True})
        return rv, True

    def get_completed_torrents(self, **kwargs):
        return []

    def get_downloading_torrents(self, **kwargs):
        if self.downclient.user_id is None:
            if self.get_status():
                return []
        try:
            offline_list = asyncio.run(self.downclient.offline_list())
            return offline_list['tasks']
        except Exception as err:
            print(str(err))
            return []

    def get_transfer_task(self, **kwargs):
        pass

    def get_remove_torrents(self, **kwargs):
        return []

    def add_torrent(self, content, download_dir=None, **kwargs):
        try:
            folder = asyncio.run(
                self.downclient.path_to_id(download_dir, True))
            count = len(folder)
            if count == 0:
                print("create parent folder failed")
                return None
            else:
                task = asyncio.run(self.downclient.offline_download(
                    content, folder[count - 1]["id"]
                ))
                return task["task"]["id"]
        except Exception as e:
            log.error("PikPak 添加离线下载任务失败: %s" % str(e))
            return None

    # 需要完成
    def delete_torrents(self, delete_file, ids):
        pass

    def start_torrents(self, ids):
        pass

    def stop_torrents(self, ids):
        pass

    # 需要完成
    def set_torrents_status(self, ids, **kwargs):
        pass

    def get_download_dirs(self):
        return []

    def change_torrent(self, **kwargs):
        pass

    # 需要完成
    def get_downloading_progress(self, **kwargs):
        """
        获取正在下载的种子进度
        """
        Torrents = self.get_downloading_torrents()
        DispTorrents = []
        for torrent in Torrents:
            DispTorrents.append({
                'id': torrent.get('id'),
                'file_id': torrent.get('file_id'),
                'name': torrent.get('file_name'),
                'nomenu': True,
                'noprogress': True
            })
        return DispTorrents
