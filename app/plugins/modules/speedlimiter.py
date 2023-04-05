import time

from apscheduler.schedulers.background import BackgroundScheduler

from app.downloader import Downloader
from app.helper.security_helper import SecurityHelper
from app.mediaserver import MediaServer
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils import ExceptionUtils
from app.utils.types import MediaServerType, EventType
from config import Config


class SpeedLimiter(_IPluginModule):
    # 插件名称
    module_name = "播放限速"
    # 插件描述
    module_desc = "媒体服务器开始播放时，自动对下载器进行限速。"
    # 插件图标
    module_icon = "SpeedLimiter.jpg"
    # 主题色
    module_color = "#183883"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "Shurelol"
    # 作者主页
    author_url = "https://github.com/Shurelol"
    # 插件配置项ID前缀
    module_config_prefix = "speedlimit_"
    # 加载顺序
    module_order = 1
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    _downloader = None
    _mediaserver = None
    _scheduler = None
    # 任务执行间隔
    _interval = 300

    # 限速开关
    _limit_enabled = False
    _limit_flag = False
    # 限速设置
    _download_limit = 0
    _upload_limit = 0
    # 不限速地址
    _unlimited_ips = {"ipv4": "0.0.0.0/0", "ipv6": "::/0"}
    # 自动限速
    _auto_limit = False
    _auto_upload_limit = 0
    # 总速宽
    _bandwidth = 0
    _residual_ratio = 0
    # 限速下载器
    _limited_downloader_ids = []

    @staticmethod
    def get_fields():
        downloaders = {k: v for k, v in Downloader().get_downloader_conf_simple().items()
                       if v.get("type") in ["qbittorrent", "transmission"] and v.get("enabled")}
        return [
            # 同一板块
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '上传下载限速',
                            'required': "",
                            'tooltip': '媒体服务器播放时对选取的下载器进行限速，不限速地址范围除外，0或留空不启用',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'upload_limit',
                                    'placeholder': '上传限速，KB/s'
                                },
                                {
                                    'id': 'download_limit',
                                    'placeholder': '下载限速，KB/s'
                                }
                            ]

                        },
                        {
                            'title': '不限速地址范围',
                            'required': 'required',
                            'tooltip': '以下地址范围不进行限速处理，一般配置为局域网地址段；多个地址段用,号分隔，配置为0.0.0.0/0,::/0则不做限制',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'ipv4',
                                    'placeholder': '192.168.1.0/24',
                                },
                                {
                                    'id': 'ipv6',
                                    'placeholder': 'FE80::/10',
                                }
                            ]
                        },
                        {
                            'title': '自动限速设置',
                            'required': "",
                            'tooltip': '设置后根据上行带宽及剩余比例自动计算限速数值,默认下载器占据3/4',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'bandwidth',
                                    'placeholder': 'Mbps，留空不启用自动限速'
                                },
                                {
                                    'id': 'residual_ratio',
                                    'placeholder': '0.5'
                                }
                            ]
                        }
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '下载器',
                'tooltip': '设置后根据上行带宽及剩余比例自动计算限速数值',
                'content': [
                    # 同一行
                    [
                        {
                            'id': 'downloaders',
                            'type': 'form-selectgroup',
                            'content': downloaders
                        },
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '任务间隔',
                'tooltip': '设置任务执行间隔,单位为秒，默认时间300秒；应优先通过配置Emby/Jellyfin/Plex的webhook发送播放事件给NAStool来触发自动限速，而非定时执行检查',
                'content': [
                    [
                        {
                            'required': "",
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'interval',
                                    'placeholder': '300'
                                }
                            ]
                        }
                    ]
                ]
            }
        ]

    def init_config(self, config=None):
        self._downloader = Downloader()
        self._mediaserver = MediaServer()

        # 读取配置
        if config:
            try:
                # 总带宽
                self._bandwidth = int(float(config.get("bandwidth") or 0)) * 1000000
                # 剩余比例
                residual_ratio = float(config.get("residual_ratio") or 1)
                if residual_ratio > 1:
                    residual_ratio = 1
                self._residual_ratio = residual_ratio
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                self._bandwidth = 0
                self._residual_ratio = 0
            # 自动限速开关
            self._auto_limit = True if self._bandwidth and self._residual_ratio else False

            try:
                # 下载限速
                self._download_limit = int(float(config.get("download_limit") or 0))
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                self._download_limit = 0
            
            try:
                # 上传限速
                self._upload_limit = int(float(config.get("upload_limit") or 0))
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                self._upload_limit = 0

            # 限速服务开关
            self._limit_enabled = True if self._download_limit or self._upload_limit or self._auto_limit else False

            # 不限速地址
            self._unlimited_ips["ipv4"] = config.get("ipv4") or "0.0.0.0/0"
            self._unlimited_ips["ipv6"] = config.get("ipv6") or "::/0"

            # 任务时间间隔
            self._interval = int(config.get("interval") or "300")

            # 下载器
            self._limited_downloader_ids = config.get("downloaders") or []
        else:
            # 限速关闭
            self._limit_enabled = False

        # 移出现有任务
        self.stop_service()

        # 启动限速任务
        if self._limit_enabled:
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            self._scheduler.add_job(func=self.__check_playing_sessions,
                                    args=[self._mediaserver.get_type(), True],
                                    trigger='interval',
                                    seconds=self._interval)
            self._scheduler.print_jobs()
            self._scheduler.start()
            self.info("播放限速服务启动")

    def get_state(self):
        return self._limit_enabled

    def __start(self, limited_downloader_confs, limited_default_downloader_id):
        """
        开始限速
        """
        if not limited_downloader_confs:
            return
        count = len(limited_downloader_confs)
        upload_limit = self._upload_limit
        download_limit = self._download_limit
        for limited_downloader_conf in limited_downloader_confs:
            did = str(limited_downloader_conf.get("id"))
            if self._auto_limit:
                if limited_default_downloader_id:
                    if did == str(limited_default_downloader_id):
                        upload_limit = int(self._auto_upload_limit * 0.75)
                    else:
                        upload_limit = int(self._auto_upload_limit * 0.25 / (count - 1))
                else:
                    upload_limit = int(self._auto_upload_limit / count)
                if upload_limit < 10:
                    upload_limit = 10
            self._downloader.set_speed_limit(
                downloader_id=limited_downloader_conf.get("id"),
                download_limit=download_limit,
                upload_limit=upload_limit
            )
            if not self._limit_flag:
                self.info(f"下载器 {limited_downloader_conf.get('name')} 开始限速")
        self._limit_flag = True

    def __stop(self, limited_downloader_confs=None):
        """
        停止限速
        """
        if not limited_downloader_confs:
            return
        for limited_downloader_conf in limited_downloader_confs:
            self._downloader.set_speed_limit(
                downloader_id=limited_downloader_conf.get("id"),
                download_limit=0,
                upload_limit=0
            )
            if self._limit_flag:
                self.info(f"下载器 {limited_downloader_conf.get('name')} 停止限速")
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
        if self._limit_enabled and event.event_data.get("NotificationType") in ["PlaybackStart", "PlaybackStop"]:
            self.__check_playing_sessions(_mediaserver_type=MediaServerType.JELLYFIN, time_check=False)

    @EventHandler.register(EventType.PlexWebhook)
    def plex_action(self, event):
        """
        检查plex Webhook消息
        """
        if self._limit_enabled and event.event_data.get("event") in ["media.play", "media.stop"]:
            self.__check_playing_sessions(_mediaserver_type=MediaServerType.PLEX, time_check=False)

    def __check_playing_sessions(self, _mediaserver_type, time_check=False):
        """
        检查是否限速
        """

        def __calc_limit(_total_bit_rate):
            """
            计算限速
            """
            if not _total_bit_rate:
                return False
            if self._auto_limit:
                residual__bandwidth = (self._bandwidth - _total_bit_rate)
                if residual__bandwidth < 0:
                    self._auto_upload_limit = 10
                else:
                    self._auto_upload_limit = residual__bandwidth / 8 / 1024 * self._residual_ratio
            return True

        if _mediaserver_type != self._mediaserver.get_type():
            return
        # plex的webhook时尝试sleep一段时间,以保证get_playing_sessions获取到正确的值
        if not time_check and _mediaserver_type == MediaServerType.PLEX:
            time.sleep(3)
        # 当前播放的会话
        playing_sessions = self._mediaserver.get_playing_sessions()
        # 本次是否限速
        _limit_flag = False
        # 当前播放的总比特率
        total_bit_rate = 0
        if _mediaserver_type == MediaServerType.EMBY:
            for session in playing_sessions:
                if not SecurityHelper.allow_access(self._unlimited_ips, session.get("RemoteEndPoint")) \
                        and session.get("NowPlayingItem", {}).get("MediaType") == "Video":
                    total_bit_rate += int(session.get("NowPlayingItem", {}).get("Bitrate") or 0)
        elif _mediaserver_type == MediaServerType.JELLYFIN:
            for session in playing_sessions:
                if not SecurityHelper.allow_access(self._unlimited_ips, session.get("RemoteEndPoint")) \
                        and session.get("NowPlayingItem", {}).get("MediaType") == "Video":
                    media_streams = session.get("NowPlayingItem", {}).get("MediaStreams") or []
                    for media_stream in media_streams:
                        total_bit_rate += int(media_stream.get("BitRate") or 0)
        elif _mediaserver_type == MediaServerType.PLEX:
            for session in playing_sessions:
                if not SecurityHelper.allow_access(self._unlimited_ips, session.get("address")) \
                        and session.get("type") == "Video":
                    total_bit_rate += int(session.get("bitrate") or 0)
        else:
            return

        # 计算限速标志及速率
        _limit_flag = __calc_limit(total_bit_rate)

        # 限速下载器
        downloader_confs = self._downloader.get_downloader_conf_simple()
        default_downloader_id = self._downloader.default_downloader_id
        limited_downloader_confs = []
        limited_default_downloader_id = 0
        for downloader_conf in downloader_confs.values():
            did = downloader_conf.get("id")
            if str(did) in self._limited_downloader_ids:
                limited_downloader_confs.append(downloader_conf)
            if str(did) == str(default_downloader_id):
                limited_default_downloader_id = did

        # 启动限速
        if time_check or self._auto_limit:
            if _limit_flag:
                self.__start(limited_downloader_confs, limited_default_downloader_id)
            else:
                self.__stop(limited_downloader_confs)
        else:
            if not self._limit_flag and _limit_flag:
                self.__start(limited_downloader_confs, limited_default_downloader_id)
            elif self._limit_flag and not _limit_flag:
                self.__stop(limited_downloader_confs)
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
