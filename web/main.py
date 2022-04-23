import _thread
import logging
import os.path
import shutil
from math import floor

import requests
from flask import Flask, request, json, render_template, make_response, session
from flask_login import LoginManager, UserMixin, login_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

import log
from message.telegram import Telegram
from monitor.media_sync import Sync
from monitor.run import restart_monitor
from pt.downloader import Downloader
from pt.searcher import Searcher
from rmt.filetransfer import FileTransfer
from rmt.media import Media
from rmt.media_server import MediaServer
from rmt.metainfo import MetaInfo
from scheduler.autoremove_torrents import AutoRemoveTorrents
from scheduler.douban_sync import DoubanSync
from scheduler.pt_signin import PTSignin
from scheduler.pt_transfer import PTTransfer
from scheduler.rss_download import RSSDownloader
from message.send import Message

from config import WECHAT_MENU, PT_TRANSFER_INTERVAL, LOG_QUEUE
from utils.functions import get_used_of_partition, str_filesize, str_timelong, INSTANCES
from utils.sqls import get_search_result_by_id, get_search_results, get_movie_keys, get_tv_keys, insert_movie_key, \
    insert_tv_key, delete_all_tv_keys, delete_all_movie_keys, get_transfer_history, get_transfer_unknown_paths, \
    update_transfer_unknown_state, delete_transfer_unknown, get_transfer_path_by_id, insert_transfer_blacklist, \
    delete_transfer_log_by_id, get_config_site, insert_config_site, get_site_by_id, delete_config_site, \
    update_config_site, get_config_search_rule, update_config_search_rule
from utils.types import MediaType, SearchType, DownloaderType, SyncType
from version import APP_VERSION
from web.backend.douban_hot import DoubanHot
from web.backend.webhook_event import WebhookEvent
from web.backend.search_torrents import search_medias_for_web
from utils.WXBizMsgCrypt3 import WXBizMsgCrypt
import xml.etree.cElementTree as ETree

login_manager = LoginManager()
login_manager.login_view = "login"


