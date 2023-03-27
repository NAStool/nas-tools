from app.mediaserver import MediaServer
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils.types import EventType


class LibraryRefresh(_IPluginModule):
    # 插件名称
    module_name = "实时刷新媒体库"
    # 插件描述
    module_desc = "入库完成后实时刷新媒体库服务器海报墙。"
    # 插件图标
    module_icon = "refresh.png"
    # 主题色
    module_color = "bg-teal"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "libraryrefresh_"
    # 加载顺序
    module_order = 8
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    _enable = False

    mediaserver = None

    def init_config(self, config: dict = None):
        self.mediaserver = MediaServer()
        if config:
            self._enable = config.get("enable")

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
                            'title': '开启媒体库实时刷新',
                            'required': "",
                            'tooltip': 'Emby已有电视剧新增剧集时只会刷新对应电视剧，其它场景下如开启了二级分类则只刷新二级分类对应媒体库，否则刷新整库；Jellyfin/Plex只支持刷新整库',
                            'type': 'switch',
                            'id': 'enable',
                        }
                    ],
                ]
            }
        ]

    def stop_service(self):
        pass

    @EventHandler.register(EventType.TransferFinished)
    def refresh(self, event):
        """
        监听入库完成事件
        """
        if not self._enable:
            return
        event_data = event.event_data
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
