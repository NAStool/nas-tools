from datetime import datetime
from threading import Event

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.downloader import Downloader
from app.helper import IyuuHelper
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.sites import Sites
from app.utils.types import EventType
from config import Config


class IYUUAutoSeed(_IPluginModule):
    # 插件名称
    module_name = "IYUU自动辅种"
    # 插件描述
    module_desc = "基于IYUU官方Api实现自动辅种。"
    # 插件图标
    module_icon = "iyuu.png"
    # 主题色
    module_color = "#F3B70B"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "iyuuautoseed_"
    # 加载顺序
    module_order = 10
    # 可使用的用户级别
    user_level = 1

    # 私有属性
    _scheduler = None
    downloader = None
    iyuuhelper = None
    # 限速开关
    _cron = None
    _onlyonce = False
    _token = None
    _downloaders = []
    _sites = []
    _notify = False
    # 退出事件
    _event = Event()

    @staticmethod
    def get_fields():
        downloaders = {k: v for k, v in Downloader().get_downloader_conf_simple().items()
                       if v.get("type") in ["qbittorrent", "transmission"] and v.get("enabled")}
        sites = {site.get("id"): site for site in Sites().get_site_dict()}
        return [
            # 同一板块
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '开启自动辅种',
                            'required': "",
                            'tooltip': '开启后，自动监控下载器，对下载完成的任务根据执行周期自动辅种。',
                            'type': 'switch',
                            'id': 'enable',
                        }
                    ],
                    [
                        {
                            'title': '立即运行一次',
                            'required': "",
                            'tooltip': '打开后立即运行一次（点击此对话框的确定按钮后即会运行，周期未设置也会运行），关闭后将仅按照刮削周期运行（同时上次触发运行的任务如果在运行中也会停止）',
                            'type': 'switch',
                            'id': 'onlyonce',
                        }
                    ],
                    [
                        {
                            'title': 'IYUU Token',
                            'required': "required",
                            'tooltip': '登录IYUU使用的Token，用于调用IYUU官方Api',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'token',
                                    'placeholder': 'IYUUxxx',
                                }
                            ]
                        },
                        {
                            'title': '执行周期',
                            'required': "required",
                            'tooltip': '辅种任务执行的时间周期，支持5位cron表达式；应避免任务执行过于频繁',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'cron',
                                    'placeholder': '0 0 0 ? *',
                                }
                            ]
                        }
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '辅种下载器',
                'tooltip': '只有选中的下载器才会执行辅种任务',
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
                'summary': '辅种站点',
                'tooltip': '只有选中的站点才会执行辅种任务，不选则默认为全选',
                'content': [
                    # 同一行
                    [
                        {
                            'id': 'sites',
                            'type': 'form-selectgroup',
                            'content': sites
                        },
                    ]
                ]
            },
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '运行时通知',
                            'required': "",
                            'tooltip': '运行辅助任务后会发送通知（需要打开自定义消息通知）',
                            'type': 'switch',
                            'id': 'notify',
                        }
                    ]
                ]
            }
        ]

    def init_config(self, config=None):
        self.downloader = Downloader()
        # 读取配置
        if config:
            self._onlyonce = config.get("onlyonce")
            self._cron = config.get("cron")
            self._token = config.get("token")
            self._downloaders = config.get("downloaders")
            self._sites = config.get("sites")
            self._notify = config.get("notify")
            if self._token:
                self.iyuuhelper = IyuuHelper(token=self._token)
        # 停止现有任务
        self.stop_service()

        # 启动定时任务 & 立即运行一次
        if self._cron or self._onlyonce:
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            if self._cron:
                self._scheduler.add_job(self.auto_seed, CronTrigger.from_crontab(self._cron))
            if self._onlyonce:
                self._scheduler.add_job(self.auto_seed, 'date',
                                        run_date=datetime.now(tz=pytz.timezone(Config().get_timezone())))
            self._scheduler.print_jobs()
            self._scheduler.start()

            if self._onlyonce:
                self.info(f"辅种服务启动，立即运行一次")
            if self._cron:
                self.info(f"辅种服务启动，周期：{self._cron}")

            # 关闭一次性开关
            self._onlyonce = False
            self.update_config({
                "onlyonce": False,
                "cron": self._cron,
                "token": self._token,
                "downloaders": self._downloaders,
                "sites": self._sites
            })

    def get_state(self):
        return True if self._cron and self._token and self._downloaders else False

    @EventHandler.register(EventType.AutoSeedStart)
    def auto_seed(self, event=None):
        """
        开始辅种
        :param event:
        :return:
        """
        if not self.get_state():
            return
        event_info = event.event_data
        if event_info and event_info.get("hash"):
            # 辅种事件中的一个种子
            downloader = event_info.get("downloader")
            self.__seed_torrent(event_info.get("hash"), downloader)
        else:
            # 扫描下载器辅种
            for downloader in self._downloaders:
                self.info(f"开始扫描下载器：{downloader} ...")
                # 下载器类型
                downloader_type = self.downloader.get_downloader_type(downloader_id=downloader)
                # 获取下载器中已完成的种子
                torrents = self.downloader.get_completed_torrents(downloader_id=downloader)
                if torrents:
                    self.info(f"下载器：{downloader}，已完成种子数：{len(torrents)}")
                else:
                    self.info(f"下载器：{downloader}，没有已完成种子")
                    continue
                for torrent in torrents:
                    # 获取种子hash
                    hash_str = self.__get_hash(torrent, downloader_type)
                    self.__seed_torrent(hash_str, downloader)
                    self.info(f"辅种进度：{torrents.index(torrent) + 1}/{len(torrents)}")

    def __seed_torrent(self, hash_str, downloader):
        """
        执行一个种子的辅种
        """
        self.info(f"开始辅种：{hash_str} ...")
        # TODO 完善辅种逻辑
        # 获取当前hash可辅助的站点和种子信息列表
        # 针对每一个站点的种子，拼装下载链接下载种子，发送至下载器
        self.info(f"下载器：{downloader}，种子：{hash_str}，辅种完成")

    @staticmethod
    def __get_hash(torrent, dl_type):
        """
        获取种子hash
        """
        return torrent.get("hash") if dl_type == "qbittorrent" else torrent.hashString

    def stop_service(self):
        """
        退出插件
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._event.set()
                    self._scheduler.shutdown()
                    self._event.clear()
                self._scheduler = None
        except Exception as e:
            print(str(e))
