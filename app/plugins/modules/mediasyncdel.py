import os
import re
import shutil

import log
from app.helper import DbHelper
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils import PathUtils, ExceptionUtils
from app.utils.types import EventType
from config import RMT_MEDIAEXT
from web.action import WebAction


class MediaSyncDel(_IPluginModule):
    # 插件名称
    module_name = "媒体库同步删除"
    # 插件描述
    module_desc = "媒体服务器删除媒体后同步删除历史记录，可选删除源文件。(目前只支持Emby)"
    # 插件图标
    module_icon = "mediasyncdel.png"
    # 主题色
    module_color = "bg-danger"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "thsrite"
    # 插件配置项ID前缀
    module_config_prefix = "mediasyncdel_"
    # 加载顺序
    module_order = 22
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    dbhelper = None
    _enable = False
    _del_dest = False
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
                            'title': '开启媒体库同步删除',
                            'required': "",
                            'tooltip': '媒体服务器删除媒体后同步删除历史记录，目前只支持emby，需按照wiki配置Emby Scripter-X插件及脚本后才能正常使用。',
                            'type': 'switch',
                            'id': 'enable',
                        },
                        {
                            'title': '是否删除源文件',
                            'required': "",
                            'tooltip': '开启后，删除历史记录的同时会同步删除源文件。',
                            'type': 'switch',
                            'id': 'del_dest',
                        }
                    ],
                ]
            },
            {
                'type': 'details',
                'summary': '排除路径',
                'tooltip': '需要排除的媒体服务器媒体库路径，多个用英文逗号分割。（例如没经过nastool刮削的或者云盘）',
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
            self._del_dest = config.get("del_dest")
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
            log.error("【Plugin】媒体库同步删除失败，未获取到媒体类型")
            return
        if not tmdb_id:
            log.error("【Plugin】媒体库同步删除失败，未获取到TMDB ID")
            return

        if self._exclude_path and media_path and any(
                os.path.abspath(media_path).startswith(os.path.abspath(path)) for path in self._exclude_path.split(",")):
            log.info(f"【Plugin】媒体路径 {media_path} 已被排除，暂不处理")
            return

        # 删除电影
        if media_type == "Movie":
            log.info(f"【Plugin】媒体库准备同步删除电影 {media_name} {tmdb_id}")
            transfer_history = self.dbhelper.get_transfer_info_by(tmdbid=tmdb_id)
            # 删除电视剧
        elif media_type == "Series":
            log.info(f"【Plugin】媒体库准备同步删除剧集 {media_name} {tmdb_id}")
            transfer_history = self.dbhelper.get_transfer_info_by(tmdbid=tmdb_id)
        # 删除季 S02
        elif media_type == "Season":
            log.info(f"【Plugin】媒体库准备同步删除剧集 {media_name} S{season_num} {tmdb_id}")
            transfer_history = self.dbhelper.get_transfer_info_by(tmdbid=tmdb_id, season=f'S{season_num}')
        # 删除剧集S02E02
        elif media_type == "Episode":
            log.info(f"【Plugin】媒体库准备同步删除剧集 {media_name} S{season_num}E{episode_num} {tmdb_id}")
            transfer_history = self.dbhelper.get_transfer_info_by(tmdbid=tmdb_id,
                                                                  season_episode=f'S{season_num} E{episode_num}')
        else:
            return

        # 遍历历史记录删除
        for history in transfer_history:
            title = history.TITLE
            if title not in media_name:
                continue
            source_path = history.SOURCE_PATH
            source_filename = history.SOURCE_FILENAME

            # 删除记录
            self.dbhelper.delete_transfer_log_by_id(history.ID)
            # 删除该识别记录对应的转移记录
            self.dbhelper.delete_transfer_blacklist("%s/%s" % (source_path, source_filename))
            log.info(f"【Plugin】媒体 {media_name} 路径 {media_path} 已删除")

            # 是否删除源文件
            if self._del_dest:
                WebAction.delete_media_file(source_path, source_filename)
    def get_state(self):
        return self._enable

    def stop_service(self):
        """
        退出插件
        """
        pass