# Flask实例
def create_flask_app(config):
    app_cfg = config.get_config('app') or {}
    admin_user = app_cfg.get('login_user') or "admin"
    admin_password = app_cfg.get('login_password') or "password"
    USERS = [{
        "id": 1,
        "name": admin_user,
        "password": generate_password_hash(str(admin_password))
    }]

    App = Flask(__name__)
    App.config['JSON_AS_ASCII'] = False
    App.secret_key = 'jxxghp'
    applog = logging.getLogger('werkzeug')
    applog.setLevel(logging.ERROR)
    login_manager.init_app(App)

    @App.after_request
    def add_header(r):
        """
        Add headers to both force latest IE rendering engine or Chrome Frame,
        and also to cache the rendered page for 10 minutes.
        """
        r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        r.headers["Pragma"] = "no-cache"
        r.headers["Expires"] = "0"
        r.headers['Cache-Control'] = 'public, max-age=0'
        return r

    # 根据用户名获得用户记录
    def get_user(user_name):
        for user in USERS:
            if user.get("name") == user_name:
                return user
        return None

    # 用户类
    class User(UserMixin):
        def __init__(self, user):
            self.username = user.get('name')
            self.password_hash = user.get('password')
            self.id = 1

        # 密码验证
        def verify_password(self, password):
            if self.password_hash is None:
                return False
            return check_password_hash(self.password_hash, password)

        # 获取用户ID
        def get_id(self):
            return self.id

        # 根据用户ID获取用户实体，为 login_user 方法提供支持
        @staticmethod
        def get(user_id):
            if not user_id:
                return None
            for user in USERS:
                if user.get('id') == user_id:
                    return User(user)
            return None

    # 定义获取登录用户的方法
    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)

    @App.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html", error=error), 404

    @App.errorhandler(500)
    def page_server_error(error):
        return render_template("500.html", error=error), 500

    # 主页面
    @App.route('/', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            GoPage = request.args.get("next") or ""
            if GoPage.startswith('/'):
                GoPage = GoPage[1:]
            user_info = session.get('_user_id')
            if not user_info:
                return render_template('login.html',
                                       GoPage=GoPage)
            else:
                return render_template('navigation.html',
                                       GoPage=GoPage,
                                       AppVersion=APP_VERSION)
        else:
            GoPage = request.form.get('next') or ""
            if GoPage.startswith('/'):
                GoPage = GoPage[1:]
            username = request.form.get('username')
            if not username:
                return render_template('login.html',
                                       GoPage=GoPage,
                                       err_msg="请输入用户名")
            password = request.form.get('password')
            user_info = get_user(username)
            if not user_info:
                return render_template('login.html',
                                       GoPage=GoPage,
                                       err_msg="用户名或密码错误")
            # 创建用户实体
            user = User(user_info)
            # 校验密码
            if user.verify_password(password):
                # 创建用户 Session
                login_user(user)
                return render_template('navigation.html',
                                       GoPage=GoPage,
                                       AppVersion=APP_VERSION)
            else:
                return render_template('login.html',
                                       GoPage=GoPage,
                                       err_msg="用户名或密码错误")

    # 开始
    @App.route('/index', methods=['POST', 'GET'])
    @login_required
    def index():
        # 获取媒体数量
        ServerSucess = True
        MovieCount = 0
        SeriesCount = 0
        SongCount = 0
        MediaServerClient = MediaServer()
        media_count = MediaServerClient.get_medias_count()
        if media_count:
            MovieCount = "{:,}".format(media_count.get('MovieCount'))
            SeriesCount = "{:,}".format(media_count.get('SeriesCount'))
            SongCount = "{:,}".format(media_count.get('SongCount'))
        elif media_count is None:
            ServerSucess = False

        # 获得活动日志
        Activity = MediaServerClient.get_activity_log(30)

        # 用户数量
        UserCount = MediaServerClient.get_user_count()

        # 磁盘空间
        UsedSapce = 0
        TotalSpace = 0
        FreeSpace = 0
        UsedPercent = 0
        media = config.get_config('media')
        if media:
            # 电影目录
            movie_paths = media.get('movie_path')
            if not isinstance(movie_paths, list):
                movie_paths = [movie_paths]
            movie_used, movie_total = 0, 0
            movie_space_list = []
            for movie_path in movie_paths:
                if not movie_path:
                    continue
                used, total = get_used_of_partition(movie_path)
                if "%s-%s" % (used, total) not in movie_space_list:
                    movie_space_list.append("%s-%s" % (used, total))
                    movie_used += used
                    movie_total += total
            # 电视目录
            tv_paths = media.get('tv_path')
            if not isinstance(tv_paths, list):
                tv_paths = [tv_paths]
            tv_used, tv_total = 0, 0
            tv_space_list = []
            for tv_path in tv_paths:
                if not tv_path:
                    continue
                used, total = get_used_of_partition(tv_path)
                if "%s-%s" % (used, total) not in tv_space_list:
                    tv_space_list.append("%s-%s" % (used, total))
                    tv_used += used
                    tv_total += total
            # 动漫目录
            anime_paths = media.get('anime_path')
            if not isinstance(anime_paths, list):
                anime_paths = [anime_paths]
            anime_used, anime_total = 0, 0
            anime_space_list = []
            for anime_path in anime_paths:
                if not anime_path:
                    continue
                used, total = get_used_of_partition(anime_path)
                if "%s-%s" % (used, total) not in anime_space_list:
                    anime_space_list.append("%s-%s" % (used, total))
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

        return render_template("index.html",
                               ServerSucess=ServerSucess,
                               MediaCount={'MovieCount': MovieCount, 'SeriesCount': SeriesCount,
                                           'SongCount': SongCount},
                               Activitys=Activity,
                               UserCount=UserCount,
                               FreeSpace=FreeSpace,
                               TotalSpace=TotalSpace,
                               UsedSapce=UsedSapce,
                               UsedPercent=UsedPercent
                               )

    # 影音搜索页面
    @App.route('/search', methods=['POST', 'GET'])
    @login_required
    def search():
        # 查询结果
        SearchWord = request.args.get("s")
        NeedSearch = request.args.get("f")
        res = get_search_results()
        return render_template("search.html",
                               SearchWord=SearchWord or "",
                               NeedSearch=NeedSearch or "",
                               Count=len(res),
                               Items=res)

    # 订阅关键字页面
    @App.route('/rss', methods=['POST', 'GET'])
    @login_required
    def rss():
        # 获取订阅关键字
        movie_key_list = get_movie_keys()
        tv_key_list = get_tv_keys()
        return render_template("rss.html",
                               MovieKeys=','.join('%s' % key[0] for key in movie_key_list),
                               TvKeys=','.join('%s' % key[0] for key in tv_key_list))

    # 站点维护页面
    @App.route('/site', methods=['POST', 'GET'])
    @login_required
    def site():
        Sites = get_config_site()
        return render_template("site.html",
                               Sites=Sites)

    # 推荐页面
    @App.route('/recommend', methods=['POST', 'GET'])
    @login_required
    def recommend():
        RecommendType = request.args.get("t")
        if RecommendType in ['hm', 'ht', 'nm', 'nt']:
            CurrentPage = request.args.get("page")
            if not CurrentPage:
                CurrentPage = 1
            else:
                CurrentPage = int(CurrentPage)

            if CurrentPage < 5:
                StartPage = 1
                EndPage = 6
            else:
                StartPage = CurrentPage - 2
                EndPage = CurrentPage + 3
            PageRange = range(StartPage, EndPage)
        else:
            PageRange = None
            CurrentPage = 0
        if RecommendType == "hm":
            # TMDB热门电影
            res_list = Media().get_tmdb_hot_movies(CurrentPage)
        elif RecommendType == "ht":
            # TMDB热门电视剧
            res_list = Media().get_tmdb_hot_tvs(CurrentPage)
        elif RecommendType == "nm":
            # TMDB最新电影
            res_list = Media().get_tmdb_new_movies(CurrentPage)
        elif RecommendType == "nt":
            # TMDB最新电视剧
            res_list = Media().get_tmdb_new_tvs(CurrentPage)
        elif RecommendType == "dbom":
            # 豆瓣正在上映
            res_list = DoubanHot().get_douban_online_movie()
        elif RecommendType == "dbhm":
            # 豆瓣热门电影
            res_list = DoubanHot().get_douban_hot_movie()
        elif RecommendType == "dbht":
            # 豆瓣热门电视剧
            res_list = DoubanHot().get_douban_hot_tv()
        elif RecommendType == "dbnm":
            # 豆瓣最新电影
            res_list = DoubanHot().get_douban_new_movie()
        elif RecommendType == "dbnt":
            # 豆瓣最新电视剧
            res_list = DoubanHot().get_douban_new_tv()
        else:
            res_list = []

        Items = []
        TvKeys = ["%s" % key[0] for key in get_tv_keys()]
        MovieKeys = ["%s" % key[0] for key in get_movie_keys()]
        for res in res_list:
            rid = res.get('id')
            if RecommendType in ['hm', 'nm', 'dbom', 'dbhm', 'dbnm']:
                title = res.get('title')
                if title in MovieKeys:
                    fav = 1
                else:
                    fav = 0
                date = res.get('release_date')
            else:
                title = res.get('name')
                if title in TvKeys:
                    fav = 1
                else:
                    fav = 0
                date = res.get('first_air_date')
            image = res.get('poster_path')
            if RecommendType in ['hm', 'nm', 'ht', 'nt']:
                image = "https://image.tmdb.org/t/p/original/%s" % image
            else:
                image = "https://images.weserv.nl/?url=%s" % image
            vote = res.get('vote_average')
            overview = res.get('overview')
            item = {'id': rid, 'title': title, 'fav': fav, 'date': date, 'vote': vote,
                    'image': image, 'overview': overview}
            Items.append(item)

        return render_template("recommend.html",
                               Items=Items,
                               RecommendType=RecommendType,
                               CurrentPage=CurrentPage,
                               PageRange=PageRange)

    # 影音搜索页面
    @App.route('/download', methods=['POST', 'GET'])
    @login_required
    def download():
        DownloadCount = 0
        Client, Torrents = Downloader().pt_downloading_torrents()
        DispTorrents = []
        for torrent in Torrents:
            if Client == DownloaderType.QB:
                name = torrent.get('name')
                # 进度
                progress = round(torrent.get('progress') * 100, 1)
                if torrent.get('state') in ['pausedDL']:
                    state = "Stoped"
                    speed = "已暂停"
                else:
                    state = "Downloading"
                    dlspeed = str_filesize(torrent.get('dlspeed'))
                    upspeed = str_filesize(torrent.get('upspeed'))
                    if progress >= 100:
                        speed = "%s%sB/s %s%sB/s" % (chr(8595), dlspeed, chr(8593), upspeed)
                    else:
                        eta = str_timelong(torrent.get('eta'))
                        speed = "%s%sB/s %s%sB/s %s" % (chr(8595), dlspeed, chr(8593), upspeed, eta)
                # 主键
                key = torrent.get('hash')
            else:
                name = torrent.name
                if torrent.status in ['stopped']:
                    state = "Stoped"
                    speed = "已暂停"
                else:
                    state = "Downloading"
                    dlspeed = str_filesize(torrent.rateDownload)
                    upspeed = str_filesize(torrent.rateUpload)
                    speed = "%s%sB/s %s%sB/s" % (chr(8595), dlspeed, chr(8593), upspeed)
                # 进度
                progress = round(torrent.progress)
                # 主键
                key = torrent.id

            if not name:
                continue
            # 识别
            media_info = Media().get_media_info(name)
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
            poster_path = media_info.poster_path
            torrent_info = {'id': key, 'title': title, 'speed': speed, 'image': poster_path or "", 'state': state,
                            'progress': progress}
            if torrent_info not in DispTorrents:
                DownloadCount += 1
                DispTorrents.append(torrent_info)

        return render_template("download.html",
                               DownloadCount=DownloadCount,
                               Torrents=DispTorrents)

    # 服务页面
    @App.route('/service', methods=['POST', 'GET'])
    @login_required
    def service():
        scheduler_cfg_list = []
        pt = config.get_config('pt')
        if pt:
            # RSS订阅
            pt_check_interval = pt.get('pt_check_interval')
            if pt_check_interval:
                tim_rssdownload = str(round(pt_check_interval / 60)) + " 分钟"
                rss_state = 'ON'
            else:
                tim_rssdownload = ""
                rss_state = 'OFF'
            svg = '''
                <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-cloud-download" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                     <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                     <path d="M19 18a3.5 3.5 0 0 0 0 -7h-1a5 4.5 0 0 0 -11 -2a4.6 4.4 0 0 0 -2.1 8.4"></path>
                     <line x1="12" y1="13" x2="12" y2="22"></line>
                     <polyline points="9 19 12 22 15 19"></polyline>
                </svg>
            '''
            color = "blue"
            scheduler_cfg_list.append(
                {'name': 'RSS订阅', 'time': tim_rssdownload, 'state': rss_state, 'id': 'rssdownload', 'svg': svg,
                 'color': color})

            # PT文件转移
            pt_monitor = pt.get('pt_monitor')
            if pt_monitor:
                tim_pttransfer = str(round(PT_TRANSFER_INTERVAL / 60)) + " 分钟"
                sta_pttransfer = 'ON'
            else:
                tim_pttransfer = ""
                sta_pttransfer = 'OFF'
            svg = '''
            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-replace" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                 <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                 <rect x="3" y="3" width="6" height="6" rx="1"></rect>
                 <rect x="15" y="15" width="6" height="6" rx="1"></rect>
                 <path d="M21 11v-3a2 2 0 0 0 -2 -2h-6l3 3m0 -6l-3 3"></path>
                 <path d="M3 13v3a2 2 0 0 0 2 2h6l-3 -3m0 6l3 -3"></path>
            </svg>
            '''
            color = "green"
            scheduler_cfg_list.append(
                {'name': 'PT下载转移', 'time': tim_pttransfer, 'state': sta_pttransfer, 'id': 'pttransfer', 'svg': svg,
                 'color': color})

            # PT删种
            pt_seeding_config_time = pt.get('pt_seeding_time')
            if pt_seeding_config_time:
                pt_seeding_time = str(round(pt_seeding_config_time / 3600)) + " 小时"
                sta_autoremovetorrents = 'ON'
                svg = '''
                <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-trash" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                     <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                     <line x1="4" y1="7" x2="20" y2="7"></line>
                     <line x1="10" y1="11" x2="10" y2="17"></line>
                     <line x1="14" y1="11" x2="14" y2="17"></line>
                     <path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12"></path>
                     <path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3"></path>
                </svg>
                '''
                color = "twitter"
                scheduler_cfg_list.append(
                    {'name': 'PT删种', 'time': pt_seeding_time, 'state': sta_autoremovetorrents,
                     'id': 'autoremovetorrents', 'svg': svg, 'color': color})

            # PT自动签到
            tim_ptsignin = pt.get('ptsignin_cron')
            if tim_ptsignin:
                if str(tim_ptsignin).find(':') == -1:
                    tim_ptsignin = "%s 小时" % tim_ptsignin
                sta_ptsignin = 'ON'
                svg = '''
                <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-user-check" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                     <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                     <circle cx="9" cy="7" r="4"></circle>
                     <path d="M3 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2"></path>
                     <path d="M16 11l2 2l4 -4"></path>
                </svg>
                '''
                color = "facebook"
                scheduler_cfg_list.append(
                    {'name': 'PT站签到', 'time': tim_ptsignin, 'state': sta_ptsignin, 'id': 'ptsignin', 'svg': svg,
                     'color': color})

        # 目录同步
        sync = config.get_config('sync')
        if sync:
            sync_path = sync.get('sync_path')
            if sync_path:
                sta_sync = 'ON'
                svg = '''
                <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-refresh" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                     <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                     <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4"></path>
                     <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4"></path>
                </svg>
                '''
                color = "orange"
                scheduler_cfg_list.append(
                    {'name': '目录同步', 'time': '实时监控', 'state': sta_sync, 'id': 'sync', 'svg': svg, 'color': color})
        # 豆瓣同步
        douban = config.get_config('douban')
        if douban:
            interval = douban.get('interval')
            if interval:
                interval = "%s 小时" % interval
                sta_douban = "ON"
                svg = '''
                <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-bookmarks" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                   <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                   <path d="M13 7a2 2 0 0 1 2 2v12l-5 -3l-5 3v-12a2 2 0 0 1 2 -2h6z"></path>
                   <path d="M9.265 4a2 2 0 0 1 1.735 -1h6a2 2 0 0 1 2 2v12l-1 -.6"></path>
                </svg>
                '''
                color = "pink"
                scheduler_cfg_list.append(
                    {'name': '豆瓣收藏', 'time': interval, 'state': sta_douban, 'id': 'douban', 'svg': svg, 'color': color})

        # 未识别转移
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-hand-move" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
           <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
           <path d="M8 13v-8.5a1.5 1.5 0 0 1 3 0v7.5"></path>
           <path d="M11 11.5v-2a1.5 1.5 0 0 1 3 0v2.5"></path>
           <path d="M14 10.5a1.5 1.5 0 0 1 3 0v1.5"></path>
           <path d="M17 11.5a1.5 1.5 0 0 1 3 0v4.5a6 6 0 0 1 -6 6h-2h.208a6 6 0 0 1 -5.012 -2.7l-.196 -.3c-.312 -.479 -1.407 -2.388 -3.286 -5.728a1.5 1.5 0 0 1 .536 -2.022a1.867 1.867 0 0 1 2.28 .28l1.47 1.47"></path>
           <path d="M2.541 5.594a13.487 13.487 0 0 1 2.46 -1.427"></path>
           <path d="M14 3.458c1.32 .354 2.558 .902 3.685 1.612"></path>
        </svg>
        '''
        scheduler_cfg_list.append(
            {'name': '未识别转移', 'time': '手动', 'state': 'OFF', 'id': 'rename', 'svg': svg, 'color': 'yellow'})

        # 配置修改
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-settings" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
           <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
           <path d="M10.325 4.317c.426 -1.756 2.924 -1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543 -.94 3.31 .826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756 .426 1.756 2.924 0 3.35a1.724 1.724 0 0 0 -1.066 2.573c.94 1.543 -.826 3.31 -2.37 2.37a1.724 1.724 0 0 0 -2.572 1.065c-.426 1.756 -2.924 1.756 -3.35 0a1.724 1.724 0 0 0 -2.573 -1.066c-1.543 .94 -3.31 -.826 -2.37 -2.37a1.724 1.724 0 0 0 -1.065 -2.572c-1.756 -.426 -1.756 -2.924 0 -3.35a1.724 1.724 0 0 0 1.066 -2.573c-.94 -1.543 .826 -3.31 2.37 -2.37c1 .608 2.296 .07 2.572 -1.065z"></path>
           <circle cx="12" cy="12" r="3"></circle>
        </svg>
        '''
        scheduler_cfg_list.append(
            {'name': '配置文件', 'time': '', 'state': 'OFF', 'id': 'config', 'svg': svg, 'color': 'purple'})

        # 实时日志
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-terminal" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
           <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
           <path d="M5 7l5 5l-5 5"></path>
           <line x1="12" y1="19" x2="19" y2="19"></line>
        </svg>
        '''
        scheduler_cfg_list.append(
            {'name': '实时日志', 'time': '', 'state': 'OFF', 'id': 'logging', 'svg': svg, 'color': 'indigo'})

        return render_template("service.html",
                               Count=len(scheduler_cfg_list),
                               SchedulerTasks=scheduler_cfg_list)

    # 历史记录页面
    @App.route('/history', methods=['POST', 'GET'])
    @login_required
    def history():
        PageNum = request.args.get("pagenum")
        if not PageNum:
            PageNum = 30
        SearchStr = request.args.get("s")
        if not SearchStr:
            SearchStr = ""
        CurrentPage = request.args.get("page")
        if not CurrentPage:
            CurrentPage = 1
        else:
            CurrentPage = int(CurrentPage)
        totalCount, historys = get_transfer_history(SearchStr, CurrentPage, PageNum)
        if totalCount:
            totalCount = totalCount[0][0]
        else:
            totalCount = 0

        TotalPage = floor(totalCount / PageNum) + 1

        if TotalPage <= 5:
            StartPage = 1
            EndPage = TotalPage
        else:
            if CurrentPage <= 3:
                StartPage = 1
                EndPage = 5
            else:
                StartPage = CurrentPage - 3
                if TotalPage > CurrentPage + 3:
                    EndPage = CurrentPage + 3
                else:
                    EndPage = TotalPage

        PageRange = range(StartPage, EndPage + 1)

        return render_template("history.html",
                               TotalCount=totalCount,
                               Count=len(historys),
                               Historys=historys,
                               Search=SearchStr,
                               CurrentPage=CurrentPage,
                               TotalPage=TotalPage,
                               PageRange=PageRange,
                               PageNum=PageNum)

    # 事件响应
    @App.route('/do', methods=['POST', 'GET'])
    def do():
        if request.method == "POST":
            cmd = request.form.get("cmd")
            data = request.form.get("data")
        else:
            cmd = request.args.get("cmd")
            data = request.args.get("data")
        if data:
            data = json.loads(data)
        if cmd:
            # 启动定时服务
            if cmd == "sch":
                commands = {
                    "autoremovetorrents": AutoRemoveTorrents().run_schedule,
                    "pttransfer": PTTransfer().run_schedule,
                    "ptsignin": PTSignin().run_schedule,
                    "sync": Sync().transfer_all_sync,
                    "rssdownload": RSSDownloader().run_schedule,
                    "douban": DoubanSync().run_schedule
                }
                sch_item = data.get("item")
                if sch_item and commands.get(sch_item):
                    _thread.start_new_thread(commands.get(sch_item), ())
                return {"retmsg": "服务已启动", "item": sch_item}

            # 电影关键字
            if cmd == "moviekey":
                movie_keys = data.get("movie_keys")
                if movie_keys:
                    if movie_keys.find(',') != -1:
                        if movie_keys.endswith(','):
                            movie_keys = movie_keys[0, -1]
                        movie_keys = movie_keys.split(',')
                    else:
                        movie_keys = [movie_keys]
                    delete_all_movie_keys()
                    for movie_key in movie_keys:
                        insert_movie_key(movie_key)
                else:
                    delete_all_movie_keys()
                return {"retcode": 0}

            # 电视剧关键字
            if cmd == "tvkey":
                tv_keys = data.get("tv_keys")
                if tv_keys:
                    if tv_keys.find(',') != -1:
                        if tv_keys.endswith(','):
                            tv_keys = tv_keys[0, -1]
                        tv_keys = tv_keys.split(',')
                    else:
                        tv_keys = [tv_keys]
                    delete_all_tv_keys()
                    for tv_key in tv_keys:
                        insert_tv_key(tv_key)
                else:
                    delete_all_tv_keys()
                return {"retcode": 0}

            # 检索资源
            if cmd == "search":
                # 开始检索
                search_word = data.get("search_word")
                if search_word:
                    search_medias_for_web(search_word)
                return {"retcode": 0}

            # 添加下载
            if cmd == "download":
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
                    Message().send_download_message(SearchType.WEB, msg_item)
                return {"retcode": 0}

            # 添加RSS关键字
            if cmd == "addrss":
                name = data.get("name")
                mtype = data.get("type")
                if name and mtype:
                    if mtype in ['nm', 'hm', 'dbom', 'dbhm', 'dbnm']:
                        insert_movie_key(name)
                    else:
                        insert_tv_key(name)
                return {"retcode": 0}

            # 开始下载
            if cmd == "pt_start":
                tid = data.get("id")
                if id:
                    Downloader().start_torrents(tid)
                return {"retcode": 0, "id": tid}

            # 停止下载
            if cmd == "pt_stop":
                tid = data.get("id")
                if id:
                    Downloader().stop_torrents(tid)
                return {"retcode": 0, "id": tid}

            # 删除下载
            if cmd == "pt_remove":
                tid = data.get("id")
                if id:
                    Downloader().delete_torrents(tid)
                return {"retcode": 0, "id": tid}

            # 查询具体种子的信息
            if cmd == "pt_info":
                ids = data.get("ids")
                Client, Torrents = Downloader().get_pt_torrents(torrent_ids=ids)
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

            # 手工转移列表
            if cmd == "rename_path":
                paths = get_transfer_unknown_paths()
                return {"paths": paths}

            # 删除路径
            if cmd == "del_rename_path":
                paths = data.get("path")
                path = paths.split("|")[0]
                retcode = delete_transfer_unknown(path)
                return {"retcode": retcode}

            # 手工转移
            if cmd == "rename":
                logid = data.get("logid")
                if logid:
                    paths = get_transfer_path_by_id(logid)
                    if paths:
                        path = os.path.join(paths[0][0], paths[0][1])
                        dest_dir = paths[0][2]
                    else:
                        return {"retcode": -1, "retmsg": "未查询到转移日志记录"}
                else:
                    path = data.get("path", "")
                    paths = path.split("|")
                    path = paths[0]
                    if len(paths) > 1:
                        dest_dir = paths[1]
                    else:
                        dest_dir = None
                if not dest_dir or dest_dir == "null":
                    dest_dir = ""
                if not path:
                    return {"retcode": -1, "retmsg": "输入路径有误"}
                tmdbid = data.get("tmdb")
                title = data.get("title")
                year = data.get("year")
                mtype = data.get("type")
                season = data.get("season")
                if mtype == "TV":
                    media_type = MediaType.TV
                elif mtype == "MOV":
                    media_type = MediaType.MOVIE
                else:
                    media_type = MediaType.ANIME
                tmdb_info = Media().get_media_info_manual(media_type, title, year, tmdbid)
                if not tmdb_info:
                    return {"retcode": 1, "retmsg": "转移失败，无法查询到TMDB信息"}
                succ_flag, ret_msg = FileTransfer().transfer_media(in_from=SyncType.MAN,
                                                                   in_path=path,
                                                                   target_dir=dest_dir,
                                                                   tmdb_info=tmdb_info,
                                                                   media_type=media_type,
                                                                   season=season)
                if succ_flag:
                    if logid:
                        insert_transfer_blacklist(path)
                    else:
                        update_transfer_unknown_state(path)
                    return {"retcode": 0, "retmsg": "转移成功"}
                else:
                    return {"retcode": 2, "retmsg": ret_msg}

            # 读取配置文件
            if cmd == "load_config":
                cfg = open(config.get_config_path(), mode="r", encoding="utf8")
                config_str = cfg.read()
                cfg.close()
                return {"config_str": config_str}

            # 保存配置文件
            if cmd == "save_config":
                editer_str = data.get('editer_str')
                if editer_str:
                    cfg = open(config.get_config_path(), mode="w", encoding="utf8")
                    cfg.write(editer_str)
                    cfg.flush()
                    cfg.close()
                    # 生效配置
                    config.init_config()
                    for instance in INSTANCES:
                        if instance.__dict__.get("init_config"):
                            instance().init_config()
                    # 重启服务
                    restart_monitor()

                return {"retcode": 0}

            # 删除识别记录及文件
            if cmd == "delete_history":
                logid = data.get('logid')
                paths = get_transfer_path_by_id(logid)
                if paths:
                    dest_dir = paths[0][2]
                    title = paths[0][3]
                    category = paths[0][4]
                    year = paths[0][5]
                    se = paths[0][6]
                    mtype = paths[0][7]
                    dest_path = FileTransfer().get_dest_path_by_info(dest=dest_dir, mtype=mtype, title=title,
                                                                     category=category, year=year, season=se)
                    if dest_path and dest_path.find(title) != -1:
                        try:
                            shutil.rmtree(dest_path)
                            delete_transfer_log_by_id(logid)
                        except Exception as e:
                            log.console(str(e))
                return {"retcode": 0}

            # 查询实时日志
            if cmd == "logging":
                if LOG_QUEUE:
                    return {"text": "<br/>".join(list(LOG_QUEUE))}
                return {"text": ""}

            # 检查新版本
            if cmd == "version":
                version = ""
                info = ""
                code = 0
                try:
                    response = requests.get("https://api.github.com/repos/jxxghp/nas-tools/releases/latest", timeout=10,
                                            proxies=config.get_proxies())
                    if response:
                        ver_json = response.json()
                        version = ver_json["tag_name"]
                        info = f'<a href="{ver_json["html_url"]}" target="_blank">{version}</a>'
                except Exception as e:
                    log.console(str(e))
                    code = -1
                return {"code": code, "version": version, "info": info}

            # 查询实时日志
            if cmd == "update_site":
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
                return {"code": ret}

            # 查询单个站点信息
            if cmd == "get_site":
                tid = data.get("id")
                if tid:
                    ret = get_site_by_id(tid)
                else:
                    ret = []
                return {"code": 0, "site": ret}

            # 删除单个站点信息
            if cmd == "del_site":
                tid = data.get("id")
                if tid:
                    ret = delete_config_site(tid)
                    return {"code": ret}
                else:
                    return {"code": 0}

            # 查询搜索过滤规则
            if cmd == "get_search_rule":
                ret = get_config_search_rule()
                return {"code": 0, "rule": ret}

            # 更新搜索过滤规则
            if cmd == "update_search_rule":
                include = data.get('search_include')
                exclude = data.get('search_exclude')
                note = data.get('search_note')
                size = data.get('search_size')
                ret = update_config_search_rule(include=include, exclude=exclude, note=note, size=size)
                return {"code": ret}

    # 响应企业微信消息
    @App.route('/wechat', methods=['GET', 'POST'])
    def wechat():
        message = config.get_config('message')
        sToken = message.get('wechat', {}).get('Token')
        sEncodingAESKey = message.get('wechat', {}).get('EncodingAESKey')
        sCorpID = message.get('wechat', {}).get('corpid')
        if not sToken or not sEncodingAESKey or not sCorpID:
            return
        wxcpt = WXBizMsgCrypt(sToken, sEncodingAESKey, sCorpID)
        sVerifyMsgSig = request.args.get("msg_signature")
        sVerifyTimeStamp = request.args.get("timestamp")
        sVerifyNonce = request.args.get("nonce")

        if request.method == 'GET':
            sVerifyEchoStr = request.args.get("echostr")
            log.debug("收到微信验证请求: echostr= %s" % sVerifyEchoStr)
            ret, sEchoStr = wxcpt.VerifyURL(sVerifyMsgSig, sVerifyTimeStamp, sVerifyNonce, sVerifyEchoStr)
            if ret != 0:
                log.error("微信请求验证失败 VerifyURL ret: %s" % str(ret))
            # 验证URL成功，将sEchoStr返回给企业号
            return sEchoStr
        else:
            sReqData = request.data
            log.debug("收到微信消息：" + str(sReqData))
            ret, sMsg = wxcpt.DecryptMsg(sReqData, sVerifyMsgSig, sVerifyTimeStamp, sVerifyNonce)
            if ret != 0:
                log.error("解密微信消息失败 DecryptMsg ret：%s" % str(ret))
            xml_tree = ETree.fromstring(sMsg)
            reponse_text = ""
            try:
                msg_type = xml_tree.find("MsgType").text
                user_id = xml_tree.find("FromUserName").text
                if msg_type == "event":
                    event_key = xml_tree.find("EventKey").text
                    log.info("点击菜单：" + event_key)
                    content = WECHAT_MENU[event_key.split('#')[2]]
                else:
                    content = xml_tree.find("Content").text
                    log.info("消息内容：" + content)
                    reponse_text = content
            except Exception as err:
                log.error("发生错误：%s" % str(err))
                return make_response("", 200)
            # 处理消息内容
            content = content.strip()
            if content:
                handle_message_job(content, SearchType.WX, user_id)
            return make_response(reponse_text, 200)

    # Emby消息通知
    @App.route('/jellyfin', methods=['POST'])
    @App.route('/emby', methods=['POST'])
    def emby():
        request_json = json.loads(request.form.get('data', {}))
        # log.debug("输入报文：" + str(request_json))
        event = WebhookEvent(request_json)
        event.report_to_discord()
        return 'Success'

    @App.route('/telegram', methods=['POST', 'GET'])
    def telegram():
        msg_json = request.get_json()
        if msg_json:
            message = msg_json.get("message", {})
            text = message.get("text")
            user_id = message.get("from", {}).get("id")
            if text:
                handle_message_job(text, SearchType.TG, user_id)
        return 'ok'

    # 处理消息事件
    def handle_message_job(msg, in_from=SearchType.OT, user_id=None):
        if not msg:
            return
        commands = {
            "/ptr": {"func": AutoRemoveTorrents().run_schedule, "desp": "PT删种"},
            "/ptt": {"func": PTTransfer().run_schedule, "desp": "PT下载转移"},
            "/pts": {"func": PTSignin().run_schedule, "desp": "PT站签到"},
            "/rst": {"func": Sync().transfer_all_sync, "desp": "监控目录全量同步"},
            "/rss": {"func": RSSDownloader().run_schedule, "desp": "RSS订阅"},
            "/db": {"func": DoubanSync().run_schedule, "desp": "豆瓣收藏同步"}
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
        else:
            # PT检索
            _thread.start_new_thread(Searcher().search_one_media, (msg, in_from, user_id,))

    return App
