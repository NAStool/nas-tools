import base64
import datetime
import importlib
import json
import os.path
import re
import shutil
import signal
from math import floor
from urllib.parse import unquote

import cn2an
from flask_login import logout_user, current_user
from werkzeug.security import generate_password_hash

import log
from app.brushtask import BrushTask
from app.conf import SystemConfig, ModuleConf
from app.doubansync import DoubanSync
from app.downloader import Downloader
from app.downloader.client import Qbittorrent, Transmission
from app.filetransfer import FileTransfer
from app.filter import Filter
from app.helper import DbHelper, ProgressHelper, ThreadHelper, \
    MetaHelper, DisplayHelper, WordsHelper, CookieCloudHelper
from app.indexer import Indexer
from app.media import Category, Media, Bangumi, DouBan
from app.media.meta import MetaInfo, MetaBase
from app.mediaserver import MediaServer
from app.message import Message, MessageCenter
from app.rss import Rss
from app.rsschecker import RssChecker
from app.scheduler import stop_scheduler
from app.sites import Sites
from app.sites.sitecookie import SiteCookie
from app.subscribe import Subscribe
from app.subtitle import Subtitle
from app.sync import Sync, stop_monitor
from app.torrentremover import TorrentRemover
from app.utils import StringUtils, EpisodeFormat, RequestUtils, PathUtils, \
    SystemUtils, ExceptionUtils, Torrent
from app.utils.types import RmtMode, OsType, SearchType, DownloaderType, SyncType, MediaType
from config import RMT_MEDIAEXT, TMDB_IMAGE_W500_URL, RMT_SUBEXT, Config
from web.backend.search_torrents import search_medias_for_web, search_media_by_message
from web.backend.web_utils import WebUtils


