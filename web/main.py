import _thread
import logging

from flask import Flask, request, json, render_template, make_response, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

import log
from pt.downloader import Downloader
from pt.jackett import Jackett
from rmt.filetransfer import FileTransfer
from rmt.media import Media
from rmt.metainfo import MetaInfo
from scheduler.autoremove_torrents import AutoRemoveTorrents
from scheduler.douban_sync import DoubanSync
from scheduler.pt_signin import PTSignin
from scheduler.pt_transfer import PTTransfer
from scheduler.rss_download import RSSDownloader
from message.send import Message

from config import WECHAT_MENU, get_config, save_config, PT_TRANSFER_INTERVAL, BACKDROP_DEFAULT_IMAGE
from utils.functions import get_used_of_partition, str_filesize, str_timelong
from utils.sqls import get_jackett_result_by_id, get_jackett_results, get_movie_keys, get_tv_keys, insert_movie_key, \
    insert_tv_key, delete_all_tv_keys, delete_all_movie_keys
from utils.types import MediaType, SearchType, DownloaderType
from version import APP_VERSION
from web.backend.emby import Emby
from web.backend.search_torrents import search_medias_for_web
from web.backend.WXBizMsgCrypt3 import WXBizMsgCrypt
import xml.etree.cElementTree as ETree

login_manager = LoginManager()
login_manager.login_view = "login"


