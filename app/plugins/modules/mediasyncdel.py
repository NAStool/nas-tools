import os

from app.helper import DbHelper
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils.types import EventType
from web.action import WebAction


class MediaSyncDel(_IPluginModule):
    # 插件名称
    module_name = "Emby同步删除"
    # 插件描述
    module_desc = "Emby删除媒体后同步删除历史记录或源文件。"
    # 插件图标
    module_icon = "emby.png"
    # 主题色
    module_color = "bg-red"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "thsrite"
    # 插件配置项ID前缀
    module_config_prefix = "mediasyncdel_"
    # 加载顺序
    module_order = 22
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    dbhelper = None
    _enable = False
    _del_source = False
    _exclude_path = None

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
                            'title': '开启Emby同步删除',
                            'required': "",
                            'tooltip': 'Emby删除媒体后同步删除历史记录，需按照wiki（https://github.com/thsrite/emby_sync_del_nt）配置Emby Scripter-X插件后才能正常使用。',
                            'type': 'switch',
                            'id': 'enable',
                        },
                        {
                            'title': '删除源文件',
                            'required': "",
                            'tooltip': '开启后，删除历史记录的同时会同步删除源文件。',
                            'type': 'switch',
                            'id': 'del_source',
                        }
                    ],
                ]
            },
            {
                'type': 'details',
                'summary': '排除路径',
                'tooltip': '需要排除的Emby媒体库路径，多个用英文逗号分割（例如没经过NAStool刮削的或者云盘）。',
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
        self.dbhelper = DbHelper()
        # 读取配置
        if config:
            self._enable = config.get("enable")
            self._del_source = config.get("del_source")
            self._exclude_path = config.get("exclude_path")

    @EventHandler.register(EventType.EmbyWebhook)
    def sync_del(self, event):
        """
        emby删除媒体库同步删除历史记录
        """
        if not self._enable:
            return
        event_data = event.event_data
        event_type = event_data.get("event_type")
        if not event_type or str(event_type) != 'media_del':
            return

        # 媒体类型
        media_type = event_data.get("media_type")
        # 媒体名称
        media_name = event_data.get("media_name")
        # 媒体路径
        media_path = event_data.get("media_path")
        # tmdb_id
        tmdb_id = event_data.get("tmdb_id")
        # 季数
        season_num = event_data.get("season_num")
        if season_num and int(season_num) < 10:
            season_num = f'0{season_num}'
        # 集数
        episode_num = event_data.get("episode_num")
        if episode_num and int(episode_num) < 10:
            episode_num = f'0{episode_num}'

        if not media_type:
            self.error(f"{media_name} 同步删除失败，未获取到媒体类型")
            return
        if not tmdb_id:
            self.error(f"{media_name} 同步删除失败，未获取到TMDB ID")
            return

        if self._exclude_path and media_path and any(
                os.path.abspath(media_path).startswith(os.path.abspath(path)) for path in
                self._exclude_path.split(",")):
            self.info(f"媒体路径 {media_path} 已被排除，暂不处理")
            return

        # 删除电影
        msg = None
        if media_type == "Movie":
            msg = f'电影 {media_name} {tmdb_id}'
            self.info(f"正在同步删除{msg}")
            transfer_history = self.dbhelper.get_transfer_info_by(tmdbid=tmdb_id)
            # 删除电视剧
        elif media_type == "Series":
            msg = f'剧集 {media_name} {tmdb_id}'
            self.info(f"正在同步删除{msg}")
            transfer_history = self.dbhelper.get_transfer_info_by(tmdbid=tmdb_id)
        # 删除季 S02
        elif media_type == "Season":
            if not season_num:
                self.error(f"{media_name} 季同步删除失败，未获取到具体季")
                return
            msg = f'剧集 {media_name} S{season_num} {tmdb_id}'
            self.info(f"正在同步删除{msg}")
            transfer_history = self.dbhelper.get_transfer_info_by(tmdbid=tmdb_id, season=f'S{season_num}')
        # 删除剧集S02E02
        elif media_type == "Episode":
            if not season_num or not episode_num:
                self.error(f"{media_name} 集同步删除失败，未获取到具体集")
                return
            msg = f'剧集 {media_name} S{season_num}E{episode_num} {tmdb_id}'
            self.info(f"正在同步删除{msg}")
            transfer_history = self.dbhelper.get_transfer_info_by(tmdbid=tmdb_id,
                                                                  season_episode=f'S{season_num} E{episode_num}')
        else:
            return

        if not transfer_history:
            return

        # 开始删除
        logids = [history.ID for history in transfer_history]
        self.info(f"获取到删除媒体数量 {len(logids)}")
        WebAction().delete_history({
            "logids": logids,
            "flag": "del_source" if self._del_source else ""
        })
        self.info(f"同步删除 {msg} 完成！")

    def get_state(self):
        return self._enable

    def stop_service(self):
        """
        退出插件
        """
        pass