class WebAction:
    dbhelper = None
    _actions = {}
    _MovieTypes = ['MOV', '电影']

    def __init__(self):
        self.dbhelper = DbHelper()
        self._actions = {
            "sch": self.__sch,
            "search": self.__search,
            "download": self.__download,
            "download_link": self.__download_link,
            "download_torrent": self.__download_torrent,
            "pt_start": self.__pt_start,
            "pt_stop": self.__pt_stop,
            "pt_remove": self.__pt_remove,
            "pt_info": self.__pt_info,
            "del_unknown_path": self.__del_unknown_path,
            "rename": self.__rename,
            "rename_udf": self.__rename_udf,
            "delete_history": self.__delete_history,
            "logging": self.__logging,
            "version": self.__version,
            "update_site": self.__update_site,
            "get_site": self.__get_site,
            "del_site": self.__del_site,
            "get_site_favicon": self.__get_site_favicon,
            "restart": self.__restart,
            "update_system": self.__update_system,
            "reset_db_version": self.__reset_db_version,
            "logout": self.__logout,
            "update_config": self.__update_config,
            "update_directory": self.__update_directory,
            "add_or_edit_sync_path": self.__add_or_edit_sync_path,
            "get_sync_path": self.__get_sync_path,
            "delete_sync_path": self.__delete_sync_path,
            "check_sync_path": self.__check_sync_path,
            "remove_rss_media": self.__remove_rss_media,
            "add_rss_media": self.__add_rss_media,
            "re_identification": self.__re_identification,
            "media_info": self.__media_info,
            "test_connection": self.__test_connection,
            "user_manager": self.__user_manager,
            "refresh_rss": self.__refresh_rss,
            "refresh_message": self.__refresh_message,
            "delete_tmdb_cache": self.__delete_tmdb_cache,
            "movie_calendar_data": self.__movie_calendar_data,
            "tv_calendar_data": self.__tv_calendar_data,
            "modify_tmdb_cache": self.__modify_tmdb_cache,
            "rss_detail": self.__rss_detail,
            "truncate_blacklist": self.__truncate_blacklist,
            "truncate_rsshistory": self.__truncate_rsshistory,
            "add_brushtask": self.__add_brushtask,
            "del_brushtask": self.__del_brushtask,
            "brushtask_detail": self.__brushtask_detail,
            "add_downloader": self.__add_downloader,
            "delete_downloader": self.__delete_downloader,
            "get_downloader": self.__get_downloader,
            "name_test": self.__name_test,
            "rule_test": self.__rule_test,
            "net_test": self.__net_test,
            "add_filtergroup": self.__add_filtergroup,
            "restore_filtergroup": self.__restore_filtergroup,
            "set_default_filtergroup": self.__set_default_filtergroup,
            "del_filtergroup": self.__del_filtergroup,
            "add_filterrule": self.__add_filterrule,
            "del_filterrule": self.__del_filterrule,
            "filterrule_detail": self.__filterrule_detail,
            "get_site_activity": self.__get_site_activity,
            "get_site_history": self.__get_site_history,
            "get_recommend": self.get_recommend,
            "get_downloaded": self.get_downloaded,
            "get_site_seeding_info": self.__get_site_seeding_info,
            "clear_tmdb_cache": self.__clear_tmdb_cache,
            "check_site_attr": self.__check_site_attr,
            "refresh_process": self.__refresh_process,
            "restory_backup": self.__restory_backup,
            "start_mediasync": self.__start_mediasync,
            "mediasync_state": self.__mediasync_state,
            "get_tvseason_list": self.__get_tvseason_list,
            "get_userrss_task": self.__get_userrss_task,
            "delete_userrss_task": self.__delete_userrss_task,
            "update_userrss_task": self.__update_userrss_task,
            "get_rssparser": self.__get_rssparser,
            "delete_rssparser": self.__delete_rssparser,
            "update_rssparser": self.__update_rssparser,
            "run_userrss": self.__run_userrss,
            "run_brushtask": self.__run_brushtask,
            "list_site_resources": self.__list_site_resources,
            "list_rss_articles": self.__list_rss_articles,
            "rss_article_test": self.__rss_article_test,
            "list_rss_history": self.__list_rss_history,
            "rss_articles_check": self.__rss_articles_check,
            "rss_articles_download": self.__rss_articles_download,
            "add_custom_word_group": self.__add_custom_word_group,
            "delete_custom_word_group": self.__delete_custom_word_group,
            "add_or_edit_custom_word": self.__add_or_edit_custom_word,
            "get_custom_word": self.__get_custom_word,
            "delete_custom_word": self.__delete_custom_word,
            "check_custom_words": self.__check_custom_words,
            "export_custom_words": self.__export_custom_words,
            "analyse_import_custom_words_code": self.__analyse_import_custom_words_code,
            "import_custom_words": self.__import_custom_words,
            "get_categories": self.__get_categories,
            "re_rss_history": self.__re_rss_history,
            "delete_rss_history": self.__delete_rss_history,
            "share_filtergroup": self.__share_filtergroup,
            "import_filtergroup": self.__import_filtergroup,
            "get_transfer_statistics": self.get_transfer_statistics,
            "get_library_spacesize": self.get_library_spacesize,
            "get_library_mediacount": self.get_library_mediacount,
            "get_library_playhistory": self.get_library_playhistory,
            "get_search_result": self.get_search_result,
            "search_media_infos": self.search_media_infos,
            "get_movie_rss_list": self.get_movie_rss_list,
            "get_tv_rss_list": self.get_tv_rss_list,
            "get_rss_history": self.get_rss_history,
            "get_transfer_history": self.get_transfer_history,
            "get_unknown_list": self.get_unknown_list,
            "get_customwords": self.get_customwords,
            "get_directorysync": self.get_directorysync,
            "get_users": self.get_users,
            "get_filterrules": self.get_filterrules,
            "get_downloading": self.get_downloading,
            "test_site": self.__test_site,
            "get_sub_path": self.__get_sub_path,
            "rename_file": self.__rename_file,
            "delete_files": self.__delete_files,
            "download_subtitle": self.__download_subtitle,
            "get_download_setting": self.__get_download_setting,
            "update_download_setting": self.__update_download_setting,
            "delete_download_setting": self.__delete_download_setting,
            "update_message_client": self.__update_message_client,
            "delete_message_client": self.__delete_message_client,
            "check_message_client": self.__check_message_client,
            "get_message_client": self.__get_message_client,
            "test_message_client": self.__test_message_client,
            "get_sites": self.__get_sites,
            "get_indexers": self.__get_indexers,
            "get_download_dirs": self.__get_download_dirs,
            "find_hardlinks": self.__find_hardlinks,
            "update_sites_cookie_ua": self.__update_sites_cookie_ua,
            "set_site_captcha_code": self.__set_site_captcha_code,
            "update_torrent_remove_task": self.__update_torrent_remove_task,
            "get_torrent_remove_task": self.__get_torrent_remove_task,
            "delete_torrent_remove_task": self.__delete_torrent_remove_task,
            "get_remove_torrents": self.__get_remove_torrents,
            "auto_remove_torrents": self.__auto_remove_torrents,
            "get_douban_history": self.get_douban_history,
            "delete_douban_history": self.__delete_douban_history,
            "list_brushtask_torrents": self.__list_brushtask_torrents,
            "set_system_config": self.__set_system_config,
            "get_site_user_statistics": self.get_site_user_statistics,
            "send_custom_message": self.send_custom_message,
            "cookiecloud_sync": self.__cookiecloud_sync,
            "media_detail": self.media_detail,
            "media_similar": self.__media_similar,
            "media_recommendations": self.__media_recommendations,
            "media_person": self.__media_person,
            "person_medias": self.__person_medias
        }

    def action(self, cmd, data=None):
        func = self._actions.get(cmd)
        if not func:
            return {"code": -1, "msg": "非授权访问！"}
        else:
            return func(data)

    def api_action(self, cmd, data=None):
        result = self.action(cmd, data)
        if not result:
            return {
                "code": -1,
                "success": False,
                "message": "服务异常，未获取到返回结果"
            }
        code = result.get("code", result.get("retcode", 0))
        if not code or str(code) == "0":
            success = True
        else:
            success = False
        message = result.get("msg", result.get("retmsg", ""))
        for key in ['code', 'retcode', 'msg', 'retmsg']:
            if key in result:
                result.pop(key)
        return {
            "code": code,
            "success": success,
            "message": message,
            "data": result
        }

    @staticmethod
    def restart_server():
        """
        停止进程
        """
        # 停止定时服务
        stop_scheduler()
        # 停止监控
        stop_monitor()
        # 签退
        logout_user()
        # 关闭虚拟显示
        DisplayHelper().quit()
        # 重启进程
        if os.name == "nt":
            os.kill(os.getpid(), getattr(signal, "SIGKILL", signal.SIGTERM))
        elif SystemUtils.is_synology():
            os.system("ps -ef | grep -v grep | grep 'python run.py'|awk '{print $2}'|xargs kill -9")
        else:
            os.system("pm2 restart NAStool")

    @staticmethod
    def handle_message_job(msg, in_from=SearchType.OT, user_id=None, user_name=None):
        """
        处理消息事件
        """
        if not msg:
            return
        commands = {
            "/ptr": {"func": TorrentRemover().auto_remove_torrents, "desp": "删种"},
            "/ptt": {"func": Downloader().transfer, "desp": "下载文件转移"},
            "/pts": {"func": Sites().signin, "desp": "站点签到"},
            "/rst": {"func": Sync().transfer_all_sync, "desp": "目录同步"},
            "/rss": {"func": Rss().rssdownload, "desp": "RSS订阅"},
            "/db": {"func": DoubanSync().sync, "desp": "豆瓣同步"},
            "/udt": {"func": WebAction().__update_system, "desp": "系统更新"}
        }
        command = commands.get(msg)
        message = Message()

        if command:
            # 启动服务
            ThreadHelper().start_thread(command.get("func"), ())
            message.send_channel_msg(channel=in_from, title="正在运行 %s ..." % command.get("desp"), user_id=user_id)
        else:
            # 站点检索或者添加订阅
            ThreadHelper().start_thread(search_media_by_message, (msg, in_from, user_id, user_name))

    @staticmethod
    def set_config_value(cfg, cfg_key, cfg_value):
        """
        根据Key设置配置值
        """
        # 密码
        if cfg_key == "app.login_password":
            if cfg_value and not cfg_value.startswith("[hash]"):
                cfg['app']['login_password'] = "[hash]%s" % generate_password_hash(cfg_value)
            else:
                cfg['app']['login_password'] = cfg_value or "password"
            return cfg
        # 代理
        if cfg_key == "app.proxies":
            if cfg_value:
                if not cfg_value.startswith("http") and not cfg_value.startswith("sock"):
                    cfg['app']['proxies'] = {"https": "http://%s" % cfg_value, "http": "http://%s" % cfg_value}
                else:
                    cfg['app']['proxies'] = {"https": "%s" % cfg_value, "http": "%s" % cfg_value}
            else:
                cfg['app']['proxies'] = {"https": None, "http": None}
            return cfg
        # 豆瓣用户列表
        if cfg_key == "douban.users":
            vals = cfg_value.split(",")
            cfg['douban']['users'] = vals
            return cfg
        # 索引器
        if cfg_key == "jackett.indexers":
            vals = cfg_value.split("\n")
            cfg['jackett']['indexers'] = vals
            return cfg
        # 最大支持三层赋值
        keys = cfg_key.split(".")
        if keys:
            if len(keys) == 1:
                cfg[keys[0]] = cfg_value
            elif len(keys) == 2:
                if not cfg.get(keys[0]):
                    cfg[keys[0]] = {}
                cfg[keys[0]][keys[1]] = cfg_value
            elif len(keys) == 3:
                if cfg.get(keys[0]):
                    if not cfg[keys[0]].get(keys[1]) or isinstance(cfg[keys[0]][keys[1]], str):
                        cfg[keys[0]][keys[1]] = {}
                    cfg[keys[0]][keys[1]][keys[2]] = cfg_value
                else:
                    cfg[keys[0]] = {}
                    cfg[keys[0]][keys[1]] = {}
                    cfg[keys[0]][keys[1]][keys[2]] = cfg_value

        return cfg

    @staticmethod
    def set_config_directory(cfg, oper, cfg_key, cfg_value, update_value=None):
        """
        更新目录数据
        """

        def remove_sync_path(obj, key):
            if not isinstance(obj, list):
                return []
            ret_obj = []
            for item in obj:
                if item.split("@")[0].replace("\\", "/") != key.split("@")[0].replace("\\", "/"):
                    ret_obj.append(item)
            return ret_obj

        # 最大支持二层赋值
        keys = cfg_key.split(".")
        if keys:
            if len(keys) == 1:
                if cfg.get(keys[0]):
                    if not isinstance(cfg[keys[0]], list):
                        cfg[keys[0]] = [cfg[keys[0]]]
                    if oper == "add":
                        cfg[keys[0]].append(cfg_value)
                    elif oper == "sub":
                        cfg[keys[0]].remove(cfg_value)
                        if not cfg[keys[0]]:
                            cfg[keys[0]] = None
                    elif oper == "set":
                        cfg[keys[0]].remove(cfg_value)
                        if update_value:
                            cfg[keys[0]].append(update_value)
                else:
                    cfg[keys[0]] = cfg_value
            elif len(keys) == 2:
                if cfg.get(keys[0]):
                    if not cfg[keys[0]].get(keys[1]):
                        cfg[keys[0]][keys[1]] = []
                    if not isinstance(cfg[keys[0]][keys[1]], list):
                        cfg[keys[0]][keys[1]] = [cfg[keys[0]][keys[1]]]
                    if oper == "add":
                        cfg[keys[0]][keys[1]].append(cfg_value.replace("\\", "/"))
                    elif oper == "sub":
                        cfg[keys[0]][keys[1]] = remove_sync_path(cfg[keys[0]][keys[1]], cfg_value)
                        if not cfg[keys[0]][keys[1]]:
                            cfg[keys[0]][keys[1]] = None
                    elif oper == "set":
                        cfg[keys[0]][keys[1]] = remove_sync_path(cfg[keys[0]][keys[1]], cfg_value)
                        if update_value:
                            cfg[keys[0]][keys[1]].append(update_value.replace("\\", "/"))
                else:
                    cfg[keys[0]] = {}
                    cfg[keys[0]][keys[1]] = cfg_value.replace("\\", "/")
        return cfg

    @staticmethod
    def __sch(data):
        """
        启动定时服务
        """
        commands = {
            "autoremovetorrents": TorrentRemover().auto_remove_torrents,
            "pttransfer": Downloader().transfer,
            "ptsignin": Sites().signin,
            "sync": Sync().transfer_all_sync,
            "rssdownload": Rss().rssdownload,
            "douban": DoubanSync().sync,
            "subscribe_search_all": Subscribe().subscribe_search_all,
        }
        sch_item = data.get("item")
        if sch_item and commands.get(sch_item):
            ThreadHelper().start_thread(commands.get(sch_item), ())
        return {"retmsg": "服务已启动", "item": sch_item}

    def __search(self, data):
        """
        WEB检索资源
        """
        search_word = data.get("search_word")
        ident_flag = False if data.get("unident") else True
        filters = data.get("filters")
        tmdbid = data.get("tmdbid")
        media_type = data.get("media_type")
        if media_type:
            if media_type in self._MovieTypes:
                media_type = MediaType.MOVIE
            else:
                media_type = MediaType.TV
        if search_word:
            ret, ret_msg = search_medias_for_web(content=search_word,
                                                 ident_flag=ident_flag,
                                                 filters=filters,
                                                 tmdbid=tmdbid,
                                                 media_type=media_type)
            if ret != 0:
                return {"code": ret, "msg": ret_msg}
        return {"code": 0}

    def __download(self, data):
        """
        从WEB添加下载
        """
        dl_id = data.get("id")
        dl_dir = data.get("dir")
        dl_setting = data.get("setting")
        results = self.dbhelper.get_search_result_by_id(dl_id)
        for res in results:
            media = Media().get_media_info(title=res.TORRENT_NAME, subtitle=res.DESCRIPTION)
            if not media:
                continue
            media.set_torrent_info(enclosure=res.ENCLOSURE,
                                   size=res.SIZE,
                                   site=res.SITE,
                                   page_url=res.PAGEURL,
                                   upload_volume_factor=float(res.UPLOAD_VOLUME_FACTOR),
                                   download_volume_factor=float(res.DOWNLOAD_VOLUME_FACTOR))
            # 添加下载
            ret, ret_msg = Downloader().download(media_info=media,
                                                 download_dir=dl_dir,
                                                 download_setting=dl_setting)
            if ret:
                # 发送消息
                media.user_name = current_user.username
                Message().send_download_message(in_from=SearchType.WEB,
                                                can_item=media)
            else:
                return {"retcode": -1, "retmsg": ret_msg}
        return {"retcode": 0, "retmsg": ""}

    @staticmethod
    def __download_link(data):
        """
        从WEB添加下载链接
        """
        site = data.get("site")
        enclosure = data.get("enclosure")
        title = data.get("title")
        description = data.get("description")
        page_url = data.get("page_url")
        size = data.get("size")
        seeders = data.get("seeders")
        uploadvolumefactor = data.get("uploadvolumefactor")
        downloadvolumefactor = data.get("downloadvolumefactor")
        dl_dir = data.get("dl_dir")
        dl_setting = data.get("dl_setting")
        if not title or not enclosure:
            return {"code": -1, "msg": "种子信息有误"}
        media = Media().get_media_info(title=title, subtitle=description)
        media.site = site
        media.enclosure = enclosure
        media.page_url = page_url
        media.size = size
        media.upload_volume_factor = float(uploadvolumefactor)
        media.download_volume_factor = float(downloadvolumefactor)
        media.seeders = seeders
        # 添加下载
        ret, ret_msg = Downloader().download(media_info=media,
                                             download_dir=dl_dir,
                                             download_setting=dl_setting)
        if ret:
            # 发送消息
            media.user_name = current_user.username
            Message().send_download_message(SearchType.WEB, media)
            return {"code": 0, "msg": "下载成功"}
        else:
            return {"code": 1, "msg": ret_msg or "如连接正常，请检查下载任务是否存在"}

    @staticmethod
    def __download_torrent(data):
        """
        从种子文件添加下载
        """

        def __download(_media_info, _file_path):
            _media_info.site = "WEB"
            # 添加下载
            ret, ret_msg = Downloader().download(media_info=_media_info,
                                                 download_dir=dl_dir,
                                                 download_setting=dl_setting,
                                                 torrent_file=_file_path)
            # 发送消息
            _media_info.user_name = current_user.username
            if ret:
                Message().send_download_message(SearchType.WEB, _media_info)
            else:
                Message().send_download_fail_message(_media_info, ret_msg)

        dl_dir = data.get("dl_dir")
        dl_setting = data.get("dl_setting")
        files = data.get("files")
        magnets = data.get("magnets")
        if not files and not magnets:
            return {"code": -1, "msg": "没有种子文件或磁链"}
        for file_item in files:
            if not file_item:
                continue
            file_name = file_item.get("upload", {}).get("filename")
            file_path = os.path.join(Config().get_temp_path(), file_name)
            media_info = Media().get_media_info(title=file_name)
            __download(media_info, file_path)
        for magnet in magnets:
            if not magnet:
                continue
            file_path = None
            title = Torrent().get_magnet_title(magnet)
            if title:
                media_info = Media().get_media_info(title=title)
            else:
                media_info = MetaInfo(title="磁力链接")
                media_info.org_string = magnet
            media_info.set_torrent_info(enclosure=magnet,
                                        download_volume_factor=0,
                                        upload_volume_factor=1)
            __download(media_info, file_path)
        return {"code": 0, "msg": "添加下载完成！"}

    @staticmethod
    def __pt_start(data):
        """
        开始下载
        """
        tid = data.get("id")
        if id:
            Downloader().start_torrents(ids=tid)
        return {"retcode": 0, "id": tid}

    @staticmethod
    def __pt_stop(data):
        """
        停止下载
        """
        tid = data.get("id")
        if id:
            Downloader().stop_torrents(ids=tid)
        return {"retcode": 0, "id": tid}

    @staticmethod
    def __pt_remove(data):
        """
        删除下载
        """
        tid = data.get("id")
        if id:
            Downloader().delete_torrents(ids=tid, delete_file=True)
        return {"retcode": 0, "id": tid}

    @staticmethod
    def __pt_info(data):
        """
        查询具体种子的信息
        """
        ids = data.get("ids")
        Client, Torrents = Downloader().get_torrents(torrent_ids=ids)
        DispTorrents = []
        for torrent in Torrents:
            if not torrent:
                continue
            if Client == DownloaderType.QB:
                if torrent.get('state') in ['pausedDL']:
                    state = "Stoped"
                    speed = "已暂停"
                else:
                    state = "Downloading"
                    dlspeed = StringUtils.str_filesize(torrent.get('dlspeed'))
                    eta = StringUtils.str_timelong(torrent.get('eta'))
                    upspeed = StringUtils.str_filesize(torrent.get('upspeed'))
                    speed = "%s%sB/s %s%sB/s %s" % (chr(8595), dlspeed, chr(8593), upspeed, eta)
                # 进度
                progress = round(torrent.get('progress') * 100)
                # 主键
                key = torrent.get('hash')
            elif Client == DownloaderType.Client115:
                state = "Downloading"
                dlspeed = StringUtils.str_filesize(torrent.get('peers'))
                upspeed = StringUtils.str_filesize(torrent.get('rateDownload'))
                speed = "%s%sB/s %s%sB/s" % (chr(8595), dlspeed, chr(8593), upspeed)
                # 进度
                progress = round(torrent.get('percentDone'), 1)
                # 主键
                key = torrent.get('info_hash')
            elif Client == DownloaderType.Aria2:
                if torrent.get('status') != 'active':
                    state = "Stoped"
                    speed = "已暂停"
                else:
                    state = "Downloading"
                    dlspeed = StringUtils.str_filesize(torrent.get('downloadSpeed'))
                    upspeed = StringUtils.str_filesize(torrent.get('uploadSpeed'))
                    speed = "%s%sB/s %s%sB/s" % (chr(8595), dlspeed, chr(8593), upspeed)
                # 进度
                progress = round(int(torrent.get('completedLength')) / int(torrent.get("totalLength")), 1) * 100
                # 主键
                key = torrent.get('gid')
            else:
                if torrent.status in ['stopped']:
                    state = "Stoped"
                    speed = "已暂停"
                else:
                    state = "Downloading"
                    dlspeed = StringUtils.str_filesize(torrent.rateDownload)
                    upspeed = StringUtils.str_filesize(torrent.rateUpload)
                    speed = "%s%sB/s %s%sB/s" % (chr(8595), dlspeed, chr(8593), upspeed)
                # 进度
                progress = round(torrent.progress, 1)
                # 主键
                key = torrent.id

            torrent_info = {'id': key, 'speed': speed, 'state': state, 'progress': progress}
            if torrent_info not in DispTorrents:
                DispTorrents.append(torrent_info)
        return {"retcode": 0, "torrents": DispTorrents}

    def __del_unknown_path(self, data):
        """
        删除路径
        """
        tids = data.get("id")
        if isinstance(tids, list):
            for tid in tids:
                if not tid:
                    continue
                self.dbhelper.delete_transfer_unknown(tid)
            return {"retcode": 0}
        else:
            retcode = self.dbhelper.delete_transfer_unknown(tids)
            return {"retcode": retcode}

    def __rename(self, data):
        """
        手工转移
        """
        path = dest_dir = None
        syncmod = ModuleConf.RMT_MODES.get(data.get("syncmod"))
        logid = data.get("logid")
        if logid:
            paths = self.dbhelper.get_transfer_path_by_id(logid)
            if paths:
                path = os.path.join(paths[0].SOURCE_PATH, paths[0].SOURCE_FILENAME)
                dest_dir = paths[0].DEST
            else:
                return {"retcode": -1, "retmsg": "未查询到转移日志记录"}
        else:
            unknown_id = data.get("unknown_id")
            if unknown_id:
                paths = self.dbhelper.get_unknown_path_by_id(unknown_id)
                if paths:
                    path = paths[0].PATH
                    dest_dir = paths[0].DEST
                else:
                    return {"retcode": -1, "retmsg": "未查询到未识别记录"}
        if not dest_dir:
            dest_dir = ""
        if not path:
            return {"retcode": -1, "retmsg": "输入路径有误"}
        tmdbid = data.get("tmdb")
        mtype = data.get("type")
        season = data.get("season")
        episode_format = data.get("episode_format")
        episode_details = data.get("episode_details")
        episode_offset = data.get("episode_offset")
        min_filesize = data.get("min_filesize")
        if mtype == "TV":
            media_type = MediaType.TV
        elif mtype == "MOV":
            media_type = MediaType.MOVIE
        else:
            media_type = MediaType.ANIME
        # 如果改次手动修复时一个单文件，自动修复改目录下同名文件，需要配合episode_format生效
        need_fix_all = False
        if os.path.splitext(path)[-1].lower() in RMT_MEDIAEXT and episode_format:
            path = os.path.dirname(path)
            need_fix_all = True
        # 开始转移
        if tmdbid:
            tmdb_info = Media().get_tmdb_info(mtype=media_type, tmdbid=tmdbid)
            if not tmdb_info:
                return {"retcode": 1, "retmsg": "转移失败，无法查询到TMDB信息"}
            succ_flag, ret_msg = FileTransfer().transfer_media(in_from=SyncType.MAN,
                                                               in_path=path,
                                                               rmt_mode=syncmod,
                                                               target_dir=dest_dir,
                                                               tmdb_info=tmdb_info,
                                                               media_type=media_type,
                                                               season=season,
                                                               episode=(EpisodeFormat(episode_format,
                                                                                      episode_details,
                                                                                      episode_offset),
                                                                        need_fix_all),
                                                               min_filesize=min_filesize)
        else:
            succ_flag, ret_msg = FileTransfer().transfer_media(in_from=SyncType.MAN,
                                                               in_path=path,
                                                               rmt_mode=syncmod,
                                                               target_dir=dest_dir,
                                                               media_type=media_type,
                                                               episode=(EpisodeFormat(episode_format,
                                                                                      episode_details,
                                                                                      episode_offset),
                                                                        need_fix_all),
                                                               min_filesize=min_filesize)
        if succ_flag:
            if not need_fix_all and not logid:
                self.dbhelper.update_transfer_unknown_state(path)
            return {"retcode": 0, "retmsg": "转移成功"}
        else:
            return {"retcode": 2, "retmsg": ret_msg}

    @staticmethod
    def __rename_udf(data):
        """
        自定义识别
        """
        inpath = os.path.normpath(data.get("inpath"))
        if data.get("outpath"):
            outpath = os.path.normpath(data.get("outpath"))
        else:
            outpath = None
        syncmod = ModuleConf.RMT_MODES.get(data.get("syncmod"))
        if not os.path.exists(inpath):
            return {"retcode": -1, "retmsg": "输入路径不存在"}
        tmdbid = data.get("tmdb")
        mtype = data.get("type")
        season = data.get("season")
        episode_format = data.get("episode_format")
        episode_details = data.get("episode_details")
        episode_offset = data.get("episode_offset")
        min_filesize = data.get("min_filesize")
        if mtype == "TV" or mtype == MediaType.TV.value:
            media_type = MediaType.TV
        elif mtype == "MOV" or mtype == MediaType.MOVIE.value:
            media_type = MediaType.MOVIE
        else:
            media_type = MediaType.ANIME
        if tmdbid:
            # 有输入TMDBID
            tmdb_info = Media().get_tmdb_info(mtype=media_type, tmdbid=tmdbid)
            if not tmdb_info:
                return {"retcode": 1, "retmsg": "识别失败，无法查询到TMDB信息"}
            # 按识别的信息转移
            succ_flag, ret_msg = FileTransfer().transfer_media(in_from=SyncType.MAN,
                                                               in_path=inpath,
                                                               rmt_mode=syncmod,
                                                               target_dir=outpath,
                                                               tmdb_info=tmdb_info,
                                                               media_type=media_type,
                                                               season=season,
                                                               episode=(
                                                                   EpisodeFormat(episode_format,
                                                                                 episode_details,
                                                                                 episode_offset),
                                                                   False),
                                                               min_filesize=min_filesize,
                                                               udf_flag=True)
        else:
            # 按识别的信息转移
            succ_flag, ret_msg = FileTransfer().transfer_media(in_from=SyncType.MAN,
                                                               in_path=inpath,
                                                               rmt_mode=syncmod,
                                                               target_dir=outpath,
                                                               media_type=media_type,
                                                               episode=(
                                                                   EpisodeFormat(episode_format,
                                                                                 episode_details,
                                                                                 episode_offset),
                                                                   False),
                                                               min_filesize=min_filesize,
                                                               udf_flag=True)
        if succ_flag:
            return {"retcode": 0, "retmsg": "转移成功"}
        else:
            return {"retcode": 2, "retmsg": ret_msg}

    def __delete_history(self, data):
        """
        删除识别记录及文件
        """
        logids = data.get('logids')
        flag = data.get('flag')
        for logid in logids:
            # 读取历史记录
            paths = self.dbhelper.get_transfer_path_by_id(logid)
            if paths:
                # 删除记录
                self.dbhelper.delete_transfer_log_by_id(logid)
                # 根据flag删除文件
                source_path = paths[0].SOURCE_PATH
                source_filename = paths[0].SOURCE_FILENAME
                dest = paths[0].DEST
                dest_path = paths[0].DEST_PATH
                dest_filename = paths[0].DEST_FILENAME
                if flag in ["del_source", "del_all"]:
                    del_flag, del_msg = self.delete_media_file(source_path, source_filename)
                    if not del_flag:
                        log.error(f"【History】{del_msg}")
                    else:
                        log.info(f"【History】{del_msg}")
                if flag in ["del_dest", "del_all"]:
                    if dest_path and dest_filename:
                        del_flag, del_msg = self.delete_media_file(dest_path, dest_filename)
                        if not del_flag:
                            log.error(f"【History】{del_msg}")
                        else:
                            log.info(f"【History】{del_msg}")
                    else:
                        meta_info = MetaInfo(title=source_filename)
                        meta_info.title = paths[0].TITLE
                        meta_info.category = paths[0].CATEGORY
                        meta_info.year = paths[0].YEAR
                        if paths[0].SEASON_EPISODE:
                            meta_info.begin_season = int(str(paths[0].SEASON_EPISODE).replace("S", ""))
                        if paths[0].TYPE == MediaType.MOVIE.value:
                            meta_info.type = MediaType.MOVIE
                        else:
                            meta_info.type = MediaType.TV
                        # 删除文件
                        dest_path = FileTransfer().get_dest_path_by_info(dest=dest, meta_info=meta_info)
                        if dest_path and dest_path.find(meta_info.title) != -1:
                            rm_parent_dir = False
                            if not meta_info.get_season_list():
                                # 电影，删除整个目录
                                try:
                                    shutil.rmtree(dest_path)
                                except Exception as e:
                                    ExceptionUtils.exception_traceback(e)
                            elif not meta_info.get_episode_string():
                                # 电视剧但没有集数，删除季目录
                                try:
                                    shutil.rmtree(dest_path)
                                except Exception as e:
                                    ExceptionUtils.exception_traceback(e)
                                rm_parent_dir = True
                            else:
                                # 有集数的电视剧，删除对应的集数文件
                                for dest_file in PathUtils.get_dir_files(dest_path):
                                    file_meta_info = MetaInfo(os.path.basename(dest_file))
                                    if file_meta_info.get_episode_list() and set(
                                            file_meta_info.get_episode_list()
                                    ).issubset(set(meta_info.get_episode_list())):
                                        try:
                                            os.remove(dest_file)
                                        except Exception as e:
                                            ExceptionUtils.exception_traceback(e)
                                rm_parent_dir = True
                            if rm_parent_dir \
                                    and not PathUtils.get_dir_files(os.path.dirname(dest_path), exts=RMT_MEDIAEXT):
                                # 没有媒体文件时，删除整个目录
                                try:
                                    shutil.rmtree(os.path.dirname(dest_path))
                                except Exception as e:
                                    ExceptionUtils.exception_traceback(e)
        return {"retcode": 0}

    @staticmethod
    def delete_media_file(filedir, filename):
        """
        删除媒体文件，空目录也支被删除
        """
        filedir = os.path.normpath(filedir).replace("\\", "/")
        file = os.path.join(filedir, filename)
        try:
            if not os.path.exists(file):
                return False, f"{file} 不存在"
            os.remove(file)
            nfoname = f"{os.path.splitext(filename)[0]}.nfo"
            nfofile = os.path.join(filedir, nfoname)
            if os.path.exists(nfofile):
                os.remove(nfofile)
            # 检查空目录并删除
            if re.findall(r"^S\d{2}|^Season", os.path.basename(filedir), re.I):
                # 当前是季文件夹，判断并删除
                seaon_dir = filedir
                if seaon_dir.count('/') > 1 and not PathUtils.get_dir_files(seaon_dir, exts=RMT_MEDIAEXT):
                    shutil.rmtree(seaon_dir)
                # 媒体文件夹
                media_dir = os.path.dirname(seaon_dir)
            else:
                media_dir = filedir
            # 检查并删除媒体文件夹，非根目录且目录大于二级，且没有媒体文件时才会删除
            if media_dir != '/' \
                    and media_dir.count('/') > 1 \
                    and not re.search(r'[a-zA-Z]:/$', media_dir) \
                    and not PathUtils.get_dir_files(media_dir, exts=RMT_MEDIAEXT):
                shutil.rmtree(media_dir)
            return True, f"{file} 删除成功"
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return True, f"{file} 删除失败"

    @staticmethod
    def __logging(data):
        """
        查询实时日志
        """
        log_list = []
        refresh_new = data.get('refresh_new')
        if not refresh_new:
            log_list = list(log.LOG_QUEUE)
        elif log.LOG_INDEX:
            if log.LOG_INDEX > len(list(log.LOG_QUEUE)):
                log_list = list(log.LOG_QUEUE)
            else:
                log_list = list(log.LOG_QUEUE)[-log.LOG_INDEX:]
        log.LOG_INDEX = 0
        return {"loglist": log_list}

    @staticmethod
    def __version(data):
        """
        检查新版本
        """
        version, url, flag = WebUtils.get_latest_version()
        if flag:
            return {"code": 0, "version": version, "url": url}
        return {"code": -1, "version": "", "url": ""}

    def __update_site(self, data):
        """
        维护站点信息
        """

        def __is_site_duplicate(query_name, query_tid):
            # 检查是否重名
            _sites = self.dbhelper.get_site_by_name(name=query_name)
            for site in _sites:
                site_id = site.ID
                if str(site_id) != str(query_tid):
                    return True
            return False

        tid = data.get('site_id')
        name = data.get('site_name')
        site_pri = data.get('site_pri')
        rssurl = data.get('site_rssurl')
        signurl = data.get('site_signurl')
        cookie = data.get('site_cookie')
        note = data.get('site_note')
        if isinstance(note, dict):
            note = json.dumps(note)
        rss_uses = data.get('site_include')

        if __is_site_duplicate(name, tid):
            return {"code": 400, "msg": "站点名称重复"}

        if tid:
            sites = self.dbhelper.get_site_by_id(tid)
            # 站点不存在
            if not sites:
                return {"code": 400, "msg": "站点不存在"}

            old_name = sites[0].NAME

            ret = self.dbhelper.update_config_site(tid=tid,
                                                   name=name,
                                                   site_pri=site_pri,
                                                   rssurl=rssurl,
                                                   signurl=signurl,
                                                   cookie=cookie,
                                                   note=note,
                                                   rss_uses=rss_uses)
            if ret and (name != old_name):
                # 更新历史站点数据信息
                self.dbhelper.update_site_user_statistics_site_name(name, old_name)
                self.dbhelper.update_site_seed_info_site_name(name, old_name)
                self.dbhelper.update_site_statistics_site_name(name, old_name)

        else:
            ret = self.dbhelper.insert_config_site(name=name,
                                                   site_pri=site_pri,
                                                   rssurl=rssurl,
                                                   signurl=signurl,
                                                   cookie=cookie,
                                                   note=note,
                                                   rss_uses=rss_uses)
        # 生效站点配置
        Sites().init_config()
        # 初始化刷流任务
        BrushTask().init_config()
        return {"code": ret}

    @staticmethod
    def __get_site(data):
        """
        查询单个站点信息
        """
        tid = data.get("id")
        site_free = False
        site_2xfree = False
        site_hr = False
        if tid:
            ret = Sites().get_sites(siteid=tid)
            if ret.get("rssurl"):
                site_attr = Sites().get_grapsite_conf(ret.get("rssurl"))
                if site_attr.get("FREE"):
                    site_free = True
                if site_attr.get("2XFREE"):
                    site_2xfree = True
                if site_attr.get("HR"):
                    site_hr = True
        else:
            ret = []
        return {"code": 0, "site": ret, "site_free": site_free, "site_2xfree": site_2xfree, "site_hr": site_hr}

    @staticmethod
    def __get_sites(data):
        """
        查询多个站点信息
        """
        rss = True if data.get("rss") else False
        brush = True if data.get("brush") else False
        signin = True if data.get("signin") else False
        statistic = True if data.get("statistic") else False
        basic = True if data.get("basic") else False
        if basic:
            sites = Sites().get_site_dict(rss=rss,
                                          brush=brush,
                                          signin=signin,
                                          statistic=statistic)
        else:
            sites = Sites().get_sites(rss=rss,
                                      brush=brush,
                                      signin=signin,
                                      statistic=statistic)
        return {"code": 0, "sites": sites}

    def __del_site(self, data):
        """
        删除单个站点信息
        """
        tid = data.get("id")
        if tid:
            ret = self.dbhelper.delete_config_site(tid)
            Sites().init_config()
            BrushTask().init_config()
            return {"code": ret}
        else:
            return {"code": 0}

    def __restart(self, data):
        """
        重启
        """
        # 退出主进程
        self.restart_server()
        return {"code": 0}

    def __update_system(self, data):
        """
        更新
        """
        # 升级
        if SystemUtils.is_synology():
            if SystemUtils.execute('/bin/ps -w -x | grep -v grep | grep -w "nastool update" | wc -l') == '0':
                # 调用群晖套件内置命令升级
                os.system('nastool update')
                # 重启
                self.restart_server()
        else:
            # 清除git代理
            os.system("git config --global --unset http.proxy")
            os.system("git config --global --unset https.proxy")
            # 设置git代理
            proxy = Config().get_proxies() or {}
            http_proxy = proxy.get("http")
            https_proxy = proxy.get("https")
            if http_proxy or https_proxy:
                os.system(f"git config --global http.proxy {http_proxy or https_proxy}")
                os.system(f"git config --global https.proxy {https_proxy or http_proxy}")
            # 清理
            os.system("git clean -dffx")
            # 升级
            branch = "dev" if os.environ.get("NASTOOL_VERSION") == "dev" else "master"
            os.system(f"git fetch --depth 1 origin {branch}")
            os.system(f"git reset --hard origin/{branch}")
            os.system("git submodule update --init --recursive")
            # 安装依赖
            os.system('pip install -r /nas-tools/requirements.txt')
            # 重启
            self.restart_server()
        return {"code": 0}

    def __reset_db_version(self, data):
        """
        重置数据库版本
        """
        try:
            self.dbhelper.drop_table("alembic_version")
            return {"code": 0}
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {"code": 1, "msg": str(e)}

    @staticmethod
    def __logout(data):
        """
        注销
        """
        logout_user()
        return {"code": 0}

    def __update_config(self, data):
        """
        更新配置信息
        """
        cfg = Config().get_config()
        cfgs = dict(data).items()
        # 仅测试不保存
        config_test = False
        # 修改配置
        for key, value in cfgs:
            if key == "test" and value:
                config_test = True
                continue
            # 生效配置
            cfg = self.set_config_value(cfg, key, value)

        # 保存配置
        if not config_test:
            Config().save_config(cfg)

        return {"code": 0}

    def __add_or_edit_sync_path(self, data):
        """
        维护同步目录
        """
        sid = data.get("sid")
        source = data.get("from")
        dest = data.get("to")
        unknown = data.get("unknown")
        mode = data.get("syncmod")
        rename = 1 if StringUtils.to_bool(data.get("rename"), False) else 0
        enabled = 1 if StringUtils.to_bool(data.get("enabled"), False) else 0
        # 源目录检查
        if not source:
            return {"code": 1, "msg": f'源目录不能为空'}
        if not os.path.exists(source):
            return {"code": 1, "msg": f'{source}目录不存在'}
        # windows目录用\，linux目录用/
        source = os.path.normpath(source)
        # 目的目录检查，目的目录可为空
        if dest:
            dest = os.path.normpath(dest)
            if PathUtils.is_path_in_path(source, dest):
                return {"code": 1, "msg": "目的目录不可包含在源目录中"}
        if unknown:
            unknown = os.path.normpath(unknown)

        # 硬链接不能跨盘
        if mode == "link" and dest:
            common_path = os.path.commonprefix([source, dest])
            if not common_path or common_path == "/":
                return {"code": 1, "msg": "硬链接不能跨盘"}

        # 编辑先删再增
        if sid:
            self.dbhelper.delete_config_sync_path(sid)
        # 若启用，则关闭其他相同源目录的同步目录
        if enabled == 1:
            self.dbhelper.check_config_sync_paths(source=source,
                                                  enabled=0)
        # 插入数据库
        self.dbhelper.insert_config_sync_path(source=source,
                                              dest=dest,
                                              unknown=unknown,
                                              mode=mode,
                                              rename=rename,
                                              enabled=enabled)
        Sync().init_config()
        return {"code": 0, "msg": ""}

    def __get_sync_path(self, data):
        """
        查询同步目录
        """
        try:
            sid = data.get("sid")
            sync_item = self.dbhelper.get_config_sync_paths(sid=sid)[0]
            syncpath = {'id': sync_item.ID,
                        'from': sync_item.SOURCE,
                        'to': sync_item.DEST or "",
                        'unknown': sync_item.UNKNOWN or "",
                        'syncmod': sync_item.MODE,
                        'rename': sync_item.RENAME,
                        'enabled': sync_item.ENABLED}
            return {"code": 0, "data": syncpath}
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {"code": 1, "msg": "查询识别词失败"}

    def __delete_sync_path(self, data):
        """
        移出同步目录
        """
        sid = data.get("sid")
        self.dbhelper.delete_config_sync_path(sid)
        Sync().init_config()
        return {"code": 0}

    def __check_sync_path(self, data):
        """
        维护同步目录
        """
        flag = data.get("flag")
        sid = data.get("sid")
        checked = data.get("checked")
        if flag == "rename":
            self.dbhelper.check_config_sync_paths(sid=sid,
                                                  rename=1 if checked else 0)
            Sync().init_config()
            return {"code": 0}
        elif flag == "enable":
            # 若启用，则关闭其他相同源目录的同步目录
            if checked:
                sync_item = self.dbhelper.get_config_sync_paths(sid=sid)[0]
                self.dbhelper.check_config_sync_paths(source=sync_item.SOURCE,
                                                      enabled=0)
            self.dbhelper.check_config_sync_paths(sid=sid,
                                                  enabled=1 if checked else 0)
            Sync().init_config()
            return {"code": 0}
        else:
            return {"code": 1}

    def __remove_rss_media(self, data):
        """
        移除RSS订阅
        """
        name = data.get("name")
        mtype = data.get("type")
        year = data.get("year")
        season = data.get("season")
        rssid = data.get("rssid")
        page = data.get("page")
        tmdbid = data.get("tmdbid")
        if name:
            name = MetaInfo(title=name).get_name()
        if mtype:
            if mtype in self._MovieTypes:
                self.dbhelper.delete_rss_movie(title=name, year=year, rssid=rssid, tmdbid=tmdbid)
            else:
                self.dbhelper.delete_rss_tv(title=name, season=season, rssid=rssid, tmdbid=tmdbid)
        return {"code": 0, "page": page, "name": name}

    def __add_rss_media(self, data):
        """
        添加RSS订阅
        """
        name = data.get("name")
        _subscribe = Subscribe()
        mtype = data.get("type")
        year = data.get("year")
        keyword = data.get("keyword")
        season = data.get("season")
        fuzzy_match = data.get("fuzzy_match")
        mediaid = data.get("mediaid")
        rss_sites = data.get("rss_sites")
        search_sites = data.get("search_sites")
        over_edition = data.get("over_edition")
        filter_restype = data.get("filter_restype")
        filter_pix = data.get("filter_pix")
        filter_team = data.get("filter_team")
        filter_rule = data.get("filter_rule")
        save_path = data.get("save_path")
        download_setting = data.get("download_setting")
        total_ep = data.get("total_ep")
        current_ep = data.get("current_ep")
        rssid = data.get("rssid")
        page = data.get("page")
        mtype = MediaType.MOVIE if mtype in self._MovieTypes else MediaType.TV
        if isinstance(season, list):
            code = 0
            msg = ""
            for sea in season:
                code, msg, media_info = _subscribe.add_rss_subscribe(mtype=mtype,
                                                                     name=name,
                                                                     year=year,
                                                                     keyword=keyword,
                                                                     season=sea,
                                                                     fuzzy_match=fuzzy_match,
                                                                     mediaid=mediaid,
                                                                     rss_sites=rss_sites,
                                                                     search_sites=search_sites,
                                                                     over_edition=over_edition,
                                                                     filter_restype=filter_restype,
                                                                     filter_pix=filter_pix,
                                                                     filter_team=filter_team,
                                                                     filter_rule=filter_rule,
                                                                     save_path=save_path,
                                                                     download_setting=download_setting,
                                                                     rssid=rssid)
                if code != 0:
                    break
        else:
            code, msg, media_info = _subscribe.add_rss_subscribe(mtype=mtype,
                                                                 name=name,
                                                                 year=year,
                                                                 keyword=keyword,
                                                                 season=season,
                                                                 fuzzy_match=fuzzy_match,
                                                                 mediaid=mediaid,
                                                                 rss_sites=rss_sites,
                                                                 search_sites=search_sites,
                                                                 over_edition=over_edition,
                                                                 filter_restype=filter_restype,
                                                                 filter_pix=filter_pix,
                                                                 filter_team=filter_team,
                                                                 filter_rule=filter_rule,
                                                                 save_path=save_path,
                                                                 download_setting=download_setting,
                                                                 total_ep=total_ep,
                                                                 current_ep=current_ep,
                                                                 rssid=rssid)
        if not rssid:
            if mtype == MediaType.MOVIE:
                rssid = self.dbhelper.get_rss_movie_id(title=name, tmdbid=mediaid)
            else:
                rssid = self.dbhelper.get_rss_tv_id(title=name, tmdbid=mediaid)
        return {"code": code, "msg": msg, "page": page, "name": name, "rssid": rssid}

    def __re_identification(self, data):
        """
        未识别的重新识别
        """
        flag = data.get("flag")
        ids = data.get("ids")
        ret_flag = True
        ret_msg = []
        if flag == "unidentification":
            for wid in ids:
                paths = self.dbhelper.get_unknown_path_by_id(wid)
                if paths:
                    path = paths[0].PATH
                    dest_dir = paths[0].DEST
                    rmt_mode = ModuleConf.get_enum_item(RmtMode, paths[0].MODE) if paths[0].MODE else None
                else:
                    return {"retcode": -1, "retmsg": "未查询到未识别记录"}
                if not dest_dir:
                    dest_dir = ""
                if not path:
                    return {"retcode": -1, "retmsg": "未识别路径有误"}
                succ_flag, msg = FileTransfer().transfer_media(in_from=SyncType.MAN,
                                                               rmt_mode=rmt_mode,
                                                               in_path=path,
                                                               target_dir=dest_dir)
                if succ_flag:
                    self.dbhelper.update_transfer_unknown_state(path)
                else:
                    ret_flag = False
                    if msg not in ret_msg:
                        ret_msg.append(msg)
        elif flag == "history":
            for wid in ids:
                paths = self.dbhelper.get_transfer_path_by_id(wid)
                if paths:
                    path = os.path.join(paths[0].SOURCE_PATH, paths[0].SOURCE_FILENAME)
                    dest_dir = paths[0].DEST
                    rmt_mode = ModuleConf.get_enum_item(RmtMode, paths[0].MODE) if paths[0].MODE else None
                else:
                    return {"retcode": -1, "retmsg": "未查询到转移日志记录"}
                if not dest_dir:
                    dest_dir = ""
                if not path:
                    return {"retcode": -1, "retmsg": "未识别路径有误"}
                succ_flag, msg = FileTransfer().transfer_media(in_from=SyncType.MAN,
                                                               rmt_mode=rmt_mode,
                                                               in_path=path,
                                                               target_dir=dest_dir)
                if not succ_flag:
                    ret_flag = False
                    if msg not in ret_msg:
                        ret_msg.append(msg)
        if ret_flag:
            return {"retcode": 0, "retmsg": "转移成功"}
        else:
            return {"retcode": 2, "retmsg": "、".join(ret_msg)}

    def __media_info(self, data):
        """
        查询媒体信息
        """
        mediaid = data.get("id")
        mtype = data.get("type")
        title = data.get("title")
        year = data.get("year")
        page = data.get("page")
        rssid = data.get("rssid")
        seasons = []
        link_url = ""
        vote_average = 0
        poster_path = ""
        release_date = ""
        overview = ""
        # 类型
        if mtype in self._MovieTypes:
            media_type = MediaType.MOVIE
        else:
            media_type = MediaType.TV

        # 先取订阅信息
        rssid_ok = False
        if rssid:
            rssid = str(rssid)
            if media_type == MediaType.MOVIE:
                rssinfo = Subscribe().get_subscribe_movies(rid=rssid)
            else:
                rssinfo = Subscribe().get_subscribe_tvs(rid=rssid)
            if not rssinfo:
                return {
                    "code": 1,
                    "retmsg": "无法查询到订阅信息",
                    "rssid": rssid,
                    "type_str": media_type.value
                }
            overview = rssinfo[rssid].get("overview")
            poster_path = rssinfo[rssid].get("poster")
            title = rssinfo[rssid].get("name")
            vote_average = rssinfo[rssid].get("vote")
            year = rssinfo[rssid].get("year")
            release_date = rssinfo[rssid].get("release_date")
            link_url = Media().get_detail_url(mtype=media_type, tmdbid=rssinfo[rssid].get("tmdbid"))
            if overview and poster_path:
                rssid_ok = True

        # 订阅信息不足
        if not rssid_ok:
            if mediaid:
                media = WebUtils.get_mediainfo_from_id(mtype=media_type, mediaid=mediaid)
            else:
                media = Media().get_media_info(title=f"{title} {year}", mtype=media_type)
            if not media or not media.tmdb_info:
                return {
                    "code": 1,
                    "retmsg": "无法查询到TMDB信息",
                    "rssid": rssid,
                    "type_str": media_type.value
                }
            if not mediaid:
                mediaid = media.tmdb_id
            link_url = media.get_detail_url()
            overview = media.overview
            poster_path = media.get_poster_image()
            title = media.title
            vote_average = round(float(media.vote_average or 0), 1)
            year = media.year
            if media_type != MediaType.MOVIE:
                release_date = media.tmdb_info.get('first_air_date')
                seasons = [{
                    "text": "第%s季" % cn2an.an2cn(season.get("season_number"), mode='low'),
                    "num": season.get("season_number")} for season in
                    Media().get_tmdb_tv_seasons(tv_info=media.tmdb_info)]
            else:
                release_date = media.tmdb_info.get('release_date')

            # 查订阅信息
            if not rssid:
                if media_type == MediaType.MOVIE:
                    rssid = self.dbhelper.get_rss_movie_id(title=title, tmdbid=mediaid)
                else:
                    rssid = self.dbhelper.get_rss_tv_id(title=title, tmdbid=mediaid)

        return {
            "code": 0,
            "type": mtype,
            "type_str": media_type.value,
            "page": page,
            "title": title,
            "vote_average": vote_average,
            "poster_path": poster_path,
            "release_date": release_date,
            "year": year,
            "overview": overview,
            "link_url": link_url,
            "tmdbid": mediaid,
            "rssid": rssid,
            "seasons": seasons
        }

    @staticmethod
    def __test_connection(data):
        """
        测试连通性
        """
        # 支持两种传入方式：命令数组或单个命令，单个命令时xx|xx模式解析为模块和类，进行动态引入
        command = data.get("command")
        ret = None
        if command:
            try:
                module_obj = None
                if isinstance(command, list):
                    for cmd_str in command:
                        ret = eval(cmd_str)
                        if not ret:
                            break
                else:
                    if command.find("|") != -1:
                        module = command.split("|")[0]
                        class_name = command.split("|")[1]
                        module_obj = getattr(importlib.import_module(module), class_name)()
                        if hasattr(module_obj, "init_config"):
                            module_obj.init_config()
                        ret = module_obj.get_status()
                    else:
                        ret = eval(command)
                # 重载配置
                Config().init_config()
                if module_obj:
                    if hasattr(module_obj, "init_config"):
                        module_obj.init_config()
            except Exception as e:
                ret = None
                ExceptionUtils.exception_traceback(e)
            return {"code": 0 if ret else 1}
        return {"code": 0}

    def __user_manager(self, data):
        """
        用户管理
        """
        oper = data.get("oper")
        name = data.get("name")
        if oper == "add":
            password = generate_password_hash(str(data.get("password")))
            pris = data.get("pris")
            if isinstance(pris, list):
                pris = ",".join(pris)
            ret = self.dbhelper.insert_user(name, password, pris)
        else:
            ret = self.dbhelper.delete_user(name)

        if ret == 1 or ret:
            return {"code": 0, "success": False}
        return {"code": -1, "success": False, 'message': '操作失败'}

    @staticmethod
    def __refresh_rss(data):
        """
        重新搜索RSS
        """
        mtype = data.get("type")
        rssid = data.get("rssid")
        page = data.get("page")
        if mtype == "MOV":
            ThreadHelper().start_thread(Subscribe().subscribe_search_movie, (rssid,))
        else:
            ThreadHelper().start_thread(Subscribe().subscribe_search_tv, (rssid,))
        return {"code": 0, "page": page}

    @staticmethod
    def get_system_message(lst_time):
        messages = MessageCenter().get_system_messages(lst_time=lst_time)
        if messages:
            lst_time = messages[0].get("time")
        return {
            "code": 0,
            "message": messages,
            "lst_time": lst_time
        }

    def __refresh_message(self, data):
        """
        刷新首页消息中心
        """
        lst_time = data.get("lst_time")
        system_msg = self.get_system_message(lst_time=lst_time)
        messages = system_msg.get("message")
        lst_time = system_msg.get("lst_time")
        message_html = []
        for message in list(reversed(messages)):
            level = "bg-red" if message.get("level") == "ERROR" else ""
            content = re.sub(r"#+", "<br>",
                             re.sub(r"<[^>]+>", "",
                                    re.sub(r"<br/?>", "####", message.get("content"), flags=re.IGNORECASE)))
            message_html.append(f"""
            <div class="list-group-item">
              <div class="row align-items-center">
                <div class="col-auto">
                  <span class="status-dot {level} d-block"></span>
                </div>
                <div class="col text-truncate">
                  <span class="text-wrap">{message.get("title")}</span>
                  <div class="d-block text-muted text-truncate mt-n1 text-wrap">{content}</div>
                  <div class="d-block text-muted text-truncate mt-n1 text-wrap">{message.get("time")}</div>
                </div>
              </div>
            </div>
            """)
        return {"code": 0, "message": message_html, "lst_time": lst_time}

    @staticmethod
    def __delete_tmdb_cache(data):
        """
        删除tmdb缓存
        """
        if MetaHelper().delete_meta_data(data.get("cache_key")):
            MetaHelper().save_meta_data()
        return {"code": 0}

    @staticmethod
    def __movie_calendar_data(data):
        """
        查询电影上映日期
        """
        tid = data.get("id")
        rssid = data.get("rssid")
        if tid and tid.startswith("DB:"):
            doubanid = tid.replace("DB:", "")
            douban_info = DouBan().get_douban_detail(doubanid=doubanid, mtype=MediaType.MOVIE)
            if not douban_info:
                return {"code": 1, "retmsg": "无法查询到豆瓣信息"}
            poster_path = douban_info.get("cover_url") or ""
            title = douban_info.get("title")
            rating = douban_info.get("rating", {}) or {}
            vote_average = rating.get("value") or "无"
            release_date = douban_info.get("pubdate")
            if release_date:
                release_date = re.sub(r"\(.*\)", "", douban_info.get("pubdate")[0])
            if not release_date:
                return {"code": 1, "retmsg": "上映日期不正确"}
            else:
                return {"code": 0,
                        "type": "电影",
                        "title": title,
                        "start": release_date,
                        "id": tid,
                        "year": release_date[0:4] if release_date else "",
                        "poster": poster_path,
                        "vote_average": vote_average,
                        "rssid": rssid
                        }
        else:
            if tid:
                tmdb_info = Media().get_tmdb_info(mtype=MediaType.MOVIE, tmdbid=tid)
            else:
                return {"code": 1, "retmsg": "没有TMDBID信息"}
            if not tmdb_info:
                return {"code": 1, "retmsg": "无法查询到TMDB信息"}
            poster_path = TMDB_IMAGE_W500_URL % tmdb_info.get('poster_path') if tmdb_info.get(
                'poster_path') else ""
            title = tmdb_info.get('title')
            vote_average = tmdb_info.get("vote_average")
            release_date = tmdb_info.get('release_date')
            if not release_date:
                return {"code": 1, "retmsg": "上映日期不正确"}
            else:
                return {"code": 0,
                        "type": "电影",
                        "title": title,
                        "start": release_date,
                        "id": tid,
                        "year": release_date[0:4] if release_date else "",
                        "poster": poster_path,
                        "vote_average": vote_average,
                        "rssid": rssid
                        }

    @staticmethod
    def __tv_calendar_data(data):
        """
        查询电视剧上映日期
        """
        tid = data.get("id")
        season = data.get("season")
        name = data.get("name")
        rssid = data.get("rssid")
        if tid and tid.startswith("DB:"):
            doubanid = tid.replace("DB:", "")
            douban_info = DouBan().get_douban_detail(doubanid=doubanid, mtype=MediaType.TV)
            if not douban_info:
                return {"code": 1, "retmsg": "无法查询到豆瓣信息"}
            poster_path = douban_info.get("cover_url") or ""
            title = douban_info.get("title")
            rating = douban_info.get("rating", {}) or {}
            vote_average = rating.get("value") or "无"
            release_date = re.sub(r"\(.*\)", "", douban_info.get("pubdate")[0])
            if not release_date:
                return {"code": 1, "retmsg": "上映日期不正确"}
            else:
                return {"code": 0,
                        "type": "电视剧",
                        "title": title,
                        "start": release_date,
                        "id": tid,
                        "year": release_date[0:4] if release_date else "",
                        "poster": poster_path,
                        "vote_average": vote_average,
                        "rssid": rssid
                        }
        else:
            if tid:
                tmdb_info = Media().get_tmdb_tv_season_detail(tmdbid=tid, season=season)
            else:
                return {"code": 1, "retmsg": "没有TMDBID信息"}
            if not tmdb_info:
                return {"code": 1, "retmsg": "无法查询到TMDB信息"}
            episode_events = []
            air_date = tmdb_info.get("air_date")
            if not tmdb_info.get("poster_path"):
                tv_tmdb_info = Media().get_tmdb_info(mtype=MediaType.TV, tmdbid=tid)
                if tv_tmdb_info:
                    poster_path = TMDB_IMAGE_W500_URL % tv_tmdb_info.get("poster_path")
                else:
                    poster_path = ""
            else:
                poster_path = TMDB_IMAGE_W500_URL % tmdb_info.get("poster_path")
            year = air_date[0:4] if air_date else ""
            for episode in tmdb_info.get("episodes"):
                episode_events.append({
                    "type": "剧集",
                    "title": "%s 第%s季第%s集" % (
                        name,
                        season,
                        episode.get("episode_number")
                    ) if season != 1 else "%s 第%s集" % (
                        name,
                        episode.get("episode_number")
                    ),
                    "start": episode.get("air_date"),
                    "id": tid,
                    "year": year,
                    "poster": poster_path,
                    "vote_average": episode.get("vote_average") or "无",
                    "rssid": rssid
                })
            return {"code": 0, "events": episode_events}

    def __rss_detail(self, data):
        rid = data.get("rssid")
        mtype = data.get("rsstype")
        if mtype in self._MovieTypes:
            rssdetail = Subscribe().get_subscribe_movies(rid=rid)
            if not rssdetail:
                return {"code": 1}
            rssdetail = list(rssdetail.values())[0]
            rssdetail["type"] = "MOV"
        else:
            rssdetail = Subscribe().get_subscribe_tvs(rid=rid)
            if not rssdetail:
                return {"code": 1}
            rssdetail = list(rssdetail.values())[0]
            rssdetail["type"] = "TV"
        return {"code": 0, "detail": rssdetail}

    @staticmethod
    def __modify_tmdb_cache(data):
        """
        修改TMDB缓存的标题
        """
        if MetaHelper().modify_meta_data(data.get("key"), data.get("title")):
            MetaHelper().save_meta_data(force=True)
        return {"code": 0}

    def __truncate_blacklist(self, data):
        """
        清空文件转移黑名单记录
        """
        self.dbhelper.truncate_transfer_blacklist()
        return {"code": 0}

    def __truncate_rsshistory(self, data):
        """
        清空RSS历史记录
        """
        self.dbhelper.truncate_rss_history()
        self.dbhelper.truncate_rss_episodes()
        return {"code": 0}

    def __add_brushtask(self, data):
        """
        新增刷流任务
        """
        # 输入值
        brushtask_id = data.get("brushtask_id")
        brushtask_name = data.get("brushtask_name")
        brushtask_site = data.get("brushtask_site")
        brushtask_interval = data.get("brushtask_interval")
        brushtask_downloader = data.get("brushtask_downloader")
        brushtask_totalsize = data.get("brushtask_totalsize")
        brushtask_state = data.get("brushtask_state")
        brushtask_transfer = 'Y' if data.get("brushtask_transfer") else 'N'
        brushtask_sendmessage = 'Y' if data.get("brushtask_sendmessage") else 'N'
        brushtask_forceupload = 'Y' if data.get("brushtask_forceupload") else 'N'
        brushtask_free = data.get("brushtask_free")
        brushtask_hr = data.get("brushtask_hr")
        brushtask_torrent_size = data.get("brushtask_torrent_size")
        brushtask_include = data.get("brushtask_include")
        brushtask_exclude = data.get("brushtask_exclude")
        brushtask_dlcount = data.get("brushtask_dlcount")
        brushtask_peercount = data.get("brushtask_peercount")
        brushtask_seedtime = data.get("brushtask_seedtime")
        brushtask_seedratio = data.get("brushtask_seedratio")
        brushtask_seedsize = data.get("brushtask_seedsize")
        brushtask_dltime = data.get("brushtask_dltime")
        brushtask_avg_upspeed = data.get("brushtask_avg_upspeed")
        brushtask_pubdate = data.get("brushtask_pubdate")
        brushtask_upspeed = data.get("brushtask_upspeed")
        brushtask_downspeed = data.get("brushtask_downspeed")
        # 选种规则
        rss_rule = {
            "free": brushtask_free,
            "hr": brushtask_hr,
            "size": brushtask_torrent_size,
            "include": brushtask_include,
            "exclude": brushtask_exclude,
            "dlcount": brushtask_dlcount,
            "peercount": brushtask_peercount,
            "pubdate": brushtask_pubdate,
            "upspeed": brushtask_upspeed,
            "downspeed": brushtask_downspeed
        }
        # 删除规则
        remove_rule = {
            "time": brushtask_seedtime,
            "ratio": brushtask_seedratio,
            "uploadsize": brushtask_seedsize,
            "dltime": brushtask_dltime,
            "avg_upspeed": brushtask_avg_upspeed
        }
        # 添加记录
        item = {
            "name": brushtask_name,
            "site": brushtask_site,
            "free": brushtask_free,
            "interval": brushtask_interval,
            "downloader": brushtask_downloader,
            "seed_size": brushtask_totalsize,
            "transfer": brushtask_transfer,
            "state": brushtask_state,
            "rss_rule": rss_rule,
            "remove_rule": remove_rule,
            "sendmessage": brushtask_sendmessage,
            "forceupload": brushtask_forceupload
        }
        self.dbhelper.insert_brushtask(brushtask_id, item)

        # 重新初始化任务
        BrushTask().init_config()
        return {"code": 0}

    def __del_brushtask(self, data):
        """
        删除刷流任务
        """
        brush_id = data.get("id")
        if brush_id:
            self.dbhelper.delete_brushtask(brush_id)
            # 重新初始化任务
            BrushTask().init_config()
            return {"code": 0}
        return {"code": 1}

    def __brushtask_detail(self, data):
        """
        查询刷流任务详情
        """
        brush_id = data.get("id")
        brushtask = self.dbhelper.get_brushtasks(brush_id)
        if not brushtask:
            return {"code": 1, "task": {}}
        site_info = Sites().get_sites(siteid=brushtask.SITE)
        task = {
            "id": brushtask.ID,
            "name": brushtask.NAME,
            "site": brushtask.SITE,
            "interval": brushtask.INTEVAL,
            "state": brushtask.STATE,
            "downloader": brushtask.DOWNLOADER,
            "transfer": brushtask.TRANSFER,
            "free": brushtask.FREELEECH,
            "rss_rule": eval(brushtask.RSS_RULE),
            "remove_rule": eval(brushtask.REMOVE_RULE),
            "seed_size": brushtask.SEED_SIZE,
            "download_count": brushtask.DOWNLOAD_COUNT,
            "remove_count": brushtask.REMOVE_COUNT,
            "download_size": StringUtils.str_filesize(brushtask.DOWNLOAD_SIZE),
            "upload_size": StringUtils.str_filesize(brushtask.UPLOAD_SIZE),
            "lst_mod_date": brushtask.LST_MOD_DATE,
            "site_url": StringUtils.get_base_url(site_info.get("signurl") or site_info.get("rssurl")),
            "sendmessage": brushtask.SENDMESSAGE,
            "forceupload": brushtask.FORCEUPLOAD
        }
        return {"code": 0, "task": task}

    def __add_downloader(self, data):
        """
        添加自定义下载器
        """
        test = data.get("test")
        dl_id = data.get("id")
        dl_name = data.get("name")
        dl_type = data.get("type")
        if test:
            # 测试
            if dl_type == "qbittorrent":
                downloader = Qbittorrent(
                    config={
                        "qbhost": data.get("host"),
                        "qbport": data.get("port"),
                        "qbusername": data.get("username"),
                        "qbpassword": data.get("password")
                    })
            else:
                downloader = Transmission(
                    config={
                        "trhost": data.get("host"),
                        "trport": data.get("port"),
                        "trusername": data.get("username"),
                        "trpassword": data.get("password")
                    })
            if downloader.get_status():
                return {"code": 0}
            else:
                return {"code": 1}
        else:
            # 保存
            self.dbhelper.update_user_downloader(
                did=dl_id,
                name=dl_name,
                dtype=dl_type,
                user_config={
                    "host": data.get("host"),
                    "port": data.get("port"),
                    "username": data.get("username"),
                    "password": data.get("password"),
                    "save_dir": data.get("save_dir")
                },
                note=None)
            BrushTask().init_config()
            return {"code": 0}

    def __delete_downloader(self, data):
        """
        删除自定义下载器
        """
        dl_id = data.get("id")
        if dl_id:
            self.dbhelper.delete_user_downloader(dl_id)
            BrushTask().init_config()
        return {"code": 0}

    def __get_downloader(self, data):
        """
        查询自定义下载器
        """
        dl_id = data.get("id")
        if dl_id:
            info = self.dbhelper.get_user_downloaders(dl_id)
            if info:
                return {"code": 0, "info": info.as_dict()}
        return {"code": 1}

    def __name_test(self, data):
        """
        名称识别测试
        """
        name = data.get("name")
        if not name:
            return {"code": -1}
        media_info = Media().get_media_info(title=name)
        if not media_info:
            return {"code": 0, "data": {"name": "无法识别"}}
        return {"code": 0, "data": self.mediainfo_dict(media_info)}

    @staticmethod
    def mediainfo_dict(media_info):
        if not media_info:
            return {}
        tmdb_id = media_info.tmdb_id
        tmdb_link = media_info.get_detail_url()
        tmdb_S_E_link = ""
        if tmdb_id:
            if media_info.get_season_string():
                tmdb_S_E_link = "%s/season/%s" % (tmdb_link, media_info.get_season_seq())
                if media_info.get_episode_string():
                    tmdb_S_E_link = "%s/episode/%s" % (tmdb_S_E_link, media_info.get_episode_seq())
        return {
            "type": media_info.type.value if media_info.type else "",
            "name": media_info.get_name(),
            "title": media_info.title,
            "year": media_info.year,
            "season_episode": media_info.get_season_episode_string(),
            "part": media_info.part,
            "tmdbid": tmdb_id,
            "tmdblink": tmdb_link,
            "tmdb_S_E_link": tmdb_S_E_link,
            "category": media_info.category,
            "restype": media_info.resource_type,
            "effect": media_info.resource_effect,
            "pix": media_info.resource_pix,
            "team": media_info.resource_team,
            "video_codec": media_info.video_encode,
            "audio_codec": media_info.audio_encode,
            "org_string": media_info.org_string,
            "ignored_words": media_info.ignored_words,
            "replaced_words": media_info.replaced_words,
            "offset_words": media_info.offset_words
        }

    @staticmethod
    def __rule_test(data):
        title = data.get("title")
        subtitle = data.get("subtitle")
        size = data.get("size")
        rulegroup = data.get("rulegroup")
        if not title:
            return {"code": -1}
        meta_info = MetaInfo(title=title, subtitle=subtitle)
        meta_info.size = float(size) * 1024 ** 3 if size else 0
        match_flag, res_order, match_msg = \
            Filter().check_torrent_filter(meta_info=meta_info,
                                          filter_args={"rule": rulegroup})
        return {
            "code": 0,
            "flag": match_flag,
            "text": "匹配" if match_flag else "未匹配",
            "order": 100 - res_order if res_order else 0
        }

    @staticmethod
    def __net_test(data):
        target = data
        if target == "image.tmdb.org":
            target = target + "/t/p/w500/wwemzKWzjKYJFfCeiB57q3r4Bcm.png"
        if target == "qyapi.weixin.qq.com":
            target = target + "/cgi-bin/message/send"
        target = "https://" + target
        start_time = datetime.datetime.now()
        if target.find("themoviedb") != -1 \
                or target.find("telegram") != -1 \
                or target.find("fanart") != -1 \
                or target.find("tmdb") != -1:
            res = RequestUtils(proxies=Config().get_proxies(), timeout=5).get_res(target)
        else:
            res = RequestUtils(timeout=5).get_res(target)
        seconds = int((datetime.datetime.now() - start_time).microseconds / 1000)
        if not res:
            return {"res": False, "time": "%s 毫秒" % seconds}
        elif res.ok:
            return {"res": True, "time": "%s 毫秒" % seconds}
        else:
            return {"res": False, "time": "%s 毫秒" % seconds}

    @staticmethod
    def __get_site_activity(data):
        """
        查询site活动[上传，下载，魔力值]
        :param data: {"name":site_name}
        :return:
        """
        if not data or "name" not in data:
            return {"code": 1, "msg": "查询参数错误"}

        resp = {"code": 0}

        resp.update({"dataset": Sites().get_pt_site_activity_history(data["name"])})
        return resp

    @staticmethod
    def __get_site_history(data):
        """
        查询site 历史[上传，下载]
        :param data: {"days":累计时间}
        :return:
        """
        if not data or "days" not in data or not isinstance(data["days"], int):
            return {"code": 1, "msg": "查询参数错误"}

        resp = {"code": 0}
        _, _, site, upload, download = Sites().get_pt_site_statistics_history(data["days"] + 1)

        # 调整为dataset组织数据
        dataset = [["site", "upload", "download"]]
        dataset.extend([[site, upload, download] for site, upload, download in zip(site, upload, download)])
        resp.update({"dataset": dataset})
        return resp

    @staticmethod
    def __get_site_seeding_info(data):
        """
        查询site 做种分布信息 大小，做种数
        :param data: {"name":site_name}
        :return:
        """
        if not data or "name" not in data:
            return {"code": 1, "msg": "查询参数错误"}

        resp = {"code": 0}

        seeding_info = Sites().get_pt_site_seeding_info(data["name"]).get("seeding_info", [])
        # 调整为dataset组织数据
        dataset = [["seeders", "size"]]
        dataset.extend(seeding_info)

        resp.update({"dataset": dataset})
        return resp

    def __add_filtergroup(self, data):
        """
        新增规则组
        """
        name = data.get("name")
        default = data.get("default")
        if not name:
            return {"code": -1}
        self.dbhelper.add_filter_group(name, default)
        Filter().init_config()
        return {"code": 0}

    def __restore_filtergroup(self, data):
        """
        恢复初始规则组
        """
        groupids = data.get("groupids")
        init_rulegroups = data.get("init_rulegroups")
        for groupid in groupids:
            try:
                self.dbhelper.delete_filtergroup(groupid)
            except Exception as err:
                ExceptionUtils.exception_traceback(err)
            for init_rulegroup in init_rulegroups:
                if str(init_rulegroup.get("id")) == groupid:
                    for sql in init_rulegroup.get("sql"):
                        self.dbhelper.excute(sql)
        Filter().init_config()
        return {"code": 0}

    def __set_default_filtergroup(self, data):
        groupid = data.get("id")
        if not groupid:
            return {"code": -1}
        self.dbhelper.set_default_filtergroup(groupid)
        Filter().init_config()
        return {"code": 0}

    def __del_filtergroup(self, data):
        groupid = data.get("id")
        self.dbhelper.delete_filtergroup(groupid)
        Filter().init_config()
        return {"code": 0}

    def __add_filterrule(self, data):
        rule_id = data.get("rule_id")
        item = {
            "group": data.get("group_id"),
            "name": data.get("rule_name"),
            "pri": data.get("rule_pri"),
            "include": data.get("rule_include"),
            "exclude": data.get("rule_exclude"),
            "size": data.get("rule_sizelimit"),
            "free": data.get("rule_free")
        }
        self.dbhelper.insert_filter_rule(ruleid=rule_id, item=item)
        Filter().init_config()
        return {"code": 0}

    def __del_filterrule(self, data):
        ruleid = data.get("id")
        self.dbhelper.delete_filterrule(ruleid)
        Filter().init_config()
        return {"code": 0}

    @staticmethod
    def __filterrule_detail(data):
        rid = data.get("ruleid")
        groupid = data.get("groupid")
        ruleinfo = Filter().get_rules(groupid=groupid, ruleid=rid)
        if ruleinfo:
            ruleinfo['include'] = "\n".join(ruleinfo.get("include"))
            ruleinfo['exclude'] = "\n".join(ruleinfo.get("exclude"))
        return {"code": 0, "info": ruleinfo}

    def get_recommend(self, data):
        Type = data.get("type")
        SubType = data.get("subtype")
        CurrentPage = data.get("page")
        if not CurrentPage:
            CurrentPage = 1
        else:
            CurrentPage = int(CurrentPage)

        if SubType == "hm":
            # TMDB热门电影
            res_list = Media().get_tmdb_hot_movies(CurrentPage)
        elif SubType == "ht":
            # TMDB热门电视剧
            res_list = Media().get_tmdb_hot_tvs(CurrentPage)
        elif SubType == "nm":
            # TMDB最新电影
            res_list = Media().get_tmdb_new_movies(CurrentPage)
        elif SubType == "nt":
            # TMDB最新电视剧
            res_list = Media().get_tmdb_new_tvs(CurrentPage)
        elif SubType == "dbom":
            # 豆瓣正在上映
            res_list = DouBan().get_douban_online_movie(CurrentPage)
        elif SubType == "dbhm":
            # 豆瓣热门电影
            res_list = DouBan().get_douban_hot_movie(CurrentPage)
        elif SubType == "dbht":
            # 豆瓣热门电视剧
            res_list = DouBan().get_douban_hot_tv(CurrentPage)
        elif SubType == "dbdh":
            # 豆瓣热门动画
            res_list = DouBan().get_douban_hot_anime(CurrentPage)
        elif SubType == "dbnm":
            # 豆瓣最新电影
            res_list = DouBan().get_douban_new_movie(CurrentPage)
        elif SubType == "dbtop":
            # 豆瓣TOP250电影
            res_list = DouBan().get_douban_top250_movie(CurrentPage)
        elif SubType == "dbzy":
            # 豆瓣最新电视剧
            res_list = DouBan().get_douban_hot_show(CurrentPage)
        elif SubType == "sim":
            TmdbId = data.get("tmdbid")
            res_list = self.__media_similar({
                "tmdbid": TmdbId,
                "page": CurrentPage,
                "type": "MOV" if Type == "MOV" else "TV"
            }).get("data")
        elif SubType == "more":
            TmdbId = data.get("tmdbid")
            res_list = self.__media_recommendations({
                "tmdbid": TmdbId,
                "page": CurrentPage,
                "type": "MOV" if Type == "MOV" else "TV"
            }).get("data")
        elif SubType == "person":
            PersonId = data.get("personid")
            res_list = self.__person_medias({
                "personid": PersonId,
                "type": "MOV" if Type == "MOV" else "TV",
                "page": CurrentPage
            }).get("data")
        elif Type == "BANGUMI":
            # Bangumi每日放送
            Week = data.get("week")
            res_list = Bangumi().get_bangumi_calendar(page=CurrentPage, week=Week)
        elif Type == "SEARCH":
            # 搜索词条
            Keyword = data.get("keyword")
            medias = WebUtils.search_media_infos(keyword=Keyword, page=CurrentPage)
            res_list = [media.to_dict() for media in medias]
        else:
            res_list = []
        # 修正数据
        filetransfer = FileTransfer()
        for res in res_list:
            fav, rssid = filetransfer.get_media_exists_flag(mtype=Type,
                                                            title=res.get("title"),
                                                            year=res.get("year"),
                                                            tmdbid=res.get("id"))
            res.update({
                'fav': fav,
                'rssid': rssid
            })
        return {"code": 0, "Items": res_list}

    def get_downloaded(self, data):
        page = data.get("page")
        Items = self.dbhelper.get_download_history(page=page)
        if Items:
            return {"code": 0, "Items": [item.as_dict() for item in Items]}
        else:
            return {"code": 0, "Items": []}

    @staticmethod
    def parse_brush_rule_string(rules: dict):
        if not rules:
            return ""
        rule_filter_string = {"gt": ">", "lt": "<", "bw": ""}
        rule_htmls = []
        if rules.get("size"):
            sizes = rules.get("size").split("#")
            if sizes[0]:
                if sizes[1]:
                    sizes[1] = sizes[1].replace(",", "-")
                rule_htmls.append(
                    '<span class="badge badge-outline text-blue me-1 mb-1" title="种子大小">种子大小: %s %sGB</span>'
                    % (rule_filter_string.get(sizes[0]), sizes[1]))
        if rules.get("pubdate"):
            pubdates = rules.get("pubdate").split("#")
            if pubdates[0]:
                if pubdates[1]:
                    pubdates[1] = pubdates[1].replace(",", "-")
                rule_htmls.append(
                    '<span class="badge badge-outline text-blue me-1 mb-1" title="发布时间">发布时间: %s %s小时</span>'
                    % (rule_filter_string.get(pubdates[0]), pubdates[1]))
        if rules.get("upspeed"):
            rule_htmls.append('<span class="badge badge-outline text-blue me-1 mb-1" title="上传限速">上传限速: %sB/s</span>'
                              % StringUtils.str_filesize(int(rules.get("upspeed")) * 1024))
        if rules.get("downspeed"):
            rule_htmls.append('<span class="badge badge-outline text-blue me-1 mb-1" title="下载限速">下载限速: %sB/s</span>'
                              % StringUtils.str_filesize(int(rules.get("downspeed")) * 1024))
        if rules.get("include"):
            rule_htmls.append(
                '<span class="badge badge-outline text-green me-1 mb-1 text-wrap text-start" title="包含规则">包含: %s</span>'
                % rules.get("include"))
        if rules.get("hr"):
            rule_htmls.append('<span class="badge badge-outline text-red me-1 mb-1" title="排除HR">排除: HR</span>')
        if rules.get("exclude"):
            rule_htmls.append(
                '<span class="badge badge-outline text-red me-1 mb-1 text-wrap text-start" title="排除规则">排除: %s</span>'
                % rules.get("exclude"))
        if rules.get("dlcount"):
            rule_htmls.append('<span class="badge badge-outline text-blue me-1 mb-1" title="同时下载数量限制">同时下载: %s</span>'
                              % rules.get("dlcount"))
        if rules.get("peercount"):
            peer_counts = None
            if rules.get("peercount") == "#":
                peer_counts = None
            elif "#" in rules.get("peercount"):
                peer_counts = rules.get("peercount").split("#")
                peer_counts[1] = peer_counts[1].replace(",", "-") if (len(peer_counts) >= 2 and peer_counts[1]) else \
                    peer_counts[1]
            else:
                try:
                    # 兼容性代码
                    peer_counts = ["lt", int(rules.get("peercount"))]
                except Exception as err:
                    ExceptionUtils.exception_traceback(err)
                    pass
            if peer_counts:
                rule_htmls.append(
                    '<span class="badge badge-outline text-blue me-1 mb-1" title="当前做种人数限制">做种人数: %s %s</span>'
                    % (rule_filter_string.get(peer_counts[0]), peer_counts[1]))
        if rules.get("time"):
            times = rules.get("time").split("#")
            if times[0]:
                rule_htmls.append(
                    '<span class="badge badge-outline text-orange me-1 mb-1" title="做种时间">做种时间: %s %s小时</span>'
                    % (rule_filter_string.get(times[0]), times[1]))
        if rules.get("ratio"):
            ratios = rules.get("ratio").split("#")
            if ratios[0]:
                rule_htmls.append(
                    '<span class="badge badge-outline text-orange me-1 mb-1" title="分享率">分享率: %s %s</span>'
                    % (rule_filter_string.get(ratios[0]), ratios[1]))
        if rules.get("uploadsize"):
            uploadsizes = rules.get("uploadsize").split("#")
            if uploadsizes[0]:
                rule_htmls.append(
                    '<span class="badge badge-outline text-orange me-1 mb-1" title="上传量">上传量: %s %sGB</span>'
                    % (rule_filter_string.get(uploadsizes[0]), uploadsizes[1]))
        if rules.get("dltime"):
            dltimes = rules.get("dltime").split("#")
            if dltimes[0]:
                rule_htmls.append(
                    '<span class="badge badge-outline text-orange me-1 mb-1" title="下载耗时">下载耗时: %s %s小时</span>'
                    % (rule_filter_string.get(dltimes[0]), dltimes[1]))
        if rules.get("avg_upspeed"):
            avg_upspeeds = rules.get("avg_upspeed").split("#")
            if avg_upspeeds[0]:
                rule_htmls.append(
                    '<span class="badge badge-outline text-orange me-1 mb-1" title="平均上传速度">平均上传速度: %s %sKB/S</span>'
                    % (rule_filter_string.get(avg_upspeeds[0]), avg_upspeeds[1]))

        return "<br>".join(rule_htmls)

    @staticmethod
    def __clear_tmdb_cache(data):
        """
        清空TMDB缓存
        """
        try:
            MetaHelper().clear_meta_data()
            os.remove(MetaHelper().get_meta_data_path())
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {"code": 0, "msg": str(e)}
        return {"code": 0}

    @staticmethod
    def __check_site_attr(data):
        """
        检查站点标识
        """
        site_attr = Sites().get_grapsite_conf(data.get("url"))
        site_free = site_2xfree = site_hr = False
        if site_attr.get("FREE"):
            site_free = True
        if site_attr.get("2XFREE"):
            site_2xfree = True
        if site_attr.get("HR"):
            site_hr = True
        return {"code": 0, "site_free": site_free, "site_2xfree": site_2xfree, "site_hr": site_hr}

    @staticmethod
    def __refresh_process(data):
        """
        刷新进度条
        """
        detail = ProgressHelper().get_process(data.get("type"))
        if detail:
            return {"code": 0, "value": detail.get("value"), "text": detail.get("text")}
        else:
            return {"code": 1, "value": 0, "text": "正在处理..."}

    @staticmethod
    def __restory_backup(data):
        """
        解压恢复备份文件
        """
        filename = data.get("file_name")
        if filename:
            config_path = Config().get_config_path()
            temp_path = Config().get_temp_path()
            file_path = os.path.join(temp_path, filename)
            try:
                shutil.unpack_archive(file_path, config_path, format='zip')
                return {"code": 0, "msg": ""}
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                return {"code": 1, "msg": str(e)}
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        return {"code": 1, "msg": "文件不存在"}

    @staticmethod
    def __start_mediasync(data):
        """
        开始媒体库同步
        """
        ThreadHelper().start_thread(MediaServer().sync_mediaserver, ())
        return {"code": 0}

    @staticmethod
    def __mediasync_state(data):
        """
        获取媒体库同步数据情况
        """
        status = MediaServer().get_mediasync_status()
        if not status:
            return {"code": 0, "text": "未同步"}
        else:
            return {"code": 0, "text": "电影：%s，电视剧：%s，同步时间：%s" %
                                       (status.get("movie_count"),
                                        status.get("tv_count"),
                                        status.get("time"))}

    @staticmethod
    def __get_tvseason_list(data):
        """
        获取剧集季列表
        """
        tmdbid = data.get("tmdbid")
        seasons = [
            {"text": "第%s季" % cn2an.an2cn(season.get("season_number"), mode='low'),
             "num": season.get("season_number")}
            for season in Media().get_tmdb_tv_seasons_byid(tmdbid=tmdbid)]
        return {"code": 0, "seasons": seasons}

    @staticmethod
    def __get_userrss_task(data):
        """
        获取自定义订阅详情
        """
        taskid = data.get("id")
        return {"code": 0, "detail": RssChecker().get_rsstask_info(taskid=taskid)}

    def __delete_userrss_task(self, data):
        """
        删除自定义订阅
        """
        if self.dbhelper.delete_userrss_task(data.get("id")):
            RssChecker().init_config()
            return {"code": 0}
        else:
            return {"code": 1}

    def __update_userrss_task(self, data):
        """
        新增或修改自定义订阅
        """
        uses = data.get("uses")
        params = {
            "id": data.get("id"),
            "name": data.get("name"),
            "address": data.get("address"),
            "parser": data.get("parser"),
            "interval": data.get("interval"),
            "uses": uses,
            "include": data.get("include"),
            "exclude": data.get("exclude"),
            "filter_rule": data.get("rule"),
            "state": data.get("state"),
            "save_path": data.get("save_path"),
            "download_setting": data.get("download_setting"),
        }
        if uses == "D":
            params.update({
                "recognization": data.get("recognization")
            })
        elif uses == "R":
            params.update({
                "over_edition": data.get("over_edition"),
                "sites": data.get("sites"),
                "filter_args": {
                    "restype": data.get("restype"),
                    "pix": data.get("pix"),
                    "team": data.get("team")
                }
            })
        else:
            return {"code": 1}
        if self.dbhelper.update_userrss_task(params):
            RssChecker().init_config()
            return {"code": 0}
        else:
            return {"code": 1}

    @staticmethod
    def __get_rssparser(data):
        """
        获取订阅解析器详情
        """
        pid = data.get("id")
        return {"code": 0, "detail": RssChecker().get_userrss_parser(pid=pid)}

    def __delete_rssparser(self, data):
        """
        删除订阅解析器
        """
        if self.dbhelper.delete_userrss_parser(data.get("id")):
            RssChecker().init_config()
            return {"code": 0}
        else:
            return {"code": 1}

    def __update_rssparser(self, data):
        """
        新增或更新订阅解析器
        """
        params = {
            "id": data.get("id"),
            "name": data.get("name"),
            "type": data.get("type"),
            "format": data.get("format"),
            "params": data.get("params")
        }
        if self.dbhelper.update_userrss_parser(params):
            RssChecker().init_config()
            return {"code": 0}
        else:
            return {"code": 1}

    @staticmethod
    def __run_userrss(data):
        RssChecker().check_task_rss(data.get("id"))
        return {"code": 0}

    @staticmethod
    def __run_brushtask(data):
        BrushTask().check_task_rss(data.get("id"))
        return {"code": 0}

    @staticmethod
    def __list_site_resources(data):
        resources = Indexer().list_builtin_resources(index_id=data.get("id"),
                                                     page=data.get("page"),
                                                     keyword=data.get("keyword"))
        if not resources:
            return {"code": 1, "msg": "获取站点资源出现错误，无法连接到站点！"}
        else:
            return {"code": 0, "data": resources}

    @staticmethod
    def __list_rss_articles(data):
        uses = RssChecker().get_rsstask_info(taskid=data.get("id")).get("uses")
        articles = RssChecker().get_rss_articles(data.get("id"))
        count = len(articles)
        if articles:
            return {"code": 0, "data": articles, "count": count, "uses": uses}
        else:
            return {"code": 1, "msg": "未获取到报文"}

    def __rss_article_test(self, data):
        taskid = data.get("taskid")
        title = data.get("title")
        if not taskid:
            return {"code": -1}
        if not title:
            return {"code": -1}
        media_info, match_flag, exist_flag = RssChecker().test_rss_articles(taskid=taskid, title=title)
        if not media_info:
            return {"code": 0, "data": {"name": "无法识别"}}
        media_dict = self.mediainfo_dict(media_info)
        media_dict.update({"match_flag": match_flag, "exist_flag": exist_flag})
        return {"code": 0, "data": media_dict}

    def __list_rss_history(self, data):
        downloads = []
        historys = self.dbhelper.get_userrss_task_history(data.get("id"))
        count = len(historys)
        for history in historys:
            params = {
                "title": history.TITLE,
                "downloader": history.DOWNLOADER,
                "date": history.DATE
            }
            downloads.append(params)
        if downloads:
            return {"code": 0, "data": downloads, "count": count}
        else:
            return {"code": 1, "msg": "无下载记录"}

    @staticmethod
    def __rss_articles_check(data):
        if not data.get("articles"):
            return {"code": 2}
        res = RssChecker().check_rss_articles(flag=data.get("flag"), articles=data.get("articles"))
        if res:
            return {"code": 0}
        else:
            return {"code": 1}

    @staticmethod
    def __rss_articles_download(data):
        if not data.get("articles"):
            return {"code": 2}
        res = RssChecker().download_rss_articles(taskid=data.get("taskid"), articles=data.get("articles"))
        if res:
            return {"code": 0}
        else:
            return {"code": 1}

    def __add_custom_word_group(self, data):
        try:
            tmdb_id = data.get("tmdb_id")
            tmdb_type = data.get("tmdb_type")
            if tmdb_type == "tv":
                if not self.dbhelper.is_custom_word_group_existed(tmdbid=tmdb_id, gtype=2):
                    tmdb_info = Media().get_tmdb_info(mtype=MediaType.TV, tmdbid=tmdb_id)
                    if not tmdb_info:
                        return {"code": 1, "msg": "添加失败，无法查询到TMDB信息"}
                    self.dbhelper.insert_custom_word_groups(title=tmdb_info.get("name"),
                                                            year=tmdb_info.get("first_air_date")[0:4],
                                                            gtype=2,
                                                            tmdbid=tmdb_id,
                                                            season_count=tmdb_info.get("number_of_seasons"))
                    return {"code": 0, "msg": ""}
                else:
                    return {"code": 1, "msg": "识别词组（TMDB ID）已存在"}
            elif tmdb_type == "movie":
                if not self.dbhelper.is_custom_word_group_existed(tmdbid=tmdb_id, gtype=1):
                    tmdb_info = Media().get_tmdb_info(mtype=MediaType.MOVIE, tmdbid=tmdb_id)
                    if not tmdb_info:
                        return {"code": 1, "msg": "添加失败，无法查询到TMDB信息"}
                    self.dbhelper.insert_custom_word_groups(title=tmdb_info.get("title"),
                                                            year=tmdb_info.get("release_date")[0:4],
                                                            gtype=1,
                                                            tmdbid=tmdb_id,
                                                            season_count=0)
                    return {"code": 0, "msg": ""}
                else:
                    return {"code": 1, "msg": "识别词组（TMDB ID）已存在"}
            else:
                return {"code": 1, "msg": "无法识别媒体类型"}
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {"code": 1, "msg": str(e)}

    def __delete_custom_word_group(self, data):
        try:
            gid = data.get("gid")
            self.dbhelper.delete_custom_word_group(gid=gid)
            WordsHelper().init_config()
            return {"code": 0, "msg": ""}
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {"code": 1, "msg": str(e)}

    def __add_or_edit_custom_word(self, data):
        try:
            wid = data.get("id")
            gid = data.get("gid")
            group_type = data.get("group_type")
            replaced = data.get("new_replaced")
            replace = data.get("new_replace")
            front = data.get("new_front")
            back = data.get("new_back")
            offset = data.get("new_offset")
            whelp = data.get("new_help")
            wtype = data.get("type")
            season = data.get("season")
            enabled = data.get("enabled")
            regex = data.get("regex")
            # 集数偏移格式检查
            if wtype in ["3", "4"]:
                if not re.findall(r'EP', offset):
                    return {"code": 1, "msg": "偏移集数格式有误"}
                if re.findall(r'(?!-|\+|\*|/|[0-9]).', re.sub(r'EP', "", offset)):
                    return {"code": 1, "msg": "偏移集数格式有误"}
            if wid:
                self.dbhelper.delete_custom_word(wid=wid)
            # 电影
            if group_type == "1":
                season = -2
            # 屏蔽
            if wtype == "1":
                if not self.dbhelper.is_custom_words_existed(replaced=replaced):
                    self.dbhelper.insert_custom_word(replaced=replaced,
                                                     replace="",
                                                     front="",
                                                     back="",
                                                     offset="",
                                                     wtype=wtype,
                                                     gid=gid,
                                                     season=season,
                                                     enabled=enabled,
                                                     regex=regex,
                                                     whelp=whelp if whelp else "")
                    WordsHelper().init_config()
                    return {"code": 0, "msg": ""}
                else:
                    return {"code": 1, "msg": "识别词已存在\n（被替换词：%s）" % replaced}
            # 替换
            elif wtype == "2":
                if not self.dbhelper.is_custom_words_existed(replaced=replaced):
                    self.dbhelper.insert_custom_word(replaced=replaced,
                                                     replace=replace,
                                                     front="",
                                                     back="",
                                                     offset="",
                                                     wtype=wtype,
                                                     gid=gid,
                                                     season=season,
                                                     enabled=enabled,
                                                     regex=regex,
                                                     whelp=whelp if whelp else "")
                    WordsHelper().init_config()
                    return {"code": 0, "msg": ""}
                else:
                    return {"code": 1, "msg": "识别词已存在\n（被替换词：%s）" % replaced}
            # 集偏移
            elif wtype == "4":
                if not self.dbhelper.is_custom_words_existed(front=front, back=back):
                    self.dbhelper.insert_custom_word(replaced="",
                                                     replace="",
                                                     front=front,
                                                     back=back,
                                                     offset=offset,
                                                     wtype=wtype,
                                                     gid=gid,
                                                     season=season,
                                                     enabled=enabled,
                                                     regex=regex,
                                                     whelp=whelp if whelp else "")
                    WordsHelper().init_config()
                    return {"code": 0, "msg": ""}
                else:
                    return {"code": 1, "msg": "识别词已存在\n（前后定位词：%s@%s）" % (front, back)}
            # 替换+集偏移
            elif wtype == "3":
                if not self.dbhelper.is_custom_words_existed(replaced=replaced):
                    self.dbhelper.insert_custom_word(replaced=replaced,
                                                     replace=replace,
                                                     front=front,
                                                     back=back,
                                                     offset=offset,
                                                     wtype=wtype,
                                                     gid=gid,
                                                     season=season,
                                                     enabled=enabled,
                                                     regex=regex,
                                                     whelp=whelp if whelp else "")
                    WordsHelper().init_config()
                    return {"code": 0, "msg": ""}
                else:
                    return {"code": 1, "msg": "识别词已存在\n（被替换词：%s）" % replaced}
            else:
                return {"code": 1, "msg": ""}
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {"code": 1, "msg": str(e)}

    def __get_custom_word(self, data):
        try:
            wid = data.get("wid")
            word_info = self.dbhelper.get_custom_words(wid=wid)
            if word_info:
                word_info = word_info[0]
                word = {"id": word_info.ID,
                        "replaced": word_info.REPLACED,
                        "replace": word_info.REPLACE,
                        "front": word_info.FRONT,
                        "back": word_info.BACK,
                        "offset": word_info.OFFSET,
                        "type": word_info.TYPE,
                        "group_id": word_info.GROUP_ID,
                        "season": word_info.SEASON,
                        "enabled": word_info.ENABLED,
                        "regex": word_info.REGEX,
                        "help": word_info.HELP, }
            else:
                word = {}
            return {"code": 0, "data": word}
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {"code": 1, "msg": "查询识别词失败"}

    def __delete_custom_word(self, data):
        try:
            wid = data.get("id")
            self.dbhelper.delete_custom_word(wid)
            WordsHelper().init_config()
            return {"code": 0, "msg": ""}
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {"code": 1, "msg": str(e)}

    def __check_custom_words(self, data):
        try:
            flag_dict = {"enable": 1, "disable": 0}
            ids_info = data.get("ids_info")
            enabled = flag_dict.get(data.get("flag"))
            ids = [id_info.split("_")[1] for id_info in ids_info]
            for wid in ids:
                self.dbhelper.check_custom_word(wid=wid, enabled=enabled)
            WordsHelper().init_config()
            return {"code": 0, "msg": ""}
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {"code": 1, "msg": "识别词状态设置失败"}

    def __export_custom_words(self, data):
        try:
            note = data.get("note")
            ids_info = data.get("ids_info").split("@")
            group_ids = []
            word_ids = []
            for id_info in ids_info:
                wid = id_info.split("_")
                group_ids.append(wid[0])
                word_ids.append(wid[1])
            export_dict = {}
            for group_id in group_ids:
                if group_id == "-1":
                    export_dict["-1"] = {"id": -1,
                                         "title": "通用",
                                         "type": 1,
                                         "words": {}, }
                else:
                    group_info = self.dbhelper.get_custom_word_groups(gid=group_id)
                    if group_info:
                        group_info = group_info[0]
                        export_dict[str(group_info.ID)] = {"id": group_info.ID,
                                                           "title": group_info.TITLE,
                                                           "year": group_info.YEAR,
                                                           "type": group_info.TYPE,
                                                           "tmdbid": group_info.TMDBID,
                                                           "season_count": group_info.SEASON_COUNT,
                                                           "words": {}, }
            for word_id in word_ids:
                word_info = self.dbhelper.get_custom_words(wid=word_id)
                if word_info:
                    word_info = word_info[0]
                    export_dict[str(word_info.GROUP_ID)]["words"][str(word_info.ID)] = {"id": word_info.ID,
                                                                                        "replaced": word_info.REPLACED,
                                                                                        "replace": word_info.REPLACE,
                                                                                        "front": word_info.FRONT,
                                                                                        "back": word_info.BACK,
                                                                                        "offset": word_info.OFFSET,
                                                                                        "type": word_info.TYPE,
                                                                                        "season": word_info.SEASON,
                                                                                        "regex": word_info.REGEX,
                                                                                        "help": word_info.HELP, }
            export_string = json.dumps(export_dict) + "@@@@@@" + str(note)
            string = base64.b64encode(export_string.encode("utf-8")).decode('utf-8')
            return {"code": 0, "string": string}
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {"code": 1, "msg": str(e)}

    @staticmethod
    def __analyse_import_custom_words_code(data):
        try:
            import_code = data.get('import_code')
            string = base64.b64decode(import_code.encode("utf-8")).decode('utf-8').split("@@@@@@")
            note_string = string[1]
            import_dict = json.loads(string[0])
            groups = []
            for group in import_dict.values():
                wid = group.get('id')
                title = group.get("title")
                year = group.get("year")
                wtype = group.get("type")
                tmdbid = group.get("tmdbid")
                season_count = group.get("season_count") or ""
                words = group.get("words")
                if tmdbid:
                    link = "https://www.themoviedb.org/%s/%s" % ("movie" if int(wtype) == 1 else "tv", tmdbid)
                else:
                    link = ""
                groups.append({"id": wid,
                               "name": "%s（%s）" % (title, year) if year else title,
                               "link": link,
                               "type": wtype,
                               "seasons": season_count,
                               "words": words})
            return {"code": 0, "groups": groups, "note_string": note_string}
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {"code": 1, "msg": str(e)}

    def __import_custom_words(self, data):
        try:
            import_code = data.get('import_code')
            ids_info = data.get('ids_info')
            string = base64.b64decode(import_code.encode("utf-8")).decode('utf-8').split("@@@@@@")
            import_dict = json.loads(string[0])
            import_group_ids = [id_info.split("_")[0] for id_info in ids_info]
            group_id_dict = {}
            for import_group_id in import_group_ids:
                import_group_info = import_dict.get(import_group_id)
                if int(import_group_info.get("id")) == -1:
                    group_id_dict["-1"] = -1
                    continue
                title = import_group_info.get("title")
                year = import_group_info.get("year")
                gtype = import_group_info.get("type")
                tmdbid = import_group_info.get("tmdbid")
                season_count = import_group_info.get("season_count")
                if not self.dbhelper.is_custom_word_group_existed(tmdbid=tmdbid, gtype=gtype):
                    self.dbhelper.insert_custom_word_groups(title=title,
                                                            year=year,
                                                            gtype=gtype,
                                                            tmdbid=tmdbid,
                                                            season_count=season_count)
                group_info = self.dbhelper.get_custom_word_groups(tmdbid=tmdbid, gtype=gtype)
                if group_info:
                    group_id_dict[import_group_id] = group_info[0].ID
            for id_info in ids_info:
                id_info = id_info.split('_')
                import_group_id = id_info[0]
                import_word_id = id_info[1]
                import_word_info = import_dict.get(import_group_id).get("words").get(import_word_id)
                gid = group_id_dict.get(import_group_id)
                replaced = import_word_info.get("replaced")
                replace = import_word_info.get("replace")
                front = import_word_info.get("front")
                back = import_word_info.get("back")
                offset = import_word_info.get("offset")
                whelp = import_word_info.get("help")
                wtype = int(import_word_info.get("type"))
                season = import_word_info.get("season")
                regex = import_word_info.get("regex")
                # 屏蔽, 替换, 替换+集偏移
                if wtype in [1, 2, 3]:
                    if self.dbhelper.is_custom_words_existed(replaced=replaced):
                        return {"code": 1, "msg": "识别词已存在\n（被替换词：%s）" % replaced}
                # 集偏移
                elif wtype == 4:
                    if self.dbhelper.is_custom_words_existed(front=front, back=back):
                        return {"code": 1, "msg": "识别词已存在\n（前后定位词：%s@%s）" % (front, back)}
                self.dbhelper.insert_custom_word(replaced=replaced,
                                                 replace=replace,
                                                 front=front,
                                                 back=back,
                                                 offset=offset,
                                                 wtype=wtype,
                                                 gid=gid,
                                                 season=season,
                                                 enabled=1,
                                                 regex=regex,
                                                 whelp=whelp if whelp else "")
            WordsHelper().init_config()
            return {"code": 0, "msg": ""}
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {"code": 1, "msg": str(e)}

    @staticmethod
    def __get_categories(data):
        if data.get("type") == "电影":
            categories = Category().get_movie_categorys()
        elif data.get("type") == "电视剧":
            categories = Category().get_tv_categorys()
        else:
            categories = Category().get_anime_categorys()
        return {"code": 0, "category": list(categories), "id": data.get("id"), "value": data.get("value")}

    def __delete_rss_history(self, data):
        rssid = data.get("rssid")
        self.dbhelper.delete_rss_history(rssid=rssid)
        return {"code": 0}

    def __re_rss_history(self, data):
        rssid = data.get("rssid")
        rtype = data.get("type")
        rssinfo = self.dbhelper.get_rss_history(rtype=rtype, rid=rssid)
        if rssinfo:
            if rtype == "MOV":
                mtype = MediaType.MOVIE
            else:
                mtype = MediaType.TV
            if rssinfo[0].SEASON:
                season = int(str(rssinfo[0].SEASON).replace("S", ""))
            else:
                season = None
            code, msg, _ = Subscribe().add_rss_subscribe(mtype=mtype,
                                                         name=rssinfo[0].NAME,
                                                         year=rssinfo[0].YEAR,
                                                         season=season,
                                                         mediaid=rssinfo[0].TMDBID,
                                                         total_ep=rssinfo[0].TOTAL,
                                                         current_ep=rssinfo[0].START)
            return {"code": code, "msg": msg}
        else:
            return {"code": 1, "msg": "订阅历史记录不存在"}

    def __share_filtergroup(self, data):
        gid = data.get("id")
        group_info = self.dbhelper.get_config_filter_group(gid=gid)
        if not group_info:
            return {"code": 1, "msg": "规则组不存在"}
        group_rules = self.dbhelper.get_config_filter_rule(groupid=gid)
        if not group_rules:
            return {"code": 1, "msg": "规则组没有对应规则"}
        rules = []
        for rule in group_rules:
            rules.append({
                "name": rule.ROLE_NAME,
                "pri": rule.PRIORITY,
                "include": rule.INCLUDE,
                "exclude": rule.EXCLUDE,
                "size": rule.SIZE_LIMIT,
                "free": rule.NOTE
            })
        rule_json = {
            "name": group_info[0].GROUP_NAME,
            "rules": rules
        }
        json_string = base64.b64encode(json.dumps(rule_json).encode("utf-8")).decode('utf-8')
        return {"code": 0, "string": json_string}

    def __import_filtergroup(self, data):
        content = data.get("content")
        try:
            json_str = base64.b64decode(str(content).encode("utf-8")).decode('utf-8')
            json_obj = json.loads(json_str)
            if json_obj:
                if not json_obj.get("name"):
                    return {"code": 1, "msg": "数据格式不正确"}
                self.dbhelper.add_filter_group(name=json_obj.get("name"))
                group_id = self.dbhelper.get_filter_groupid_by_name(json_obj.get("name"))
                if not group_id:
                    return {"code": 1, "msg": "数据内容不正确"}
                if json_obj.get("rules"):
                    for rule in json_obj.get("rules"):
                        self.dbhelper.insert_filter_rule(item={
                            "group": group_id,
                            "name": rule.get("name"),
                            "pri": rule.get("pri"),
                            "include": rule.get("include"),
                            "exclude": rule.get("exclude"),
                            "size": rule.get("size"),
                            "free": rule.get("free")
                        })
                Filter().init_config()
            return {"code": 0, "msg": ""}
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return {"code": 1, "msg": "数据格式不正确，%s" % str(err)}

    @staticmethod
    def get_library_spacesize(data=None):
        """
        查询媒体库存储空间
        """
        # 磁盘空间
        UsedPercent = 0
        TotalSpaceList = []
        media = Config().get_config('media')
        if media:
            # 电影目录
            movie_paths = media.get('movie_path')
            if not isinstance(movie_paths, list):
                movie_paths = [movie_paths]
            movie_used, movie_total = 0, 0
            for movie_path in movie_paths:
                if not movie_path:
                    continue
                used, total = SystemUtils.get_used_of_partition(movie_path)
                if "%s-%s" % (used, total) not in TotalSpaceList:
                    TotalSpaceList.append("%s-%s" % (used, total))
                    movie_used += used
                    movie_total += total
            # 电视目录
            tv_paths = media.get('tv_path')
            if not isinstance(tv_paths, list):
                tv_paths = [tv_paths]
            tv_used, tv_total = 0, 0
            for tv_path in tv_paths:
                if not tv_path:
                    continue
                used, total = SystemUtils.get_used_of_partition(tv_path)
                if "%s-%s" % (used, total) not in TotalSpaceList:
                    TotalSpaceList.append("%s-%s" % (used, total))
                    tv_used += used
                    tv_total += total
            # 动漫目录
            anime_paths = media.get('anime_path')
            if not isinstance(anime_paths, list):
                anime_paths = [anime_paths]
            anime_used, anime_total = 0, 0
            for anime_path in anime_paths:
                if not anime_path:
                    continue
                used, total = SystemUtils.get_used_of_partition(anime_path)
                if "%s-%s" % (used, total) not in TotalSpaceList:
                    TotalSpaceList.append("%s-%s" % (used, total))
                    anime_used += used
                    anime_total += total
            # 总空间
            TotalSpaceAry = []
            if movie_total not in TotalSpaceAry:
                TotalSpaceAry.append(movie_total)
            if tv_total not in TotalSpaceAry:
                TotalSpaceAry.append(tv_total)
            if anime_total not in TotalSpaceAry:
                TotalSpaceAry.append(anime_total)
            TotalSpace = sum(TotalSpaceAry)
            # 已使用空间
            UsedSapceAry = []
            if movie_used not in UsedSapceAry:
                UsedSapceAry.append(movie_used)
            if tv_used not in UsedSapceAry:
                UsedSapceAry.append(tv_used)
            if anime_used not in UsedSapceAry:
                UsedSapceAry.append(anime_used)
            UsedSapce = sum(UsedSapceAry)
            # 电影电视使用百分比格式化
            if TotalSpace:
                UsedPercent = "%0.1f" % ((UsedSapce / TotalSpace) * 100)
            # 总剩余空间 格式化
            FreeSpace = "{:,} TB".format(round((TotalSpace - UsedSapce) / 1024 / 1024 / 1024 / 1024, 2))
            # 总使用空间 格式化
            UsedSapce = "{:,} TB".format(round(UsedSapce / 1024 / 1024 / 1024 / 1024, 2))
            # 总空间 格式化
            TotalSpace = "{:,} TB".format(round(TotalSpace / 1024 / 1024 / 1024 / 1024, 2))

            return {"code": 0,
                    "UsedPercent": UsedPercent,
                    "FreeSpace": FreeSpace,
                    "UsedSapce": UsedSapce,
                    "TotalSpace": TotalSpace}

    def get_transfer_statistics(self, data=None):
        """
        查询转移历史统计数据
        """
        MovieChartLabels = []
        MovieNums = []
        TvChartData = {}
        TvNums = []
        AnimeNums = []
        for statistic in self.dbhelper.get_transfer_statistics():
            if statistic[0] == "电影":
                MovieChartLabels.append(statistic[1])
                MovieNums.append(statistic[2])
            else:
                if not TvChartData.get(statistic[1]):
                    TvChartData[statistic[1]] = {"tv": 0, "anime": 0}
                if statistic[0] == "电视剧":
                    TvChartData[statistic[1]]["tv"] += statistic[2]
                elif statistic[0] == "动漫":
                    TvChartData[statistic[1]]["anime"] += statistic[2]
        TvChartLabels = list(TvChartData)
        for tv_data in TvChartData.values():
            TvNums.append(tv_data.get("tv"))
            AnimeNums.append(tv_data.get("anime"))

        return {
            "code": 0,
            "MovieChartLabels": MovieChartLabels,
            "MovieNums": MovieNums,
            "TvChartLabels": TvChartLabels,
            "TvNums": TvNums,
            "AnimeNums": AnimeNums
        }

    @staticmethod
    def get_library_mediacount(data=None):
        """
        查询媒体库统计数据
        """
        MediaServerClient = MediaServer()
        media_counts = MediaServerClient.get_medias_count()
        UserCount = MediaServerClient.get_user_count()
        if media_counts:
            return {
                "code": 0,
                "Movie": "{:,}".format(media_counts.get('MovieCount')),
                "Series": "{:,}".format(media_counts.get('SeriesCount')),
                "Episodes": "{:,}".format(media_counts.get('EpisodeCount')) if media_counts.get(
                    'EpisodeCount') else "",
                "Music": "{:,}".format(media_counts.get('SongCount')),
                "User": UserCount
            }
        else:
            return {"code": -1, "msg": "媒体库服务器连接失败"}

    @staticmethod
    def get_library_playhistory(data=None):
        """
        查询媒体库播放记录
        """
        return {"code": 0, "result": MediaServer().get_activity_log(30)}

    def get_search_result(self, data=None):
        """
        查询所有搜索结果
        """
        SearchResults = {}
        res = self.dbhelper.get_search_results()
        total = len(res)
        for item in res:
            # 质量(来源、效果)、分辨率
            if item.RES_TYPE:
                try:
                    res_mix = json.loads(item.RES_TYPE)
                except Exception as err:
                    ExceptionUtils.exception_traceback(err)
                    continue
                respix = res_mix.get("respix") or ""
                video_encode = res_mix.get("video_encode") or ""
                restype = res_mix.get("restype") or ""
                reseffect = res_mix.get("reseffect") or ""
            else:
                restype = ""
                respix = ""
                reseffect = ""
                video_encode = ""
            # 分组标识 (来源，分辨率)
            group_key = re.sub(r"[-.\s@|]", "", f"{respix}_{restype}").lower()
            # 分组信息
            group_info = {
                "respix": respix,
                "restype": restype,
            }
            # 种子唯一标识 （大小，质量(来源、效果)，制作组组成）
            unique_key = re.sub(r"[-.\s@|]", "",
                                f"{respix}_{restype}_{video_encode}_{reseffect}_{item.SIZE}_{item.OTHERINFO}").lower()
            # 标识信息
            unique_info = {
                "video_encode": video_encode,
                "size": item.SIZE,
                "reseffect": reseffect,
                "releasegroup": item.OTHERINFO
            }
            # 结果
            title_string = f"{item.TITLE}"
            if item.YEAR:
                title_string = f"{title_string} ({item.YEAR})"
            # 电视剧季集标识
            mtype = item.TYPE or ""
            SE_key = item.ES_STRING or "TV" if mtype != "MOV" else "MOV"
            media_type = {"MOV": "电影", "TV": "电视剧", "ANI": "动漫"}.get(mtype)
            # 种子信息
            torrent_item = {
                "id": item.ID,
                "seeders": item.SEEDERS,
                "enclosure": item.ENCLOSURE,
                "site": item.SITE,
                "torrent_name": item.TORRENT_NAME,
                "description": item.DESCRIPTION,
                "pageurl": item.PAGEURL,
                "uploadvalue": item.UPLOAD_VOLUME_FACTOR,
                "downloadvalue": item.DOWNLOAD_VOLUME_FACTOR,
                "size": item.SIZE,
                "respix": respix,
                "restype": restype,
                "reseffect": reseffect,
                "releasegroup": item.OTHERINFO,
                "video_encode": video_encode
            }
            # 促销
            free_item = {
                "value": f"{item.UPLOAD_VOLUME_FACTOR} {item.DOWNLOAD_VOLUME_FACTOR}",
                "name": MetaBase.get_free_string(item.UPLOAD_VOLUME_FACTOR, item.DOWNLOAD_VOLUME_FACTOR)
            }
            # 季
            filter_season = SE_key.split()[0] if SE_key and SE_key not in ["MOV", "TV"] else None
            # 合并搜索结果
            if SearchResults.get(title_string):
                # 种子列表
                result_item = SearchResults[title_string]
                torrent_dict = SearchResults[title_string].get("torrent_dict")
                SE_dict = torrent_dict.get(SE_key)
                if SE_dict:
                    group = SE_dict.get(group_key)
                    if group:
                        unique = group.get("group_torrents").get(unique_key)
                        if unique:
                            unique["torrent_list"].append(torrent_item)
                            group["group_total"] += 1
                        else:
                            group["group_total"] += 1
                            group.get("group_torrents")[unique_key] = {
                                "unique_info": unique_info,
                                "torrent_list": [torrent_item]
                            }
                    else:
                        SE_dict[group_key] = {
                            "group_info": group_info,
                            "group_total": 1,
                            "group_torrents": {
                                unique_key: {
                                    "unique_info": unique_info,
                                    "torrent_list": [torrent_item]
                                }
                            }
                        }
                else:
                    torrent_dict[SE_key] = {
                        group_key: {
                            "group_info": group_info,
                            "group_total": 1,
                            "group_torrents": {
                                unique_key: {
                                    "unique_info": unique_info,
                                    "torrent_list": [torrent_item]
                                }
                            }
                        }
                    }
                # 过滤条件
                torrent_filter = dict(result_item.get("filter"))
                if free_item not in torrent_filter.get("free"):
                    torrent_filter["free"].append(free_item)
                if item.SITE not in torrent_filter.get("site"):
                    torrent_filter["site"].append(item.SITE)
                if video_encode \
                        and video_encode not in torrent_filter.get("video"):
                    torrent_filter["video"].append(video_encode)
                if filter_season \
                        and filter_season not in torrent_filter.get("season"):
                    torrent_filter["season"].append(filter_season)
            else:
                # 是否已存在
                if item.TMDBID:
                    exist_flag = MediaServer().check_item_exists(title=item.TITLE, year=item.YEAR, tmdbid=item.TMDBID)
                else:
                    exist_flag = False
                SearchResults[title_string] = {
                    "key": item.ID,
                    "title": item.TITLE,
                    "year": item.YEAR,
                    "type_key": mtype,
                    "image": item.IMAGE,
                    "type": media_type,
                    "vote": item.VOTE,
                    "tmdbid": item.TMDBID,
                    "backdrop": item.IMAGE,
                    "poster": item.POSTER,
                    "overview": item.OVERVIEW,
                    "exist": exist_flag,
                    "torrent_dict": {
                        SE_key: {
                            group_key: {
                                "group_info": group_info,
                                "group_total": 1,
                                "group_torrents": {
                                    unique_key: {
                                        "unique_info": unique_info,
                                        "torrent_list": [torrent_item]
                                    }
                                }
                            }
                        }
                    },
                    "filter": {
                        "site": [item.SITE],
                        "free": [free_item],
                        "video": [video_encode] if video_encode else [],
                        "season": [filter_season] if filter_season else []
                    }
                }

        # 提升整季的顺序到顶层
        def se_sort(k):
            k = re.sub(r" +|(?<=s\d)\D*?(?=e)|(?<=s\d\d)\D*?(?=e)", " ", k[0], flags=re.I).split()
            return (k[0], k[1]) if len(k) > 1 else ("Z" + k[0], "ZZZ")

        # 开始排序季集顺序
        for title, item in SearchResults.items():
            # 排序筛选器 季
            item["filter"]["season"].sort(reverse=True)
            # 排序种子列 集
            item["torrent_dict"] = sorted(item["torrent_dict"].items(),
                                          key=se_sort,
                                          reverse=True)
        return {"code": 0, "total": total, "result": SearchResults}

    @staticmethod
    def search_media_infos(data):
        """
        根据关键字搜索相似词条
        """
        SearchWord = data.get("keyword")
        if not SearchWord:
            return []
        SearchSourceType = data.get("searchtype")
        medias = WebUtils.search_media_infos(keyword=SearchWord,
                                             source=SearchSourceType)

        return {"code": 0, "result": [media.to_dict() for media in medias]}

    @staticmethod
    def get_movie_rss_list(data=None):
        """
        查询所有电影订阅
        """
        return {"code": 0, "result": Subscribe().get_subscribe_movies()}

    @staticmethod
    def get_tv_rss_list(data=None):
        """
        查询所有电视剧订阅
        """
        return {"code": 0, "result": Subscribe().get_subscribe_tvs()}

    def get_rss_history(self, data):
        """
        查询所有订阅历史
        """
        mtype = data.get("type")
        return {"code": 0, "result": [rec.as_dict() for rec in self.dbhelper.get_rss_history(rtype=mtype)]}

    @staticmethod
    def get_downloading(data=None):
        """
        查询正在下载的任务
        """
        torrents = Downloader().get_downloading_progress()
        MediaHander = Media()
        for torrent in torrents:
            # 识别
            media_info = MediaHander.get_media_info(title=torrent.get("name"))
            if not media_info:
                continue
            if not media_info.tmdb_info:
                year = media_info.year
                if year:
                    title = "%s (%s) %s" % (media_info.get_name(), year, media_info.get_season_episode_string())
                else:
                    title = "%s %s" % (media_info.get_name(), media_info.get_season_episode_string())
            else:
                title = "%s %s" % (media_info.get_title_string(), media_info.get_season_episode_string())
            poster_path = media_info.get_poster_image()
            torrent.update({
                "title": title,
                "image": poster_path or ""
            })
        return {"code": 0, "result": torrents}

    def get_transfer_history(self, data):
        """
        查询媒体整理历史记录
        """
        PageNum = data.get("pagenum")
        if not PageNum:
            PageNum = 30
        SearchStr = data.get("keyword")
        CurrentPage = data.get("page")
        if not CurrentPage:
            CurrentPage = 1
        else:
            CurrentPage = int(CurrentPage)
        totalCount, historys = self.dbhelper.get_transfer_history(SearchStr, CurrentPage, PageNum)
        historys_list = []
        for history in historys:
            history = history.as_dict()
            sync_mode = history.get("MODE")
            rmt_mode = ModuleConf.get_dictenum_key(ModuleConf.RMT_MODES, sync_mode) if sync_mode else ""
            history.update({
                "SYNC_MODE": sync_mode,
                "RMT_MODE": rmt_mode
            })
            historys_list.append(history)
        TotalPage = floor(totalCount / PageNum) + 1

        return {
            "code": 0,
            "total": totalCount,
            "result": historys_list,
            "totalPage": TotalPage,
            "pageNum": PageNum,
            "currentPage": CurrentPage
        }

    def get_unknown_list(self, data=None):
        """
        查询所有未识别记录
        """
        Items = []
        Records = self.dbhelper.get_transfer_unknown_paths()
        for rec in Records:
            if not rec.PATH:
                continue
            path = rec.PATH.replace("\\", "/") if rec.PATH else ""
            path_to = rec.DEST.replace("\\", "/") if rec.DEST else ""
            sync_mode = rec.MODE or ""
            rmt_mode = ModuleConf.get_dictenum_key(ModuleConf.RMT_MODES,
                                                   sync_mode) if sync_mode else ""
            Items.append({
                "id": rec.ID,
                "path": path,
                "to": path_to,
                "name": path,
                "sync_mode": sync_mode,
                "rmt_mode": rmt_mode,
            })

        return {"code": 0, "items": Items}

    def get_customwords(self, data=None):
        words = []
        words_info = self.dbhelper.get_custom_words(gid=-1)
        for word_info in words_info:
            words.append({"id": word_info.ID,
                          "replaced": word_info.REPLACED,
                          "replace": word_info.REPLACE,
                          "front": word_info.FRONT,
                          "back": word_info.BACK,
                          "offset": word_info.OFFSET,
                          "type": word_info.TYPE,
                          "group_id": word_info.GROUP_ID,
                          "season": word_info.SEASON,
                          "enabled": word_info.ENABLED,
                          "regex": word_info.REGEX,
                          "help": word_info.HELP, })
        groups = [{"id": "-1",
                   "name": "通用",
                   "link": "",
                   "type": "1",
                   "seasons": "0",
                   "words": words}]
        groups_info = self.dbhelper.get_custom_word_groups()
        for group_info in groups_info:
            gid = group_info.ID
            name = "%s (%s)" % (group_info.TITLE, group_info.YEAR)
            gtype = group_info.TYPE
            if gtype == 1:
                link = "https://www.themoviedb.org/movie/%s" % group_info.TMDBID
            else:
                link = "https://www.themoviedb.org/tv/%s" % group_info.TMDBID
            words = []
            words_info = self.dbhelper.get_custom_words(gid=gid)
            for word_info in words_info:
                words.append({"id": word_info.ID,
                              "replaced": word_info.REPLACED,
                              "replace": word_info.REPLACE,
                              "front": word_info.FRONT,
                              "back": word_info.BACK,
                              "offset": word_info.OFFSET,
                              "type": word_info.TYPE,
                              "group_id": word_info.GROUP_ID,
                              "season": word_info.SEASON,
                              "enabled": word_info.ENABLED,
                              "regex": word_info.REGEX,
                              "help": word_info.HELP, })
            groups.append({"id": gid,
                           "name": name,
                           "link": link,
                           "type": group_info.TYPE,
                           "seasons": group_info.SEASON_COUNT,
                           "words": words})
        return {
            "code": 0,
            "result": groups
        }

    def get_directorysync(self, data=None):
        """
        查询所有同步目录
        """
        sync_paths = self.dbhelper.get_config_sync_paths()
        SyncPaths = []
        if sync_paths:
            for sync_item in sync_paths:
                SyncPath = {'id': sync_item.ID,
                            'from': sync_item.SOURCE,
                            'to': sync_item.DEST or "",
                            'unknown': sync_item.UNKNOWN or "",
                            'syncmod': sync_item.MODE,
                            'syncmod_name': RmtMode[sync_item.MODE.upper()].value,
                            'rename': sync_item.RENAME,
                            'enabled': sync_item.ENABLED}
                SyncPaths.append(SyncPath)
        SyncPaths = sorted(SyncPaths, key=lambda o: o.get("from"))
        return {"code": 0, "result": SyncPaths}

    def get_users(self, data=None):
        """
        查询所有用户
        """
        user_list = self.dbhelper.get_users()
        Users = []
        for user in user_list:
            pris = str(user.PRIS).split(",")
            Users.append({"id": user.ID, "name": user.NAME, "pris": pris})
        return {"code": 0, "result": Users}

    @staticmethod
    def get_filterrules(data=None):
        """
        查询所有过滤规则
        """
        RuleGroups = Filter().get_rule_infos()
        sql_file = os.path.join(Config().get_root_path(), "config", "init_filter.sql")
        with open(sql_file, "r", encoding="utf-8") as f:
            sql_list = f.read().split(';\n')
            Init_RuleGroups = []
            i = 0
            while i < len(sql_list):
                rulegroup = {}
                rulegroup_info = re.findall(r"[0-9]+,'[^\"]+NULL", sql_list[i], re.I)[0].split(",")
                rulegroup['id'] = int(rulegroup_info[0])
                rulegroup['name'] = rulegroup_info[1][1:-1]
                rulegroup['rules'] = []
                rulegroup['sql'] = [sql_list[i]]
                if i + 1 < len(sql_list):
                    rules = re.findall(r"[0-9]+,'[^\"]+NULL", sql_list[i + 1], re.I)[0].split("),\n (")
                    for rule in rules:
                        rule_info = {}
                        rule = rule.split(",")
                        rule_info['name'] = rule[2][1:-1]
                        rule_info['include'] = rule[4][1:-1]
                        rule_info['exclude'] = rule[5][1:-1]
                        rulegroup['rules'].append(rule_info)
                    rulegroup["sql"].append(sql_list[i + 1])
                Init_RuleGroups.append(rulegroup)
                i = i + 2
        return {
            "code": 0,
            "ruleGroups": RuleGroups,
            "initRules": Init_RuleGroups
        }

    def __update_directory(self, data):
        """
        维护媒体库目录
        """
        cfg = self.set_config_directory(Config().get_config(),
                                        data.get("oper"),
                                        data.get("key"),
                                        data.get("value"),
                                        data.get("replace_value"))
        # 保存配置
        Config().save_config(cfg)
        return {"code": 0}

    @staticmethod
    def __test_site(data):
        """
        测试站点连通性
        """
        flag, msg, times = Sites().test_connection(data.get("id"))
        code = 0 if flag else -1
        return {"code": code, "msg": msg, "time": times}

    @staticmethod
    def __get_sub_path(data):
        """
        查询下级子目录
        """
        r = []
        try:
            ft = data.get("filter") or "ALL"
            d = data.get("dir")
            if not d or d == "/":
                if SystemUtils.get_system() == OsType.WINDOWS:
                    partitions = SystemUtils.get_windows_drives()
                    if partitions:
                        dirs = [os.path.join(partition, "/") for partition in partitions]
                    else:
                        dirs = [os.path.join("C:/", f) for f in os.listdir("C:/")]
                else:
                    dirs = [os.path.join("/", f) for f in os.listdir("/")]
            else:
                d = os.path.normpath(unquote(d))
                if not os.path.isdir(d):
                    d = os.path.dirname(d)
                dirs = [os.path.join(d, f) for f in os.listdir(d)]
            dirs.sort()
            for ff in dirs:
                if os.path.isdir(ff):
                    if 'ONLYDIR' in ft or 'ALL' in ft:
                        r.append({
                            "path": ff.replace("\\", "/"),
                            "name": os.path.basename(ff),
                            "type": "dir",
                            "rel": os.path.dirname(ff).replace("\\", "/")
                        })
                else:
                    ext = os.path.splitext(ff)[-1][1:]
                    flag = False
                    if 'ONLYFILE' in ft or 'ALL' in ft:
                        flag = True
                    elif "MEDIAFILE" in ft and f".{str(ext).lower()}" in RMT_MEDIAEXT:
                        flag = True
                    elif "SUBFILE" in ft and f".{str(ext).lower()}" in RMT_SUBEXT:
                        flag = True
                    if flag:
                        r.append({
                            "path": ff.replace("\\", "/"),
                            "name": os.path.basename(ff),
                            "type": "file",
                            "rel": os.path.dirname(ff).replace("\\", "/"),
                            "ext": ext,
                            "size": StringUtils.str_filesize(os.path.getsize(ff))
                        })

        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {
                "code": -1,
                "message": '加载路径失败: %s' % str(e)
            }
        return {
            "code": 0,
            "count": len(r),
            "data": r
        }

    @staticmethod
    def __rename_file(data):
        """
        文件重命名
        """
        path = data.get("path")
        name = data.get("name")
        if path and name:
            try:
                os.rename(path, os.path.join(os.path.dirname(path), name))
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                return {"code": -1, "msg": str(e)}
        return {"code": 0}

    def __delete_files(self, data):
        """
        删除文件
        """
        files = data.get("files")
        if files:
            # 删除文件
            for file in files:
                del_flag, del_msg = self.delete_media_file(filedir=os.path.dirname(file),
                                                           filename=os.path.basename(file))
                if not del_flag:
                    log.error(f"【MediaFile】{del_msg}")
                else:
                    log.info(f"【MediaFile】{del_msg}")
        return {"code": 0}

    @staticmethod
    def __download_subtitle(data):
        """
        从配置的字幕服务下载单个文件的字幕
        """
        path = data.get("path")
        name = data.get("name")
        media = Media().get_media_info(title=name)
        if not media or not media.tmdb_info:
            return {"code": -1, "msg": f"{name} 无法从TMDB查询到媒体信息"}
        if not media.imdb_id:
            media.set_tmdb_info(Media().get_tmdb_info(mtype=media.type,
                                                      tmdbid=media.tmdb_id))
        subtitle_item = [{"type": media.type,
                          "file": os.path.splitext(path)[0],
                          "file_ext": os.path.splitext(name)[-1],
                          "name": media.en_name if media.en_name else media.cn_name,
                          "title": media.title,
                          "year": media.year,
                          "season": media.begin_season,
                          "episode": media.begin_episode,
                          "bluray": False,
                          "imdbid": media.imdb_id}]
        success, retmsg = Subtitle().download_subtitle(items=subtitle_item)
        if success:
            return {"code": 0, "msg": retmsg}
        else:
            return {"code": -1, "msg": retmsg}

    @staticmethod
    def __get_download_setting(data):
        sid = data.get("sid")
        if sid:
            download_setting = Downloader().get_download_setting(sid=sid)
        else:
            download_setting = list(Downloader().get_download_setting().values())
        return {"code": 0, "data": download_setting}

    def __update_download_setting(self, data):
        sid = data.get("sid")
        name = data.get("name")
        category = data.get("category")
        tags = data.get("tags")
        content_layout = data.get("content_layout")
        is_paused = data.get("is_paused")
        upload_limit = data.get("upload_limit")
        download_limit = data.get("download_limit")
        ratio_limit = data.get("ratio_limit")
        seeding_time_limit = data.get("seeding_time_limit")
        downloader = data.get("downloader")
        self.dbhelper.update_download_setting(sid=sid,
                                              name=name,
                                              category=category,
                                              tags=tags,
                                              content_layout=content_layout,
                                              is_paused=is_paused,
                                              upload_limit=upload_limit or 0,
                                              download_limit=download_limit or 0,
                                              ratio_limit=ratio_limit or 0,
                                              seeding_time_limit=seeding_time_limit or 0,
                                              downloader=downloader)
        Downloader().init_config()
        return {"code": 0}

    def __delete_download_setting(self, data):
        sid = data.get("sid")
        self.dbhelper.delete_download_setting(sid=sid)
        Downloader().init_config()
        return {"code": 0}

    def __update_message_client(self, data):
        """
        更新消息设置
        """
        name = data.get("name")
        cid = data.get("cid")
        ctype = data.get("type")
        config = data.get("config")
        switchs = data.get("switchs")
        interactive = data.get("interactive")
        enabled = data.get("enabled")
        if cid:
            self.dbhelper.delete_message_client(cid=cid)
        self.dbhelper.insert_message_client(name=name,
                                            ctype=ctype,
                                            config=config,
                                            switchs=switchs,
                                            interactive=interactive,
                                            enabled=enabled)
        Message().init_config()
        return {"code": 0}

    def __delete_message_client(self, data):
        """
        删除消息设置
        """
        if self.dbhelper.delete_message_client(cid=data.get("cid")):
            Message().init_config()
            return {"code": 0}
        else:
            return {"code": 1}

    def __check_message_client(self, data):
        """
        维护消息设置
        """
        flag = data.get("flag")
        cid = data.get("cid")
        ctype = data.get("type")
        checked = data.get("checked")
        if flag == "interactive":
            # TG/WX只能开启一个交互
            if checked:
                self.dbhelper.check_message_client(interactive=0, ctype=ctype)
            self.dbhelper.check_message_client(cid=cid,
                                               interactive=1 if checked else 0)
            Message().init_config()
            return {"code": 0}
        elif flag == "enable":
            self.dbhelper.check_message_client(cid=cid,
                                               enabled=1 if checked else 0)
            Message().init_config()
            return {"code": 0}
        else:
            return {"code": 1}

    @staticmethod
    def __get_message_client(data):
        """
        获取消息设置
        """
        cid = data.get("cid")
        return {"code": 0, "detail": Message().get_message_client_info(cid=cid)}

    @staticmethod
    def __test_message_client(data):
        """
        测试消息设置
        """
        ctype = data.get("type")
        config = json.loads(data.get("config"))
        res = Message().get_status(ctype=ctype, config=config)
        if res:
            return {"code": 0}
        else:
            return {"code": 1}

    @staticmethod
    def __get_indexers(data=None):
        """
        获取索引器
        """
        return {"code": 0, "indexers": Indexer().get_indexer_dict()}

    @staticmethod
    def __get_download_dirs(data):
        """
        获取下载目录
        """
        sid = data.get("sid")
        site = data.get("site")
        if not sid and site:
            sid = Sites().get_site_download_setting(site_name=site)
        dirs = Downloader().get_download_dirs(setting=sid)
        return {"code": 0, "paths": dirs}

    @staticmethod
    def __find_hardlinks(data):
        files = data.get("files")
        file_dir = data.get("dir")
        if not files:
            return []
        if not file_dir and os.name != "nt":
            # 取根目录下一级为查找目录
            file_dir = os.path.commonpath(files).replace("\\", "/")
            if file_dir != "/":
                file_dir = "/" + str(file_dir).split("/")[1]
            else:
                return []
        hardlinks = {}
        if files:
            try:
                for file in files:
                    hardlinks[os.path.basename(file)] = SystemUtils().find_hardlinks(file=file, fdir=file_dir)
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                return {"code": 1}
        return {"code": 0, "data": hardlinks}

    @staticmethod
    def __update_sites_cookie_ua(data):
        """
        更新所有站点的Cookie和UA
        """
        siteid = data.get("siteid")
        username = data.get("username")
        password = data.get("password")
        twostepcode = data.get("two_step_code")
        ocrflag = data.get("ocrflag")
        retcode, messages = SiteCookie().update_sites_cookie_ua(siteid=siteid,
                                                                username=username,
                                                                password=password,
                                                                twostepcode=twostepcode,
                                                                ocrflag=ocrflag)
        if retcode == 0:
            Sites().init_config()
        return {"code": retcode, "messages": messages}

    @staticmethod
    def __set_site_captcha_code(data):
        """
        设置站点验证码
        """
        code = data.get("code")
        value = data.get("value")
        SiteCookie().set_code(code=code, value=value)
        return {"code": 0}

    @staticmethod
    def __update_torrent_remove_task(data):
        """
        更新自动删种任务
        """
        flag, msg = TorrentRemover().update_torrent_remove_task(data=data)
        if not flag:
            return {"code": 1, "msg": msg}
        else:
            TorrentRemover().init_config()
            return {"code": 0}

    @staticmethod
    def __get_torrent_remove_task(data=None):
        """
        获取自动删种任务
        """
        if data:
            tid = data.get("tid")
        else:
            tid = None
        return {"code": 0, "detail": TorrentRemover().get_torrent_remove_tasks(taskid=tid)}

    @staticmethod
    def __delete_torrent_remove_task(data):
        """
        删除自动删种任务
        """
        tid = data.get("tid")
        flag = TorrentRemover().delete_torrent_remove_task(taskid=tid)
        if flag:
            TorrentRemover().init_config()
            return {"code": 0}
        else:
            return {"code": 1}

    @staticmethod
    def __get_remove_torrents(data):
        """
        获取满足自动删种任务的种子
        """
        tid = data.get("tid")
        flag, torrents = TorrentRemover().get_remove_torrents(taskid=tid)
        if not flag or not torrents:
            return {"code": 1, "msg": "未获取到符合处理条件种子"}
        return {"code": 0, "data": torrents}

    @staticmethod
    def __auto_remove_torrents(data):
        """
        执行自动删种任务
        """
        tid = data.get("tid")
        TorrentRemover().auto_remove_torrents(taskids=tid)
        return {"code": 0}

    @staticmethod
    def __get_site_favicon(data):
        """
        获取站点图标
        """
        sitename = data.get("name")
        return {"code": 0, "icon": Sites().get_site_favicon(site_name=sitename)}

    def get_douban_history(self, data=None):
        """
        查询豆瓣同步历史
        """
        results = self.dbhelper.get_douban_history()
        return {"code": 0, "result": [item.as_dict() for item in results]}

    def __delete_douban_history(self, data):
        """
        删除豆瓣同步历史
        """
        self.dbhelper.delete_douban_history(data.get("id"))
        return {"code": 0}

    def __list_brushtask_torrents(self, data):
        """
        获取刷流任务的种子明细
        """
        results = self.dbhelper.get_brushtask_torrents(brush_id=data.get("id"),
                                                       active=False)
        if not results:
            return {"code": 1, "msg": "未下载种子或未获取到种子明细"}
        return {"code": 0, "data": [item.as_dict() for item in results]}

    @staticmethod
    def __set_system_config(data):
        """
        设置系统设置（数据库）
        """
        key = data.get("key")
        value = data.get("value")
        if not key or not value:
            return {"code": 1}
        try:
            SystemConfig().set_system_config(key=key, value=value)
            return {"code": 0}
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            return {"code": 1}

    @staticmethod
    def get_site_user_statistics(data):
        """
        获取站点用户统计信息
        """
        sites = data.get("sites")
        encoding = data.get("encoding") or "RAW"
        sort_by = data.get("sort_by")
        sort_on = data.get("sort_on")
        site_hash = data.get("site_hash")
        statistics = Sites().get_site_user_statistics(sites=sites, encoding=encoding)
        if sort_by and sort_on in ["asc", "desc"]:
            if sort_on == "asc":
                statistics.sort(key=lambda x: x[sort_by])
            else:
                statistics.sort(key=lambda x: x[sort_by], reverse=True)
        if site_hash == "Y":
            for item in statistics:
                item["site_hash"] = StringUtils.md5_hash(item.get("site"))
        return {"code": 0, "data": statistics}

    @staticmethod
    def send_custom_message(data):
        """
        发送自定义消息
        """
        title = data.get("title")
        text = data.get("text") or ""
        image = data.get("image") or ""
        Message().send_custom_message(title=title, text=text, image=image)
        return {"code": 0}

    @staticmethod
    def get_rmt_modes():
        RmtModes = ModuleConf.RMT_MODES_LITE if SystemUtils.is_lite_version() else ModuleConf.RMT_MODES
        return [{
            "value": value,
            "name": name.value
        } for value, name in RmtModes.items()]

    def __cookiecloud_sync(self, data):
        """
        CookieCloud数据同步
        """
        server = data.get("server")
        key = data.get("key")
        password = data.get("password")
        # 保存设置
        SystemConfig().set_system_config(key="CookieCloud",
                                         value={
                                             "server": server,
                                             "key": key,
                                             "password": password
                                         })
        # 同步数据
        contents, retmsg = CookieCloudHelper(server=server,
                                             key=key,
                                             password=password).download_data()
        if not contents:
            return {"code": 1, "msg": retmsg}
        success_count = 0
        for domain, content_list in contents.items():
            if domain.startswith('.'):
                domain = domain[1:]
            cookie_str = ""
            for content in content_list:
                cookie_str += content.get("name") + "=" + content.get("value") + ";"
            if not cookie_str:
                continue
            site_info = Sites().get_sites(siteurl=domain)
            if not site_info:
                continue
            self.dbhelper.update_site_cookie_ua(tid=site_info.get("id"),
                                                cookie=cookie_str)
            success_count += 1
        if success_count:
            # 重载站点信息
            Sites().init_config()
            return {"code": 0, "msg": f"成功更新 {success_count} 个站点的Cookie数据"}
        return {"code": 0, "msg": "同步完成，但未更新任何站点的Cookie！"}

    def media_detail(self, data):
        """
        获取媒体详情
        """
        # TMDBID 或 DB:豆瓣ID
        tmdbid = data.get("tmdbid")
        mtype = MediaType.MOVIE if data.get("type") in self._MovieTypes else MediaType.TV
        if not tmdbid:
            return {"code": 1, "msg": "未指定媒体ID"}
        media_info = WebUtils.get_mediainfo_from_id(mtype=mtype, mediaid=tmdbid)
        # 检查TMDB信息
        if not media_info or not media_info.tmdb_info:
            return {
                "code": 1,
                "msg": "无法查询到TMDB信息"
            }
        # 查询存在及订阅状态
        fav, rssid = FileTransfer().get_media_exists_flag(mtype=mtype,
                                                          title=media_info.title,
                                                          year=media_info.year,
                                                          tmdbid=media_info.tmdb_id)
        MediaHander = Media()
        return {
            "code": 0,
            "data": {
                "tmdbid": media_info.tmdb_id,
                "background": MediaHander.get_tmdb_backdrops(tmdbinfo=media_info.tmdb_info),
                "image": media_info.get_poster_image(),
                "vote": media_info.vote_average,
                "year": media_info.year,
                "title": media_info.title,
                "genres": MediaHander.get_tmdb_genres_names(tmdbinfo=media_info.tmdb_info),
                "overview": media_info.overview,
                "runtime": StringUtils.str_timehours(media_info.runtime),
                "fact": MediaHander.get_tmdb_factinfo(media_info),
                "crews": MediaHander.get_tmdb_crews(tmdbinfo=media_info.tmdb_info, nums=6),
                "actors": MediaHander.get_tmdb_cats(mtype=mtype, tmdbid=media_info.tmdb_id),
                "link": media_info.get_detail_url(),
                "fav": fav,
                "rssid": rssid
            }
        }

    def __media_similar(self, data):
        """
        查询TMDB相似媒体
        """
        tmdbid = data.get("tmdbid")
        page = data.get("page") or 1
        mtype = MediaType.MOVIE if data.get("type") in self._MovieTypes else MediaType.TV
        if not tmdbid:
            return {"code": 1, "msg": "未指定TMDBID"}
        if mtype == MediaType.MOVIE:
            result = Media().get_movie_similar(tmdbid=tmdbid, page=page)
        else:
            result = Media().get_tv_similar(tmdbid=tmdbid, page=page)
        return {"code": 0, "data": result}

    def __media_recommendations(self, data):
        """
        查询TMDB同类推荐媒体
        """
        tmdbid = data.get("tmdbid")
        page = data.get("page") or 1
        mtype = MediaType.MOVIE if data.get("type") in self._MovieTypes else MediaType.TV
        if not tmdbid:
            return {"code": 1, "msg": "未指定TMDBID"}
        if mtype == MediaType.MOVIE:
            result = Media().get_movie_recommendations(tmdbid=tmdbid, page=page)
        else:
            result = Media().get_tv_recommendations(tmdbid=tmdbid, page=page)
        return {"code": 0, "data": result}

    def __media_person(self, data):
        """
        查询TMDB媒体所有演员
        """
        tmdbid = data.get("tmdbid")
        mtype = MediaType.MOVIE if data.get("type") in self._MovieTypes else MediaType.TV
        if not tmdbid:
            return {"code": 1, "msg": "未指定TMDBID"}
        return {"code": 0, "data": Media().get_tmdb_cats(tmdbid=tmdbid,
                                                         mtype=mtype)}

    def __person_medias(self, data):
        """
        查询演员参演作品
        """
        personid = data.get("personid")
        page = data.get("page") or 1
        mtype = MediaType.MOVIE if data.get("type") in self._MovieTypes else MediaType.TV
        if not personid:
            return {"code": 1, "msg": "未指定演员ID"}
        return {"code": 0, "data": Media().get_person_medias(personid=personid,
                                                             mtype=mtype,
                                                             page=page)}