# Flask实例
def create_flask_app():
    config = get_config()
    app_cfg = config.get('app')
    if not app_cfg:
        return None
    else:
        if app_cfg.get('simple_mode'):
            # 精简模式不启用WEBUI
            return None
        elif not app_cfg.get('web_port'):
            return None
        elif not app_cfg.get('login_user'):
            return None
        elif not app_cfg.get('login_password'):
            return None

    app = Flask(__name__)
    app.config['JSON_AS_ASCII'] = False
    app.secret_key = 'jxxghp'
    applog = logging.getLogger('werkzeug')
    applog.setLevel(logging.ERROR)
    app.logger.disabled = True
    applog.disabled = True
    login_manager.init_app(app)

    EmbyClient = Emby()
    USERS = [{
        "id": 1,
        "name": config.get('app', {}).get('login_user'),
        "password": generate_password_hash(config.get('app', {}).get('login_password'))
    }]

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

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html", error=error), 404

    @app.errorhandler(500)
    def page_server_error(error):
        return render_template("500.html", error=error), 500

    # 主页面
    @app.before_request
    def before_request():
        if request.url.startswith('http://'):
            ssl_cert = config['app'].get('ssl_cert')
            if ssl_cert:
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)

    # 登录页面
    @app.route('/', methods=['POST', 'GET'])
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            return render_template('login.html')
        else:
            username = request.form.get('username')
            if not username:
                return render_template('login.html', err_msg="请输入用户名！")
            password = request.form.get('password')
            user_info = get_user(username)
            if not user_info:
                return render_template('login.html', err_msg="用户名或密码错误！")
            # 创建用户实体
            user = User(user_info)
            # 校验密码
            if user.verify_password(password):
                # 创建用户 Session
                login_user(user)
                return redirect(request.args.get('next') or url_for('home'))
            else:
                return render_template('login.html', err_msg="用户名或密码错误！")

    # 首页
    @app.route('/home', methods=['POST', 'GET'])
    @login_required
    def home():
        # 获取媒体数量
        EmbySucess = 1
        MovieCount = 0
        SeriesCount = 0
        SongCount = 0
        media_count = EmbyClient.get_emby_medias_count()
        if media_count:
            MovieCount = "{:,}".format(media_count.get('MovieCount'))
            SeriesCount = "{:,}".format(media_count.get('SeriesCount'))
            SongCount = "{:,}".format(media_count.get('SongCount'))
        else:
            EmbySucess = 0

        # 获得活动日志
        Activity = EmbyClient.get_emby_activity_log(30)

        # 用户数量
        UserCount = EmbyClient.get_emby_user_count()

        # 磁盘空间
        UsedSapce = 0
        TotalSpace = 0
        FreeSpace = 0
        UsedPercent = 0
        if config.get('media'):
            # 电影目录
            movie_path = config['media'].get('movie_path')
            if movie_path:
                movie_used, movie_total = get_used_of_partition(movie_path)
            else:
                movie_used, movie_total = 0, 0
            # 电视目录
            tv_path = config['media'].get('tv_path')
            if tv_path:
                tv_used, tv_total = get_used_of_partition(movie_path)
            else:
                tv_used, tv_total = 0, 0
            # 总空间
            if movie_total == tv_total:
                TotalSpace = movie_total
            else:
                TotalSpace = movie_total + tv_total
            # 已使用空间
            if movie_used == tv_used:
                UsedSapce = movie_used
            else:
                UsedSapce = movie_used + tv_used

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
                               EmbySucess=EmbySucess,
                               MediaCount={'MovieCount': MovieCount, 'SeriesCount': SeriesCount,
                                           'SongCount': SongCount},
                               Activitys=Activity,
                               UserCount=UserCount,
                               FreeSpace=FreeSpace,
                               TotalSpace=TotalSpace,
                               UsedSapce=UsedSapce,
                               UsedPercent=UsedPercent,
                               AppVersion=APP_VERSION
                               )

    # 影音搜索页面
    @app.route('/search', methods=['POST', 'GET'])
    @login_required
    def search():
        # 查询结果
        res = get_jackett_results()
        return render_template("search.html",
                               Count=len(res),
                               Items=res,
                               AppVersion=APP_VERSION)

    # 站点订阅页面
    @app.route('/sites', methods=['POST', 'GET'])
    @login_required
    def sites():
        # 获取订阅关键字
        movie_key_list = get_movie_keys()
        tv_key_list = get_tv_keys()
        return render_template("sites.html",
                               MovieKeys=','.join('%s' % key for key in movie_key_list),
                               TvKeys=','.join('%s' % key for key in tv_key_list),
                               AppVersion=APP_VERSION)

    # 推荐页面
    @app.route('/recommend', methods=['POST', 'GET'])
    @login_required
    def recommend():
        RecommendType = request.args.get("t")
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
        if RecommendType == "hm":
            # 热门电影
            res_list = Media().get_tmdb_hot_movies(CurrentPage)
        elif RecommendType == "ht":
            # 热门电影
            res_list = Media().get_tmdb_hot_tvs(CurrentPage)
        elif RecommendType == "nm":
            # 热门电影
            res_list = Media().get_tmdb_new_movies(CurrentPage)
        elif RecommendType == "nt":
            # 热门电影
            res_list = Media().get_tmdb_new_tvs(CurrentPage)
        else:
            res_list = []

        Items = []
        TvKeys = get_tv_keys()
        MovieKeys = get_movie_keys()
        for res in res_list:
            rid = res.get('id')
            if RecommendType in ['hm', 'nm']:
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
            vote = res.get('vote_average')
            item = {'id': rid, 'title': title, 'fav': fav, 'date': date, 'vote': vote,
                    'image': "https://image.tmdb.org/t/p/original/%s" % image}
            Items.append(item)

        return render_template("recommend.html",
                               Items=Items,
                               RecommendType=RecommendType,
                               CurrentPage=CurrentPage,
                               PageRange=PageRange,
                               AppVersion=APP_VERSION)

    # 影音搜索页面
    @app.route('/download', methods=['POST', 'GET'])
    @login_required
    def download():
        DownloadCount = 0
        Client, Torrents = Downloader().get_pt_torrents()
        DispTorrents = []
        for torrent in Torrents:
            if Client == DownloaderType.QB:
                if torrent.get('state') not in ['downloading', 'forcedDL', 'pausedDL', 'stalledDL']:
                    continue
                name = torrent.get('name')
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
                progress = round(torrent.get('progress') * 100, 1)
                # 主键
                key = torrent.get('hash')
            else:
                if torrent.status not in ['downloading', 'download_pending', 'stopped']:
                    continue
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
                progress = round(torrent.progress, 1)
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
                    title = "%s (%s)" % (media_info.get_name(), year)
                else:
                    title = media_info.get_name()
                poster_path = BACKDROP_DEFAULT_IMAGE
            else:
                title = "%s (%s)" % (media_info.title, media_info.year)
                poster_path = media_info.poster_path

            torrent_info = {'id': key, 'title': title, 'speed': speed, 'image': poster_path, 'state': state, 'progress': progress}
            if torrent_info not in DispTorrents:
                DownloadCount += 1
                DispTorrents.append(torrent_info)

        return render_template("download.html",
                               DownloadCount=DownloadCount,
                               Torrents=DispTorrents,
                               AppVersion=APP_VERSION)

    # 服务页面
    @app.route('/service', methods=['POST', 'GET'])
    @login_required
    def service():
        scheduler_cfg_list = []
        if config.get('pt'):
            # RSS下载
            pt_check_interval = config['pt'].get('pt_check_interval')
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
                {'name': 'RSS下载', 'time': tim_rssdownload, 'state': rss_state, 'id': 'rssdownload', 'svg': svg,
                 'color': color})

            # PT文件转移
            pt_monitor = config['pt'].get('pt_monitor')
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
                {'name': 'PT文件转移', 'time': tim_pttransfer, 'state': sta_pttransfer, 'id': 'pttransfer', 'svg': svg,
                 'color': color})

            # PT删种
            pt_seeding_config_time = config['pt'].get('pt_seeding_time')
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
            tim_ptsignin = config['pt'].get('ptsignin_cron')
            if tim_ptsignin:
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
                    {'name': 'PT自动签到', 'time': tim_ptsignin, 'state': sta_ptsignin, 'id': 'ptsignin', 'svg': svg,
                     'color': color})

        # 资源同步
        if config.get('sync'):
            sync_path = config['sync'].get('sync_path')
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
                    {'name': '资源同步', 'time': '实时监控', 'state': sta_sync, 'id': 'sync', 'svg': svg, 'color': color})
        # 豆瓣同步
        if config.get('douban'):
            interval = config['douban'].get('interval')
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

        return render_template("service.html",
                               Count=len(scheduler_cfg_list),
                               SchedulerTasks=scheduler_cfg_list,
                               AppVersion=APP_VERSION)

    # 事件响应
    @app.route('/do', methods=['POST'])
    def do():
        cmd = request.form.get("cmd")
        data = json.loads(request.form.get("data"))
        if cmd:
            # 启动定时服务
            if cmd == "sch":
                sch_item = data.get("item")
                if sch_item == "autoremovetorrents":
                    AutoRemoveTorrents().run_schedule()
                if sch_item == "pttransfer":
                    PTTransfer().run_schedule()
                if sch_item == "ptsignin":
                    PTSignin().run_schedule()
                if sch_item == "sync":
                    FileTransfer().transfer_all_sync()
                if sch_item == "rssdownload":
                    RSSDownloader().run_schedule()
                if sch_item == "douban":
                    DoubanSync().run_schedule()
                return {"retmsg": "执行完成！", "item": sch_item}

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
                results = get_jackett_result_by_id(dl_id)
                for res in results:
                    if res[7] == "TV":
                        mtype = MediaType.TV
                    else:
                        mtype = MediaType.MOVIE
                    Downloader().add_pt_torrent(res[0], mtype)
                    msg_item = MetaInfo("%s %s" % (res[1], res[2]))
                    msg_item.title = res[1]
                    msg_item.vote_average = res[5]
                    msg_item.backdrop_path = res[6]
                    msg_item.type = mtype
                    Message().send_download_message(SearchType.WEB, msg_item)
                return {"retcode": 0}

            # 添加RSS关键字
            if cmd == "addrss":
                name = data.get("name")
                mtype = data.get("type")
                if name and mtype:
                    if mtype in ['nm', 'hm']:
                        insert_movie_key(name)
                    else:
                        insert_tv_key(name)
                return {"retcode": 0}

            # 删除RSS关键字
            if cmd == "delrss":
                name = data.get("name")
                mtype = data.get("type")
                if name and mtype:
                    if mtype in ['nm', 'hm']:
                        movie_keys = config['pt'].get('movie_keys')
                        if movie_keys:
                            if not isinstance(movie_keys, list):
                                movie_keys = [movie_keys]
                            if name in movie_keys:
                                movie_keys.remove(name)
                                config['pt']['movie_keys'] = movie_keys
                                save_config(config)
                    else:
                        tv_keys = config['pt'].get('tv_keys')
                        if tv_keys:
                            if not isinstance(tv_keys, list):
                                tv_keys = [tv_keys]
                            if name in tv_keys:
                                tv_keys.remove(name)
                                config['pt']['tv_keys'] = tv_keys
                                save_config(config)
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
                        progress = round(torrent.get('progress') * 100, 1)
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

    # 响应企业微信消息
    @app.route('/wechat', methods=['GET', 'POST'])
    def wechat():
        sToken = config['message'].get('wechat', {}).get('Token')
        sEncodingAESKey = config['message'].get('wechat', {}).get('EncodingAESKey')
        sCorpID = config['message'].get('wechat', {}).get('corpid')
        if not sToken or not sEncodingAESKey or not sCorpID:
            return
        wxcpt = WXBizMsgCrypt(sToken, sEncodingAESKey, sCorpID)
        sVerifyMsgSig = request.args.get("msg_signature")
        sVerifyTimeStamp = request.args.get("timestamp")
        sVerifyNonce = request.args.get("nonce")

        if request.method == 'GET':
            sVerifyEchoStr = request.args.get("echostr")
            log.info("收到微信验证请求: echostr= %s" % sVerifyEchoStr)
            ret, sEchoStr = wxcpt.VerifyURL(sVerifyMsgSig, sVerifyTimeStamp, sVerifyNonce, sVerifyEchoStr)
            if ret != 0:
                log.error("微信请求验证失败 VerifyURL ret: %s" % str(ret))
            # 验证URL成功，将sEchoStr返回给企业号
            return sEchoStr
        else:
            sReqData = request.data
            log.info("收到微信消息：" + str(sReqData))
            ret, sMsg = wxcpt.DecryptMsg(sReqData, sVerifyMsgSig, sVerifyTimeStamp, sVerifyNonce)
            if ret != 0:
                log.error("解密微信消息失败 DecryptMsg ret：%s" % str(ret))
            xml_tree = ETree.fromstring(sMsg)
            reponse_text = ""
            try:
                msg_type = xml_tree.find("MsgType").text
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
            if content == "/ptr":
                _thread.start_new_thread(AutoRemoveTorrents().run_schedule, ())
            elif content == "/ptt":
                _thread.start_new_thread(PTTransfer().run_schedule, ())
            elif content == "/pts":
                _thread.start_new_thread(PTSignin().run_schedule, ())
            elif content == "/rst":
                _thread.start_new_thread(FileTransfer().transfer_all_sync, ())
            elif content == "/rss":
                _thread.start_new_thread(RSSDownloader().run_schedule, ())
            elif content == "/db":
                _thread.start_new_thread(DoubanSync().run_schedule, ())
            elif content.startswith("http://") or content.startswith("https://") or content.startswith("magnet:"):
                _thread.start_new_thread(Downloader().add_pt_torrent, (content,))
            else:
                _thread.start_new_thread(Jackett().search_one_media, (content, SearchType.WX,))

            return make_response(reponse_text, 200)

    # Emby消息通知
    @app.route('/emby', methods=['POST', 'GET'])
    def emby():
        if request.method == 'POST':
            request_json = json.loads(request.form.get('data', {}))
        else:
            server_name = request.args.get("server_name")
            user_name = request.args.get("user_name")
            device_name = request.args.get("device_name")
            ip = request.args.get("ip")
            flag = request.args.get("flag")
            request_json = {"Event": "user.login",
                            "User": {"user_name": user_name, "device_name": device_name, "device_ip": ip},
                            "Server": {"server_name": server_name},
                            "Status": flag
                            }
        # log.debug("输入报文：" + str(request_json))
        event = Emby.EmbyEvent(request_json)
        Emby().report_to_discord(event)
        return 'Success'

    # DDNS消息通知
    @app.route('/ddns', methods=['POST'])
    def ddns():
        request_json = json.loads(request.data, {})
        log.debug("【DDNS】输入报文：" + str(request_json))
        text = request_json['text']
        content = text['content']
        Message().sendmsg("【DDNS】IP地址变化", content)
        return '0'

    return app
