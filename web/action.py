import _thread
import importlib
import signal
from flask_login import logout_user
from werkzeug.security import generate_password_hash

import log
from config import RMT_MEDIAEXT, LOG_QUEUE, Config
from message.channel.telegram import Telegram
from message.channel.wechat import WeChat
from message.send import Message
from pt.client.qbittorrent import Qbittorrent
from pt.client.transmission import Transmission
from pt.douban import DouBan
from pt.downloader import Downloader
from pt.mediaserver.jellyfin import Jellyfin
from pt.mediaserver.plex import Plex
from pt.rss import Rss
from pt.sites import Sites
from rmt.doubanv2api.doubanapi import DoubanApi
from rmt.filetransfer import FileTransfer
from rmt.media import Media
from rmt.metainfo import MetaInfo
from service.run import stop_scheduler, stop_monitor, restart_scheduler, restart_monitor
from service.scheduler import Scheduler
from service.sync import Sync
from utils.commons import EpisodeFormat
from utils.functions import *
from utils.meta_helper import MetaHelper
from utils.sqls import *
from utils.types import MediaType, SearchType, DownloaderType, SyncType
from web.backend.search_torrents import search_medias_for_web, search_media_by_message
from web.backend.subscribe import add_rss_subscribe, add_rss_substribe_from_string


