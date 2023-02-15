from app.downloader import Downloader
from app.mediaserver import MediaServer
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils import ExceptionUtils
from app.utils.types import DownloaderType, MediaServerType, EventType
from app.helper.security_helper import SecurityHelper
from apscheduler.schedulers.background import BackgroundScheduler
from config import Config

import log


class SpeedLimiter(_IPluginModule):

    # 插件ID
    module_id = "SpeedLimiter"
    # 插件名称
    module_name = "播放限速"
    # 插件描述
    module_desc = "媒体服务器开始播放时，自动对下载器进行限速。"
    # 插件图标
    module_icon = "SpeedLimiter.jpg"
    # 主题色
    module_color = "bg-blue"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "Shurelol"
    # 插件配置项ID前缀
    module_config_prefix = "speedlimit_"

    # 私有属性
    _downloader = None
    _mediaserver = None
    _limit_enabled = False
    _limit_flag = False
    _qb_limit = False
    _qb_download_limit = 0
    _qb_upload_limit = 0
    _qb_upload_ratio = 0
    _tr_limit = False
    _tr_download_limit = 0
    _tr_upload_limit = 0
    _tr_upload_ratio = 0
    _unlimited_ips = {"ipv4": "0.0.0.0/0", "ipv6": "::/0"}
    _auto_limit = False
    _bandwidth = 0

    _scheduler = None

    def __init__(self):
        self.init_config()

    @staticmethod
    def get_fields():
        return {
            "ipv4": {
                "required": False,
                "title": "不限速地址范围",
                "tooltip": "以下地址范围不进行限速处理，一般配置为局域网地址段；多个地址段用,号分隔，配置为0.0.0.0/0,::/0则不做限制",
                "type": "text",
                "placeholder": "192.168.1.0/24",
                "default": "192.168.1.0/24"
            },
            "ipv6": {
                "title": "&nbsp;",
                "required": False,
                "type": "text",
                "placeholder": "IPv6 CIDR"
            },
            "qb_upload": {
                "required": False,
                "title": "Qbittorrent限速",
                "tooltip": "媒体服务器播放时对Qbittorrent下载器进行限速，不限速地址范围除外，0或留空不启用",
                "type": "text",
                "placeholder": "上传限速，KB/s"
            },
            "qb_download": {
                "title": "&nbsp;",
                "required": False,
                "type": "text",
                "placeholder": "下载限速，KB/s"
            },
            "tr_upload": {
                "required": False,
                "title": "Transmission限速",
                "tooltip": "媒体服务器播放时对Transmission下载器进行限速，不限速地址范围除外，0或留空不启用",
                "type": "text",
                "placeholder": "上传限速，Kb/s"
            },
            "tr_download": {
                "title": "&nbsp;",
                "required": False,
                "type": "text",
                "placeholder": "下载限速，Kb/s"
            },
            "bandwidth": {
                "required": False,
                "title": "上行带宽",
                "type": "text",
                "tooltip": "设置后将根据上行带宽、剩余比例、分配比例自动计算限速数值，否则使用Qbittorrent、Transmisson设定的限速数值",
                "placeholder": "Mbps，留空不启用自动限速"
            },
            "residual_ratio": {
                "required": False,
                "title": "剩余比例",
                "tooltip": "上行带宽扣除播放媒体比特率后，乘以剩余比例为剩余带宽分配给下载器，最大为1",
                "type": "text",
                "placeholder": "0.5"
            },
            "allocation": {
                "required": False,
                "title": "分配比例",
                "tooltip": "Qbittorrent与Transmission下载器分配剩余带宽比例，如Qbittorrent下载器无需上传限速，可设为0:x（x可为任意正整数）",
                "type": "text",
                "placeholder": "1:1"
            }
        }

    def init_config(self, config=None):
        self._downloader = Downloader()
        self._mediaserver = MediaServer()

        # 读取配置
        if config:
            try:
                self._bandwidth = int(float(config.get("bandwidth") or 0)) * 1000000
                residual_ratio = float(config.get("residual_ratio") or 1)
                if residual_ratio > 1:
                    residual_ratio = 1
                allocation = (config.get("allocation") or "1:1").split(":")
                if len(allocation) != 2 or not str(allocation[0]).isdigit() or not str(allocation[-1]).isdigit():
                    allocation = ["1", "1"]
                self._qb_upload_ratio = round(int(allocation[0]) / (int(allocation[-1]) + int(allocation[0])) * residual_ratio, 2)
                self._tr_upload_ratio = round(int(allocation[-1]) / (int(allocation[-1]) + int(allocation[0])) * residual_ratio, 2)
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                self._bandwidth = 0
                self._qb_upload_ratio = 0
                self._tr_upload_ratio = 0
            self._auto_limit = True if self._bandwidth and (self._qb_upload_ratio or self._tr_upload_ratio) else False
            try:
                self._qb_download_limit = int(float(config.get("qb_download") or 0)) * 1024
                self._qb_upload_limit = int(float(config.get("qb_upload") or 0)) * 1024
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                self._qb_download_limit = 0
                self._qb_upload_limit = 0
            self._qb_limit = True if self._qb_download_limit or self._qb_upload_limit or self._auto_limit else False
            try:
                self._tr_download_limit = int(float(config.get("tr_download") or 0))
                self._tr_upload_limit = int(float(config.get("tr_upload") or 0))
            except Exception as e:
                self._tr_download_limit = 0
                self._tr_upload_limit = 0
                ExceptionUtils.exception_traceback(e)
            self._tr_limit = True if self._tr_download_limit or self._tr_upload_limit or self._auto_limit else False
            self._limit_enabled = True if self._qb_limit or self._tr_limit else False
            self._unlimited_ips["ipv4"] = config.get("ipv4") or "0.0.0.0/0"
            self._unlimited_ips["ipv6"] = config.get("ipv6") or "::/0"
        else:
            self._limit_enabled = False
        # 移出现有任务
        self.stop_service()
        # 启动限速任务
        if self._limit_enabled:
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            self._scheduler.add_job(func=self.__check_playing_sessions,
                                    args=[self._mediaserver.get_type(), True],
                                    trigger='interval',
                                    seconds=300)
            self._scheduler.print_jobs()
            self._scheduler.start()
            log.info("播放限速服务启动")

    def __start(self):
        """
        开始限速
        """
        if self._qb_limit:
            self._downloader.set_speed_limit(
                downloader=DownloaderType.QB,
                download_limit=self._qb_download_limit,
                upload_limit=self._qb_upload_limit
            )
            if not self._limit_flag:
                log.info(f"【SpeedLimiter】Qbittorrent下载器开始限速")
        if self._tr_limit:
            self._downloader.set_speed_limit(
                downloader=DownloaderType.TR,
                download_limit=self._tr_download_limit,
                upload_limit=self._tr_upload_limit
            )
            if not self._limit_flag:
                log.info(f"【SpeedLimiter】Transmission下载器开始限速")
        self._limit_flag = True

    def __stop(self):
        """
        停止限速
        """
        if self._qb_limit:
            self._downloader.set_speed_limit(
                downloader=DownloaderType.QB,
                download_limit=0,
                upload_limit=0
            )
            if self._limit_flag:
                log.info(f"【SpeedLimiter】Qbittorrent下载器停止限速")
        if self._tr_limit:
            self._downloader.set_speed_limit(
                downloader=DownloaderType.TR,
                download_limit=0,
                upload_limit=0
            )
            if self._limit_flag:
                log.info(f"【SpeedLimiter】Transmission下载器停止限速")
        self._limit_flag = False

    @EventHandler.register(EventType.EmbyWebhook)
    def emby_action(self, event):
        """
        检查emby Webhook消息
        """
        if self._limit_enabled and event.event_data.get("Event") in ["playback.start", "playback.stop"]:
            self.__check_playing_sessions(_mediaserver_type=MediaServerType.EMBY, time_check=False)

    @EventHandler.register(EventType.JellyfinWebhook)
    def jellyfin_action(self, event):
        """
        检查jellyfin Webhook消息
        """
        pass

    @EventHandler.register(EventType.PlexWebhook)
    def plex_action(self, event):
        """
        检查plex Webhook消息
        """
        pass

    def __check_playing_sessions(self, _mediaserver_type, time_check=False):
        """
        检查是否限速
        """
        if _mediaserver_type != self._mediaserver.get_type():
            return
        playing_sessions = self._mediaserver.get_playing_sessions()
        _limit_flag = False
        if _mediaserver_type == MediaServerType.EMBY:
            total_bit_rate = 0
            for session in playing_sessions:
                if not SecurityHelper.allow_access(self._unlimited_ips, session.get("RemoteEndPoint")) \
                        and session.get("NowPlayingItem").get("MediaType") == "Video":
                    total_bit_rate += int(session.get("NowPlayingItem").get("Bitrate")) or 0
            if total_bit_rate:
                _limit_flag = True
                if self._auto_limit:
                    residual__bandwidth = (self._bandwidth - total_bit_rate)
                    if residual__bandwidth < 0:
                        self._qb_upload_limit = 10*1024
                        self._tr_upload_limit = 10
                    else:
                        _qb_upload_limit = residual__bandwidth / 8 / 1024 * self._qb_upload_ratio
                        _tr_upload_limit = residual__bandwidth / 8 / 1024 * self._tr_upload_ratio
                        self._qb_upload_limit = _qb_upload_limit * 1024 if _qb_upload_limit > 10 else 10*1024
                        self._tr_upload_limit = _tr_upload_limit if _tr_upload_limit > 10 else 10
        elif _mediaserver_type == MediaServerType.JELLYFIN:
            pass
        elif _mediaserver_type == MediaServerType.PLEX:
            pass
        else:
            return
        if time_check or self._auto_limit:
            if _limit_flag:
                self.__start()
            else:
                self.__stop()
        else:
            if not self._limit_flag and _limit_flag:
                self.__start()
            elif self._limit_flag and not _limit_flag:
                self.__stop()
            else:
                pass

    def stop_service(self):
        """
        退出插件
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            print(str(e))
