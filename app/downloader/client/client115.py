import log
from config import Config
from app.downloader.client.client import IDownloadClient
from app.downloader.client.py115 import Py115


class Client115(IDownloadClient):

    downclient = None
    lasthash = None

    def get_config(self):
        # 读取配置文件
        config = Config()
        cloudconfig = config.get_config('client115')
        if cloudconfig:
            self.downclient = Py115(cloudconfig.get("cookie"))

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

    def get_torrents(self, ids=None, status=None, tag=None):
        tlist = []
        if not self.downclient:
            return tlist
        ret, tasks = self.downclient.gettasklist(page=1)
        if not ret:
            log.info("【115】获取任务列表错误：{}".format(self.downclient.err))
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
                log.error("【115】添加下载任务失败：{}".format(self.downclient.err))
                return None
            return self.lasthash
        else:
            log.info("【115】暂时不支持非链接下载")
            return None

    def delete_torrents(self, delete_file, ids):
        if not self.downclient:
            return False
        return self.downclient.deltask(thash=ids)

    def start_torrents(self, ids):
        pass

    def stop_torrents(self, ids):
        pass

    def set_torrents_status(self, ids):
        return self.delete_torrents(ids=ids, delete_file=False)

    def get_download_dirs(self):
        return []

    def change_torrent(self, **kwargs):
        pass
