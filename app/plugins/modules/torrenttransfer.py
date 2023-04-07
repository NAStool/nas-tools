import re
from datetime import datetime
from threading import Event

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from lxml import etree

from app.downloader import Downloader
from app.helper import IyuuHelper
from app.media.meta import MetaInfo
from app.message import Message
from app.plugins.modules._base import _IPluginModule
from app.sites import Sites
from app.utils import RequestUtils
from app.utils.types import DownloaderType
from config import Config


class TorrentTransfer(_IPluginModule):
    # 插件名称
    module_name = "自动转种"
    # 插件描述
    module_desc = "定期转移下载器中的做种任务到另一个下载器。"
    # 插件图标
    module_icon = "torrenttransfer.jpg"
    # 主题色
    module_color = "#272636"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "torrenttransfer_"
    # 加载顺序
    module_order = 20
    # 可使用的用户级别
    user_level = 1

    # 私有属性
    _scheduler = None
    downloader = None
    sites = None
    message = None
    # 限速开关
    _enable = False
    _cron = None
    _onlyonce = False
    _fromdownloader = None
    _todownloader = None
    _frompath = None
    _topath = None
    _notify = False
    _nolabels = None
    _nopaths = None
    _deletesource = False
    _fromtorrentpath = None
    _totorrentpath = None
    # 退出事件
    _event = Event()

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
                            'title': '开启自动转种',
                            'required': "",
                            'tooltip': '开启后，定期将源下载器中已完成的种子任务迁移至目的下载器。',
                            'type': 'switch',
                            'id': 'enable',
                        }
                    ],
                    [
                        {
                            'title': '执行周期',
                            'required': "required",
                            'tooltip': '设置转种任务执行的时间周期，支持5位cron表达式；应避免任务执行过于频繁',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'cron',
                                    'placeholder': '0 0 0 ? *',
                                }
                            ]
                        },
                        {
                            'title': '不转种标签',
                            'required': "",
                            'tooltip': '下载器中的种子有以下标签时不进行转种，多个标签使用英文,分隔',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'nolabels',
                                    'placeholder': '使用,分隔多个标签',
                                }
                            ]
                        }
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '源下载器',
                'tooltip': '只有选中的下载器才会执行转种任务，只能选择一个',
                'content': [
                    # 同一行
                    [
                        {
                            'id': 'fromdownloader',
                            'type': 'form-selectgroup',
                            'content': downloaders
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
                            'title': '源下载器种子文件保存路径',
                            'required': "required",
                            'tooltip': '源下载器保存种子文件的路径，需要是NAStool可访问的路径，QB一般为BT_backup，TR一般为torrents',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'fromtorrentpath',
                                    'placeholder': 'BT_backup|torrents',
                                }
                            ]
                        },
                        {
                            'title': '源下载器数据文件根路径',
                            'required': "required",
                            'tooltip': '源下载器中的种子数据文件保存根目录路径，必须是下载器能访问的路径，用于转移时替换种子数据文件路径使用',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'frompath',
                                    'placeholder': '根路径',
                                }
                            ]
                        }
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '目的下载器',
                'tooltip': '将做种任务转移到这个下载器，只能选择一个',
                'content': [
                    # 同一行
                    [
                        {
                            'id': 'todownloader',
                            'type': 'form-selectgroup',
                            'content': downloaders
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
                            'title': '目的下载器种子文件保存路径',
                            'required': "required",
                            'tooltip': '目的下载器保存种子文件的路径，需要是NAStool可访问的路径，QB一般为BT_backup，TR一般为torrents',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'totorrentpath',
                                    'placeholder': 'BT_backup|torrents',
                                }
                            ]
                        },
                        {
                            'title': '目的下载器数据文件根路径',
                            'required': "required",
                            'tooltip': '目的下载器的种子数据文件保存目录根路径，必须是下载器能访问的路径，将会使用该路径替换源下载器中种子数据文件保存路径中的源目录根路径，替换后的新路径做为目的下载器种子数据文件的保存路径，需要准确填写，否则可能导致转种后找不到数据文件，从而触发重新下载',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'topath',
                                    'placeholder': '根路径',
                                }
                            ]
                        }
                    ]
                ]
            },
            {
                'type': 'div',
                'content': [
                    [
                        {
                            'title': '不转种目录',
                            'required': "",
                            'tooltip': '以下目录中的种子不进行转种，指下载器可访问的目录，每一行一个目录',
                            'type': 'textarea',
                            'content': {
                                'id': 'nopaths',
                                'placeholder': '每一行一个目录',
                                'rows': 3
                            }
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
                            'title': '删除源种子',
                            'required': "",
                            'tooltip': '转移成功后删除源下载器中的种子，首次运行请不要打开，避免种子丢失',
                            'type': 'switch',
                            'id': 'deletesource',
                        },
                        {
                            'title': '运行时通知',
                            'required': "",
                            'tooltip': '运行辅助任务后会发送通知（需要打开自定义消息通知）',
                            'type': 'switch',
                            'id': 'notify',
                        },
                        {
                            'title': '立即运行一次',
                            'required': "",
                            'tooltip': '打开后立即运行一次（点击此对话框的确定按钮后即会运行，周期未设置也会运行），关闭后将仅按照刮削周期运行（同时上次触发运行的任务如果在运行中也会停止）',
                            'type': 'switch',
                            'id': 'onlyonce',
                        }
                    ]
                ]
            }
        ]

    def init_config(self, config=None):
        self.downloader = Downloader()
        self.message = Message()
        # 读取配置
        if config:
            self._enable = config.get("enable")
            self._onlyonce = config.get("onlyonce")
            self._cron = config.get("cron")
            self._notify = config.get("notify")
            self._nolabels = config.get("nolabels")
            self._frompath = config.get("frompath")
            self._topath = config.get("topath")
            self._fromdownloader = config.get("fromdownloader")
            self._todownloader = config.get("todownloader")
            self._deletesource = config.get("deletesource")
            self._fromtorrentpath = config.get("fromtorrentpath")
            self._totorrentpath = config.get("totorrentpath")

        # 停止现有任务
        self.stop_service()

        # 启动定时任务 & 立即运行一次
        if self.get_state() or self._onlyonce:
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            if self._cron:
                self.info(f"转种服务启动，周期：{self._cron}")
                self._scheduler.add_job(self.transfer,
                                        CronTrigger.from_crontab(self._cron))
            if self._onlyonce:
                self.info(f"转种服务启动，立即运行一次")
                self._scheduler.add_job(self.transfer, 'date',
                                        run_date=datetime.now(tz=pytz.timezone(Config().get_timezone())))
                # 关闭一次性开关
                self._onlyonce = False
                self.update_config({
                    "enable": self._enable,
                    "onlyonce": self._onlyonce,
                    "cron": self._cron,
                    "notify": self._notify,
                    "nolabels": self._nolabels,
                    "frompath": self._frompath,
                    "topath": self._topath,
                    "fromdownloader": self._fromdownloader,
                    "todownloader": self._todownloader,
                    "deletesource": self._deletesource,
                    "fromtorrentpath": self._fromtorrentpath,
                    "totorrentpath": self._totorrentpath
                })
            if self._scheduler.get_jobs():
                # 启动服务
                self._scheduler.print_jobs()
                self._scheduler.start()

    def get_state(self):
        return True if self._enable \
                       and self._cron \
                       and self._fromdownloader \
                       and self._todownloader else False

    def transfer(self):
        """
        开始转种
        """
        if not self._enable or not self._fromdownloader or not self._todownloader:
            self.warn("转种服务未启用或未配置")
            return
        self.info("开始转种任务 ...")
        # TODO 转种
        
        self.info("转种任务执行完成")

    @staticmethod
    def __get_hash(torrent, dl_type):
        """
        获取种子hash
        """
        try:
            return torrent.get("hash") if dl_type == DownloaderType.QB else torrent.hashString
        except Exception as e:
            print(str(e))
            return ""

    @staticmethod
    def __get_label(torrent, dl_type):
        """
        获取种子标签
        """
        try:
            return torrent.get("tags") or [] if dl_type == DownloaderType.QB else torrent.labels or []
        except Exception as e:
            print(str(e))
            return []

    @staticmethod
    def __get_save_path(torrent, dl_type):
        """
        获取种子保存路径
        """
        try:
            return torrent.get("save_path") if dl_type == DownloaderType.QB else torrent.download_dir
        except Exception as e:
            print(str(e))
            return ""

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
