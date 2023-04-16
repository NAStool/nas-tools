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
    _download_unlimit = 0
    _upload_unlimit = 0
    # 不限速地址
    _unlimited_ips = {"ipv4": "0.0.0.0/0", "ipv6": "::/0"}
    # 自动限速
    _auto_limit = False
    _auto_upload_limit = 0
    # 总速宽
    _bandwidth = 0
    _allocation_ratio = 0
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
                            'title': '播放时限速',
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
                            'title': '未播放时限速',
                            'required': "",
                            'tooltip': '媒体服务器未播放时对选取的下载器进行限速，0或留空不启用',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'upload_unlimit',
                                    'placeholder': '上传限速，KB/s'
                                },
                                {
                                    'id': 'download_unlimit',
                                    'placeholder': '下载限速，KB/s'
                                }
                            ]
                        },
                        {
                            'title': '智能上传限速设置',
                            'required': "",
                            'tooltip': '设置上行带宽后，媒体服务器播放时根据上行带宽和媒体播放占用带宽计算上传限速数值。多个下载器设置分配比例，如两个下载器设置1:2,留空均分',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'bandwidth',
                                    'placeholder': '上行带宽，Mbps'
                                },
                                {
                                    'id': 'allocation_ratio',
                                    'placeholder': '分配比例，1:1:1'
                                }
                            ]
                        }
                    ]
                ]
            },
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '不限速地址范围',
                            'required': 'required',
                            'tooltip': '以下地址范围不进行限速处理，一般配置为局域网地址段；多个地址段用,号分隔，留空或配置为0.0.0.0/0,::/0则不做限制',
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
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                self._bandwidth = 0
            # 自动限速开关
            self._auto_limit = True if self._bandwidth else False

            try:
                # 播放下载限速
                self._download_limit = int(float(config.get("download_limit") or 0))
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                self._download_limit = 0
            
            try:
                # 播放上传限速
                self._upload_limit = int(float(config.get("upload_limit") or 0))
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                self._upload_limit = 0

            # 限速服务开关
            self._limit_enabled = True if self._download_limit or self._upload_limit or self._auto_limit else False

            # 下载器
            self._limited_downloader_ids = config.get("downloaders") or []
            if not self._limited_downloader_ids:
                self._limit_enabled = False

            # 不限速地址
            self._unlimited_ips["ipv4"] = config.get("ipv4") or "0.0.0.0/0"
            self._unlimited_ips["ipv6"] = config.get("ipv6") or "::/0"
            if "0.0.0.0/0" in self._unlimited_ips["ipv4"] and "::/0" in self._unlimited_ips["ipv6"]:
                self._limit_enabled = False

            try:
                # 未播放下载限速
                self._download_unlimit = int(float(config.get("download_unlimit") or 0))
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                self._download_unlimit = 0

            try:
                # 未播放上传限速
                self._upload_unlimit = int(float(config.get("upload_unlimit") or 0))
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                self._upload_unlimit = 0

            # 任务时间间隔
            self._interval = int(config.get("interval") or "300")

            # 下载器限速分配比例
            self._allocation_ratio = config.get("allocation_ratio").split(":") or []
            try:
                self._allocation_ratio = [int(i) for i in self._allocation_ratio]
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                self.warn("分配比例含有:外非数字字符，执行均分")
                self._allocation_ratio = []

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

    def __start(self, downloader_confs, allocation_ratio):
        """
        播放限速
        """
        if not downloader_confs:
            return
        allocation_count = sum(allocation_ratio) if allocation_ratio else len(downloader_confs)
        upload_limit = self._upload_limit
        download_limit = self._download_limit
        for i in range(len(downloader_confs)):
            downloader_conf = downloader_confs[i]
            if self._auto_limit:
                if not allocation_ratio:
                    upload_limit = int(self._auto_upload_limit / allocation_count)
                else:
                    upload_limit = int(self._auto_upload_limit * allocation_ratio[i] / allocation_count)
            if upload_limit < 10:
                upload_limit = 10
            self._downloader.set_speed_limit(
                downloader_id=downloader_conf.get("id"),
                download_limit=download_limit,
                upload_limit=upload_limit
            )
            if upload_limit and download_limit:
                limit_info = f"上传：{upload_limit}KB/s 下载：{download_limit}KB/s"
            elif upload_limit:
                limit_info = f"上传：{upload_limit}KB/s"
            elif download_limit:
                limit_info = f"下载：{download_limit}KB/s"
            else:
                limit_info = "不限速"
            self.info(f"下载器 {downloader_conf.get('name')} {limit_info}")
        self._limit_flag = True

    def __stop(self, downloader_confs):
        """
        未播放限速
        """
        if not downloader_confs:
            return
        upload_limit = self._upload_unlimit
        download_limit = self._download_unlimit
        if upload_limit and download_limit:
            limit_info = f"上传：{upload_limit}KB/s 下载：{download_limit}KB/s"
        elif upload_limit:
            limit_info = f"上传：{upload_limit}KB/s"
        elif download_limit:
            limit_info = f"下载：{download_limit}KB/s"
        else:
            limit_info = "不限速"
        for downloader_conf in downloader_confs:
            self._downloader.set_speed_limit(
                downloader_id=downloader_conf.get("id"),
                download_limit=download_limit,
                upload_limit=upload_limit
            )
            self.info(f"下载器 {downloader_conf.get('name')} {limit_info}")
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
                residual_bandwidth = (self._bandwidth - _total_bit_rate)
                if residual_bandwidth < 0:
                    self._auto_upload_limit = 10
                else:
                    self._auto_upload_limit = residual_bandwidth / 8 / 1024
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
        limited_downloader_confs = []
        limited_allocation_ratio = []
        # 检查分配比例配置
        if self._allocation_ratio and len(self._allocation_ratio) != len(self._limited_downloader_ids):
            self._allocation_ratio = []
            self.warn("分配比例配置错误，与限速下载器数量不一致，执行均分")

        downloader_confs_dict = self._downloader.get_downloader_conf_simple()
        for i in range(len(self._limited_downloader_ids)):
            did = self._limited_downloader_ids[i]
            if downloader_confs_dict.get(did) and downloader_confs_dict.get(did).get("enabled"):
                limited_downloader_confs.append(downloader_confs_dict.get(self._limited_downloader_ids[i]))
                if self._allocation_ratio:
                    limited_allocation_ratio.append(self._allocation_ratio[i])
        if not limited_downloader_confs:
            self.warn("未有启用的限速下载器")
            return

        # 启动限速
        if time_check or self._auto_limit:
            if _limit_flag:
                self.__start(limited_downloader_confs, limited_allocation_ratio)
            else:
                self.__stop(limited_downloader_confs)
        else:
            if not self._limit_flag and _limit_flag:
                self.__start(limited_downloader_confs, limited_allocation_ratio)
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
