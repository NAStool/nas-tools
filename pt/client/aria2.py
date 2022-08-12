from config import Config
from pt.client.client import IDownloadClient
from pt.client.pyaria2 import PyAria2


class Aria2(IDownloadClient):

    _client = None

    def get_config(self):
        # 读取配置文件
        config = Config()
        aria2config = config.get_config('aria2')
        if aria2config:
            self.host = aria2config.get("host")
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
                ids = ids[0]
            ret_torrents = [self._client.tellStatus(gid=ids)]
        elif status:
            torrents = self._client.tellActive() or []
            for torrent in torrents:
                if status == "downloading":
                    if int(torrent.get("completedLength")) < int(torrent.get("totalLength")):
                        ret_torrents.append(torrent)
                    if torrent.get("status") == "paused":
                        ret_torrents.append(torrent)
                elif status == "completed":
                    if int(torrent.get("completedLength")) >= int(torrent.get("totalLength")):
                        ret_torrents.append(torrent)
                    if torrent.get("status") == "complete":
                        ret_torrents.append(torrent)
                else:
                    ret_torrents.append(torrent)
        return ret_torrents

    def get_downloading_torrents(self, **kwargs):
        return self.get_torrents(status="downloading")

    def get_completed_torrents(self, **kwargs):
        return self.get_torrents(status="completed")

    def set_torrents_status(self, ids):
        pass

    def get_transfer_task(self, tag):
        return []

    def get_remove_torrents(self, seeding_time, **kwargs):
        return []

    def add_torrent(self, content, mtype, **kwargs):
        if not self._client:
            return None
        if isinstance(content, str):
            return self._client.addUri(uris=[content])
        else:
            return self._client.addTorrent(torrent=content)

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
