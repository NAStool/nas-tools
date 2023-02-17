import os.path

import log
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
    module_color = "bg-green"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "chinesesubfinder_"
    # 加载顺序
    module_order = 3

    # 私有属性
    _save_tmp_path = None
    _host = None
    _api_key = None
    _remote_path = None
    _local_path = None

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
                    ],
                    [
                        {
                            'title': '本地路径',
                            'required': "required",
                            'tooltip': 'NAStool访问媒体库的路径，如NAStool与ChineseSubFinder的媒体目录路径一致则不用配置',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'local_path',
                                    'placeholder': '本地映射路径'
                                }
                            ]
                        },
                        {
                            'title': '远程路径',
                            'required': "required",
                            'tooltip': 'ChineseSubFinder的媒体目录访问路径，会用此路径替换掉本地路径后传递给ChineseSubFinder下载字幕，如NAStool与ChineseSubFinder的媒体目录路径一致则不用配置',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'remote_path',
                                    'placeholder': '远程映射路径'
                                }
                            ]
                        }
                    ]
                ]
            }
        ]

    def stop_service(self):
        pass

    @EventHandler.register(EventType.SubtitleDownload)
    def download_chinesesubfinder(self, event):
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

        # 一个名称只建一个任务
        log.info("【Plugin】通知ChineseSubFinder下载字幕: %s" % file_path)
        params = {
            "video_type": 0 if item_type == MediaType.MOVIE.value else 1,
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
                log.error("【Plugin】调用ChineseSubFinder API失败！")
            else:
                # 如果文件目录没有识别的nfo元数据， 此接口会返回控制符，推测是ChineseSubFinder的原因
                # emby refresh元数据时异步的
                if res.text:
                    job_id = res.json().get("job_id")
                    message = res.json().get("message")
                    if not job_id:
                        log.warn("【Plugin】ChineseSubFinder下载字幕出错：%s" % message)
                    else:
                        log.info("【Plugin】ChineseSubFinder任务添加成功：%s" % job_id)
                else:
                    log.error("【Plugin】%s 目录缺失nfo元数据" % file_path)
        except Exception as e:
            log.error("【Plugin】连接ChineseSubFinder出错：" + str(e))
