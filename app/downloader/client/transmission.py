import os.path
import re
import time
from datetime import datetime

import transmission_rpc

import log
from app.utils import ExceptionUtils, StringUtils
from app.utils.types import DownloaderType
from config import Config
from app.downloader.client._base import _IDownloadClient


class Transmission(_IDownloadClient):
    schema = "transmission"
    client_type = DownloaderType.TR.value
    _client_config = {}

    # 参考transmission web，仅查询需要的参数，加速种子检索
    _trarg = ["id", "name", "status", "labels", "hashString", "totalSize", "percentDone", "addedDate", "trackerStats",
              "leftUntilDone", "rateDownload", "rateUpload", "recheckProgress", "rateDownload", "rateUpload",
              "peersGettingFromUs", "peersSendingToUs", "uploadRatio", "uploadedEver", "downloadedEver", "downloadDir",
              "error", "errorString", "doneDate", "queuePosition", "activityDate", "trackers"]
    trc = None
    host = None
    port = None
    username = None
    password = None

    def __init__(self, config=None):
        if config:
            self._client_config = config
        else:
            self._client_config = Config().get_config('transmission')
        self.init_config()
        self.connect()

    def init_config(self):
        if self._client_config:
            self.host = self._client_config.get('trhost')
            self.port = int(self._client_config.get('trport')) if str(self._client_config.get('trport')).isdigit() else 0
            self.username = self._client_config.get('trusername')
            self.password = self._client_config.get('trpassword')

    @classmethod
    def match(cls, ctype):
        return True if ctype in [cls.schema, cls.client_type] else False

    def connect(self):
        if self.host and self.port:
            self.trc = self.__login_transmission()

    def __login_transmission(self):
        """
        连接transmission
        :return: transmission对象
        """
        try:
            # 登录
            trt = transmission_rpc.Client(host=self.host,
                                          port=self.port,
                                          username=self.username,
                                          password=self.password,
                                          timeout=30)
            return trt
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            log.error(f"【{self.client_type}】transmission连接出错：{str(err)}")
            return None

    def get_status(self):
        return True if self.trc else False

    def get_torrents(self, ids=None, status=None, tag=None):
        """
        获取种子列表
        返回结果 种子列表, 是否有错误
        """
        if not self.trc:
            return [], True
        if isinstance(ids, list):
            ids = [int(x) for x in ids if str(x).isdigit()]
        elif str(ids).isdigit():
            ids = int(ids)
        try:
            torrents = self.trc.get_torrents(ids=ids, arguments=self._trarg)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return [], True
        if status and not isinstance(status, list):
            status = [status]
        if tag and not isinstance(tag, list):
            tag = [tag]
        ret_torrents = []
        for torrent in torrents:
            if status and torrent.status not in status:
                continue
            labels = torrent.labels if hasattr(torrent, "labels") else []
            include_flag = True
            if tag:
                for t in tag:
                    if t and t not in labels:
                        include_flag = False
                        break
            if include_flag:
                ret_torrents.append(torrent)
        return ret_torrents, False

    def get_completed_torrents(self, tag=None):
        """
        获取已完成的种子列表
        return 种子列表, 是否有错误
        """
        if not self.trc:
            return []
        try:
            torrents, _ = self.get_torrents(status=["seeding", "seed_pending"], tag=tag)
            return torrents
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return []

    def get_downloading_torrents(self, tag=None):
        """
        获取正在下载的种子列表
        return 种子列表, 是否有错误
        """
        if not self.trc:
            return []
        try:
            torrents, _ = self.get_torrents(status=["downloading", "download_pending"], tag=tag)
            return torrents
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return []

    def set_torrents_status(self, ids, tags=None):
        if not self.trc:
            return
        if isinstance(ids, list):
            ids = [int(x) for x in ids if str(x).isdigit()]
        elif str(ids).isdigit():
            ids = int(ids)
        # 合成标签
        if tags:
            if not isinstance(tags, list):
                tags = [tags, "已整理"]
            else:
                tags.append("已整理")
        else:
            tags = ["已整理"]
        # 打标签
        try:
            self.trc.change_torrent(labels=tags, ids=ids)
            log.info(f"【{self.client_type}】设置transmission种子标签成功")
        except Exception as err:
            ExceptionUtils.exception_traceback(err)

    def set_torrent_tag(self, tid, tag):
        if not tid or not tag:
            return
        try:
            self.trc.change_torrent(labels=tag, ids=int(tid))
        except Exception as err:
            ExceptionUtils.exception_traceback(err)

    def change_torrent(self,
                       tid,
                       tag=None,
                       upload_limit=None,
                       download_limit=None,
                       ratio_limit=None,
                       seeding_time_limit=None):
        """
        设置种子
        :param tid: ID
        :param tag: 标签
        :param upload_limit: 上传限速 Kb/s
        :param download_limit: 下载限速 Kb/s
        :param ratio_limit: 分享率限制
        :param seeding_time_limit: 做种时间限制
        :return: bool
        """
        if not tid:
            return
        else:
            ids = int(tid)
        if tag:
            if isinstance(tag, list):
                labels = tag
            else:
                labels = [tag]
        else:
            labels = []
        if upload_limit:
            uploadLimited = True
            uploadLimit = int(upload_limit)
        else:
            uploadLimited = False
            uploadLimit = 0
        if download_limit:
            downloadLimited = True
            downloadLimit = int(download_limit)
        else:
            downloadLimited = False
            downloadLimit = 0
        if ratio_limit:
            seedRatioMode = 1
            seedRatioLimit = round(float(ratio_limit), 2)
        else:
            seedRatioMode = 2
            seedRatioLimit = 0
        if seeding_time_limit:
            seedIdleMode = 1
            seedIdleLimit = int(seeding_time_limit)
        else:
            seedIdleMode = 2
            seedIdleLimit = 0
        try:
            self.trc.change_torrent(ids=ids,
                                    labels=labels,
                                    uploadLimited=uploadLimited,
                                    uploadLimit=uploadLimit,
                                    downloadLimited=downloadLimited,
                                    downloadLimit=downloadLimit,
                                    seedRatioMode=seedRatioMode,
                                    seedRatioLimit=seedRatioLimit,
                                    seedIdleMode=seedIdleMode,
                                    seedIdleLimit=seedIdleLimit)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)

    def get_transfer_task(self, tag):
        # 处理所有任务
        torrents = self.get_completed_torrents(tag=tag)
        trans_tasks = []
        for torrent in torrents:
            # 3.0版本以下的Transmission没有labels
            if not hasattr(torrent, "labels"):
                log.error(f"【{self.client_type}】当前transmission版本可能过低，无labels属性，请安装3.0以上版本！")
                break
            if torrent.labels and "已整理" in torrent.labels:
                continue
            path = torrent.download_dir
            if not path:
                continue
            true_path = self.get_replace_path(path)
            trans_tasks.append({
                'path': os.path.join(true_path, torrent.name).replace("\\", "/"),
                'id': torrent.id,
                'tags': torrent.labels
            })
        return trans_tasks

    def get_remove_torrents(self, config=None):
        if not config:
            return []
        remove_torrents = []
        remove_torrents_ids = []
        torrents, error_flag = self.get_torrents()
        if error_flag:
            return []
        tags = config.get("filter_tags")
        ratio = config.get("ratio")
        # 做种时间 单位：小时
        seeding_time = config.get("seeding_time")
        # 大小 单位：GB
        size = config.get("size")
        minsize = size[0]*1024*1024*1024 if size else 0
        maxsize = size[-1]*1024*1024*1024 if size else 0
        # 平均上传速度 单位 KB/s
        upload_avs = config.get("upload_avs")
        savepath_key = config.get("savepath_key")
        tracker_key = config.get("tracker_key")
        tr_state = config.get("tr_state")
        tr_error_key = config.get("tr_error_key")
        for torrent in torrents:
            date_done = torrent.date_done or torrent.date_added
            date_now = int(time.mktime(datetime.now().timetuple()))
            torrent_seeding_time = date_now - int(time.mktime(date_done.timetuple())) if date_done else 0
            torrent_uploaded = torrent.ratio * torrent.total_size
            torrent_upload_avs = torrent_uploaded / torrent_seeding_time if torrent_seeding_time else 0
            if ratio and torrent.ratio <= ratio:
                continue
            if seeding_time and torrent_seeding_time <= seeding_time*3600:
                continue
            if size and (torrent.total_size >= maxsize or torrent.total_size <= minsize):
                continue
            if upload_avs and torrent_upload_avs >= upload_avs*1024:
                continue
            if savepath_key and not re.findall(savepath_key, torrent.download_dir, re.I):
                continue
            if tracker_key:
                if not torrent.trackers:
                    continue
                else:
                    tacker_key_flag = False
                    for tracker in torrent.trackers:
                        if re.findall(tracker_key, tracker.get("announce", ""), re.I):
                            tacker_key_flag = True
                            break
                    if not tacker_key_flag:
                        continue
            if tr_state and torrent.status not in tr_state:
                continue
            if tr_error_key and not re.findall(tr_error_key, torrent.error_string, re.I):
                continue
            labels = set(torrent.labels)
            if tags and (not labels or not set(tags).issubset(labels)):
                continue
            remove_torrents.append({
                "id": torrent.id,
                "name": torrent.name,
                "site": torrent.trackers[0].get("sitename"),
                "size": torrent.total_size
            })
            remove_torrents_ids.append(torrent.id)
        if config.get("samedata") and remove_torrents:
            remove_torrents_plus = []
            for remove_torrent in remove_torrents:
                name = remove_torrent.get("name")
                size = remove_torrent.get("size")
                for torrent in torrents:
                    if torrent.name == name and torrent.total_size == size and torrent.id not in remove_torrents_ids:
                        remove_torrents_plus.append({
                            "id": torrent.id,
                            "name": torrent.name,
                            "site": torrent.trackers[0].get("sitename") if torrent.trackers else "",
                            "size": torrent.total_size
                        })
            remove_torrents_plus += remove_torrents
            return remove_torrents_plus
        return remove_torrents

    def add_torrent(self, content,
                    is_paused=False,
                    download_dir=None,
                    upload_limit=None,
                    download_limit=None,
                    cookie=None,
                    **kwargs):
        try:
            ret = self.trc.add_torrent(torrent=content,
                                       download_dir=download_dir,
                                       paused=is_paused,
                                       cookies=cookie)
            if ret and ret.id:
                if upload_limit:
                    self.set_uploadspeed_limit(ret.id, int(upload_limit))
                if download_limit:
                    self.set_downloadspeed_limit(ret.id, int(download_limit))
            return ret
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return False

    def start_torrents(self, ids):
        if not self.trc:
            return False
        if isinstance(ids, list):
            ids = [int(x) for x in ids if str(x).isdigit()]
        elif str(ids).isdigit():
            ids = int(ids)
        try:
            return self.trc.start_torrent(ids=ids)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return False

    def stop_torrents(self, ids):
        if not self.trc:
            return False
        if isinstance(ids, list):
            ids = [int(x) for x in ids if str(x).isdigit()]
        elif str(ids).isdigit():
            ids = int(ids)
        try:
            return self.trc.stop_torrent(ids=ids)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return False

    def delete_torrents(self, delete_file, ids):
        if not self.trc:
            return False
        if not ids:
            return False
        if isinstance(ids, list):
            ids = [int(x) for x in ids if str(x).isdigit()]
        elif str(ids).isdigit():
            ids = int(ids)
        try:
            return self.trc.remove_torrent(delete_data=delete_file, ids=ids)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return False

    def get_files(self, tid):
        """
        获取种子文件列表
        """
        if not tid:
            return None
        try:
            torrent = self.trc.get_torrent(tid)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return None
        if torrent:
            return torrent.files()
        else:
            return None

    def set_files(self, **kwargs):
        """
        设置下载文件的状态
        {
            <torrent id>: {
                <file id>: {
                    'priority': <priority ('high'|'normal'|'low')>,
                    'selected': <selected for download (True|False)>
                },
                ...
            },
            ...
        }
        """
        if not kwargs.get("file_info"):
            return False
        try:
            self.trc.set_files(kwargs.get("file_info"))
            return True
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return False

    def get_download_dirs(self):
        if not self.trc:
            return []
        try:
            return [self.trc.get_session(timeout=10).download_dir]
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return []

    def set_uploadspeed_limit(self, ids, limit):
        """
        设置上传限速，单位 KB/sec
        """
        if not self.trc:
            return
        if not ids or not limit:
            return
        if not isinstance(ids, list):
            ids = int(ids)
        else:
            ids = [int(x) for x in ids if str(x).isdigit()]
        self.trc.change_torrent(ids, uploadLimit=int(limit))

    def set_downloadspeed_limit(self, ids, limit):
        """
        设置下载限速，单位 KB/sec
        """
        if not self.trc:
            return
        if not ids or not limit:
            return
        if not isinstance(ids, list):
            ids = int(ids)
        else:
            ids = [int(x) for x in ids if str(x).isdigit()]
        self.trc.change_torrent(ids, downloadLimit=int(limit))

    def get_downloading_progress(self, tag=None):
        """
        获取正在下载的种子进度
        """
        Torrents = self.get_downloading_torrents(tag=tag)
        DispTorrents = []
        for torrent in Torrents:
            if torrent.status in ['stopped']:
                state = "Stoped"
                speed = "已暂停"
            else:
                state = "Downloading"
                _dlspeed = StringUtils.str_filesize(torrent.rateDownload)
                _upspeed = StringUtils.str_filesize(torrent.rateUpload)
                speed = "%s%sB/s %s%sB/s" % (chr(8595), _dlspeed, chr(8593), _upspeed)
            # 进度
            progress = round(torrent.progress)
            DispTorrents.append({
                'id': torrent.id,
                'name': torrent.name,
                'speed': speed,
                'state': state,
                'progress': progress
            })
        return DispTorrents
