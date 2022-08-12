import os
import time

import log
from config import Config
from pt.client.client import IDownloadClient
from pt.client.pyaria2 import PyAria2
from utils.types import MediaType


class Aria2(IDownloadClient):

    _client = None

    def get_config(self):
        # 读取配置文件
        config = Config()
        aria2config = config.get_config('aria2')
        if aria2config:
            # 解析下载目录
            self.save_path = aria2config.get('save_path')
            self.save_containerpath = aria2config.get('save_containerpath')
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
        if not self._client:
            return []

        torrents = self.get_completed_torrents()
        trans_tasks = []
        for torrent in torrents:
            name = torrent.get('bittorrent', {}).get('info', {}).get("name")
            if not name:
                continue
            true_path = os.path.join(torrent.get("dir"), name)
            if not true_path:
                continue
            true_path = self.get_replace_path(true_path)
            trans_tasks.append({'path': true_path, 'id': torrent.get("gid")})
        return trans_tasks

    def get_remove_torrents(self, seeding_time, **kwargs):
        if not self._client:
            return []
        if not seeding_time:
            return []
        torrents = self.get_completed_torrents()
        remove_torrents = []
        for torrent in torrents:
            torrent_time = int(time.time() - torrent.get("creationDate"))
            name = torrent.get('bittorrent', {}).get('info', {}).get("name")
            if not name:
                continue
            if torrent_time > int(seeding_time):
                log.info("【Aria2】%s 做种时间：%s（秒），已达清理条件，进行清理..." % (name, torrent_time))
                remove_torrents.append(torrent.get("gid"))
        return remove_torrents

    def add_torrent(self, content, mtype, **kwargs):
        if not self._client:
            return None
        if mtype == MediaType.TV:
            dl_dir = self.tv_save_path
        elif mtype == MediaType.ANIME:
            dl_dir = self.anime_save_path
        else:
            dl_dir = self.movie_category
        if isinstance(content, str):
            return self._client.addUri(uris=[content], options={"dir": dl_dir})
        else:
            return self._client.addTorrent(torrent=content, options={"dir": dl_dir})

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
