import os
import re
import time
from datetime import datetime
from urllib import parse

import log
import qbittorrentapi
from app.downloader.client._base import _IDownloadClient
from app.utils import ExceptionUtils, StringUtils
from app.utils.types import DownloaderType


class Qbittorrent(_IDownloadClient):

    # 下载器ID
    client_id = "qbittorrent"
    # 下载器类型
    client_type = DownloaderType.QB
    # 下载器名称
    client_name = DownloaderType.QB.value

    # 私有属性
    _client_config = {}
    _torrent_management = False

    qbc = None
    ver = None
    host = None
    port = None
    username = None
    password = None
    download_dir = []

    def __init__(self, config):
        self._client_config = config
        self.init_config()
        self.connect()

    def init_config(self):
        if self._client_config:
            self.host = self._client_config.get('host')
            self.port = int(self._client_config.get('port')) if str(self._client_config.get('port')).isdigit() else 0
            self.username = self._client_config.get('username')
            self.password = self._client_config.get('password')
            self.download_dir = self._client_config.get('download_dir')
            # 种子管理模式
            match self._client_config.get('torrent_management'):
                case "default":
                    self._torrent_management = None
                case "manual":
                    self._torrent_management = False
                case "auto":
                    self._torrent_management = True
                case _:
                    self._torrent_management = False

    @classmethod
    def match(cls, ctype):
        return True if ctype in [cls.client_id, cls.client_type, cls.client_name] else False

    def get_type(self):
        return self.client_type

    def connect(self):
        if self.host and self.port:
            self.qbc = self.__login_qbittorrent()

    def __login_qbittorrent(self):
        """
        连接qbittorrent
        :return: qbittorrent对象
        """
        try:
            # 登录
            qbt = qbittorrentapi.Client(host=self.host,
                                        port=self.port,
                                        username=self.username,
                                        password=self.password,
                                        VERIFY_WEBUI_CERTIFICATE=False,
                                        REQUESTS_ARGS={'timeout': (10, 30)})
            try:
                qbt.auth_log_in()
                self.ver = qbt.app_version()
            except qbittorrentapi.LoginFailed as e:
                print(str(e))
            return qbt
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            log.error(f"【{self.client_name}】qBittorrent连接出错：{str(err)}")
            return None

    def get_status(self):
        if not self.qbc:
            return False
        try:
            return True if self.qbc.transfer_info() else False
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return False

    def get_torrents(self, ids=None, status=None, tag=None):
        """
        获取种子列表
        return: 种子列表, 是否发生异常
        """
        if not self.qbc:
            return [], True
        try:
            torrents = self.qbc.torrents_info(torrent_hashes=ids,
                                              status_filter=status)
            if tag:
                results = []
                if not isinstance(tag, list):
                    tag = [tag]
                for torrent in torrents:
                    include_flag = True
                    for t in tag:
                        if t and t not in torrent.get("tags"):
                            include_flag = False
                            break
                    if include_flag:
                        results.append(torrent)
                return results or [], False
            return torrents or [], False
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return [], True

    def get_completed_torrents(self, ids=None, tag=None):
        """
        获取已完成的种子
        return: 种子列表, 如发生异常则返回None
        """
        if not self.qbc:
            return None
        torrents, error = self.get_torrents(status=["completed"], ids=ids, tag=tag)
        return None if error else torrents or []

    def get_downloading_torrents(self, ids=None, tag=None):
        """
        获取正在下载的种子
        return: 种子列表, 如发生异常则返回None
        """
        if not self.qbc:
            return None
        torrents, error = self.get_torrents(ids=ids,
                                            status=["downloading"],
                                            tag=tag)
        return None if error else torrents or []

    def remove_torrents_tag(self, ids, tag):
        """
        移除种子Tag
        :param ids: 种子Hash列表
        :param tag: 标签内容
        """
        try:
            return self.qbc.torrents_delete_tags(torrent_hashes=ids, tags=tag)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return False

    def set_torrents_status(self, ids, tags=None):
        """
        设置种子状态为已整理，以及是否强制做种
        """
        if not self.qbc:
            return
        try:
            # 打标签
            self.qbc.torrents_add_tags(tags="已整理", torrent_hashes=ids)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)

    def torrents_set_force_start(self, ids):
        """
        设置强制作种
        """
        try:
            self.qbc.torrents_set_force_start(enable=True, torrent_hashes=ids)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)

    def get_transfer_task(self, tag, match_path=None):
        """
        获取下载文件转移任务种子
        """
        # 处理下载完成的任务
        torrents = self.get_completed_torrents(tag=tag) or []
        trans_tasks = []
        for torrent in torrents:
            # 判断标签是否包含"已整理"
            if torrent.get("tags") and "已整理" in torrent.get("tags"):
                continue
            path = torrent.get("save_path")
            if not path:
                continue
            # 判断路径是否已经在下载目录中指定
            if match_path and not self.is_download_dir(path, self.download_dir):
                continue
            content_path = torrent.get("content_path")
            if content_path:
                trans_name = content_path.replace(path, "")
                if trans_name.startswith('/') or trans_name.startswith('\\'):
                    trans_name = trans_name[1:]
            else:
                trans_name = torrent.get('name')
            true_path = self.get_replace_path(path, self.download_dir)
            trans_tasks.append(
                {'path': os.path.join(true_path, trans_name).replace("\\", "/"), 'id': torrent.get('hash')})
        return trans_tasks

    def get_remove_torrents(self, config=None):
        """
        获取自动删种任务种子
        """
        if not config:
            return []
        remove_torrents = []
        remove_torrents_ids = []
        torrents, error_flag = self.get_torrents(tag=config.get("filter_tags"))
        if error_flag:
            return []
        ratio = config.get("ratio")
        # 做种时间 单位：小时
        seeding_time = config.get("seeding_time")
        # 大小 单位：GB
        size = config.get("size")
        minsize = size[0] * 1024 * 1024 * 1024 if size else 0
        maxsize = size[-1] * 1024 * 1024 * 1024 if size else 0
        # 平均上传速度 单位 KB/s
        upload_avs = config.get("upload_avs")
        savepath_key = config.get("savepath_key")
        tracker_key = config.get("tracker_key")
        qb_state = config.get("qb_state")
        qb_category = config.get("qb_category")
        for torrent in torrents:
            date_done = torrent.completion_on if torrent.completion_on > 0 else torrent.added_on
            date_now = int(time.mktime(datetime.now().timetuple()))
            torrent_seeding_time = date_now - date_done if date_done else 0
            torrent_upload_avs = torrent.uploaded / torrent_seeding_time if torrent_seeding_time else 0
            if ratio and torrent.ratio <= ratio:
                continue
            if seeding_time and torrent_seeding_time <= seeding_time * 3600:
                continue
            if size and (torrent.size >= maxsize or torrent.size <= minsize):
                continue
            if upload_avs and torrent_upload_avs >= upload_avs * 1024:
                continue
            if savepath_key and not re.findall(savepath_key, torrent.save_path, re.I):
                continue
            if tracker_key and not re.findall(tracker_key, torrent.tracker, re.I):
                continue
            if qb_state and torrent.state not in qb_state:
                continue
            if qb_category and torrent.category not in qb_category:
                continue
            site = parse.urlparse(torrent.tracker).netloc.split(".") if torrent.tracker else [""]
            remove_torrents.append({
                "id": torrent.hash,
                "name": torrent.name,
                "site": site[-2] if len(site) >= 2 else site[0],
                "size": torrent.size
            })
            remove_torrents_ids.append(torrent.hash)
        if config.get("samedata") and remove_torrents:
            remove_torrents_plus = []
            for remove_torrent in remove_torrents:
                name = remove_torrent.get("name")
                size = remove_torrent.get("size")
                for torrent in torrents:
                    if torrent.name == name and torrent.size == size and torrent.hash not in remove_torrents_ids:
                        remove_torrents_plus.append({
                            "id": torrent.hash,
                            "name": torrent.name,
                            "site": parse.urlparse(torrent.tracker).netloc.split(".")[-2],
                            "size": torrent.size
                        })
            remove_torrents_plus += remove_torrents
            return remove_torrents_plus
        return remove_torrents

    def __get_last_add_torrentid_by_tag(self, tag, status=None):
        """
        根据种子的下载链接获取下载中或暂停的钟子的ID
        :return: 种子ID
        """
        try:
            torrents, _ = self.get_torrents(status=status, tag=tag)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return None
        if torrents:
            return torrents[0].get("hash")
        else:
            return None

    def get_torrent_id_by_tag(self, tag, status=None):
        """
        通过标签多次尝试获取刚添加的种子ID，并移除标签
        """
        torrent_id = None
        # QB添加下载后需要时间，重试5次每次等待5秒
        for i in range(1, 6):
            time.sleep(5)
            torrent_id = self.__get_last_add_torrentid_by_tag(tag=tag,
                                                              status=status)
            if torrent_id is None:
                continue
            else:
                self.remove_torrents_tag(torrent_id, tag)
                break
        return torrent_id

    def add_torrent(self,
                    content,
                    is_paused=False,
                    download_dir=None,
                    tag=None,
                    category=None,
                    content_layout=None,
                    upload_limit=None,
                    download_limit=None,
                    ratio_limit=None,
                    seeding_time_limit=None,
                    cookie=None
                    ):
        """
        添加种子
        :param content: 种子urls或文件
        :param is_paused: 添加后暂停
        :param tag: 标签
        :param download_dir: 下载路径
        :param category: 分类
        :param content_layout: 布局
        :param upload_limit: 上传限速 Kb/s
        :param download_limit: 下载限速 Kb/s
        :param ratio_limit: 分享率限制
        :param seeding_time_limit: 做种时间限制
        :param cookie: 站点Cookie用于辅助下载种子
        :return: bool
        """
        if not self.qbc or not content:
            return False
        if isinstance(content, str):
            urls = content
            torrent_files = None
        else:
            urls = None
            torrent_files = content
        if download_dir:
            save_path = download_dir
        else:
            save_path = None
        if not category:
            category = None
        if tag:
            tags = tag
        else:
            tags = None
        if not content_layout:
            content_layout = None
        if upload_limit:
            upload_limit = int(upload_limit) * 1024
        else:
            upload_limit = None
        if download_limit:
            download_limit = int(download_limit) * 1024
        else:
            download_limit = None
        if ratio_limit:
            ratio_limit = round(float(ratio_limit), 2)
        else:
            ratio_limit = None
        if seeding_time_limit:
            seeding_time_limit = int(seeding_time_limit)
        else:
            seeding_time_limit = None
        try:
            if self._torrent_management:
                save_path = None
            qbc_ret = self.qbc.torrents_add(urls=urls,
                                            torrent_files=torrent_files,
                                            save_path=save_path,
                                            category=category,
                                            is_paused=is_paused,
                                            tags=tags,
                                            content_layout=content_layout,
                                            upload_limit=upload_limit,
                                            download_limit=download_limit,
                                            ratio_limit=ratio_limit,
                                            seeding_time_limit=seeding_time_limit,
                                            use_auto_torrent_management=self._torrent_management,
                                            cookie=cookie)
            return True if qbc_ret and str(qbc_ret).find("Ok") != -1 else False
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return False

    def start_torrents(self, ids):
        if not self.qbc:
            return False
        try:
            return self.qbc.torrents_resume(torrent_hashes=ids)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return False

    def stop_torrents(self, ids):
        if not self.qbc:
            return False
        try:
            return self.qbc.torrents_pause(torrent_hashes=ids)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return False

    def delete_torrents(self, delete_file, ids):
        if not self.qbc:
            return False
        if not ids:
            return False
        try:
            self.qbc.torrents_delete(delete_files=delete_file, torrent_hashes=ids)
            return True
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return False

    def get_files(self, tid):
        try:
            return self.qbc.torrents_files(torrent_hash=tid)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return None

    def set_files(self, **kwargs):
        """
        设置下载文件的状态，priority为0为不下载，priority为1为下载
        """
        if not kwargs.get("torrent_hash") or not kwargs.get("file_ids"):
            return False
        try:
            self.qbc.torrents_file_priority(torrent_hash=kwargs.get("torrent_hash"),
                                            file_ids=kwargs.get("file_ids"),
                                            priority=kwargs.get("priority"))
            return True
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return False

    def set_torrent_tag(self, **kwargs):
        pass

    def get_download_dirs(self):
        if not self.qbc:
            return []
        ret_dirs = []
        try:
            categories = self.qbc.torrents_categories(requests_args={'timeout': (5, 10)}) or {}
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return []
        for category in categories.values():
            if category and category.get("savePath") and category.get("savePath") not in ret_dirs:
                ret_dirs.append(category.get("savePath"))
        return ret_dirs

    def set_uploadspeed_limit(self, ids, limit):
        """
        设置上传限速，单位bytes/sec
        """
        if not self.qbc:
            return
        if not ids or not limit:
            return
        self.qbc.torrents_set_upload_limit(limit=int(limit),
                                           torrent_hashes=ids)

    def set_downloadspeed_limit(self, ids, limit):
        """
        设置下载限速，单位bytes/sec
        """
        if not self.qbc:
            return
        if not ids or not limit:
            return
        self.qbc.torrents_set_download_limit(limit=int(limit),
                                             torrent_hashes=ids)

    def change_torrent(self, **kwargs):
        """
        修改种子状态
        """
        pass

    def get_downloading_progress(self, tag=None, ids=None):
        """
        获取正在下载的种子进度
        """
        Torrents = self.get_downloading_torrents(tag=tag, ids=ids) or []
        DispTorrents = []
        for torrent in Torrents:
            # 进度
            progress = round(torrent.get('progress') * 100, 1)
            if torrent.get('state') in ['pausedDL']:
                state = "Stoped"
                speed = "已暂停"
            else:
                state = "Downloading"
                _dlspeed = StringUtils.str_filesize(torrent.get('dlspeed'))
                _upspeed = StringUtils.str_filesize(torrent.get('upspeed'))
                if progress >= 100:
                    speed = "%s%sB/s %s%sB/s" % (chr(8595), _dlspeed, chr(8593), _upspeed)
                else:
                    eta = StringUtils.str_timelong(torrent.get('eta'))
                    speed = "%s%sB/s %s%sB/s %s" % (chr(8595), _dlspeed, chr(8593), _upspeed, eta)
            # 主键
            DispTorrents.append({
                'id': torrent.get('hash'),
                'name': torrent.get('name'),
                'speed': speed,
                'state': state,
                'progress': progress
            })
        return DispTorrents

    def set_speed_limit(self, download_limit=None, upload_limit=None):
        """
        设置速度限制
        :param download_limit: 下载速度限制，单位KB/s
        :param upload_limit: 上传速度限制，单位kB/s
        """
        if not self.qbc:
            return
        download_limit = download_limit * 1024
        upload_limit = upload_limit * 1024
        try:
            if self.qbc.transfer.upload_limit != upload_limit:
                self.qbc.transfer.upload_limit = upload_limit
            if self.qbc.transfer.download_limit != download_limit:
                self.qbc.transfer.download_limit = download_limit
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return False
