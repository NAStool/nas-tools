import os

import log
from app.filetransfer import FileTransfer
from app.media import Category
from app.mediaserver import MediaServer
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils import SystemUtils
from app.utils.types import EventType, MediaServerType, MediaType
from config import RMT_FAVTYPE, Config


class MovieLike(_IPluginModule):
    # 插件名称
    module_name = "电影精选"
    # 插件描述
    module_desc = "媒体服务器中用户将电影设为最爱时，自动转移到精选文件夹。"
    # 插件图标
    module_icon = "like.jpg"
    # 主题色
    module_color = "bg-pink"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "movielike_"
    # 加载顺序
    module_order = 7
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    _enable = False
    _dir_name = RMT_FAVTYPE

    mediaserver = None
    filetransfer = None
    category = None

    def init_config(self, config: dict = None):
        self.mediaserver = MediaServer()
        self.filetransfer = FileTransfer()
        self.category = Category()
        if config:
            self._enable = config.get("enable")
            self._dir_name = config.get("dir_name")
            if self._dir_name:
                Config().update_favtype(self._dir_name)

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
                            'title': '分类目录名称',
                            'required': True,
                            'tooltip': '添加到喜爱的电影将移动到该目录下',
                            'type': 'text',
                            'content': [
                                {
                                    'default': RMT_FAVTYPE,
                                    'placeholder': RMT_FAVTYPE,
                                    'id': 'dir_name',
                                }
                            ]
                        }
                    ],
                    [
                        {
                            'title': '开启电影精选',
                            'required': "",
                            'tooltip': '目前仅支持Emby，NAStool挂载目录需与Emby媒体库目录一致。在Emby的Webhooks中勾选 用户->添加到最爱 事件，如需控制仅部分用户生效，可在媒体服务器单独建立Webhook并设置对应用户范围',
                            'type': 'switch',
                            'id': 'enable',
                        }
                    ],
                ]
            }
        ]

    def stop_service(self):
        pass

    @EventHandler.register(EventType.EmbyWebhook)
    def favtransfer(self, event):
        """
        监听Emby的Webhook事件
        """
        if not self._enable or not self._dir_name:
            return
        # 不是当前正在使用的媒体服务器时不处理
        if self.mediaserver.get_type() != MediaServerType.EMBY:
            return
        event_info = event.event_data
        # 用户事件
        action_type = event_info.get('Event')
        # 不是like事件不处理
        if action_type != 'item.rate':
            return
        # 不是电影不处理
        if event_info.get('Item', {}).get('Type') != 'Movie':
            return
        # 路径不存在不处理
        item_path = event_info.get('Item', {}).get('Path')
        if not item_path:
            return
        if not os.path.exists(item_path):
            return
        # 文件转为目录
        if os.path.isdir(item_path):
            movie_dir = item_path
        else:
            movie_dir = os.path.dirname(item_path)
        # 电影二级分类名
        movie_type = os.path.basename(os.path.dirname(movie_dir))
        if movie_type == self._dir_name:
            return
        if movie_type not in self.category.get_movie_categorys():
            return
        # 电影名
        movie_name = os.path.basename(movie_dir)
        # 最优媒体库路径
        movie_path = self.filetransfer.get_best_target_path(mtype=MediaType.MOVIE, in_path=movie_dir)
        # 原路径
        org_path = os.path.join(movie_path, movie_type, movie_name)
        # 精选路径
        new_path = os.path.join(movie_path, self._dir_name, movie_name)
        # 开始转移文件
        if os.path.exists(org_path):
            log.info("【Plugin】开始转移文件 %s 到 %s ..." % (org_path, new_path))
            if os.path.exists(new_path):
                log.info("【Plugin】目录 %s 已存在" % new_path)
                return
            ret, retmsg = SystemUtils.move(org_path, new_path)
            if ret != 0:
                log.error("【Plugin】%s" % retmsg)
        else:
            log.error("【Plugin】%s 目录不存在" % org_path)
