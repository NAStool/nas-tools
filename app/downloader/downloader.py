import os
from threading import Lock
from enum import Enum
import json

from apscheduler.schedulers.background import BackgroundScheduler

import log
from app.conf import ModuleConf
from app.conf import SystemConfig
from app.filetransfer import FileTransfer
from app.helper import DbHelper, ThreadHelper, SubmoduleHelper
from app.media import Media
from app.media.meta import MetaInfo
from app.mediaserver import MediaServer
from app.message import Message
from app.plugins import EventManager
from app.sites import Sites, SiteSubtitle
from app.utils import Torrent, StringUtils, SystemUtils, ExceptionUtils, NumberUtils
from app.utils.commons import singleton
from app.utils.types import MediaType, DownloaderType, SearchType, RmtMode, EventType, SystemConfigKey
from config import Config, PT_TAG, RMT_MEDIAEXT, PT_TRANSFER_INTERVAL

lock = Lock()
client_lock = Lock()


@singleton
class Downloader:
    # 客户端实例
    clients = {}

    _downloader_schema = []
    _download_order = None
    _download_settings = {}
    _downloader_confs = {}
    _monitor_downloader_ids = []
    # 下载器ID-名称枚举类
    _DownloaderEnum = None
    _scheduler = None

    message = None
    mediaserver = None
    filetransfer = None
    media = None
    sites = None
    sitesubtitle = None
    dbhelper = None
    systemconfig = None
    eventmanager = None

    def __init__(self):
        self._downloader_schema = SubmoduleHelper.import_submodules(
            'app.downloader.client',
            filter_func=lambda _, obj: hasattr(obj, 'client_id')
        )
        log.debug(f"【Downloader】加载下载器类型：{self._downloader_schema}")
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()
        self.message = Message()
        self.mediaserver = MediaServer()
        self.filetransfer = FileTransfer()
        self.media = Media()
        self.sites = Sites()
        self.systemconfig = SystemConfig()
        self.eventmanager = EventManager()
        self.sitesubtitle = SiteSubtitle()
        # 清空已存在下载器实例
        self.clients = {}
        # 下载器配置，生成实例
        self._downloader_confs = {}
        self._monitor_downloader_ids = []
        for downloader_conf in self.dbhelper.get_downloaders():
            if not downloader_conf:
                continue
            did = downloader_conf.ID
            name = downloader_conf.NAME
            enabled = downloader_conf.ENABLED
            # 下载器监控配置
            transfer = downloader_conf.TRANSFER
            only_nastool = downloader_conf.ONLY_NASTOOL
            match_path = downloader_conf.MATCH_PATH
            rmt_mode = downloader_conf.RMT_MODE
            rmt_mode_name = ModuleConf.RMT_MODES.get(rmt_mode).value if rmt_mode else ""
            # 输出日志
            if transfer:
                log_content = ""
                if only_nastool:
                    log_content += "启用标签隔离，"
                if match_path:
                    log_content += "启用目录隔离，"
                log.info(f"【Downloader】读取到监控下载器：{name}{log_content}转移方式：{rmt_mode_name}")
                if enabled:
                    self._monitor_downloader_ids.append(did)
                else:
                    log.info(f"【Downloader】下载器：{name} 不进行监控：下载器未启用")
            # 下载器登录配置
            config = json.loads(downloader_conf.CONFIG)
            dtype = downloader_conf.TYPE
            self._downloader_confs[str(did)] = {
                "id": did,
                "name": name,
                "type": dtype,
                "enabled": enabled,
                "transfer": transfer,
                "only_nastool": only_nastool,
                "match_path": match_path,
                "rmt_mode": rmt_mode,
                "rmt_mode_name": rmt_mode_name,
                "config": config,
                "download_dir": json.loads(downloader_conf.DOWNLOAD_DIR)
            }
        # 下载器ID-名称枚举类生成
        self._DownloaderEnum = Enum('DownloaderIdName',
                                    {did: conf.get("name") for did, conf in self._downloader_confs.items()})
        pt = Config().get_config('pt')
        if pt:
            self._download_order = pt.get("download_order")
        # 下载设置
        self._download_settings = {
            "-1": {
                "id": -1,
                "name": "预设",
                "category": '',
                "tags": PT_TAG,
                "is_paused": 0,
                "upload_limit": 0,
                "download_limit": 0,
                "ratio_limit": 0,
                "seeding_time_limit": 0,
                "downloader": "",
                "downloader_name": "",
                "downloader_type": ""
            }
        }
        download_settings = self.dbhelper.get_download_setting()
        for download_setting in download_settings:
            downloader_id = download_setting.DOWNLOADER
            download_conf = self._downloader_confs.get(str(downloader_id))
            if download_conf:
                downloader_name = download_conf.get("name")
                downloader_type = download_conf.get("type")
            else:
                downloader_name = ""
                downloader_type = ""
                downloader_id = ""
            self._download_settings[str(download_setting.ID)] = {
                "id": download_setting.ID,
                "name": download_setting.NAME,
                "category": download_setting.CATEGORY,
                "tags": download_setting.TAGS,
                "is_paused": download_setting.IS_PAUSED,
                "upload_limit": download_setting.UPLOAD_LIMIT,
                "download_limit": download_setting.DOWNLOAD_LIMIT,
                "ratio_limit": download_setting.RATIO_LIMIT / 100,
                "seeding_time_limit": download_setting.SEEDING_TIME_LIMIT,
                "downloader": downloader_id,
                "downloader_name": downloader_name,
                "downloader_type": downloader_type
            }
        # 启动下载器监控服务
        self.start_service()

    def __build_class(self, ctype, conf=None):
        for downloader_schema in self._downloader_schema:
            try:
                if downloader_schema.match(ctype):
                    return downloader_schema(conf)
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
        return None

    @property
    def default_downloader_id(self):
        """
        获取默认下载器id
        """
        default_downloader_id = SystemConfig().get(SystemConfigKey.DefaultDownloader)
        if not default_downloader_id or not self.get_downloader_conf(default_downloader_id):
            default_downloader_id = ""
        return default_downloader_id

    @property
    def default_download_setting_id(self):
        """
        获取默认下载设置
        :return: 默认下载设置id
        """
        default_download_setting_id = SystemConfig().get(SystemConfigKey.DefaultDownloadSetting) or "-1"
        if not self._download_settings.get(default_download_setting_id):
            default_download_setting_id = "-1"
        return default_download_setting_id

    def get_downloader_type(self, downloader_id=None):
        """
        获取下载器的类型
        """
        if not downloader_id:
            return self.default_client.get_type()
        return self.__get_client(downloader_id).get_type()

    @property
    def default_client(self):
        """
        获取默认下载器实例
        """
        return self.__get_client(self.default_downloader_id)

    @property
    def monitor_downloader_ids(self):
        """
        获取监控下载器ID列表
        """
        return self._monitor_downloader_ids

    def start_service(self):
        """
        转移任务调度
        """
        # 移出现有任务
        self.stop_service()
        # 启动转移任务
        if not self._monitor_downloader_ids:
            return
        self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
        for downloader_id in self._monitor_downloader_ids:
            self._scheduler.add_job(func=self.transfer,
                                    args=[downloader_id],
                                    trigger='interval',
                                    seconds=PT_TRANSFER_INTERVAL)
        self._scheduler.print_jobs()
        self._scheduler.start()
        log.info("下载文件转移服务启动，目的目录：媒体库")

    def __get_client(self, did=None):
        if not did:
            return None
        downloader_conf = self.get_downloader_conf(did)
        if not downloader_conf:
            log.info("【Downloader】下载器配置不存在")
            return None
        if not downloader_conf.get("enabled"):
            log.info(f"【Downloader】下载器 {downloader_conf.get('name')} 未启用")
            return None
        ctype = downloader_conf.get("type")
        config = downloader_conf.get("config")
        config["download_dir"] = downloader_conf.get("download_dir")
        config["name"] = downloader_conf.get("name")
        with client_lock:
            if not self.clients.get(str(did)):
                self.clients[str(did)] = self.__build_class(ctype, config)
            return self.clients.get(str(did))

    def download(self,
                 media_info,
                 is_paused=None,
                 tag=None,
                 download_dir=None,
                 download_setting=None,
                 downloader_id=None,
                 upload_limit=None,
                 download_limit=None,
                 torrent_file=None,
                 in_from=None,
                 user_name=None,
                 proxy=None):
        """
        添加下载任务，根据当前使用的下载器分别调用不同的客户端处理
        :param media_info: 需下载的媒体信息，含URL地址
        :param is_paused: 是否暂停下载
        :param tag: 种子标签
        :param download_dir: 指定下载目录
        :param download_setting: 下载设置id，为None则使用-1默认设置，为"-2"则不使用下载设置
        :param downloader_id: 指定下载器ID下载
        :param upload_limit: 上传速度限制
        :param download_limit: 下载速度限制
        :param torrent_file: 种子文件路径
        :param in_from: 来源
        :param user_name: 用户名
        :param proxy: 是否使用代理，指定该选项为 True/False 会覆盖 site_info 的设置
        :return: 下载器类型, 种子ID，错误信息
        """

        def __download_fail(msg):
            """
            触发下载失败事件和发送消息
            """
            self.eventmanager.send_event(EventType.DownloadFail, {
                "media_info": media_info.to_dict(),
                "reason": msg
            })
            if in_from:
                self.message.send_download_fail_message(media_info, f"添加下载任务失败：{msg}")

        # 触发下载事件
        self.eventmanager.send_event(EventType.DownloadAdd, {
            "media_info": media_info.to_dict(),
            "is_paused": is_paused,
            "tag": tag,
            "download_dir": download_dir,
            "download_setting": download_setting,
            "downloader_id": downloader_id,
            "torrent_file": torrent_file
        })

        # 标题
        title = media_info.org_string
        # 详情页面
        page_url = media_info.page_url
        # 默认值
        site_info, dl_files_folder, dl_files, retmsg = {}, "", [], ""

        if torrent_file:
            # 有种子文件时解析种子信息
            url = os.path.basename(torrent_file)
            content, dl_files_folder, dl_files, retmsg = Torrent().read_torrent_content(torrent_file)
        else:
            # 没有种子文件解析链接
            url = media_info.enclosure
            if not url:
                __download_fail("下载链接为空")
                return None, None, "下载链接为空"
            # 获取种子内容，磁力链不解析
            if url.startswith("magnet:"):
                content = url
            else:
                # 获取Cookie和ua等
                site_info = self.sites.get_sites(siteurl=url)
                # 下载种子文件，并读取信息
                _, content, dl_files_folder, dl_files, retmsg = Torrent().get_torrent_info(
                    url=url,
                    cookie=site_info.get("cookie"),
                    ua=site_info.get("ua"),
                    referer=page_url if site_info.get("referer") else None,
                    proxy=proxy if proxy is not None else site_info.get("proxy")
                )

        # 解析完成
        if retmsg:
            log.warn("【Downloader】%s" % retmsg)

        if not content:
            __download_fail(retmsg)
            return None, None, retmsg

        # 下载设置
        if not download_setting and media_info.site:
            # 站点的下载设置
            download_setting = self.sites.get_site_download_setting(media_info.site)
        if download_setting == "-2":
            # 不使用下载设置
            download_attr = {}
        elif download_setting:
            # 传入的下载设置
            download_attr = self.get_download_setting(download_setting) \
                            or self.get_download_setting(self.default_download_setting_id)
        else:
            # 默认下载设置
            download_attr = self.get_download_setting(self.default_download_setting_id)

        # 下载设置名称
        download_setting_name = download_attr.get('name')

        # 下载器实例
        if not downloader_id:
            downloader_id = download_attr.get("downloader")
        downloader_conf = self.get_downloader_conf(downloader_id)
        downloader = self.__get_client(downloader_id)

        if not downloader or not downloader_conf:
            __download_fail("请检查下载设置所选下载器是否有效且启用")
            return None, None, f"下载设置 {download_setting_name} 所选下载器失效"
        downloader_name = downloader_conf.get("name")

        # 开始添加下载
        try:
            # 下载设置中的分类
            category = download_attr.get("category")
            # 合并TAG
            tags = download_attr.get("tags")
            if tags:
                tags = str(tags).split(";")
                if tag:
                    if isinstance(tag, list):
                        tags.extend(tag)
                    else:
                        tags.append(tag)
            else:
                if tag:
                    if isinstance(tag, list):
                        tags = tag
                    else:
                        tags = [tag]

            # 暂停
            if is_paused is None:
                is_paused = StringUtils.to_bool(download_attr.get("is_paused"))
            else:
                is_paused = True if is_paused else False
            # 上传限速
            if not upload_limit:
                upload_limit = download_attr.get("upload_limit")
            # 下载限速
            if not download_limit:
                download_limit = download_attr.get("download_limit")
            # 分享率
            ratio_limit = download_attr.get("ratio_limit")
            # 做种时间
            seeding_time_limit = download_attr.get("seeding_time_limit")
            # 下载目录设置
            if not download_dir:
                download_info = self.__get_download_dir_info(media_info, downloader_conf.get("download_dir"))
                download_dir = download_info.get('path')
                # 从下载目录中获取分类标签
                if not category:
                    category = download_info.get('category')
            # 添加下载
            print_url = content if isinstance(content, str) else url
            if is_paused:
                log.info(f"【Downloader】下载器 {downloader_name} 添加任务并暂停：%s，目录：%s，Url：%s" % (
                    title, download_dir, print_url))
            else:
                log.info(f"【Downloader】下载器 {downloader_name} 添加任务：%s，目录：%s，Url：%s" % (
                    title, download_dir, print_url))
            # 下载ID
            download_id = None
            downloader_type = downloader.get_type()
            if downloader_type == DownloaderType.TR:
                ret = downloader.add_torrent(content,
                                             is_paused=is_paused,
                                             download_dir=download_dir,
                                             cookie=site_info.get("cookie"))
                if ret:
                    download_id = ret.hashString
                    downloader.change_torrent(tid=download_id,
                                              tag=tags,
                                              upload_limit=upload_limit,
                                              download_limit=download_limit,
                                              ratio_limit=ratio_limit,
                                              seeding_time_limit=seeding_time_limit)

            elif downloader_type == DownloaderType.QB:
                # 加标签以获取添加下载后的编号
                torrent_tag = "NT" + StringUtils.generate_random_str(5)
                if tags:
                    tags += [torrent_tag]
                else:
                    tags = [torrent_tag]
                # 布局默认原始
                ret = downloader.add_torrent(content,
                                             is_paused=is_paused,
                                             download_dir=download_dir,
                                             tag=tags,
                                             category=category,
                                             content_layout="Original",
                                             upload_limit=upload_limit,
                                             download_limit=download_limit,
                                             ratio_limit=ratio_limit,
                                             seeding_time_limit=seeding_time_limit,
                                             cookie=site_info.get("cookie"))
                if ret:
                    download_id = downloader.get_torrent_id_by_tag(torrent_tag)
            else:
                # 其它下载器，添加下载后需返回下载ID或添加状态
                ret = downloader.add_torrent(content,
                                             is_paused=is_paused,
                                             tag=tags,
                                             download_dir=download_dir,
                                             category=category)
                download_id = ret
            # 添加下载成功
            if ret:
                # 计算数据文件保存的路径
                save_dir = subtitle_dir = None
                visit_dir = self.get_download_visit_dir(download_dir)
                if visit_dir:
                    if dl_files_folder:
                        # 种子文件带目录
                        save_dir = os.path.join(visit_dir, dl_files_folder)
                        subtitle_dir = save_dir
                    elif dl_files:
                        # 种子文件为单独文件
                        save_dir = os.path.join(visit_dir, dl_files[0])
                        subtitle_dir = visit_dir
                    else:
                        save_dir = None
                        subtitle_dir = visit_dir
                # 登记下载历史，记录下载目录
                self.dbhelper.insert_download_history(media_info=media_info,
                                                      downloader=downloader_id,
                                                      download_id=download_id,
                                                      save_dir=save_dir)
                # 下载站点字幕文件
                if page_url \
                        and subtitle_dir \
                        and site_info \
                        and site_info.get("subtitle"):
                    ThreadHelper().start_thread(
                        self.sitesubtitle.download,
                        (
                            media_info,
                            site_info.get("id"),
                            site_info.get("cookie"),
                            site_info.get("ua"),
                            subtitle_dir
                        )
                    )
                # 发送下载消息
                if in_from:
                    media_info.user_name = user_name
                    self.message.send_download_message(in_from=in_from,
                                                       can_item=media_info,
                                                       download_setting_name=download_setting_name,
                                                       downloader_name=downloader_name)
                return downloader_id, download_id, ""
            else:
                __download_fail("请检查下载任务是否已存在")
                return downloader_id, None, f"下载器 {downloader_name} 添加下载任务失败，请检查下载任务是否已存在"
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            __download_fail(str(e))
            log.error(f"【Downloader】下载器 {downloader_name} 添加任务出错：%s" % str(e))
            return None, None, str(e)

    def transfer(self, downloader_id=None):
        """
        转移下载完成的文件，进行文件识别重命名到媒体库目录
        """
        downloader_ids = [downloader_id] if downloader_id \
            else self._monitor_downloader_ids
        for downloader_id in downloader_ids:
            with lock:
                # 获取下载器配置
                downloader_conf = self.get_downloader_conf(downloader_id)
                name = downloader_conf.get("name")
                only_nastool = downloader_conf.get("only_nastool")
                match_path = downloader_conf.get("match_path")
                rmt_mode = ModuleConf.RMT_MODES.get(downloader_conf.get("rmt_mode"))
                # 获取下载器实例
                _client = self.__get_client(downloader_id)
                if not _client:
                    continue
                trans_tasks = _client.get_transfer_task(tag=PT_TAG if only_nastool else None, match_path=match_path)
                if trans_tasks:
                    log.info(f"【Downloader】下载器 {name} 开始转移下载文件...")
                else:
                    continue
                for task in trans_tasks:
                    done_flag, done_msg = self.filetransfer.transfer_media(
                        in_from=self._DownloaderEnum[str(downloader_id)],
                        in_path=task.get("path"),
                        rmt_mode=rmt_mode)
                    if not done_flag:
                        log.warn(f"【Downloader】下载器 {name} 任务%s 转移失败：%s" % (task.get("path"), done_msg))
                        _client.set_torrents_status(ids=task.get("id"),
                                                    tags=task.get("tags"))
                    else:
                        if rmt_mode in [RmtMode.MOVE, RmtMode.RCLONE, RmtMode.MINIO]:
                            log.warn(f"【Downloader】下载器 {name} 移动模式下删除种子文件：%s" % task.get("id"))
                            _client.delete_torrents(delete_file=True, ids=task.get("id"))
                        else:
                            _client.set_torrents_status(ids=task.get("id"),
                                                        tags=task.get("tags"))
                log.info(f"【Downloader】下载器 {name} 下载文件转移结束")

    def get_torrents(self, downloader_id=None, ids=None, tag=None):
        """
        获取种子信息
        :param downloader_id: 下载器ID
        :param ids: 种子ID
        :param tag: 种子标签
        :return: 种子信息列表
        """
        if not downloader_id:
            downloader_id = self.default_downloader_id
        _client = self.__get_client(downloader_id)
        if not _client:
            return None
        try:
            torrents, error_flag = _client.get_torrents(tag=tag, ids=ids)
            if error_flag:
                return None
            return torrents
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return None

    def get_remove_torrents(self, downloader_id=None, config=None):
        """
        查询符合删种策略的种子信息
        :return: 符合删种策略的种子信息列表
        """
        if not config or not downloader_id:
            return []
        _client = self.__get_client(downloader_id)
        if not _client:
            return []
        config["filter_tags"] = []
        if config.get("onlynastool"):
            config["filter_tags"] = config["tags"] + [PT_TAG]
        else:
            config["filter_tags"] = config["tags"]
        torrents = _client.get_remove_torrents(config=config)
        torrents.sort(key=lambda x: x.get("name"))
        return torrents

    def get_downloading_torrents(self, downloader_id=None, ids=None, tag=None):
        """
        查询正在下载中的种子信息
        :return: 下载器名称，发生错误时返回None
        """
        if not downloader_id:
            downloader_id = self.default_downloader_id
        _client = self.__get_client(downloader_id)
        if not _client:
            return None
        try:
            return _client.get_downloading_torrents(tag=tag, ids=ids)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return None

    def get_downloading_progress(self, downloader_id=None, ids=None):
        """
        查询正在下载中的进度信息
        """
        if not downloader_id:
            downloader_id = self.default_downloader_id
        downloader_conf = self.get_downloader_conf(downloader_id)
        only_nastool = downloader_conf.get("only_nastool")
        _client = self.__get_client(downloader_id)
        if not _client:
            return []
        if only_nastool:
            tag = [PT_TAG]
        else:
            tag = None
        return _client.get_downloading_progress(tag=tag, ids=ids)

    def get_completed_torrents(self, downloader_id=None, ids=None, tag=None):
        """
        查询下载完成的种子列表
        :param downloader_id: 下载器ID
        :param ids: 种子ID列表
        :param tag: 种子标签
        :return: 种子信息列表，发生错误时返回None
        """
        if not downloader_id:
            downloader_id = self.default_downloader_id
        _client = self.__get_client(downloader_id)
        if not _client:
            return None
        return _client.get_completed_torrents(ids=ids, tag=tag)

    def start_torrents(self, downloader_id=None, ids=None):
        """
        下载控制：开始
        :param downloader_id: 下载器ID
        :param ids: 种子ID列表
        :return: 处理状态
        """
        if not ids:
            return False
        _client = self.__get_client(downloader_id) if downloader_id else self.default_client
        if not _client:
            return False
        return _client.start_torrents(ids)

    def stop_torrents(self, downloader_id=None, ids=None):
        """
        下载控制：停止
        :param downloader_id: 下载器ID
        :param ids: 种子ID列表
        :return: 处理状态
        """
        if not ids:
            return False
        _client = self.__get_client(downloader_id) if downloader_id else self.default_client
        if not _client:
            return False
        return _client.stop_torrents(ids)

    def delete_torrents(self, downloader_id=None, ids=None, delete_file=False):
        """
        删除种子
        :param downloader_id: 下载器ID
        :param ids: 种子ID列表
        :param delete_file: 是否删除文件
        :return: 处理状态
        """
        if not ids:
            return False
        _client = self.__get_client(downloader_id) if downloader_id else self.default_client
        if not _client:
            return False
        return _client.delete_torrents(delete_file=delete_file, ids=ids)

    def batch_download(self,
                       in_from: SearchType,
                       media_list: list,
                       need_tvs: dict = None,
                       user_name=None):
        """
        根据命中的种子媒体信息，添加下载，由RSS或Searcher调用
        :param in_from: 来源
        :param media_list: 命中并已经识别好的媒体信息列表，包括名称、年份、季、集等信息
        :param need_tvs: 缺失的剧集清单，对于剧集只有在该清单中的季和集才会下载，对于电影无需输入该参数
        :param user_name: 用户名称
        :return: 已经添加了下载的媒体信息表表、剩余未下载到的媒体信息
        """

        # 已下载的项目
        return_items = []
        # 返回按季、集数倒序排序的列表
        download_list = Torrent().get_download_list(media_list, self._download_order)

        def __download(download_item, torrent_file=None, tag=None, is_paused=None):
            """
            下载及发送通知
            """
            _downloader_id, did, msg = self.download(
                media_info=download_item,
                download_dir=download_item.save_path,
                download_setting=download_item.download_setting,
                torrent_file=torrent_file,
                tag=tag,
                is_paused=is_paused,
                in_from=in_from,
                user_name=user_name)
            if did:
                if download_item not in return_items:
                    return_items.append(download_item)
            return _downloader_id, did

        def __update_seasons(tmdbid, need, current):
            """
            更新need_tvs季数
            """
            need = list(set(need).difference(set(current)))
            for cur in current:
                for nt in need_tvs.get(tmdbid):
                    if cur == nt.get("season") or (cur == 1 and not nt.get("season")):
                        need_tvs[tmdbid].remove(nt)
            if not need_tvs.get(tmdbid):
                need_tvs.pop(tmdbid)
            return need

        def __update_episodes(tmdbid, seq, need, current):
            """
            更新need_tvs集数
            """
            need = list(set(need).difference(set(current)))
            if need:
                need_tvs[tmdbid][seq]["episodes"] = need
            else:
                need_tvs[tmdbid].pop(seq)
                if not need_tvs.get(tmdbid):
                    need_tvs.pop(tmdbid)
            return need

        def __get_season_episodes(tmdbid, season):
            """
            获取需要的季的集数
            """
            if not need_tvs.get(tmdbid):
                return 0
            for nt in need_tvs.get(tmdbid):
                if season == nt.get("season"):
                    return nt.get("total_episodes")
            return 0

        # 下载掉所有的电影
        for item in download_list:
            if item.type == MediaType.MOVIE:
                __download(item)

        # 电视剧整季匹配
        if need_tvs:
            # 先把整季缺失的拿出来，看是否刚好有所有季都满足的种子
            need_seasons = {}
            for need_tmdbid, need_tv in need_tvs.items():
                for tv in need_tv:
                    if not tv:
                        continue
                    if not tv.get("episodes"):
                        if not need_seasons.get(need_tmdbid):
                            need_seasons[need_tmdbid] = []
                        need_seasons[need_tmdbid].append(tv.get("season") or 1)
            # 查找整季包含的种子，只处理整季没集的种子或者是集数超过季的种子
            for need_tmdbid, need_season in need_seasons.items():
                for item in download_list:
                    if item.type == MediaType.MOVIE:
                        continue
                    item_season = item.get_season_list()
                    if item.get_episode_list():
                        continue
                    if need_tmdbid == item.tmdb_id:
                        if set(item_season).issubset(set(need_season)):
                            if len(item_season) == 1:
                                # 只有一季的可能是命名错误，需要打开种子鉴别，只有实际集数大于等于总集数才下载
                                torrent_episodes, torrent_path = self.get_torrent_episodes(
                                    url=item.enclosure,
                                    page_url=item.page_url)
                                if not torrent_episodes \
                                        or len(torrent_episodes) >= __get_season_episodes(need_tmdbid, item_season[0]):
                                    _, download_id = __download(download_item=item, torrent_file=torrent_path)
                                else:
                                    log.info(
                                        f"【Downloader】种子 {item.org_string} 未含集数信息，解析文件数为 {len(torrent_episodes)}")
                                    continue
                            else:
                                _, download_id = __download(item)
                            if download_id:
                                # 更新仍需季集
                                need_season = __update_seasons(tmdbid=need_tmdbid,
                                                               need=need_season,
                                                               current=item_season)
        # 电视剧季内的集匹配
        if need_tvs:
            need_tv_list = list(need_tvs)
            for need_tmdbid in need_tv_list:
                need_tv = need_tvs.get(need_tmdbid)
                if not need_tv:
                    continue
                index = 0
                for tv in need_tv:
                    need_season = tv.get("season") or 1
                    need_episodes = tv.get("episodes")
                    total_episodes = tv.get("total_episodes")
                    # 缺失整季的转化为缺失集进行比较
                    if not need_episodes:
                        need_episodes = list(range(1, total_episodes + 1))
                    for item in download_list:
                        if item.type == MediaType.MOVIE:
                            continue
                        if item.tmdb_id == need_tmdbid:
                            if item in return_items:
                                continue
                            # 只处理单季含集的种子
                            item_season = item.get_season_list()
                            if len(item_season) != 1 or item_season[0] != need_season:
                                continue
                            item_episodes = item.get_episode_list()
                            if not item_episodes:
                                continue
                            # 为需要集的子集则下载
                            if set(item_episodes).issubset(set(need_episodes)):
                                _, download_id = __download(item)
                                if download_id:
                                    # 更新仍需集数
                                    need_episodes = __update_episodes(tmdbid=need_tmdbid,
                                                                      need=need_episodes,
                                                                      seq=index,
                                                                      current=item_episodes)
                    index += 1

        # 仍然缺失的剧集，从整季中选择需要的集数文件下载，仅支持QB和TR
        if need_tvs:
            need_tv_list = list(need_tvs)
            for need_tmdbid in need_tv_list:
                need_tv = need_tvs.get(need_tmdbid)
                if not need_tv:
                    continue
                index = 0
                for tv in need_tv:
                    need_season = tv.get("season") or 1
                    need_episodes = tv.get("episodes")
                    if not need_episodes:
                        continue
                    for item in download_list:
                        if item.type == MediaType.MOVIE:
                            continue
                        if item in return_items:
                            continue
                        if not need_episodes:
                            break
                        # 选中一个单季整季的或单季包括需要的所有集的
                        if item.tmdb_id == need_tmdbid \
                                and (not item.get_episode_list()
                                     or set(item.get_episode_list()).intersection(set(need_episodes))) \
                                and len(item.get_season_list()) == 1 \
                                and item.get_season_list()[0] == need_season:
                            # 检查种子看是否有需要的集
                            torrent_episodes, torrent_path = self.get_torrent_episodes(
                                url=item.enclosure,
                                page_url=item.page_url)
                            selected_episodes = set(torrent_episodes).intersection(set(need_episodes))
                            if not selected_episodes:
                                log.info("【Downloader】%s 没有需要的集，跳过..." % item.org_string)
                                continue
                            # 添加下载并暂停
                            downloader_id, download_id = __download(download_item=item,
                                                                    torrent_file=torrent_path,
                                                                    is_paused=True)
                            if not download_id:
                                continue
                            # 更新仍需集数
                            need_episodes = __update_episodes(tmdbid=need_tmdbid,
                                                              need=need_episodes,
                                                              seq=index,
                                                              current=selected_episodes)
                            # 设置任务只下载想要的文件
                            log.info("【Downloader】从 %s 中选取集：%s" % (item.org_string, selected_episodes))
                            self.set_files_status(tid=download_id,
                                                  need_episodes=selected_episodes,
                                                  downloader_id=downloader_id)
                            # 重新开始任务
                            log.info("【Downloader】%s 开始下载 " % item.org_string)
                            self.start_torrents(ids=download_id,
                                                downloader_id=downloader_id)
                            # 记录下载项
                            return_items.append(item)
                index += 1

        # 返回下载的资源，剩下没下完的
        return return_items, need_tvs

    def check_exists_medias(self, meta_info, no_exists=None, total_ep=None):
        """
        检查媒体库，查询是否存在，对于剧集同时返回不存在的季集信息
        :param meta_info: 已识别的媒体信息，包括标题、年份、季、集信息
        :param no_exists: 在调用该方法前已经存储的不存在的季集信息，有传入时该函数搜索的内容将会叠加后输出
        :param total_ep: 各季的总集数
        :return: 当前媒体是否缺失，各标题总的季集和缺失的季集，需要发送的消息
        """
        if not no_exists:
            no_exists = {}
        if not total_ep:
            total_ep = {}
        # 查找的季
        if not meta_info.begin_season:
            search_season = None
        else:
            search_season = meta_info.get_season_list()
        # 查找的集
        search_episode = meta_info.get_episode_list()
        if search_episode and not search_season:
            search_season = [1]

        # 返回的消息列表
        message_list = []
        if meta_info.type != MediaType.MOVIE:
            # 是否存在的标志
            return_flag = False
            # 搜索电视剧的信息
            tv_info = self.media.get_tmdb_info(mtype=MediaType.TV, tmdbid=meta_info.tmdb_id)
            if tv_info:
                # 传入检查季
                total_seasons = []
                if search_season:
                    for season in search_season:
                        if total_ep.get(season):
                            episode_num = total_ep.get(season)
                        else:
                            episode_num = self.media.get_tmdb_season_episodes_num(tv_info=tv_info, season=season)
                        if not episode_num:
                            log.info("【Downloader】%s 第%s季 不存在" % (meta_info.get_title_string(), season))
                            message_list.append("%s 第%s季 不存在" % (meta_info.get_title_string(), season))
                            continue
                        total_seasons.append({"season_number": season, "episode_count": episode_num})
                        log.info(
                            "【Downloader】%s 第%s季 共有 %s 集" % (meta_info.get_title_string(), season, episode_num))
                else:
                    # 共有多少季，每季有多少季
                    total_seasons = self.media.get_tmdb_tv_seasons(tv_info=tv_info)
                    log.info(
                        "【Downloader】%s %s 共有 %s 季" % (
                            meta_info.type.value, meta_info.get_title_string(), len(total_seasons)))
                    message_list.append(
                        "%s %s 共有 %s 季" % (meta_info.type.value, meta_info.get_title_string(), len(total_seasons)))
                # 没有得到总季数时，返回None
                if not total_seasons:
                    return_flag = None
                else:
                    # 查询缺少多少集
                    for season in total_seasons:
                        season_number = season.get("season_number")
                        episode_count = season.get("episode_count")
                        if not season_number or not episode_count:
                            continue
                        # 检查Emby
                        no_exists_episodes = self.mediaserver.get_no_exists_episodes(meta_info,
                                                                                     season_number,
                                                                                     episode_count)
                        # 没有配置Emby
                        if no_exists_episodes is None:
                            no_exists_episodes = self.filetransfer.get_no_exists_medias(meta_info,
                                                                                        season_number,
                                                                                        episode_count)
                        if no_exists_episodes:
                            # 排序
                            no_exists_episodes.sort()
                            # 缺失集初始化
                            if not no_exists.get(meta_info.tmdb_id):
                                no_exists[meta_info.tmdb_id] = []
                            # 缺失集提示文本
                            exists_tvs_str = "、".join(["%s" % tv for tv in no_exists_episodes])
                            # 存入总缺失集
                            if len(no_exists_episodes) >= episode_count:
                                no_item = {"season": season_number, "episodes": [], "total_episodes": episode_count}
                                log.info(
                                    "【Downloader】%s 第%s季 缺失 %s 集" % (
                                        meta_info.get_title_string(), season_number, episode_count))
                                if search_season:
                                    message_list.append(
                                        "%s 第%s季 缺失 %s 集" % (meta_info.title, season_number, episode_count))
                                else:
                                    message_list.append("第%s季 缺失 %s 集" % (season_number, episode_count))
                            else:
                                no_item = {"season": season_number, "episodes": no_exists_episodes,
                                           "total_episodes": episode_count}
                                log.info(
                                    "【Downloader】%s 第%s季 缺失集：%s" % (
                                        meta_info.get_title_string(), season_number, exists_tvs_str))
                                if search_season:
                                    message_list.append(
                                        "%s 第%s季 缺失集：%s" % (meta_info.title, season_number, exists_tvs_str))
                                else:
                                    message_list.append("第%s季 缺失集：%s" % (season_number, exists_tvs_str))
                            if no_item not in no_exists.get(meta_info.tmdb_id):
                                no_exists[meta_info.tmdb_id].append(no_item)
                            # 输入检查集
                            if search_episode:
                                # 有集数，肯定只有一季
                                if not set(search_episode).intersection(set(no_exists_episodes)):
                                    # 搜索的跟不存在的没有交集，说明都存在了
                                    msg = f"媒体库中已存在剧集：\n" \
                                          f" • {meta_info.get_title_string()} {meta_info.get_season_episode_string()}"
                                    log.info(f"【Downloader】{msg}")
                                    message_list.append(msg)
                                    return_flag = True
                                    break
                        else:
                            log.info("【Downloader】%s 第%s季 共%s集 已全部存在" % (
                                meta_info.get_title_string(), season_number, episode_count))
                            if search_season:
                                message_list.append(
                                    "%s 第%s季 共%s集 已全部存在" % (meta_info.title, season_number, episode_count))
                            else:
                                message_list.append(
                                    "第%s季 共%s集 已全部存在" % (season_number, episode_count))
            else:
                log.info("【Downloader】%s 无法查询到媒体详细信息" % meta_info.get_title_string())
                message_list.append("%s 无法查询到媒体详细信息" % meta_info.get_title_string())
                return_flag = None
            # 全部存在
            if return_flag is False and not no_exists.get(meta_info.tmdb_id):
                return_flag = True
            # 返回
            return return_flag, no_exists, message_list
        # 检查电影
        else:
            exists_movies = self.mediaserver.get_movies(meta_info.title, meta_info.year)
            if exists_movies is None:
                exists_movies = self.filetransfer.get_no_exists_medias(meta_info)
            if exists_movies:
                movies_str = "\n • ".join(["%s (%s)" % (m.get('title'), m.get('year')) for m in exists_movies])
                msg = f"媒体库中已存在电影：\n • {movies_str}"
                log.info(f"【Downloader】{msg}")
                message_list.append(msg)
                return True, {}, message_list
            return False, {}, message_list

    def get_files(self, tid, downloader_id=None):
        """
        获取种子文件列表
        """
        # 客户端
        _client = self.__get_client(downloader_id) if downloader_id else self.default_client
        if not _client:
            return []
        # 种子文件
        torrent_files = _client.get_files(tid)
        if not torrent_files:
            return []

        ret_files = []
        if _client.get_type() == DownloaderType.TR:
            for file_id, torrent_file in enumerate(torrent_files):
                ret_files.append({
                    "id": file_id,
                    "name": torrent_file.name
                })
        elif _client.get_type() == DownloaderType.QB:
            for torrent_file in torrent_files:
                ret_files.append({
                    "id": torrent_file.get("index"),
                    "name": torrent_file.get("name")
                })

        return ret_files

    def set_files_status(self, tid, need_episodes, downloader_id=None):
        """
        设置文件下载状态，选中需要下载的季集对应的文件下载，其余不下载
        :param tid: 种子的hash或id
        :param need_episodes: 需要下载的文件的集信息
        :param downloader_id: 下载器ID
        :return: 返回选中的集的列表
        """
        sucess_epidised = []

        # 客户端
        if not downloader_id:
            downloader_id = self.default_downloader_id
        _client = self.__get_client(downloader_id)
        downloader_conf = self.get_downloader_conf(downloader_id)
        if not _client:
            return []
        # 种子文件
        torrent_files = self.get_files(tid=tid, downloader_id=downloader_id)
        if not torrent_files:
            return []
        if downloader_conf.get("type") == "transmission":
            files_info = {}
            for torrent_file in torrent_files:
                file_id = torrent_file.get("id")
                file_name = torrent_file.get("name")
                meta_info = MetaInfo(file_name)
                if not meta_info.get_episode_list():
                    selected = False
                else:
                    selected = set(meta_info.get_episode_list()).issubset(set(need_episodes))
                    if selected:
                        sucess_epidised = list(set(sucess_epidised).union(set(meta_info.get_episode_list())))
                if not files_info.get(tid):
                    files_info[tid] = {file_id: {'priority': 'normal', 'selected': selected}}
                else:
                    files_info[tid][file_id] = {'priority': 'normal', 'selected': selected}
            if sucess_epidised and files_info:
                _client.set_files(file_info=files_info)
        elif downloader_conf.get("type") == "qbittorrent":
            file_ids = []
            for torrent_file in torrent_files:
                file_id = torrent_file.get("id")
                file_name = torrent_file.get("name")
                meta_info = MetaInfo(file_name)
                if not meta_info.get_episode_list() or not set(meta_info.get_episode_list()).issubset(
                        set(need_episodes)):
                    file_ids.append(file_id)
                else:
                    sucess_epidised = list(set(sucess_epidised).union(set(meta_info.get_episode_list())))
            if sucess_epidised and file_ids:
                _client.set_files(torrent_hash=tid, file_ids=file_ids, priority=0)
        return sucess_epidised

    def get_download_dirs(self, setting=None):
        """
        返回下载器中设置的保存目录
        """
        if not setting:
            setting = self.default_download_setting_id
        # 查询下载设置
        download_setting = self.get_download_setting(sid=setting)
        downloader_conf = self.get_downloader_conf(download_setting.get("downloader"))
        if not downloader_conf:
            return []
        downloaddir = downloader_conf.get("download_dir")
        # 查询目录
        save_path_list = [attr.get("save_path") for attr in downloaddir if attr.get("save_path")]
        save_path_list.sort()
        return list(set(save_path_list))

    def get_download_visit_dirs(self):
        """
        返回所有下载器中设置的访问目录
        """
        download_dirs = []
        for downloader_conf in self.get_downloader_conf().values():
            download_dirs += downloader_conf.get("download_dir")
        visit_path_list = [attr.get("container_path") or attr.get("save_path") for attr in download_dirs if
                           attr.get("save_path")]
        visit_path_list.sort()
        return list(set(visit_path_list))

    def get_download_visit_dir(self, download_dir, downloader_id=None):
        """
        返回下载器中设置的访问目录
        """
        if not downloader_id:
            downloader_id = self.default_downloader_id
        downloader_conf = self.get_downloader_conf(downloader_id)
        _client = self.__get_client(downloader_id)
        if not _client:
            return ""
        true_path, _ = _client.get_replace_path(download_dir, downloader_conf.get("download_dir"))
        return true_path

    @staticmethod
    def __get_download_dir_info(media, downloaddir):
        """
        根据媒体信息读取一个下载目录的信息
        """
        if media:
            for attr in downloaddir or []:
                if not attr:
                    continue
                if attr.get("type") and attr.get("type") != media.type.value:
                    continue
                if attr.get("category") and attr.get("category") != media.category:
                    continue
                if not attr.get("save_path") and not attr.get("label"):
                    continue
                if (attr.get("container_path") or attr.get("save_path")) \
                        and os.path.exists(attr.get("container_path") or attr.get("save_path")) \
                        and media.size \
                        and SystemUtils.get_free_space(
                    attr.get("container_path") or attr.get("save_path")
                ) < NumberUtils.get_size_gb(
                    StringUtils.num_filesize(media.size)
                ):
                    continue
                return {
                    "path": attr.get("save_path"),
                    "category": attr.get("label")
                }
        return {"path": None, "category": None}

    @staticmethod
    def __get_client_type(type_name):
        """
        根据名称返回下载器类型
        """
        if not type_name:
            return None
        for dict_type in DownloaderType:
            if dict_type.name == type_name or dict_type.value == type_name:
                return dict_type

    def get_torrent_episodes(self, url, page_url=None):
        """
        解析种子文件，获取集数
        :return: 集数列表、种子路径
        """
        site_info = self.sites.get_sites(siteurl=url)
        # 保存种子文件
        file_path, _, _, files, retmsg = Torrent().get_torrent_info(
            url=url,
            cookie=site_info.get("cookie"),
            ua=site_info.get("ua"),
            referer=page_url if site_info.get("referer") else None,
            proxy=site_info.get("proxy")
        )
        if not files:
            log.error("【Downloader】读取种子文件集数出错：%s" % retmsg)
            return [], None
        episodes = []
        for file in files:
            if os.path.splitext(file)[-1] not in RMT_MEDIAEXT:
                continue
            meta = MetaInfo(file)
            if not meta.begin_episode:
                continue
            episodes = list(set(episodes).union(set(meta.get_episode_list())))
        return episodes, file_path

    def get_download_setting(self, sid=None):
        """
        获取下载设置
        :return: 下载设置
        """
        # 更新预设
        preset_downloader_conf = self.get_downloader_conf(self.default_downloader_id)
        if preset_downloader_conf:
            self._download_settings["-1"]["downloader"] = self.default_downloader_id
            self._download_settings["-1"]["downloader_name"] = preset_downloader_conf.get("name")
            self._download_settings["-1"]["downloader_type"] = preset_downloader_conf.get("type")
        if not sid:
            return self._download_settings
        return self._download_settings.get(str(sid)) or {}

    def set_speed_limit(self, downloader_id=None, download_limit=None, upload_limit=None):
        """
        设置速度限制
        :param downloader_id: 下载器ID
        :param download_limit: 下载速度限制，单位KB/s
        :param upload_limit: 上传速度限制，单位kB/s
        """
        if not downloader_id:
            return
        _client = self.__get_client(downloader_id)
        if not _client:
            return
        try:
            download_limit = int(download_limit) if download_limit else 0
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            download_limit = 0
        try:
            upload_limit = int(upload_limit) if upload_limit else 0
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            upload_limit = 0
        _client.set_speed_limit(download_limit=download_limit, upload_limit=upload_limit)

    def get_downloader_conf(self, did=None):
        """
        获取下载器配置
        """
        if not did:
            return self._downloader_confs
        return self._downloader_confs.get(str(did))

    def get_downloader_conf_simple(self):
        """
        获取简化下载器配置
        """
        ret_dict = {}
        for downloader_conf in self.get_downloader_conf().values():
            ret_dict[str(downloader_conf.get("id"))] = {
                "id": downloader_conf.get("id"),
                "name": downloader_conf.get("name"),
                "type": downloader_conf.get("type"),
                "enabled": downloader_conf.get("enabled"),
            }
        return ret_dict

    def get_downloader(self, downloader_id=None):
        """
        获取下载器实例
        """
        if not downloader_id:
            return self.default_client
        return self.__get_client(downloader_id)

    def get_status(self, dtype=None, config=None):
        """
        测试下载器状态
        """
        if not config or not dtype:
            return False
        # 测试状态
        state = self.__build_class(ctype=dtype, conf=config).get_status()
        if not state:
            log.error(f"【Downloader】下载器连接测试失败")
        return state

    def recheck_torrents(self, downloader_id=None, ids=None):
        """
        下载控制：重新校验种子
        :param downloader_id: 下载器ID
        :param ids: 种子ID列表
        :return: 处理状态
        """
        if not ids:
            return False
        _client = self.__get_client(downloader_id) if downloader_id else self.default_client
        if not _client:
            return False
        return _client.recheck_torrents(ids)

    def stop_service(self):
        """
        停止服务
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            print(str(e))

    def get_download_history(self, date=None, hid=None, num=30, page=1):
        """
        获取下载历史记录
        """
        return self.dbhelper.get_download_history(date=date, hid=hid, num=num, page=page)

    def get_download_history_by_title(self, title):
        """
        根据标题查询下载历史记录
        :return:
        """
        return self.dbhelper.get_download_history_by_title(title=title) or []

    def get_download_history_by_downloader(self, downloader, download_id):
        """
        根据下载器和下载ID查询下载历史记录
        :return:
        """
        return self.dbhelper.get_download_history_by_downloader(downloader=downloader,
                                                                download_id=download_id)

    def update_downloader(self,
                          did,
                          name,
                          enabled,
                          dtype,
                          transfer,
                          only_nastool,
                          match_path,
                          rmt_mode,
                          config,
                          download_dir):
        """
        更新下载器
        """
        ret = self.dbhelper.update_downloader(
            did=did,
            name=name,
            enabled=enabled,
            dtype=dtype,
            transfer=transfer,
            only_nastool=only_nastool,
            match_path=match_path,
            rmt_mode=rmt_mode,
            config=config,
            download_dir=download_dir
        )
        self.init_config()
        return ret

    def delete_downloader(self, did):
        """
        删除下载器
        """
        ret = self.dbhelper.delete_downloader(did=did)
        self.init_config()
        return ret

    def check_downloader(self, did=None, transfer=None, only_nastool=None, enabled=None, match_path=None):
        """
        检查下载器
        """
        ret = self.dbhelper.check_downloader(did=did,
                                             transfer=transfer,
                                             only_nastool=only_nastool,
                                             enabled=enabled,
                                             match_path=match_path)
        self.init_config()
        return ret

    def delete_download_setting(self, sid):
        """
        删除下载设置
        """
        ret = self.dbhelper.delete_download_setting(sid=sid)
        self.init_config()
        return ret

    def update_download_setting(self,
                                sid,
                                name,
                                category,
                                tags,
                                is_paused,
                                upload_limit,
                                download_limit,
                                ratio_limit,
                                seeding_time_limit,
                                downloader):
        """
        更新下载设置
        """
        ret = self.dbhelper.update_download_setting(
            sid=sid,
            name=name,
            category=category,
            tags=tags,
            is_paused=is_paused,
            upload_limit=upload_limit,
            download_limit=download_limit,
            ratio_limit=ratio_limit,
            seeding_time_limit=seeding_time_limit,
            downloader=downloader
        )
        self.init_config()
        return ret
