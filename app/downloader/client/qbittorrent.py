import os

import qbittorrentapi

import log
from app.utils.types import DownloaderType
from config import Config, PT_TAG
from app.downloader.client.client import IDownloadClient
from pkg_resources import parse_version as v


class Qbittorrent(IDownloadClient):
    _force_upload = False
    qbc = None
    ver = None
    client_type = DownloaderType.QB

    def get_config(self):
        # 读取配置文件
        config = Config()
        qbittorrent = config.get_config('qbittorrent')
        if qbittorrent:
            self.host = qbittorrent.get('qbhost')
            self.port = int(qbittorrent.get('qbport')) if str(qbittorrent.get('qbport')).isdigit() else 0
            self.username = qbittorrent.get('qbusername')
            self.password = qbittorrent.get('qbpassword')
            # 强制做种开关
            self._force_upload = qbittorrent.get('force_upload')

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
                                        REQUESTS_ARGS={'timeout': (5, 15)})
            try:
                qbt.auth_log_in()
                self.ver = qbt.app_version()
            except qbittorrentapi.LoginFailed as e:
                print(e)
            return qbt
        except Exception as err:
            log.error(f"【{self.client_type}】qBittorrent连接出错：{str(err)}")
            return None

    def get_status(self):
        if not self.qbc:
            return False
        try:
            return True if self.qbc.transfer_info() else False
        except Exception as err:
            print(str(err))
            return False

    def get_torrents(self, ids=None, status=None, tag=None):
        """
        获取种子列表
        return: 种子列表, 是否发生异常
        """
        if not self.qbc:
            return [], True
        try:
            torrents = self.qbc.torrents_info(torrent_hashes=ids, status_filter=status, tag=tag)
            if self.is_ver_less_4_4():
                torrents = self.filter_torrent_by_tag(torrents, tag=tag)
            return torrents or [], False
        except Exception as err:
            print(str(err))
            return [], True

    def get_completed_torrents(self, tag=None):
        """
        获取已完成的种子
        return: 种子列表, 是否发生异常
        """
        if not self.qbc:
            return []
        torrents, _ = self.get_torrents(status=["completed"], tag=tag)
        return torrents

    def get_downloading_torrents(self, tag=None):
        """
        获取正在下载的种子
        return: 种子列表, 是否发生异常
        """
        if not self.qbc:
            return []
        torrents, _ = self.get_torrents(status=["downloading"], tag=tag)
        return torrents

    def remove_torrents_tag(self, ids, tag):
        """
        移除种子Tag
        :param ids: 种子Hash列表
        :param tag: 标签内容
        """
        try:
            return self.qbc.torrents_delete_tags(torrent_hashes=ids, tags=tag)
        except Exception as err:
            print(str(err))
            return False

    def set_torrents_status(self, ids):
        if not self.qbc:
            return
        try:
            # 删除标签
            self.qbc.torrents_remove_tags(tags=PT_TAG, torrent_hashes=ids)
            # 打标签
            self.qbc.torrents_add_tags(tags="已整理", torrent_hashes=ids)
            # 超级做种
            if self._force_upload:
                self.qbc.torrents_set_force_start(enable=True, torrent_hashes=ids)
            log.info(f"【{self.client_type}】设置qBittorrent种子状态成功")
        except Exception as err:
            print(str(err))

    def torrents_set_force_start(self, ids):
        """
        设置强制作种
        """
        try:
            self.qbc.torrents_set_force_start(enable=True, torrent_hashes=ids)
        except Exception as err:
            print(str(err))

    def get_transfer_task(self, tag):
        # 处理下载完成的任务
        torrents = self.get_completed_torrents(tag=tag)
        trans_tasks = []
        for torrent in torrents:
            # 判断标签是否包含"已整理"
            if torrent.get("tags") and "已整理" in torrent.get("tags"):
                continue
            path = torrent.get("save_path")
            if not path:
                continue
            content_path = torrent.get("content_path")
            if content_path:
                trans_name = content_path.replace(path, "")
                if trans_name.startswith('/') or trans_name.startswith('\\'):
                    trans_name = trans_name[1:]
            else:
                trans_name = torrent.get('name')
            true_path = self.get_replace_path(path)
            trans_tasks.append({'path': os.path.join(true_path, trans_name), 'id': torrent.get('hash')})
        return trans_tasks

    def get_remove_torrents(self, seeding_time, tag):
        if not seeding_time or not str(seeding_time).isdigit():
            return []
        torrents = self.get_completed_torrents(tag=tag)
        remove_torrents = []
        for torrent in torrents:
            if not torrent.get('seeding_time'):
                continue
            if int(torrent.get('seeding_time')) > int(seeding_time):
                log.info(f"【{self.client_type}】{torrent.get('name')} 做种时间：{torrent.get('seeding_time')}（秒），已达清理条件，进行清理...")
                remove_torrents.append(torrent.get('hash'))
        return remove_torrents

    def get_last_add_torrentid_by_tag(self, tag, status=None):
        """
        根据种子的下载链接获取下载中或暂停的钟子的ID
        :return: 种子ID
        """
        try:
            torrents, _ = self.get_torrents(status=status, tag=tag)
        except Exception as err:
            print(str(err))
            return None
        if torrents:
            return torrents[0].get("hash")
        else:
            return None

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
                    seeding_time_limit=None
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
            use_auto_torrent_management = False
            if not save_path:
                use_auto_torrent_management = True
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
                                            use_auto_torrent_management=use_auto_torrent_management)
            return True if qbc_ret and str(qbc_ret).find("Ok") != -1 else False
        except Exception as err:
            print(str(err))
            return False

    def start_torrents(self, ids):
        if not self.qbc:
            return False
        try:
            return self.qbc.torrents_resume(torrent_hashes=ids)
        except Exception as err:
            print(str(err))
            return False

    def stop_torrents(self, ids):
        if not self.qbc:
            return False
        try:
            return self.qbc.torrents_pause(torrent_hashes=ids)
        except Exception as err:
            print(str(err))
            return False

    def delete_torrents(self, delete_file, ids):
        if not self.qbc:
            return False
        if not ids:
            return False
        try:
            ret = self.qbc.torrents_delete(delete_files=delete_file, torrent_hashes=ids)
            return ret
        except Exception as err:
            print(str(err))
            return False

    def get_files(self, tid):
        try:
            return self.qbc.torrents_files(torrent_hash=tid)
        except Exception as err:
            print(str(err))
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
            print(str(err))
            return False

    def set_torrent_tag(self, **kwargs):
        pass

    def get_download_dirs(self):
        if not self.qbc:
            return []
        ret_dirs = []
        try:
            categories = self.qbc.torrents_categories(requests_args={'timeout': (3, 5)}) or {}
        except Exception as err:
            print(str(err))
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

    def is_ver_less_4_4(self):
        return v(self.ver) < v("v4.4.0")

    @staticmethod
    def filter_torrent_by_tag(torrents, tag):
        if not tag:
            return torrents
        if not isinstance(tag, list):
            tag = [tag]
        results = []
        for torrent in torrents:
            include_flag = True
            for t in tag:
                if t and t not in torrent.get("tags"):
                    include_flag = False
                    break
            if include_flag:
                results.append(torrent)
        return results

    def change_torrent(self, **kwargs):
        """
        修改种子状态
        """
        pass
