import os
import re

from app.utils import RequestUtils
from config import Config
from app.downloader.client.client import IDownloadClient
from app.downloader.client.pyaria2 import PyAria2


class Aria2(IDownloadClient):

    _client = None

    def get_config(self):
        # 读取配置文件
        config = Config()
        aria2config = config.get_config('aria2')
        if aria2config:
            self.host = aria2config.get("host")
            if self.host:
                if not self.host.startswith('http'):
                    self.host = "http://" + self.host
                if self.host.endswith('/'):
                    self.host = self.host[:-1]
            self.port = aria2config.get("port")
            self.secret = aria2config.get("secret")
            if self.host and self.port:
                self._client = PyAria2(secret=self.secret, host=self.host, port=self.port)

    def connect(self):
        pass

    def get_status(self):
        if not self._client:
            return False
        ver = self._client.getVersion()
        return True if ver else False

    def get_torrents(self, ids=None, status=None, **kwargs):
        if not self._client:
            return []
        ret_torrents = []
        if ids:
            if isinstance(ids, list):
                for gid in ids:
                    ret_torrents.append(self._client.tellStatus(gid=gid))
            else:
                ret_torrents = [self._client.tellStatus(gid=ids)]
        elif status:
            if status == "downloading":
                ret_torrents = self._client.tellActive() or [] + self._client.tellWaiting(offset=-1, num=100) or []
            else:
                ret_torrents = self._client.tellStopped(offset=-1, num=1000)
        return ret_torrents

    def get_downloading_torrents(self, **kwargs):
        return self.get_torrents(status="downloading")

    def get_completed_torrents(self, **kwargs):
        return self.get_torrents(status="completed")

    def set_torrents_status(self, ids):
        return self.delete_torrents(ids=ids, delete_file=False)

    def get_transfer_task(self, tag):
        if not self._client:
            return []
        torrents = self.get_completed_torrents()
        trans_tasks = []
        for torrent in torrents:
            name = torrent.get('bittorrent', {}).get('info', {}).get("name")
            if not name:
                continue
            path = torrent.get("dir")
            if not path:
                continue
            true_path = self.get_replace_path(path)
            trans_tasks.append({'path': os.path.join(true_path, name), 'id': torrent.get("gid")})
        return trans_tasks

    def get_remove_torrents(self, seeding_time, **kwargs):
        return []

    def add_torrent(self, content, download_dir=None, **kwargs):
        if not self._client:
            return None
        if isinstance(content, str):
            # 转换为磁力链
            if re.match("^https*://", content):
                try:
                    p = RequestUtils().get_res(url=content, allow_redirects=False)
                    if p and p.headers.get("Location"):
                        content = p.headers.get("Location")
                except Exception as result:
                    print(str(result))
            return self._client.addUri(uris=[content], options=dict(dir=download_dir))
        else:
            return self._client.addTorrent(torrent=content, uris=[], options=dict(dir=download_dir))

    def start_torrents(self, ids):
        if not self._client:
            return False
        return self._client.unpause(gid=ids)

    def stop_torrents(self, ids):
        if not self._client:
            return False
        return self._client.pause(gid=ids)

    def delete_torrents(self, delete_file, ids):
        if not self._client:
            return False
        return self._client.remove(gid=ids)

    def get_download_dirs(self):
        return []

    def change_torrent(self, **kwargs):
        pass
