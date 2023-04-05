import os.path
from functools import lru_cache

from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils import RequestUtils
from app.utils.types import MediaType, EventType
from config import Config


class ChineseSubFinder(_IPluginModule):
    # 插件名称
    module_name = "ChineseSubFinder"
    # 插件描述
    module_desc = "通知ChineseSubFinder下载字幕。"
    # 插件图标
    module_icon = "chinesesubfinder.png"
    # 主题色
    module_color = "#83BE39"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "chinesesubfinder_"
    # 加载顺序
    module_order = 3
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _save_tmp_path = None
    _host = None
    _api_key = None
    _remote_path = None
    _local_path = None
    _remote_path2 = None
    _local_path2 = None
    _remote_path3 = None
    _local_path3 = None

    def init_config(self, config: dict = None):
        self._save_tmp_path = Config().get_temp_path()
        if not os.path.exists(self._save_tmp_path):
            os.makedirs(self._save_tmp_path)
        if config:
            self._api_key = config.get("api_key")
            self._host = config.get('host')
            if self._host:
                if not self._host.startswith('http'):
                    self._host = "http://" + self._host
                if not self._host.endswith('/'):
                    self._host = self._host + "/"
            self._local_path = config.get("local_path")
            self._remote_path = config.get("remote_path")
            self._local_path2 = config.get("local_path2")
            self._remote_path2 = config.get("remote_path2")
            self._local_path3 = config.get("local_path3")
            self._remote_path3 = config.get("remote_path3")

    def get_state(self):
        return self._host and self._api_key

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
                            'title': '服务器地址',
                            'required': "required",
                            'tooltip': '配置IP地址和端口，如为https则需要增加https://前缀',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'host',
                                    'placeholder': 'http://127.0.0.1:19035'
                                }
                            ]

                        },
                        {
                            'title': 'Api Key',
                            'required': "required",
                            'tooltip': '在ChineseSubFinder->配置中心->实验室->API Key处生成',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'api_key',
                                    'placeholder': ''
                                }
                            ]
                        }
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '路径映射',
                'tooltip': '当NAStool与ChineseSubFinder媒体库路程不一致时，需要映射转换，最多可设置三组,留空时不启用',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '路径1',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'local_path',
                                    'placeholder': '本地路径'
                                },
                                {
                                    'id': 'remote_path',
                                    'placeholder': '远程路径'
                                }
                            ]
                        },
                        {
                            'title': '路径2',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'local_path2',
                                    'placeholder': '本地路径'
                                },
                                {
                                    'id': 'remote_path2',
                                    'placeholder': '远程路径'
                                }
                            ]
                        },
                        {
                            'title': '路径3',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'local_path3',
                                    'placeholder': '本地路径'
                                },
                                {
                                    'id': 'remote_path3',
                                    'placeholder': '远程路径'
                                }
                            ]
                        }
                    ],
                ]
            }
        ]

    def stop_service(self):
        pass

    @EventHandler.register(EventType.SubtitleDownload)
    def download(self, event):
        """
        调用ChineseSubFinder下载字幕
        """
        if not self._host or not self._api_key:
            return
        item = event.event_data
        if not item:
            return

        req_url = "%sapi/v1/add-job" % self._host

        item_media = item.get("media_info")
        item_type = item_media.get("type")
        item_bluray = item.get("bluray")
        item_file = item.get("file")
        item_file_ext = item.get("file_ext")

        if item_bluray:
            file_path = "%s.mp4" % item_file
        else:
            if os.path.splitext(item_file)[-1] != item_file_ext:
                file_path = "%s%s" % (item_file, item_file_ext)
            else:
                file_path = item_file

        # 路径替换
        if self._local_path and self._remote_path and file_path.startswith(self._local_path):
            file_path = file_path.replace(self._local_path, self._remote_path).replace('\\', '/')

        if self._local_path2 and self._remote_path2 and file_path.startswith(self._local_path2):
            file_path = file_path.replace(self._local_path2, self._remote_path2).replace('\\', '/')

        if self._local_path3 and self._remote_path3 and file_path.startswith(self._local_path3):
            file_path = file_path.replace(self._local_path3, self._remote_path3).replace('\\', '/')

        # 调用CSF下载字幕
        self.__request_csf(req_url=req_url,
                           file_path=file_path,
                           item_type=0 if item_type == MediaType.MOVIE.value else 1,
                           item_bluray=item_bluray)

    @lru_cache(maxsize=128)
    def __request_csf(self, req_url, file_path, item_type, item_bluray):
        # 一个名称只建一个任务
        self.info("通知ChineseSubFinder下载字幕: %s" % file_path)
        params = {
            "video_type": item_type,
            "physical_video_file_full_path": file_path,
            "task_priority_level": 3,
            "media_server_inside_video_id": "",
            "is_bluray": item_bluray
        }
        try:
            res = RequestUtils(headers={
                "Authorization": "Bearer %s" % self._api_key
            }).post(req_url, json=params)
            if not res or res.status_code != 200:
                self.error("调用ChineseSubFinder API失败！")
            else:
                # 如果文件目录没有识别的nfo元数据， 此接口会返回控制符，推测是ChineseSubFinder的原因
                # emby refresh元数据时异步的
                if res.text:
                    job_id = res.json().get("job_id")
                    message = res.json().get("message")
                    if not job_id:
                        self.warn("ChineseSubFinder下载字幕出错：%s" % message)
                    else:
                        self.info("ChineseSubFinder任务添加成功：%s" % job_id)
                else:
                    self.error("%s 目录缺失nfo元数据" % file_path)
        except Exception as e:
            self.error("连接ChineseSubFinder出错：" + str(e))
