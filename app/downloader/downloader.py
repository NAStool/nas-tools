import os
from threading import Lock

import log
from app.conf import ModuleConf
from app.filetransfer import FileTransfer
from app.helper import DbHelper, ThreadHelper, SubmoduleHelper
from app.media import Media
from app.media.meta import MetaInfo
from app.mediaserver import MediaServer
from app.message import Message
from app.sites import Sites
from app.subtitle import Subtitle
from app.conf import SystemConfig
from app.utils import Torrent, StringUtils, SystemUtils, ExceptionUtils
from app.utils.commons import singleton
from app.utils.types import MediaType, DownloaderType, SearchType, RmtMode
from config import Config, PT_TAG, RMT_MEDIAEXT

lock = Lock()
client_lock = Lock()


@singleton
class Downloader:
    clients = {}
    _downloader_schema = []
    _default_client_type = None
    _pt_monitor_only = None
    _download_order = None
    _pt_rmt_mode = None
    _downloaddir = []
    _download_setting = {}

    message = None
    mediaserver = None
    filetransfer = None
    media = None
    sites = None
    dbhelper = None
    systemconfig = None

    def __init__(self):
        self._downloader_schema = SubmoduleHelper.import_submodules(
            'app.downloader.client',
            filter_func=lambda _, obj: hasattr(obj, 'schema')
        )
        log.debug(f"【Downloader】: 已经加载的下载器：{self._downloader_schema}")
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()
        self.message = Message()
        self.mediaserver = MediaServer()
        self.filetransfer = FileTransfer()
        self.media = Media()
        self.sites = Sites()
        self.systemconfig = SystemConfig()
        # 下载器配置
        pt = Config().get_config('pt')
        if pt:
            self._default_client_type = ModuleConf.DOWNLOADER_DICT.get(pt.get('pt_client')) or DownloaderType.QB
            self._pt_monitor_only = pt.get("pt_monitor_only")
            self._download_order = pt.get("download_order")
            self._pt_rmt_mode = ModuleConf.RMT_MODES.get(pt.get("rmt_mode", "copy"), RmtMode.COPY)
        # 下载目录配置
        self._downloaddir = Config().get_config('downloaddir') or []
        # 下载设置
        self._download_setting = {
            "-1": {
                "id": -1,
                "name": "预设",
                "category": '',
                "tags": PT_TAG,
                "content_layout": 0,
                "is_paused": 0,
                "upload_limit": 0,
                "download_limit": 0,
                "ratio_limit": 0,
                "seeding_time_limit": 0,
                "downloader": ""}
        }
        download_settings = self.dbhelper.get_download_setting()
        for download_setting in download_settings:
            self._download_setting[str(download_setting.ID)] = {
                "id": download_setting.ID,
                "name": download_setting.NAME,
                "category": download_setting.CATEGORY,
                "tags": download_setting.TAGS,
                "content_layout": download_setting.CONTENT_LAYOUT,
                "is_paused": download_setting.IS_PAUSED,
                "upload_limit": download_setting.UPLOAD_LIMIT,
                "download_limit": download_setting.DOWNLOAD_LIMIT,
                "ratio_limit": download_setting.RATIO_LIMIT / 100,
                "seeding_time_limit": download_setting.SEEDING_TIME_LIMIT,
                "downloader": download_setting.DOWNLOADER}

    def __build_class(self, ctype, conf=None):
        for downloader_schema in self._downloader_schema:
            try:
                if downloader_schema.match(ctype):
                    return downloader_schema(conf)
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
        return None

    @property
    def default_client(self):
        return self.__get_client(self._default_client_type)

    def __get_client(self, ctype: DownloaderType, conf: dict = None):
        if not ctype:
            return None
        with client_lock:
            if not self.clients.get(ctype.value):
                self.clients[ctype.value] = self.__build_class(ctype.value, conf)
            return self.clients.get(ctype.value)

    def download(self,
                 media_info,
                 is_paused=None,
                 tag=None,
                 download_dir=None,
                 download_setting=None,
                 torrent_file=None):
        """
        添加下载任务，根据当前使用的下载器分别调用不同的客户端处理
        :param media_info: 需下载的媒体信息，含URL地址
        :param is_paused: 是否暂停下载
        :param tag: 种子标签
        :param download_dir: 指定下载目录
        :param download_setting: 下载设置id
        :param torrent_file: 种子文件路径
        :return: 种子或状态，错误信息
        """
        # 标题
        title = media_info.org_string
        # 详情页面
        page_url = media_info.page_url
        # 默认值
        _xpath, _hash, site_info, dl_files_folder, dl_files, retmsg = None, False, {}, "", [], ""
        # 有种子文件时解析种子信息
        if torrent_file:
            url = os.path.basename(torrent_file)
            content, dl_files_folder, dl_files, retmsg = Torrent().read_torrent_content(torrent_file)
        # 没有种子文件解析链接
        else:
            url = media_info.enclosure
            if not url:
                return None, "下载链接为空"
            # 获取种子内容，磁力链不解析
            if url.startswith("magnet:"):
                content = url
            else:
                # [XPATH]为需从详情页面解析磁力链
                if url.startswith("["):
                    _xpath = url[1:-1]
                    url = page_url
                # #XPATH#为需从详情页面解析磁力Hash
                elif url.startswith("#"):
                    _xpath = url[1:-1]
                    _hash = True
                    url = page_url
                # 从详情页面XPATH解析下载链接
                if _xpath:
                    content = self.sites.parse_site_download_url(page_url=url,
                                                                 xpath=_xpath)
                    if not content:
                        return None, "无法从详情页面：%s 解析出下载链接" % url
                    # 解析出磁力链，补充Trackers
                    if content.startswith("magnet:"):
                        content = Torrent.add_trackers_to_magnet(url=content, title=title)
                    # 解析出来的是HASH值，转换为磁力链
                    elif _hash:
                        content = Torrent.convert_hash_to_magnet(hash_text=content, title=title)
                        if not content:
                            return None, "%s 转换磁力链失败" % content
                # 从HTTP链接下载种子
                else:
                    # 获取Cookie和ua等
                    site_info = self.sites.get_site_attr(url)
                    # 下载种子文件，并读取信息
                    _, content, dl_files_folder, dl_files, retmsg = Torrent().get_torrent_info(
                        url=url,
                        cookie=site_info.get("cookie"),
                        ua=site_info.get("ua"),
                        referer=page_url if site_info.get("referer") else None,
                        proxy=site_info.get("proxy")
                    )
        # 解析完成
        if retmsg:
            log.warn("【Downloader】%s" % retmsg)
        if not content:
            return None, retmsg

        # 下载设置
        if not download_setting and media_info.site:
            download_setting = self.sites.get_site_download_setting(media_info.site)
        if download_setting:
            download_attr = self.get_download_setting(download_setting) \
                            or self.get_download_setting(self.get_default_download_setting())
        else:
            download_attr = self.get_download_setting(self.get_default_download_setting())
        # 下载器类型
        dl_type = self.__get_client_type(download_attr.get("downloader")) or self._default_client_type
        # 下载器客户端
        downloader = self.__get_client(dl_type)

        # 开始添加下载
        try:
            # 分类
            category = download_attr.get("category")
            # 合并TAG
            tags = download_attr.get("tags")
            if tags:
                tags = tags.split(";")
                if tag:
                    tags.append(tag)
            else:
                if tag:
                    tags = [tag]
            # 布局
            content_layout = download_attr.get("content_layout")
            if content_layout == 1:
                content_layout = "Original"
            elif content_layout == 2:
                content_layout = "Subfolder"
            elif content_layout == 3:
                content_layout = "NoSubfolder"
            else:
                content_layout = ""
            # 暂停
            if is_paused is None:
                is_paused = StringUtils.to_bool(download_attr.get("is_paused"))
            else:
                is_paused = True if is_paused else False
            # 上传限速
            upload_limit = download_attr.get("upload_limit")
            # 下载限速
            download_limit = download_attr.get("download_limit")
            # 分享率
            ratio_limit = download_attr.get("ratio_limit")
            # 做种时间
            seeding_time_limit = download_attr.get("seeding_time_limit")
            # 下载目录
            if not download_dir:
                download_info = self.__get_download_dir_info(media_info)
                download_dir = download_info.get('path')
                download_label = download_info.get('label')
                if not category:
                    category = download_label
            # 添加下载
            print_url = content if isinstance(content, str) else url
            if is_paused:
                log.info("【Downloader】添加下载任务并暂停：%s，目录：%s，Url：%s" % (title, download_dir, print_url))
            else:
                log.info("【Downloader】添加下载任务：%s，目录：%s，Url：%s" % (title, download_dir, print_url))
            if dl_type == DownloaderType.TR:
                ret = downloader.add_torrent(content,
                                             is_paused=is_paused,
                                             download_dir=download_dir,
                                             cookie=site_info.get("cookie"))
                if ret:
                    downloader.change_torrent(tid=ret.id,
                                              tag=tags,
                                              upload_limit=upload_limit,
                                              download_limit=download_limit,
                                              ratio_limit=ratio_limit,
                                              seeding_time_limit=seeding_time_limit)
            elif dl_type == DownloaderType.QB:
                ret = downloader.add_torrent(content,
                                             is_paused=is_paused,
                                             download_dir=download_dir,
                                             tag=tags,
                                             category=category,
                                             content_layout=content_layout,
                                             upload_limit=upload_limit,
                                             download_limit=download_limit,
                                             ratio_limit=ratio_limit,
                                             seeding_time_limit=seeding_time_limit,
                                             cookie=site_info.get("cookie"))
            else:
                ret = downloader.add_torrent(content,
                                             is_paused=is_paused,
                                             tag=tags,
                                             download_dir=download_dir,
                                             category=category)
            # 添加下载成功
            if ret:
                # 登记下载历史
                self.dbhelper.insert_download_history(media_info)
                # 下载站点字幕文件
                if page_url \
                        and download_dir \
                        and dl_files \
                        and site_info \
                        and site_info.get("subtitle"):
                    # 下载访问目录
                    visit_dir = self.get_download_visit_dir(download_dir)
                    if visit_dir:
                        if dl_files_folder:
                            subtitle_dir = os.path.join(visit_dir, dl_files_folder)
                        else:
                            subtitle_dir = visit_dir
                        ThreadHelper().start_thread(
                            Subtitle().download_subtitle_from_site,
                            (media_info, site_info.get("cookie"), site_info.get("ua"), subtitle_dir)
                        )
                return ret, ""
            else:
                return ret, "请检查下载任务是否已存在"
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error("【Downloader】添加下载任务出错：%s" % str(e))
            return None, str(e)

    def transfer(self):
        """
        转移下载完成的文件，进行文件识别重命名到媒体库目录
        """
        if self.default_client:
            try:
                lock.acquire()
                if self._pt_monitor_only:
                    tag = [PT_TAG]
                else:
                    tag = None
                trans_tasks = self.default_client.get_transfer_task(tag=tag)
                if trans_tasks:
                    log.info("【Downloader】开始转移下载文件...")
                else:
                    return
                for task in trans_tasks:
                    done_flag, done_msg = self.filetransfer.transfer_media(in_from=self._default_client_type,
                                                                           in_path=task.get("path"),
                                                                           rmt_mode=self._pt_rmt_mode)
                    if not done_flag:
                        log.warn("【Downloader】%s 转移失败：%s" % (task.get("path"), done_msg))
                        self.default_client.set_torrents_status(ids=task.get("id"),
                                                                tags=task.get("tags"))
                    else:
                        if self._pt_rmt_mode in [RmtMode.MOVE, RmtMode.RCLONE, RmtMode.MINIO]:
                            log.warn("【Downloader】移动模式下删除种子文件：%s" % task.get("id"))
                            self.default_client.delete_torrents(delete_file=True, ids=task.get("id"))
                        else:
                            self.default_client.set_torrents_status(ids=task.get("id"),
                                                                    tags=task.get("tags"))
                log.info("【Downloader】下载文件转移结束")
            finally:
                lock.release()

    def get_remove_torrents(self, downloader=None, config=None):
        """
        查询符合删种策略的种子信息
        :return: 符合删种策略的种子信息列表
        """
        if not downloader or not config:
            return []
        _client = self.__get_client(downloader)
        if config.get("onlynastool"):
            config["filter_tags"] = config["tags"] + [PT_TAG]
        else:
            config["filter_tags"] = config["tags"]
        torrents = _client.get_remove_torrents(config=config)
        torrents.sort(key=lambda x: x.get("name"))
        return torrents

    def get_downloading_torrents(self):
        """
        查询正在下载中的种子信息
        :return: 客户端类型，下载中的种子信息列表
        """
        if not self.default_client:
            return self._default_client_type, []
        if self._pt_monitor_only:
            tag = [PT_TAG]
        else:
            tag = None
        try:
            return self._default_client_type, self.default_client.get_downloading_torrents(tag=tag)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return self._default_client_type, []

    def get_downloading_progress(self):
        """
        查询正在下载中的进度信息
        """
        if not self.default_client:
            return []
        return self.default_client.get_downloading_progress()

    def get_torrents(self, torrent_ids):
        """
        根据ID或状态查询下载器中的种子信息
        :param torrent_ids: 种子ID列表
        :return: 客户端类型，种子信息列表, 是否发生异常
        """
        if not self.default_client:
            return None, [], True
        torrent_list, _ = self.default_client.get_torrents(ids=torrent_ids)
        return self._default_client_type, torrent_list

    def start_torrents(self, downloader=None, ids=None):
        """
        下载控制：开始
        :param downloader: 下载器类型
        :param ids: 种子ID列表
        :return: 处理状态
        """
        if not ids:
            return False
        if not downloader:
            if not self.default_client:
                return False
            return self.default_client.start_torrents(ids)
        else:
            _client = self.__get_client(downloader)
            return _client.start_torrents(ids)

    def stop_torrents(self, downloader=None, ids=None):
        """
        下载控制：停止
        :param downloader: 下载器类型
        :param ids: 种子ID列表
        :return: 处理状态
        """
        if not ids:
            return False
        if not downloader:
            if not self.default_client:
                return False
            return self.default_client.stop_torrents(ids)
        else:
            _client = self.__get_client(downloader)
            return _client.stop_torrents(ids)

    def delete_torrents(self, downloader=None, ids=None, delete_file=False):
        """
        删除种子
        :param downloader: 下载器类型
        :param ids: 种子ID列表
        :param delete_file: 是否删除文件
        :return: 处理状态
        """
        if not ids:
            return False
        if not downloader:
            if not self.default_client:
                return False
            return self.default_client.delete_torrents(delete_file=delete_file, ids=ids)
        else:
            _client = self.__get_client(downloader)
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
        download_list = self.get_download_list(media_list)

        def __download(download_item, torrent_file=None, tag=None, is_paused=None):
            """
            下载及发送通知
            """
            download_item.user_name = user_name
            state, msg = self.download(
                media_info=download_item,
                download_dir=download_item.save_path,
                download_setting=download_item.download_setting,
                torrent_file=torrent_file,
                tag=tag,
                is_paused=is_paused)
            if state:
                if download_item not in return_items:
                    return_items.append(download_item)
                self.message.send_download_message(in_from, download_item)
            else:
                self.message.send_download_fail_message(download_item, msg)
            return state

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
                                    download_state = __download(download_item=item, torrent_file=torrent_path)
                                else:
                                    log.info(
                                        f"【Downloader】种子 {item.org_string} 未含集数信息，解析文件数为 {len(torrent_episodes)}")
                                    continue
                            else:
                                download_state = __download(item)
                            if download_state:
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
                            item_season = item.get_season_list()
                            if len(item_season) != 1 or item_season[0] != need_season:
                                continue
                            item_episodes = item.get_episode_list()
                            if not item_episodes:
                                continue
                            # 只处理单季含集的种子，从集最多的开始下
                            if set(item_episodes).issubset(set(need_episodes)):
                                if __download(item):
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
                                     or set(item.get_episode_list()).issuperset(set(need_episodes))) \
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
                            torrent_tag = "NT" + StringUtils.generate_random_str(5)
                            ret = __download(download_item=item,
                                             torrent_file=torrent_path,
                                             tag=torrent_tag,
                                             is_paused=True)
                            if not ret:
                                continue
                            # 更新仍需集数
                            need_episodes = __update_episodes(tmdbid=need_tmdbid,
                                                              need=need_episodes,
                                                              seq=index,
                                                              current=selected_episodes)
                            # 获取下载器
                            downloader = self._default_client_type
                            if item.download_setting:
                                download_attr = self.get_download_setting(item.download_setting)
                                if download_attr.get("downloader"):
                                    downloader = self.__get_client_type(download_attr.get("downloader"))
                            _client = self.__get_client(downloader)
                            # 获取刚添加的任务ID
                            if downloader == DownloaderType.TR:
                                torrent_id = ret.id
                            elif downloader == DownloaderType.QB:
                                torrent_id = _client.get_torrent_id_by_tag(tag=torrent_tag, status=["paused"])
                            else:
                                continue
                            if not torrent_id:
                                log.error("【Downloader】获取下载器添加的任务信息出错：%s，tag=%s" % (
                                    item.org_string, torrent_tag))
                                continue
                            # 设置任务只下载想要的文件
                            log.info("【Downloader】从 %s 中选取集：%s" % (item.org_string, selected_episodes))
                            self.set_files_status(torrent_id, selected_episodes, downloader)
                            # 重新开始任务
                            log.info("【Downloader】%s 开始下载 " % item.org_string)
                            _client.start_torrents(torrent_id)
                            # 记录下载项
                            return_items.append(item)
                index += 1

        # 返回下载的资源，剩下没下完的
        return return_items, need_tvs

    def check_exists_medias(self, meta_info, no_exists=None, total_ep=None):
        """
        检查媒体库，查询是否存在，对于剧集同时返回不存在的季集信息
        :param meta_info: 已识别的媒体信息，包括标题、年份、季、集信息
        :param no_exists: 在调用该方法前已经存储的不存在的季集信息，有传入时该函数检索的内容将会叠加后输出
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
            # 检索电视剧的信息
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

    def set_files_status(self, tid, need_episodes, downloader):
        """
        设置文件下载状态，选中需要下载的季集对应的文件下载，其余不下载
        :param tid: 种子的hash或id
        :param need_episodes: 需要下载的文件的集信息
        :param downloader: 下载器
        :return: 返回选中的集的列表
        """
        sucess_epidised = []
        _client = self.__get_client(downloader)
        if downloader == DownloaderType.TR:
            files_info = {}
            torrent_files = _client.get_files(tid)
            if not torrent_files:
                return []
            for file_id, torrent_file in enumerate(torrent_files):
                meta_info = MetaInfo(torrent_file.name)
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
        elif downloader == DownloaderType.QB:
            file_ids = []
            torrent_files = _client.get_files(tid)
            if not torrent_files:
                return []
            for torrent_file in torrent_files:
                meta_info = MetaInfo(torrent_file.get("name"))
                if not meta_info.get_episode_list() or not set(meta_info.get_episode_list()).issubset(
                        set(need_episodes)):
                    file_ids.append(torrent_file.get("index"))
                else:
                    sucess_epidised = list(set(sucess_epidised).union(set(meta_info.get_episode_list())))
            if sucess_epidised and file_ids:
                _client.set_files(torrent_hash=tid, file_ids=file_ids, priority=0)
        return sucess_epidised

    def get_download_list(self, media_list):
        """
        对媒体信息进行排序、去重
        """
        if not media_list:
            return []

        # 排序函数，标题、站点、资源类型、做种数量
        def get_sort_str(x):
            season_len = str(len(x.get_season_list())).rjust(2, '0')
            episode_len = str(len(x.get_episode_list())).rjust(4, '0')
            # 排序：标题、资源类型、站点、做种、季集
            if self._download_order == "seeder":
                return "%s%s%s%s%s" % (str(x.title).ljust(100, ' '),
                                       str(x.res_order).rjust(3, '0'),
                                       str(x.seeders).rjust(10, '0'),
                                       str(x.site_order).rjust(3, '0'),
                                       "%s%s" % (season_len, episode_len))
            else:
                return "%s%s%s%s%s" % (str(x.title).ljust(100, ' '),
                                       str(x.res_order).rjust(3, '0'),
                                       str(x.site_order).rjust(3, '0'),
                                       str(x.seeders).rjust(10, '0'),
                                       "%s%s" % (season_len, episode_len))

        # 匹配的资源中排序分组选最好的一个下载
        # 按站点顺序、资源匹配顺序、做种人数下载数逆序排序
        media_list = sorted(media_list, key=lambda x: get_sort_str(x), reverse=True)
        # 控重
        can_download_list_item = []
        can_download_list = []
        # 排序后重新加入数组，按真实名称控重，即只取每个名称的第一个
        for t_item in media_list:
            # 控重的主链是名称、年份、季、集
            if t_item.type != MediaType.MOVIE:
                media_name = "%s%s" % (t_item.get_title_string(),
                                       t_item.get_season_episode_string())
            else:
                media_name = t_item.get_title_string()
            if media_name not in can_download_list:
                can_download_list.append(media_name)
                can_download_list_item.append(t_item)
        return can_download_list_item

    def get_download_dirs(self, setting=None):
        """
        返回下载器中设置的保存目录
        """
        if not self._downloaddir:
            return []
        if not setting:
            setting = self.get_default_download_setting()
        # 查询下载设置
        download_setting = self.get_download_setting(sid=setting)
        # 下载设置为QB
        if download_setting \
                and download_setting.get('downloader') == "Qbittorrent" \
                and Config().get_config("qbittorrent").get("auto_management"):
            return []
        # 默认下载器为QB
        if download_setting \
                and not download_setting.get('downloader') \
                and Config().get_config("pt").get("pt_client") == "qbittorrent" \
                and Config().get_config("qbittorrent").get("auto_management"):
            return []
        # 查询目录
        save_path_list = [attr.get("save_path") for attr in self._downloaddir if attr.get("save_path")]
        save_path_list.sort()
        return list(set(save_path_list))

    def get_download_visit_dirs(self):
        """
        返回下载器中设置的访问目录
        """
        if not self._downloaddir:
            return []
        visit_path_list = [attr.get("container_path") or attr.get("save_path") for attr in self._downloaddir if
                           attr.get("save_path")]
        visit_path_list.sort()
        return list(set(visit_path_list))

    def get_download_visit_dir(self, download_dir):
        """
        返回下载器中设置的访问目录
        """
        if not self.default_client:
            return ""
        return self.default_client.get_replace_path(download_dir)

    def __get_download_dir_info(self, media):
        """
        根据媒体信息读取一个下载目录的信息
        """
        if media and media.tmdb_info:
            for attr in self._downloaddir or []:
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
                        and float(SystemUtils.get_free_space_gb(attr.get("container_path") or attr.get("save_path"))) \
                        < float(int(StringUtils.num_filesize(media.size)) / 1024 / 1024 / 1024):
                    continue
                return {"path": attr.get("save_path"), "label": attr.get("label")}
        return {"path": None, "label": None}

    def get_default_client_type(self):
        """
        返回下载器类型
        """
        return self._default_client_type

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
        site_info = self.sites.get_site_attr(url)
        if not site_info.get("cookie"):
            return [], None
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
        if sid:
            return self._download_setting.get(str(sid))
        else:
            return self._download_setting

    def get_default_download_setting(self):
        """
        获取默认下载设置
        :return: 默认下载设置id
        """
        default_download_setting = SystemConfig().get_system_config("DefaultDownloadSetting") or "-1"
        if not self._download_setting.get(default_download_setting):
            default_download_setting = "-1"
        return default_download_setting
