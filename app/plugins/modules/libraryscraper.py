from datetime import datetime
from threading import Event

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.media import Scraper
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils.types import EventType
from config import Config


class LibraryScraper(_IPluginModule):
    # 插件名称
    module_name = "媒体库刮削"
    # 插件描述
    module_desc = "定时对媒体库进行刮削，补齐缺失元数据和图片。"
    # 插件图标
    module_icon = "scraper.png"
    # 主题色
    module_color = "#FF7D00"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "libraryscraper_"
    # 加载顺序
    module_order = 7
    # 可使用的用户级别
    user_level = 1

    # 私有属性
    _scheduler = None
    _scraper = None
    # 限速开关
    _cron = None
    _onlyonce = False
    _mode = None
    _scraper_path = None
    _exclude_path = None
    # 退出事件
    _event = Event()

    @staticmethod
    def get_fields():
        movie_path = Config().get_config('media').get('movie_path') or []
        tv_path = Config().get_config('media').get('tv_path') or []
        anime_path = Config().get_config('media').get('anime_path') or []
        path = {p: {'name': p} for p in (movie_path + tv_path + anime_path)}
        return [
            # 同一板块
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '刮削周期',
                            'required': "required",
                            'tooltip': '支持5位cron表达式；需要在基础设置中配置好刮削内容；刮削时间根据媒体库中的文件数量及网络状况而定，耗时可能会非常长，建议合理设置刮削周期，留空则不启用定期刮削',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'cron',
                                    'placeholder': '0 0 0 ? *',
                                }
                            ]
                        },
                        {
                            'title': '刮削模式',
                            'required': "required",
                            'type': 'select',
                            'content': [
                                {
                                    'id': 'mode',
                                    'default': 'no_force',
                                    'options': {
                                        "no_force": "仅刮削缺失的元数据和图片",
                                        "force_nfo": "覆盖所有元数据",
                                        "force_all": "覆盖所有元数据和图片"
                                    },
                                }
                            ]
                        }
                    ],
                ]
            },
            {
                'type': 'details',
                'summary': '刮削媒体库',
                'tooltip': '请选择需要刮削的媒体库',
                'content': [
                    # 同一行
                    [
                        {
                            'id': 'scraper_path',
                            'type': 'form-selectgroup',
                            'content': path
                        },
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '排除路径',
                'tooltip': '需要排除的媒体库路径，多个用英文逗号分割',
                'content': [
                    [
                        {
                            'required': "",
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'exclude_path',
                                    'placeholder': '多个路径用,分割'
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
                            'title': '立即运行一次',
                            'required': "",
                            'tooltip': '打开后立即运行一次（点击此对话框的确定按钮后即会运行，周期未设置也会运行），关闭后将仅按照刮削周期运行（同时上次触发运行的任务如果在运行中也会停止）',
                            'type': 'switch',
                            'id': 'onlyonce',
                        }
                    ],
                ]
            }
        ]

    def init_config(self, config=None):
        self._scraper = Scraper()

        # 读取配置
        if config:
            self._onlyonce = config.get("onlyonce")
            self._cron = config.get("cron")
            self._mode = config.get("mode")
            self._scraper_path = config.get("scraper_path")
            self._exclude_path = config.get("exclude_path")

        # 停止现有任务
        self.stop_service()

        # 启动定时任务 & 立即运行一次
        if self.get_state() or self._onlyonce:
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            if self._cron:
                self.info(f"刮削服务启动，周期：{self._cron}")
                self._scheduler.add_job(self.__libraryscraper,
                                        CronTrigger.from_crontab(self._cron))
            if self._onlyonce:
                self.info(f"刮削服务启动，立即运行一次")
                self._scheduler.add_job(self.__libraryscraper, 'date',
                                        run_date=datetime.now(tz=pytz.timezone(Config().get_timezone())))
                # 关闭一次性开关
                self._onlyonce = False
                self.update_config({
                    "onlyonce": self._onlyonce,
                    "cron": self._cron,
                    "mode": self._mode,
                    "scraper_path": self._scraper_path,
                    "exclude_path": self._exclude_path
                })
            if self._scheduler.get_jobs():
                # 启动服务
                self._scheduler.print_jobs()
                self._scheduler.start()

    def get_state(self):
        return True if self._cron else False

    @EventHandler.register(EventType.MediaScrapStart)
    def start_scrap(self, event):
        """
        刮削事件响应
        :param event:
        :return:
        """
        event_info = event.event_data
        if not event_info:
            return
        path = event_info.get("path")
        force = event_info.get("force")
        if force:
            mode = 'force_all'
        else:
            mode = 'no_force'
        self._scraper.folder_scraper(path, mode=mode)

    def __libraryscraper(self):
        """
        开始刮削媒体库
        """
        # 已选择的目录
        self.info(f"开始刮削媒体库：{self._scraper_path} ...")
        for path in self._scraper_path:
            if not path:
                continue
            if self._event.is_set():
                self.info(f"媒体库刮削服务停止")
                return
            # 刮削目录
            self._scraper.folder_scraper(path=path,
                                         exclude_path=self._exclude_path,
                                         mode=self._mode)
        self.info(f"媒体库刮削完成")

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
