import os
import re

from app.utils import RequestUtils, ExceptionUtils, StringUtils
from app.utils.types import DownloaderType
from config import Config
from app.downloader.client._base import _IDownloadClient
from app.downloader.client._pyaria2 import PyAria2


class Aria2(_IDownloadClient):

    schema = "aria2"
    client_type = DownloaderType.Aria2.value
    _client_config = {}

    _client = None
    host = None
    port = None
    secret = None

    def __init__(self, config=None):
        if config:
            self._client_config = config
        else:
            self._client_config = Config().get_config('aria2')
        self.init_config()
        self.connect()

    def init_config(self):
        if self._client_config:
            self.host = self._client_config.get("host")
            if self.host:
                if not self.host.startswith('http'):
                    self.host = "http://" + self.host
                if self.host.endswith('/'):
                    self.host = self.host[:-1]
            self.port = self._client_config.get("port")
            self.secret = self._client_config.get("secret")
            if self.host and self.port:
                self._client = PyAria2(secret=self.secret, host=self.host, port=self.port)

    @classmethod
    def match(cls, ctype):
        return True if ctype in [cls.schema, cls.client_type] else False

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

    def set_torrents_status(self, ids, **kwargs):
        return self.delete_torrents(ids=ids, delete_file=False)

    def get_transfer_task(self, **kwargs):
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

    def get_remove_torrents(self, **kwargs):
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
                    ExceptionUtils.exception_traceback(result)
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

    def get_downloading_progress(self, **kwargs):
        """
        获取正在下载的种子进度
        """
        Torrents = self.get_downloading_torrents()
        DispTorrents = []
        for torrent in Torrents:
            # 进度
            try:
                progress = round(int(torrent.get('completedLength')) / int(torrent.get("totalLength")), 1) * 100
            except ZeroDivisionError:
                progress = 0.0
            state = "Downloading"
            _dlspeed = StringUtils.str_filesize(torrent.get('downloadSpeed'))
            _upspeed = StringUtils.str_filesize(torrent.get('uploadSpeed'))
            speed = "%s%sB/s %s%sB/s" % (chr(8595), _dlspeed, chr(8593), _upspeed)
            DispTorrents.append({
                'id': torrent.get('gid'),
                'name': torrent.get('bittorrent', {}).get('info', {}).get("name"),
                'speed': speed,
                'state': state,
                'progress': progress
            })
        return DispTorrents
