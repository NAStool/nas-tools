import log
from app.utils import StringUtils
from app.utils.types import DownloaderType
from config import Config
from app.downloader.client._base import _IDownloadClient
from app.downloader.client._py115 import Py115


class Client115(_IDownloadClient):
    schema = "client115"
    client_type = DownloaderType.Client115.value
    _client_config = {}

    downclient = None
    lasthash = None

    def __init__(self, config=None):
        if config:
            self._client_config = config
        else:
            self._client_config = Config().get_config('client115')
        self.init_config()
        self.connect()

    def init_config(self):
        if self._client_config:
            self.downclient = Py115(self._client_config.get("cookie"))

    @classmethod
    def match(cls, ctype):
        return True if ctype in [cls.schema, cls.client_type] else False

    def connect(self):
        self.downclient.login()

    def get_status(self):
        if not self.downclient:
            return False
        ret = self.downclient.login()
        if not ret:
            log.info(self.downclient.err)
            return False
        return True

    def get_torrents(self, ids=None, status=None, **kwargs):
        tlist = []
        if not self.downclient:
            return tlist
        ret, tasks = self.downclient.gettasklist(page=1)
        if not ret:
            log.info(f"【{self.client_type}】获取任务列表错误：{self.downclient.err}")
            return tlist
        if tasks:
            for task in tasks:
                if ids:
                    if task.get("info_hash") not in ids:
                        continue
                if status:
                    if task.get("status") not in status:
                        continue
                ret, tdir = self.downclient.getiddir(task.get("file_id"))
                task["path"] = tdir
                tlist.append(task)

        return tlist or []

    def get_completed_torrents(self, **kwargs):
        return self.get_torrents(status=[2])

    def get_downloading_torrents(self, **kwargs):
        return self.get_torrents(status=[0, 1])

    def remove_torrents_tag(self, **kwargs):
        pass

    def get_transfer_task(self, **kwargs):
        pass

    def get_remove_torrents(self, **kwargs):
        return []

    def add_torrent(self, content, download_dir=None, **kwargs):
        if not self.downclient:
            return False
        if isinstance(content, str):
            ret, self.lasthash = self.downclient.addtask(tdir=download_dir, content=content)
            if not ret:
                log.error(f"【{self.client_type}】添加下载任务失败：{self.downclient.err}")
                return None
            return self.lasthash
        else:
            log.info(f"【{self.client_type}】暂时不支持非链接下载")
            return None

    def delete_torrents(self, delete_file, ids):
        if not self.downclient:
            return False
        return self.downclient.deltask(thash=ids)

    def start_torrents(self, ids):
        pass

    def stop_torrents(self, ids):
        pass

    def set_torrents_status(self, ids, **kwargs):
        return self.delete_torrents(ids=ids, delete_file=False)

    def get_download_dirs(self):
        return []

    def change_torrent(self, **kwargs):
        pass

    def get_downloading_progress(self):
        """
        获取正在下载的种子进度
        """
        Torrents = self.get_downloading_torrents()
        DispTorrents = []
        for torrent in Torrents:
            # 进度
            progress = round(torrent.get('percentDone'), 1)
            state = "Downloading"
            _dlspeed = StringUtils.str_filesize(torrent.get('peers'))
            _upspeed = StringUtils.str_filesize(torrent.get('rateDownload'))
            speed = "%s%sB/s %s%sB/s" % (chr(8595), _dlspeed, chr(8593), _upspeed)
            DispTorrents.append({
                'id': torrent.get('info_hash'),
                'name': torrent.get('name'),
                'speed': speed,
                'state': state,
                'progress': progress
            })
        return DispTorrents