class WebAction:
    config = None
    _actions = {}

    def __init__(self):
        self.config = Config()
        self._actions = {
            "sch": self.__sch,
            "search": self.__search,
            "download": self.__download,
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
            "get_search_rule": self.__get_search_rule,
            "update_search_rule": self.__update_search_rule,
            "get_rss_rule": self.__get_rss_rule,
            "update_rss_rule": self.__update_rss_rule,
            "restart": self.__restart,
            "update_system": self.__update_system,
            "logout": self.__logout,
            "update_config": self.__update_config,
            "update_directory": self.__update_directory,
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
            "tv_calendar_data": self.__tv_calendar_data
        }

    def action(self, cmd, data):
        func = self._actions.get(cmd)
        if not func:
            return "非授权访问！"
        else:
            return func(data)

    @staticmethod
    def stop_service():
        """
        停止所有服务
        """
        # 停止定时服务
        stop_scheduler()
        # 停止监控
        stop_monitor()
        # 签退
        logout_user()

    @staticmethod
    def shutdown_server():
        """
        停卡Flask进程
        """
        sig = getattr(signal, "SIGKILL", signal.SIGTERM)
        os.kill(os.getpid(), sig)

    @staticmethod
    def handle_message_job(msg, in_from=SearchType.OT, user_id=None):
        """
        处理消息事件
        """
        if not msg:
            return
        commands = {
            "/ptr": {"func": Downloader().pt_removetorrents, "desp": "PT删种"},
            "/ptt": {"func": Downloader().pt_transfer, "desp": "PT下载转移"},
            "/pts": {"func": Sites().signin, "desp": "PT站签到"},
            "/rst": {"func": Sync().transfer_all_sync, "desp": "监控目录全量同步"},
            "/rss": {"func": Rss().rssdownload, "desp": "RSS订阅"},
            "/db": {"func": DouBan().sync, "desp": "豆瓣同步"}
        }
        command = commands.get(msg)
        if command:
            # 检查用户权限
            if in_from == SearchType.TG and user_id:
                if str(user_id) != Telegram().get_admin_user():
                    Message().send_channel_msg(channel=in_from, title="错误：只有管理员才有权限执行此命令")
                    return
            # 启动服务
            _thread.start_new_thread(command.get("func"), ())
            Message().send_channel_msg(channel=in_from, title="已启动：%s" % command.get("desp"))
        elif msg.startswith("订阅"):
            # 添加订阅
            _thread.start_new_thread(add_rss_substribe_from_string, (msg, in_from, user_id,))
        else:
            # PT检索
            _thread.start_new_thread(search_media_by_message, (msg, in_from, user_id,))

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
        # 文件转移模式
        if cfg_key == "app.rmt_mode":
            cfg['sync']['sync_mod'] = cfg_value
            cfg['pt']['rmt_mode'] = cfg_value
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
                        cfg[keys[0]][keys[1]].append(cfg_value)
                    elif oper == "sub":
                        cfg[keys[0]][keys[1]].remove(cfg_value)
                        if not cfg[keys[0]][keys[1]]:
                            cfg[keys[0]][keys[1]] = None
                    elif oper == "set":
                        cfg[keys[0]][keys[1]].remove(cfg_value)
                        if update_value:
                            cfg[keys[0]][keys[1]].append(update_value)
                else:
                    cfg[keys[0]] = {}
                    cfg[keys[0]][keys[1]] = cfg_value
        return cfg

    @staticmethod
    def __sch(data):
        """
        启动定时服务
        """
        commands = {
            "autoremovetorrents": Downloader().pt_removetorrents,
            "pttransfer": Downloader().pt_transfer,
            "ptsignin": Sites().signin,
            "sync": Sync().transfer_all_sync,
            "rssdownload": Rss().rssdownload,
            "douban": DouBan().sync
        }
        sch_item = data.get("item")
        if sch_item and commands.get(sch_item):
            _thread.start_new_thread(commands.get(sch_item), ())
        return {"retmsg": "服务已启动", "item": sch_item}

    @staticmethod
    def __search(data):
        """
        WEB检索资源
        """
        search_word = data.get("search_word")
        ident_flag = False if data.get("unident") else True
        filters = data.get("filters")
        if search_word:
            search_medias_for_web(content=search_word, ident_flag=ident_flag, filters=filters)
        return {"retcode": 0}

    @staticmethod
    def __download(data):
        """
        从WEB添加下载
        """
        dl_id = data.get("id")
        results = get_search_result_by_id(dl_id)
        for res in results:
            if res[7] == "TV":
                mtype = MediaType.TV
            elif res[7] == "MOV":
                mtype = MediaType.MOVIE
            else:
                mtype = MediaType.ANIME
            Downloader().add_pt_torrent(res[0], mtype)
            msg_item = MetaInfo("%s" % res[8])
            msg_item.title = res[1]
            msg_item.vote_average = res[5]
            msg_item.poster_path = res[6]
            msg_item.type = mtype
            msg_item.description = res[9]
            msg_item.size = res[10]
            msg_item.tmdb_id = res[11]
            msg_item.poster_path = res[12]
            msg_item.overview = res[13]
            msg_item.enclosure = res[0]
            msg_item.site = res[14]
            Message().send_download_message(SearchType.WEB, msg_item)
        return {"retcode": 0}

    @staticmethod
    def __pt_start(data):
        """
        开始下载
        """
        tid = data.get("id")
        if id:
            Downloader().start_torrents(tid)
        return {"retcode": 0, "id": tid}

    @staticmethod
    def __pt_stop(data):
        """
        停止下载
        """
        tid = data.get("id")
        if id:
            Downloader().stop_torrents(tid)
        return {"retcode": 0, "id": tid}

    @staticmethod
    def __pt_remove(data):
        """
        删除下载
        """
        tid = data.get("id")
        if id:
            Downloader().delete_torrents(tid)
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
            if Client == DownloaderType.QB:
                if torrent.get('state') in ['pausedDL']:
                    state = "Stoped"
                    speed = "已暂停"
                else:
                    state = "Downloading"
                    dlspeed = str_filesize(torrent.get('dlspeed'))
                    eta = str_timelong(torrent.get('eta'))
                    upspeed = str_filesize(torrent.get('upspeed'))
                    speed = "%s%sB/s %s%sB/s %s" % (chr(8595), dlspeed, chr(8593), upspeed, eta)
                # 进度
                progress = round(torrent.get('progress') * 100)
                # 主键
                key = torrent.get('hash')
            else:
                if torrent.status in ['stopped']:
                    state = "Stoped"
                    speed = "已暂停"
                else:
                    state = "Downloading"
                    dlspeed = str_filesize(torrent.rateDownload)
                    upspeed = str_filesize(torrent.rateUpload)
                    speed = "%s%sB/s %s%sB/s" % (chr(8595), dlspeed, chr(8593), upspeed)
                # 进度
                progress = round(torrent.progress, 1)
                # 主键
                key = torrent.id

            torrent_info = {'id': key, 'speed': speed, 'state': state, 'progress': progress}
            if torrent_info not in DispTorrents:
                DispTorrents.append(torrent_info)
        return {"retcode": 0, "torrents": DispTorrents}

    @staticmethod
    def __del_unknown_path(data):
        """
        删除路径
        """
        tids = data.get("id")
        if isinstance(tids, list):
            for tid in tids:
                if not tid:
                    continue
                delete_transfer_unknown(tid)
            return {"retcode": 0}
        else:
            retcode = delete_transfer_unknown(tids)
            return {"retcode": retcode}

    @staticmethod
    def __rename(data):
        """
        手工转移
        """
        path = dest_dir = None
        logid = data.get("logid")
        if logid:
            paths = get_transfer_path_by_id(logid)
            if paths:
                path = os.path.join(paths[0][0], paths[0][1])
                dest_dir = paths[0][2]
            else:
                return {"retcode": -1, "retmsg": "未查询到转移日志记录"}
        else:
            unknown_id = data.get("unknown_id")
            if unknown_id:
                paths = get_unknown_path_by_id(unknown_id)
                if paths:
                    path = paths[0][0]
                    dest_dir = paths[0][1]
                else:
                    return {"retcode": -1, "retmsg": "未查询到未识别记录"}
        if not dest_dir:
            dest_dir = ""
        if not path:
            return {"retcode": -1, "retmsg": "输入路径有误"}
        tmdbid = data.get("tmdb")
        title = data.get("title")
        year = data.get("year")
        mtype = data.get("type")
        season = data.get("season")
        episode_format = data.get("episode_format")
        min_filesize = data.get("min_filesize")
        if mtype == "TV":
            media_type = MediaType.TV
        elif mtype == "MOV":
            media_type = MediaType.MOVIE
        else:
            media_type = MediaType.ANIME
        tmdb_info = Media().get_tmdb_info(media_type, title, year, tmdbid)
        if not tmdb_info:
            return {"retcode": 1, "retmsg": "转移失败，无法查询到TMDB信息"}
        # 如果改次手动修复时一个单文件，自动修复改目录下同名文件，需要配合episode_format生效
        need_fix_all = False
        if os.path.splitext(path)[-1].lower() in RMT_MEDIAEXT and episode_format:
            path = os.path.dirname(path)
            need_fix_all = True
        succ_flag, ret_msg = FileTransfer().transfer_media(in_from=SyncType.MAN,
                                                           in_path=path,
                                                           target_dir=dest_dir,
                                                           tmdb_info=tmdb_info,
                                                           media_type=media_type,
                                                           season=season,
                                                           episode=(
                                                               EpisodeFormat(episode_format), need_fix_all,
                                                               logid),
                                                           min_filesize=min_filesize
                                                           )
        if succ_flag:
            if not need_fix_all:
                if logid:
                    insert_transfer_blacklist(path)
                else:
                    update_transfer_unknown_state(path)
            return {"retcode": 0, "retmsg": "转移成功"}
        else:
            return {"retcode": 2, "retmsg": ret_msg}

    @staticmethod
    def __rename_udf(data):
        """
        自定义识别
        """
        inpath = data.get("inpath")
        outpath = data.get("outpath")
        if not os.path.exists(inpath):
            return {"retcode": -1, "retmsg": "输入路径不存在"}
        tmdbid = data.get("tmdb")
        if not tmdbid.strip() and not tmdbid.isdigit():
            return {"retcode": -1, "retmsg": "tmdbid 格式不正确！"}
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
        tmdb_info = Media().get_tmdb_info(media_type, None, None, tmdbid)
        if not tmdb_info:
            return {"retcode": 1, "retmsg": "识别失败，无法查询到TMDB信息"}
        # 自定义转移
        succ_flag, ret_msg = FileTransfer().transfer_media(in_from=SyncType.MAN,
                                                           in_path=inpath,
                                                           target_dir=outpath,
                                                           tmdb_info=tmdb_info,
                                                           media_type=media_type,
                                                           season=season,
                                                           episode=(
                                                               EpisodeFormat(episode_format, episode_details,
                                                                             episode_offset), False, None),
                                                           min_filesize=min_filesize,
                                                           udf_flag=True)
        if succ_flag:
            return {"retcode": 0, "retmsg": "转移成功"}
        else:
            return {"retcode": 2, "retmsg": ret_msg}

    @staticmethod
    def __delete_history(data):
        """
        删除识别记录及文件
        """
        logid = data.get('logid')
        paths = get_transfer_path_by_id(logid)
        if paths:
            file_name = paths[0][1]
            dest_dir = paths[0][2]
            title = paths[0][3]
            category = paths[0][4]
            year = paths[0][5]
            se = paths[0][6]
            mtype = paths[0][7]
            dest_path = FileTransfer().get_dest_path_by_info(dest=dest_dir, mtype=mtype, title=title,
                                                             category=category, year=year, season=se)
            meta_info = MetaInfo(file_name)
            if dest_path and dest_path.find(title) != -1:
                delete_transfer_log_by_id(logid)
                if not meta_info.get_episode_string():
                    # 电影或者没有集数的电视剧，删除整个目录
                    try:
                        shutil.rmtree(dest_path)
                    except Exception as e:
                        log.console(str(e))
                else:
                    # 有集数的电视剧
                    for dest_file in get_dir_files(dest_path):
                        file_meta_info = MetaInfo(os.path.basename(dest_file))
                        if file_meta_info.get_episode_list() and set(
                                file_meta_info.get_episode_list()).issubset(set(meta_info.get_episode_list())):
                            try:
                                shutil.rmtree(dest_file)
                            except Exception as e:
                                log.console(str(e))
        return {"retcode": 0}

    @staticmethod
    def __logging(data):
        """
        查询实时日志
        """
        if LOG_QUEUE:
            return {"text": "<br/>".join(list(LOG_QUEUE))}
        return {"text": ""}

    def __version(self, data):
        """
        检查新版本
        """
        version = ""
        info = ""
        code = 0
        try:
            response = requests.get("https://api.github.com/repos/jxxghp/nas-tools/releases/latest", timeout=10,
                                    proxies=self.config.get_proxies())
            if response:
                ver_json = response.json()
                version = ver_json["tag_name"]
                info = f'<a href="{ver_json["html_url"]}" target="_blank">{version}</a>'
        except Exception as e:
            log.console(str(e))
            code = -1
        return {"code": code, "version": version, "info": info}

    @staticmethod
    def __update_site(data):
        """
        维护站点信息
        """
        tid = data.get('site_id')
        name = data.get('site_name')
        site_pri = data.get('site_pri')
        rssurl = data.get('site_rssurl')
        signurl = data.get('site_signurl')
        cookie = data.get('site_cookie')
        include = data.get('site_include')
        exclude = data.get('site_exclude')
        note = data.get('site_note')
        size = data.get('site_size')
        if tid:
            ret = update_config_site(tid=tid,
                                     name=name,
                                     site_pri=site_pri,
                                     rssurl=rssurl,
                                     signurl=signurl,
                                     cookie=cookie,
                                     include=include,
                                     exclude=exclude,
                                     size=size,
                                     note=note)
        else:
            ret = insert_config_site(name=name,
                                     site_pri=site_pri,
                                     rssurl=rssurl,
                                     signurl=signurl,
                                     cookie=cookie,
                                     include=include,
                                     exclude=exclude,
                                     size=size,
                                     note=note)
        # 生效站点配置
        Sites().init_config()
        return {"code": ret}

    @staticmethod
    def __get_site(data):
        """
        查询单个站点信息
        """
        tid = data.get("id")
        if tid:
            ret = get_site_by_id(tid)
        else:
            ret = []
        return {"code": 0, "site": ret}

    @staticmethod
    def __del_site(data):
        """
        删除单个站点信息
        """
        tid = data.get("id")
        if tid:
            ret = delete_config_site(tid)
            return {"code": ret}
        else:
            return {"code": 0}

    @staticmethod
    def __get_search_rule(data):
        """
        查询搜索过滤规则
        """
        ret = get_config_search_rule()
        return {"code": 0, "rule": ret}

    @staticmethod
    def __update_search_rule(data):
        """
        更新搜索过滤规则
        """
        include = data.get('search_include')
        exclude = data.get('search_exclude')
        note = data.get('search_note')
        size = data.get('search_size')
        ret = update_config_search_rule(include=include, exclude=exclude, note=note, size=size)
        return {"code": ret}

    @staticmethod
    def __get_rss_rule(data):
        """
        查询RSS全局过滤规则
        """
        ret = get_config_rss_rule()
        return {"code": 0, "rule": ret}

    @staticmethod
    def __update_rss_rule(data):
        """
        更新搜索过滤规则
        """
        note = data.get('rss_note')
        ret = update_config_rss_rule(note=note)
        return {"code": ret}

    def __restart(self, data):
        """
        重启
        """
        # 停止服务
        self.stop_service()
        # 退出主进程
        self.shutdown_server()

    def __update_system(self, data):
        """
        更新
        """
        # 停止服务
        self.stop_service()
        # 安装依赖
        subprocess.call(['pip', 'install', '-r', '/nas-tools/requirements.txt', ])
        # 升级
        subprocess.call(['git', 'pull'])
        # 退出主进程
        self.shutdown_server()

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
        cfg = self.config.get_config()
        cfgs = dict(data).items()
        # 重载配置标志
        config_test = False
        scheduler_reload = False
        jellyfin_reload = False
        plex_reload = False
        qbittorrent_reload = False
        transmission_reload = False
        wechat_reload = False
        telegram_reload = False
        # 修改配置
        for key, value in cfgs:
            if key == "test" and value:
                config_test = True
                continue
            # 生效配置
            cfg = self.set_config_value(cfg, key, value)
            if key in ['pt.ptsignin_cron', 'pt.pt_monitor', 'pt.pt_check_interval', 'pt.pt_seeding_time',
                       'douban.interval']:
                scheduler_reload = True
            if key.startswith("jellyfin"):
                jellyfin_reload = True
            if key.startswith("plex"):
                plex_reload = True
            if key.startswith("qbittorrent"):
                qbittorrent_reload = True
            if key.startswith("transmission"):
                transmission_reload = True
            if key.startswith("message.telegram"):
                telegram_reload = True
            if key.startswith("message.wechat"):
                wechat_reload = True
        # 保存配置
        if not config_test:
            self.config.save_config(cfg)
        # 重启定时服务
        if scheduler_reload:
            Scheduler().init_config()
            restart_scheduler()
        # 重载Jellyfin
        if jellyfin_reload:
            Jellyfin().init_config()
        # 重载Plex
        if plex_reload:
            Plex().init_config()
        # 重载qbittorrent
        if qbittorrent_reload:
            Qbittorrent().init_config()
        # 重载transmission
        if transmission_reload:
            Transmission().init_config()
        # 重载wechat
        if wechat_reload:
            WeChat().init_config()
        # 重载telegram
        if telegram_reload:
            Telegram().init_config()

        return {"code": 0}

    def __update_directory(self, data):
        """
        维护媒体库目录
        """
        cfg = self.set_config_directory(self.config.get_config(), data.get("oper"), data.get("key"),
                                        data.get("value"), data.get("replace_value"))
        # 保存配置
        self.config.save_config(cfg)
        if data.get("key") == "sync.sync_path":
            # 生效配置
            Sync().init_config()
            # 重启目录同步服务
            restart_monitor()
        return {"code": 0}

    @staticmethod
    def __remove_rss_media(data):
        """
        移除RSS订阅
        """
        name = data.get("name")
        mtype = data.get("type")
        year = data.get("year")
        season = data.get("season")
        rssid = data.get("rssid")
        page = data.get("page")
        if name:
            meta_info = MetaInfo(title=name)
            name = meta_info.get_name()
            if not season:
                season = meta_info.get_season_string()
        if mtype:
            if mtype in ['nm', 'hm', 'dbom', 'dbhm', 'dbnm', 'MOV']:
                delete_rss_movie(title=name, year=year, rssid=rssid)
            else:
                delete_rss_tv(title=name, year=year, season=season, rssid=rssid)
        return {"code": 0, "page": page, "name": name}

    @staticmethod
    def __add_rss_media(data):
        """
        添加RSS订阅
        """
        doubanid = data.get("doubanid")
        tmdbid = data.get("tmdbid")
        name = data.get("name")
        mtype = data.get("type")
        year = data.get("year")
        season = data.get("season")
        match = data.get("match")
        page = data.get("page")
        if name and mtype:
            if mtype in ['nm', 'hm', 'dbom', 'dbhm', 'dbnm', 'MOV']:
                mtype = MediaType.MOVIE
            else:
                mtype = MediaType.TV
        code, msg, media_info = add_rss_subscribe(mtype=mtype,
                                                  name=name,
                                                  year=year,
                                                  season=season,
                                                  match=match,
                                                  doubanid=doubanid,
                                                  tmdbid=tmdbid)
        return {"code": code, "msg": msg, "page": page, "name": name}

    @staticmethod
    def __re_identification(data):
        """
        未识别的重新识别
        """
        path = dest_dir = None
        unknown_id = data.get("unknown_id")
        if unknown_id:
            paths = get_unknown_path_by_id(unknown_id)
            if paths:
                path = paths[0][0]
                dest_dir = paths[0][1]
            else:
                return {"retcode": -1, "retmsg": "未查询到未识别记录"}
        if not dest_dir:
            dest_dir = ""
        if not path:
            return {"retcode": -1, "retmsg": "未识别路径有误"}
        succ_flag, ret_msg = FileTransfer().transfer_media(in_from=SyncType.MAN,
                                                           in_path=path,
                                                           target_dir=dest_dir)
        if succ_flag:
            update_transfer_unknown_state(path)
            return {"retcode": 0, "retmsg": "转移成功"}
        else:
            return {"retcode": 2, "retmsg": ret_msg}

    @staticmethod
    def __media_info(data):
        """
        查询媒体信息
        """
        tmdbid = data.get("id")
        mtype = data.get("type")
        title = data.get("title")
        year = data.get("year")
        page = data.get("page")
        doubanid = data.get("doubanid")
        rssid = data.get("rssid")
        if mtype in ['hm', 'nm', 'dbom', 'dbhm', 'dbnm', 'MOV']:
            media_type = MediaType.MOVIE
        else:
            media_type = MediaType.TV

        if media_type == MediaType.MOVIE:
            if doubanid:
                link_url = "https://movie.douban.com/subject/%s" % doubanid
                douban_info = DoubanApi().movie_detail(doubanid)
                if not douban_info:
                    return {"code": 1, "retmsg": "无法查询到豆瓣信息", "link_url": link_url}
                overview = douban_info.get("intro")
                poster_path = douban_info.get("cover_url")
                title = douban_info.get("title")
                vote_average = douban_info.get("rating", {}).get("value") or ""
                release_date = douban_info.get("pubdate")
                year = douban_info.get("year")
            else:
                link_url = "https://www.themoviedb.org/movie/%s" % tmdbid
                tmdb_info = Media().get_tmdb_info(media_type, title, year, tmdbid)
                if not tmdb_info:
                    return {"code": 1, "retmsg": "无法查询到TMDB信息", "link_url": link_url}
                overview = tmdb_info.get("overview")
                poster_path = "https://image.tmdb.org/t/p/w500%s" % tmdb_info.get('poster_path')
                title = tmdb_info.get('title')
                vote_average = tmdb_info.get("vote_average")
                release_date = tmdb_info.get('release_date')
                year = release_date[0:4] if release_date else ""
            return {
                "code": 0,
                "type": mtype,
                "page": page,
                "title": title,
                "vote_average": vote_average,
                "poster_path": poster_path,
                "release_date": release_date,
                "year": year,
                "overview": overview,
                "link_url": link_url,
                "tmdbid": tmdbid,
                "doubanid": doubanid,
                "rssid": rssid or get_rss_movie_id(title=title, year=year)
            }
        else:
            if doubanid:
                link_url = "https://movie.douban.com/subject/%s" % doubanid
                douban_info = DoubanApi().tv_detail(doubanid)
                if not douban_info:
                    return {"code": 1, "retmsg": "无法查询到豆瓣信息", "link_url": link_url}
                overview = douban_info.get("intro")
                poster_path = douban_info.get("cover_url")
                title = douban_info.get("title")
                vote_average = douban_info.get("rating", {}).get("value") or ""
                release_date = douban_info.get("pubdate")
                year = douban_info.get("year")
            else:
                link_url = "https://www.themoviedb.org/tv/%s" % tmdbid
                tmdb_info = Media().get_tmdb_info(media_type, title, year, tmdbid)
                if not tmdb_info:
                    return {"code": 1, "retmsg": "无法查询到TMDB信息", "link_url": link_url}
                overview = tmdb_info.get("overview")
                poster_path = "https://image.tmdb.org/t/p/w500%s" % tmdb_info.get('poster_path')
                title = tmdb_info.get('name')
                vote_average = tmdb_info.get("vote_average")
                release_date = tmdb_info.get('first_air_date')
                year = release_date[0:4] if release_date else ""
            return {
                "code": 0,
                "type": mtype,
                "page": page,
                "title": title,
                "vote_average": vote_average,
                "poster_path": poster_path,
                "release_date": release_date,
                "year": year,
                "overview": overview,
                "link_url": link_url,
                "tmdbid": tmdbid,
                "doubanid": doubanid,
                "rssid": rssid or get_rss_tv_id(title=title, year=year)
            }

    def __test_connection(self, data):
        """
        测试连通性
        """
        # 支持两种传入方式：命令数组或单个命令，单个命令时xx|xx模式解析为模块和类，进行动态引入
        command = data.get("command")
        ret = None
        if command:
            try:
                if isinstance(command, list):
                    for cmd_str in command:
                        ret = eval(cmd_str)
                        if not ret:
                            break
                else:
                    if command.find("|") != -1:
                        module = command.split("|")[0]
                        class_name = command.split("|")[1]
                        ret = getattr(importlib.import_module(module), class_name)().get_status()
                    else:
                        ret = eval(command)
                # 重载配置
                self.config.init_config()
            except Exception as e:
                ret = None
                print(str(e))
            return {"code": 0 if ret else 1}
        return {"code": 0}

    @staticmethod
    def __user_manager(data):
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
            ret = insert_user(name, password, pris)
        else:
            ret = delete_user(name)
        return {"code": ret}

    @staticmethod
    def __refresh_rss(data):
        """
        重新搜索RSS
        """
        mtype = data.get("type")
        rssid = data.get("rssid")
        page = data.get("page")
        if mtype == "MOV":
            _thread.start_new_thread(Rss().rsssearch_movie, (rssid,))
        else:
            _thread.start_new_thread(Rss().rsssearch_tv, (rssid,))
        return {"code": 0, "page": page}

    @staticmethod
    def __refresh_message(data):
        """
        刷新首页消息中心
        """
        lst_time = data.get("lst_time")
        messages = get_system_messages(lst_time=lst_time)
        return {"code": 0, "message": messages}

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
        if tid and tid.startswith("DB:"):
            doubanid = tid.replace("DB:", "")
            douban_info = DoubanApi().movie_detail(doubanid)
            if not douban_info:
                return {"code": 1, "retmsg": "无法查询到豆瓣信息"}
            poster_path = douban_info.get("cover_url")
            title = douban_info.get("title")
            vote_average = douban_info.get("rating", {}).get("value") or "无"
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
                        "vote_average": vote_average
                        }
        else:
            tmdb_info = Media().get_tmdb_info(MediaType.MOVIE, None, None, tid)
            if not tmdb_info:
                return {"code": 1, "retmsg": "无法查询到TMDB信息"}
            poster_path = "https://image.tmdb.org/t/p/w500%s" % tmdb_info.get('poster_path')
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
                        "vote_average": vote_average
                        }

    @staticmethod
    def __tv_calendar_data(data):
        """
        查询电视剧上映日期
        """
        tid = data.get("id")
        season = data.get("season")
        name = data.get("name")
        if tid and tid.startswith("DB:"):
            doubanid = tid.replace("DB:", "")
            douban_info = DoubanApi().tv_detail(doubanid)
            if not douban_info:
                return {"code": 1, "retmsg": "无法查询到豆瓣信息"}
            poster_path = douban_info.get("cover_url")
            title = douban_info.get("title")
            vote_average = douban_info.get("rating", {}).get("value") or "无"
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
                        "vote_average": vote_average
                        }
        else:
            tmdb_info = Media().get_tmdb_tv_season_info(tmdbid=tid, season=season)
            if not tmdb_info:
                return {"code": 1, "retmsg": "无法查询到TMDB信息"}
            episode_events = []
            air_date = tmdb_info.get("air_date")
            poster_path = "https://image.tmdb.org/t/p/w500%s" % tmdb_info.get("poster_path")
            year = air_date[0:4] if air_date else ""
            for episode in tmdb_info.get("episodes"):
                episode_events.append({
                    "type": "剧集",
                    "title": "%s 第%s季第%s集" % (
                        name, season, episode.get("episode_number")) if season != 1 else "%s 第%s集" % (
                        name, episode.get("episode_number")),
                    "start": episode.get("air_date"),
                    "id": tid,
                    "year": year,
                    "poster": poster_path,
                    "vote_average": episode.get("vote_average") or "无"
                })
            return {"code": 0, "events": episode_events}
