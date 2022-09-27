import os

import qbittorrentapi

import log
from config import Config, PT_TAG
from app.downloader.client.client import IDownloadClient
from app.utils.types import MediaType


class Qbittorrent(IDownloadClient):
    __force_upload = False
    qbc = None

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
            self.__force_upload = qbittorrent.get('force_upload')
            # 解析下载目录
            self.save_path = qbittorrent.get('save_path')
            self.save_containerpath = qbittorrent.get('save_containerpath')

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
                                        REQUESTS_ARGS={'timeout': (3, 10)})
            try:
                qbt.auth_log_in()
            except qbittorrentapi.LoginFailed as e:
                print(e)
            return qbt
        except Exception as err:
            log.error("【QB】qBittorrent连接出错：%s" % str(err))
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
        if not self.qbc:
            return []
        try:
            torrents = self.qbc.torrents_info(torrent_hashes=ids, status_filter=status, tag=tag)
            return torrents or []
        except Exception as err:
            print(str(err))
            return []

    def get_completed_torrents(self, tag=None):
        if not self.qbc:
            return []
        return self.get_torrents(status=["completed"], tag=tag)

    def get_downloading_torrents(self, tag=None):
        if not self.qbc:
            return []
        return self.get_torrents(status=["downloading"], tag=tag)

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
            if self.__force_upload:
                self.qbc.torrents_set_force_start(enable=True, torrent_hashes=ids)
            log.info("【QB】设置qBittorrent种子状态成功")
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
            true_path = torrent.get('content_path', os.path.join(torrent.get('save_path'), torrent.get('name')))
            if not true_path:
                continue
            true_path = self.get_replace_path(true_path)
            trans_tasks.append({'path': true_path, 'id': torrent.get('hash')})
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
                log.info("【QB】%s 做种时间：%s（秒），已达清理条件，进行清理..." % (torrent.get('name'), torrent.get('seeding_time')))
                remove_torrents.append(torrent.get('hash'))
        return remove_torrents

    def get_last_add_torrentid_by_tag(self, tag, status=None):
        """
        根据种子的下载链接获取下载中或暂停的钟子的ID
        :return: 种子ID
        """
        if not status:
            status = ["paused"]
        try:
            torrents = self.get_torrents(status=status, tag=tag)
        except Exception as err:
            print(str(err))
            return None
        if torrents:
            return torrents[0].get("hash")
        else:
            return None

    def add_torrent(self, content, mtype, is_paused=False, tag=None, download_dir=None):
        if not self.qbc or not content:
            return False
        try:
            if mtype == MediaType.TV:
                save_path = self.tv_save_path
                category = self.tv_category
            elif mtype == MediaType.ANIME:
                save_path = self.anime_save_path
                category = self.anime_category
            else:
                save_path = self.movie_save_path
                category = self.movie_category
            use_auto_torrent_management = None
            if download_dir:
                save_path = download_dir
                use_auto_torrent_management = False
            if isinstance(content, str):
                qbc_ret = self.qbc.torrents_add(urls=content,
                                                save_path=save_path,
                                                category=category,
                                                is_paused=is_paused,
                                                tags=tag,
                                                use_auto_torrent_management=use_auto_torrent_management)
            else:
                qbc_ret = self.qbc.torrents_add(torrent_files=content,
                                                save_path=save_path,
                                                category=category,
                                                is_paused=is_paused,
                                                tags=tag,
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
