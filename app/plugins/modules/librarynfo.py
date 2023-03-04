import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import log
from app.media import Media, Scraper
from app.plugins.modules._base import _IPluginModule
from app.sync import Sync
from config import Config, RMT_MEDIAEXT


class LibraryNfo(_IPluginModule):
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
    module_config_prefix = "librarynfo_"
    # 加载顺序
    module_order = 10
    # 可使用的用户级别
    user_level = 1

    # 私有属性
    _scheduler = None
    _media = None
    _scraper = None
    _scraper_nfo = {}
    _scraper_pic = {}
    # 限速开关
    _cron = None

    @staticmethod
    def get_fields():
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
                            'tooltip': '刮削时间根据媒体库中的文件数量及网络状况而定，耗时可能会非常长，建议合理设置刮削周期，留空则不启动',
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
            }
        ]

    def init_config(self, config=None):
        self._media = Media()
        self._scraper = Scraper()

        # 读取配置
        if config:
            self._cron = config.get("cron")

        # 刮削配置
        self._scraper_nfo = Config().get_config('scraper_nfo')
        self._scraper_pic = Config().get_config('scraper_pic')

        # 停止现有任务
        self.stop_service()

        # 启动定时任务
        if self._cron:
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            self._scheduler.add_job(self.__libraryscraper, CronTrigger.from_crontab(self._cron))
            self._scheduler.print_jobs()
            self._scheduler.start()
            log.info(f"媒体库刮削服务启动，周期：{self._cron}")

    def get_state(self):
        return True if self._cron else False

    def __libraryscraper(self):
        """
        开始刮削媒体库
        """
        # 每个媒体库目录
        movie_path = Config().get_config('media').get('movie_path')
        tv_path = Config().get_config('media').get('tv_path')
        anime_path = Config().get_config('media').get('anime_path')
        # 所有类型
        log.info(f"【Plugin】开始刮削媒体库：{movie_path} {tv_path} {anime_path} ...")
        for library in [movie_path, tv_path, anime_path]:
            if not library:
                continue
            # 每个类型的所有媒体库路径
            for path in library:
                if not path:
                    continue
                # 每个媒体库下的所有文件
                for file in self.__get_library_files(path):
                    if not file:
                        continue
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
                    log.info(f"【Plugin】开始刮削媒体库文件：{file}")
                    self._scraper.gen_scraper_files(media=media_info,
                                                    scraper_nfo=self._scraper_nfo,
                                                    scraper_pic=self._scraper_pic,
                                                    dir_path=os.path.dirname(file),
                                                    file_name=os.path.splitext(os.path.basename(file))[0],
                                                    file_ext=os.path.splitext(file)[-1])
                    log.info(f"【Plugin】{file} 刮削完成")
        log.info(f"【Plugin】媒体库刮削完成")

    @staticmethod
    def __get_library_files(in_path):
        """
        获取媒体库文件列表
        """
        if os.path.isdir(in_path):
            for root, dirs, files in os.walk(in_path):
                for file in files:
                    cur_path = os.path.join(root, file)
                    # 检查后缀
                    if os.path.splitext(file)[-1].lower() not in RMT_MEDIAEXT:
                        continue
                    yield cur_path

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
