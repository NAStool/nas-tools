import os.path
import transmission_rpc
from datetime import datetime
import log
from config import Config
from pt.client.client import IDownloadClient
from utils.types import MediaType


class Transmission(IDownloadClient):
    
    # 参考transmission web，仅查询需要的参数，加速种子检索
    __trarg = ["id", "name", "status", "labels", "hashString", "totalSize", "percentDone", "addedDate", "trackerStats",
               "leftUntilDone", "rateDownload", "rateUpload", "recheckProgress", "rateDownload", "rateUpload",
               "peersGettingFromUs", "peersSendingToUs", "uploadRatio", "uploadedEver", "downloadedEver", "downloadDir",
               "error", "errorString", "doneDate", "queuePosition", "activityDate"]
    trc = None

    def get_config(self):
        # 读取配置文件
        config = Config()
        transmission = config.get_config('transmission')
        if transmission:
            self.host = transmission.get('trhost')
            self.port = int(transmission.get('trport'))
            self.username = transmission.get('trusername')
            self.password = transmission.get('trpassword')
            self.save_path = transmission.get('save_path')
            self.save_containerpath = transmission.get('save_containerpath')

    def connect(self):
        """
        连接
        """
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
                                          timeout=10)
            return trt
        except Exception as err:
            log.error("【TR】transmission连接出错：%s" % str(err))
            return None

    def get_status(self):
        """
        检查连通性
        :return: True、Fals
        """
        return True if self.trc else False

    def get_torrents(self, ids=None, status=None, tag=None):
        """
        按条件读取种子信息
        :param ids: ID列表，为空则读取所有
        :param status: 种子状态过滤，为空则读取所有
        :param tag: 标签过滤
        """
        if not self.trc:
            return []
        if isinstance(ids, list):
            ids = [int(x) for x in ids]
        elif ids:
            ids = int(ids)
        torrents = self.trc.get_torrents(ids=ids, arguments=self.__trarg)
        if status and not isinstance(status, list):
            status = [status]
        ret_torrents = []
        for torrent in torrents:
            if status and torrent.status not in status:
                continue
            labels = torrent.labels if hasattr(torrent, "labels") else []
            if tag and tag not in labels:
                continue
            ret_torrents.append(torrent)
        return ret_torrents

    def get_completed_torrents(self, tag=None):
        """
        读取完成的种子信息
        :return: 种子信息列表
        """
        if not self.trc:
            return []
        return self.get_torrents(status=["seeding", "seed_pending"], tag=tag)

    def get_downloading_torrents(self, tag=None):
        """
        读取下载中的种子信息
        :return: 种子信息列表
        """
        if not self.trc:
            return []
        return self.get_torrents(status=["downloading", "download_pending", "stopped"], tag=tag)

    def set_torrents_status(self, ids):
        """
        迁移完成后设置种子状态，设置标签为已整理
        :param ids: 种子ID列表
        """
        if not self.trc:
            return
        if isinstance(ids, list):
            ids = [int(x) for x in ids]
        elif ids:
            ids = int(ids)
        # 打标签
        self.trc.change_torrent(labels=["已整理"], ids=ids)
        log.info("【TR】设置transmission种子标签成功")

    def set_torrent_tag(self, tid, tag):
        """
        给种子设置标签
        :param tid: 种子ID
        :param tag: 标签
        """
        if not tid or not tag:
            return
        self.trc.change_torrent(labels=[tag], ids=int(tid))

    def get_transfer_task(self, tag):
        """
        查询可以转移的种子列表，用于定时服务调用
        :return: 种子对应的文件路径清单
        """
        # 处理所有任务
        torrents = self.get_completed_torrents(tag=tag)
        trans_tasks = []
        for torrent in torrents:
            # 3.0版本以下的Transmission没有labels
            if not hasattr(torrent, "labels"):
                log.warn(f"【TR】当前transmission版本可能过低，无labels属性，请安装3.0以上版本！")
                break

            if torrent.labels and "已整理" in torrent.labels:
                continue
            true_path = os.path.join(torrent.download_dir, torrent.name)
            if not true_path:
                continue
            true_path = self.get_replace_path(true_path)
            trans_tasks.append({'path': true_path, 'id': torrent.id})
        return trans_tasks

    def get_remove_torrents(self, seeding_time, tag):
        """
        查询可以清单的种子
        :return: 可以清理的种子ID列表
        """
        if not seeding_time:
            return []
        torrents = self.get_completed_torrents(tag=tag)
        remove_torrents = []
        for torrent in torrents:
            date_done = torrent.date_done
            if not date_done:
                date_done = torrent.date_added
            if not date_done:
                continue
            date_now = datetime.now().astimezone()
            torrent_time = (date_now - date_done).seconds
            if torrent_time > int(seeding_time):
                log.info("【PT】%s 做种时间：%s（秒），已达清理条件，进行清理..." % (torrent.name, torrent_time))
                remove_torrents.append(torrent.id)
        return remove_torrents

    def add_torrent(self, content, mtype, is_paused=None, **kwargs):
        """
        添加下载
        :param content: 种子数据
        :param mtype: 媒体类型：电影、电视剧或动漫，用于选择下载保存目录
        :param is_paused: 是否默认暂停，只有需要进行下一步控制时，才会添加种子时默认暂停
        """
        if mtype == MediaType.TV:
            return self.trc.add_torrent(torrent=content, download_dir=self.tv_save_path, paused=is_paused)
        elif mtype == MediaType.MOVIE:
            return self.trc.add_torrent(torrent=content, download_dir=self.movie_save_path, paused=is_paused)
        else:
            return self.trc.add_torrent(torrent=content, download_dir=self.anime_save_path, paused=is_paused)

    def start_torrents(self, ids):
        """
        下载控制：开始
        """
        if not self.trc:
            return False
        if isinstance(ids, list):
            ids = [int(x) for x in ids]
        elif ids:
            ids = int(ids)
        return self.trc.start_torrent(ids=ids)

    def stop_torrents(self, ids):
        """
        下载控制：停止
        """
        if not self.trc:
            return False
        if isinstance(ids, list):
            ids = [int(x) for x in ids]
        elif ids:
            ids = int(ids)
        return self.trc.stop_torrent(ids=ids)

    def delete_torrents(self, delete_file, ids):
        """
        删除种子
        """
        if not self.trc:
            return False
        if not ids:
            return False
        if isinstance(ids, list):
            ids = [int(x) for x in ids]
        elif ids:
            ids = int(ids)
        return self.trc.remove_torrent(delete_data=delete_file, ids=ids)

    def get_files(self, tid):
        """
        获取种子文件列表
        """
        if not tid:
            return None
        torrent = self.trc.get_torrent(tid)
        if torrent:
            return torrent.files()
        else:
            return None

    def set_files(self, file_items):
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
        if not file_items:
            return False
        self.trc.set_files(file_items)
        return True

    def get_pt_data(self):
        """
        获取PT下载软件中当前上传和下载量
        :return: 上传量、下载量
        """
        if not self.trc:
            return 0, 0
        session = self.trc.session_stats()
        for key, value in session.items():
            if key == "current_stats":
                return value.get("uploadedBytes"), value.get("downloadedBytes")
        return 0, 0
