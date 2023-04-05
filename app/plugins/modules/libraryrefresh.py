from app.mediaserver import MediaServer
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils.types import EventType
from datetime import datetime, timedelta
from app.utils import ExceptionUtils
from apscheduler.schedulers.background import BackgroundScheduler

class LibraryRefresh(_IPluginModule):
    # 插件名称
    module_name = "刷新媒体库"
    # 插件描述
    module_desc = "入库完成后刷新媒体库服务器海报墙。"
    # 插件图标
    module_icon = "refresh.png"
    # 主题色
    module_color = "#32BEA6"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "libraryrefresh_"
    # 加载顺序
    module_order = 8
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    _delay = 0
    _enable = False
    _scheduler = None

    mediaserver = None

    def init_config(self, config: dict = None):
        self.mediaserver = MediaServer()
        if config:
            self._enable = config.get("enable")
            try:
                # 延迟时间
                delay = int(float(config.get("delay") or 0))
                if delay < 0:
                    delay = 0
                self._delay = delay
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                self._delay = 0

        self.stop_service()

        if self._delay > 0:
            self.info(f"媒体库延迟刷新服务启动，延迟 {self._delay} 分钟刷新媒体库")
            self._scheduler = BackgroundScheduler()
        else:
            self.info("媒体库实时刷新服务启动")

    def get_state(self):
        return self._enable

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
                            'title': '延迟刷新时间',
                            'required': "",
                            'tooltip': '延迟刷新时间，单位分钟，0或留空则不延迟',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'delay',
                                    'placeholder': '0',
                                }
                            ]
                        }
                    ],
                    [
                        {
                            'title': '开启媒体库刷新',
                            'required': "",
                            'tooltip': 'Emby已有电视剧新增剧集时只会刷新对应电视剧，其它场景下如开启了二级分类则只刷新二级分类对应媒体库，否则刷新整库；Jellyfin/Plex只支持刷新整库',
                            'type': 'switch',
                            'id': 'enable',
                        },

                    ]
                ]
            }
        ]

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

    def __refresh_library(self, event_data):
        media_info = event_data.get("media_info")
        title = media_info.get("title")
        year = media_info.get("year")
        media_name = f"{title} ({year})" if year else title
        mediaserver_type = self.mediaserver.get_type().value
        self.info(f"媒体服务器 {mediaserver_type} 刷新媒体 {media_name}")
        self.mediaserver.refresh_library_by_items([{
            "title": title,
            "year": year,
            "type": media_info.get("type"),
            "category": media_info.get("category"),
            "target_path": event_data.get("dest")
        }])

    @EventHandler.register(EventType.TransferFinished)
    def refresh(self, event):
        """
        监听入库完成事件
        """
        if not self._enable:
            return

        if self._delay > 0:
            # 计算延迟时间
            run_date = datetime.now() + timedelta(minutes=self._delay)

            # 使用 date 触发器添加任务到调度器
            self._scheduler.add_job(func=self.__refresh_library, args=[event.event_data], trigger='date', run_date=run_date)

            # 启动调度器（懒启动）
            if not self._scheduler.running:
              self._scheduler.start()
        else:
            # 不延迟刷新
            self.__refresh_library(event.event_data)