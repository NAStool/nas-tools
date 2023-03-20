import os
from datetime import datetime
from threading import Event

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import log
from app.media import Media, Scraper
from app.media.meta import MetaInfo
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils import NfoReader
from app.utils.types import MediaType, EventType
from config import Config, RMT_MEDIAEXT


class LibraryScraper(_IPluginModule):
    # 插件名称
    module_name = "媒体库刮削"
    # 插件描述
    module_desc = "定时对媒体库进行刮削，补齐缺失元数据和图片。"
    # 插件图标
    module_icon = "nfo.png"
    # 主题色
    module_color = ""
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "libraryscraper_"
    # 加载顺序
    module_order = 10
    # 可使用的用户级别
    user_level = 1

    # 私有属性
    _scheduler = None
    _media = None
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
                                    'placeholder': ''
                                }
                            ]
                        }
                    ]
                ]
            }
        ]

    def init_config(self, config=None):
        self._media = Media()
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
        if self._cron or self._onlyonce:
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            if self._cron:
                self._scheduler.add_job(self.__libraryscraper, CronTrigger.from_crontab(self._cron))
            if self._onlyonce:
                self._scheduler.add_job(self.__libraryscraper, 'date',
                                        run_date=datetime.now(tz=pytz.timezone(Config().get_timezone())))
            self._scheduler.print_jobs()
            self._scheduler.start()

            if self._onlyonce:
                log.info(f"媒体库刮削服务启动，立即运行一次")
            if self._cron:
                log.info(f"媒体库刮削服务启动，周期：{self._cron}")

            # 关闭一次性开关
            self._onlyonce = False
            self.update_config({
                "onlyonce": False,
                "cron": self._cron,
                "mode": self._mode,
                "scraper_path": self._scraper_path,
                "exclude_path": self._exclude_path
            })

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
        self.__folder_scraper(path)

    def __folder_scraper(self, path, exclude_path=None):
        """
        刮削指定文件夹或文件
        :param path:
        :return:
        """
        # 模式
        force_nfo = True if self._mode in ["force_nfo", "force_all"] else False
        force_pic = True if self._mode in ["force_all"] else False
        # 每个媒体库下的所有文件
        for file in self.__get_library_files(path, exclude_path):
            if self._event.is_set():
                log.info(f"【Plugin】媒体库刮削服务停止")
                return
            if not file:
                continue
            log.info(f"【Plugin】开始刮削媒体库文件：{file}")
            # 识别媒体文件
            meta_info = MetaInfo(os.path.basename(file))
            # 优先读取本地文件
            tmdbid = None
            if meta_info.type == MediaType.MOVIE:
                # 电影
                movie_nfo = os.path.join(os.path.dirname(file), "movie.nfo")
                if os.path.exists(movie_nfo):
                    tmdbid = self.__get_tmdbid_from_nfo(movie_nfo)
                file_nfo = os.path.join(os.path.splitext(file)[0] + ".nfo")
                if not tmdbid and os.path.exists(file_nfo):
                    tmdbid = self.__get_tmdbid_from_nfo(file_nfo)
            else:
                # 电视剧
                tv_nfo = os.path.join(os.path.dirname(os.path.dirname(file)), "tvshow.nfo")
                if os.path.exists(tv_nfo):
                    tmdbid = self.__get_tmdbid_from_nfo(tv_nfo)
            if tmdbid:
                log.info(f"【Plugin】读取到本地nfo文件的tmdbid：{tmdbid}")
                meta_info.set_tmdb_info(self._media.get_tmdb_info(mtype=meta_info.type,
                                                                  tmdbid=tmdbid,
                                                                  append_to_response='all'))
                media_info = meta_info
            else:
                medias = self._media.get_media_info_on_files(file_list=[file],
                                                             append_to_response="all")
                if not medias:
                    continue
                media_info = None
                for _, media in medias.items():
                    media_info = media
                    break
            if not media_info or not media_info.tmdb_info:
                continue
            self._scraper.gen_scraper_files(media=media_info,
                                            dir_path=os.path.dirname(file),
                                            file_name=os.path.splitext(os.path.basename(file))[0],
                                            file_ext=os.path.splitext(file)[-1],
                                            force=True,
                                            force_nfo=force_nfo,
                                            force_pic=force_pic)
            log.info(f"【Plugin】{file} 刮削完成")

    def __libraryscraper(self):
        """
        开始刮削媒体库
        """
        # 已选择的目录
        log.info(f"【Plugin】开始刮削媒体库：{self._scraper_path} ...")
        for path in self._scraper_path:
            if not path:
                continue
            # 刮削目录
            self.__folder_scraper(path, self._exclude_path)
        log.info(f"【Plugin】媒体库刮削完成")

    @staticmethod
    def __get_library_files(in_path, exclude_path=None):
        """
        获取媒体库文件列表
        """
        if not os.path.isdir(in_path):
            yield in_path
            return

        for root, dirs, files in os.walk(in_path):
            if exclude_path and any(os.path.abspath(root).startswith(os.path.abspath(path))
                                    for path in exclude_path.split(",")):
                continue

            for file in files:
                cur_path = os.path.join(root, file)
                # 检查后缀
                if os.path.splitext(file)[-1].lower() in RMT_MEDIAEXT:
                    yield cur_path

    @staticmethod
    def __get_tmdbid_from_nfo(file_path):
        """
        从nfo文件中获取信息
        :param file_path:
        :return: tmdbid
        """
        if not file_path:
            return None
        xpaths = [
            "uniqueid[@type='Tmdb']",
            "uniqueid[@type='tmdb']",
            "uniqueid[@type='TMDB']",
            "tmdbid"
        ]
        reader = NfoReader(file_path)
        for xpath in xpaths:
            try:
                tmdbid = reader.get_element_value(xpath)
                if tmdbid:
                    return tmdbid
            except Exception as err:
                print(str(err))
        return None

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
