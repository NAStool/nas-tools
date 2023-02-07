from app.conf import SystemConfig
from app.downloader import Downloader
from app.mediaserver import MediaServer
from app.utils import ExceptionUtils
from app.utils.commons import singleton
from app.utils.types import DownloaderType, MediaServerType
from app.helper.security_helper import SecurityHelper
from apscheduler.schedulers.background import BackgroundScheduler
from config import Config

import log


@singleton
class SpeedLimiter:
    downloader = None
    mediaserver = None
    limit_enabled = False
    limit_flag = False
    qb_limit = False
    qb_download_limit = 0
    qb_upload_limit = 0
    tr_limit = False
    tr_download_limit = 0
    tr_upload_limit = 0
    unlimited_ips = {"ipv4": "0.0.0.0/0", "ipv6": "::/0"}

    _scheduler = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.downloader = Downloader()
        self.mediaserver = MediaServer()

        config = SystemConfig().get_system_config("SpeedLimit")
        if config:
            try:
                self.qb_download_limit = int(float(config.get("qb_download") or 0))*1024
                self.qb_upload_limit = int(float(config.get("qb_upload") or 0))*1024
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
            self.qb_limit = True if self.qb_download_limit or self.qb_upload_limit else False
            try:
                self.tr_download_limit = int(float(config.get("tr_download") or 0))
                self.tr_upload_limit = int(float(config.get("tr_upload") or 0))
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
            self.tr_limit = True if self.tr_download_limit or self.tr_upload_limit else False
            self.limit_enabled = True if self.qb_limit or self.tr_limit else False
            self.unlimited_ips["ipv4"] = config.get("ipv4") or "0.0.0.0/0"
            self.unlimited_ips["ipv6"] = config.get("ipv6") or "::/0"
        else:
            self.limit_enabled = False
        # 移出现有任务
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
        # 启动限速任务
        if self.limit_enabled:
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            self._scheduler.add_job(func=self.__check_playing_sessions,
                                    args=[self.mediaserver.get_type(), True],
                                    trigger='interval',
                                    seconds=300)
            self._scheduler.print_jobs()
            self._scheduler.start()
            log.info("播放限速服务启动")

    def __start(self):
        """
        开始限速
        """
        if self.qb_limit:
            self.downloader.set_speed_limit(
                downloader=DownloaderType.QB,
                download_limit=self.qb_download_limit,
                upload_limit=self.qb_upload_limit
            )
            log.info(f"【SpeedLimiter】Qbittorrent下载器开始限速")
        if self.tr_limit:
            self.downloader.set_speed_limit(
                downloader=DownloaderType.TR,
                download_limit=self.tr_download_limit,
                upload_limit=self.tr_upload_limit
            )
            log.info(f"【SpeedLimiter】Transmission下载器开始限速")
        self.limit_flag = True

    def __stop(self):
        """
        停止限速
        """
        if self.qb_limit:
            self.downloader.set_speed_limit(
                downloader=DownloaderType.QB,
                download_limit=0,
                upload_limit=0
            )
            log.info(f"【SpeedLimiter】Qbittorrent下载器停止限速")
        if self.tr_limit:
            self.downloader.set_speed_limit(
                downloader=DownloaderType.TR,
                download_limit=0,
                upload_limit=0
            )
            log.info(f"【SpeedLimiter】Transmission下载器停止限速")
        self.limit_flag = False

    def emby_action(self, message):
        """
        检查emby Webhook消息
        """
        if self.limit_enabled and message.get("Event") in ["playback.start", "playback.stop"]:
            self.__check_playing_sessions(mediaserver_type=MediaServerType.EMBY, time_check=False)

    def jellyfin_action(self, message):
        """
        检查jellyfin Webhook消息
        """
        pass

    def plex_action(self, message):
        """
        检查plex Webhook消息
        """
        pass

    def __check_playing_sessions(self, mediaserver_type, time_check=False):
        """
        检查是否限速
        """
        if mediaserver_type != self.mediaserver.get_type():
            return
        playing_sessions = self.mediaserver.get_playing_sessions()
        limit_flag = False
        match mediaserver_type:
            case MediaServerType.EMBY:
                for session in playing_sessions:
                    if not SecurityHelper.allow_access(self.unlimited_ips, session.get("RemoteEndPoint")) \
                            and "Video" in session.get("PlayableMediaTypes"):
                        limit_flag = True
                        break
            case MediaServerType.JELLYFIN:
                pass
            case MediaServerType.PLEX:
                pass
            case _:
                pass
        if time_check:
            if limit_flag:
                self.__start()
            else:
                self.__stop()
        else:
            if not self.limit_flag and limit_flag:
                self.__start()
            elif self.limit_flag and not limit_flag:
                self.__stop()
            else:
                pass






