import base64
import datetime
import hashlib
import mimetypes
import os.path
import re
import time
import traceback
import urllib
import xml.dom.minidom
from functools import wraps
from math import floor
from pathlib import Path
from threading import Lock
from urllib import parse
from urllib.parse import unquote

from flask import Flask, request, json, render_template, make_response, session, send_from_directory, send_file, \
    redirect, Response
from flask_compress import Compress
from flask_login import LoginManager, login_user, login_required, current_user
from flask_sock import Sock
from icalendar import Calendar, Event, Alarm
from werkzeug.middleware.proxy_fix import ProxyFix

import log
from app.brushtask import BrushTask
from app.conf import ModuleConf, SystemConfig
from app.downloader import Downloader
from app.filter import Filter
from app.helper import SecurityHelper, MetaHelper, ChromeHelper, ThreadHelper
from app.indexer import Indexer
from app.media.meta import MetaInfo
from app.mediaserver import MediaServer
from app.message import Message
from app.plugins import EventManager
from app.rsschecker import RssChecker
from app.sites import Sites, SiteUserInfo
from app.subscribe import Subscribe
from app.sync import Sync
from app.torrentremover import TorrentRemover
from app.utils import DomUtils, SystemUtils, ExceptionUtils, StringUtils
from app.utils.types import *
from config import PT_TRANSFER_INTERVAL, Config, TMDB_API_DOMAINS
from web.action import WebAction
from web.apiv1 import apiv1_bp
from web.backend.WXBizMsgCrypt3 import WXBizMsgCrypt
from web.backend.user import User
from web.backend.wallpaper import get_login_wallpaper
from web.backend.web_utils import WebUtils
from web.security import require_auth

# 配置文件锁
ConfigLock = Lock()

# Flask App
App = Flask(__name__)
App.wsgi_app = ProxyFix(App.wsgi_app)
App.config['JSON_AS_ASCII'] = False
App.config['JSON_SORT_KEYS'] = False
App.config['SOCK_SERVER_OPTIONS'] = {'ping_interval': 25}
App.secret_key = os.urandom(24)
App.permanent_session_lifetime = datetime.timedelta(days=30)

# Flask Socket
Sock = Sock(App)

# 启用压缩
Compress(App)

# 登录管理模块
LoginManager = LoginManager()
LoginManager.login_view = "login"
LoginManager.init_app(App)

# SSE
LoggingSource = ""
LoggingLock = Lock()

# 路由注册
App.register_blueprint(apiv1_bp, url_prefix="/api/v1")

# fix Windows registry stuff
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')


@App.after_request
def add_header(r):
    """
    统一添加Http头，标用缓存，避免Flask多线程+Chrome内核会发生的静态资源加载出错的问题
    r.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    """
    return r


# 定义获取登录用户的方法
@LoginManager.user_loader
def load_user(user_id):
    return User().get(user_id)


# 页面不存在
@App.errorhandler(404)
def page_not_found(error):
    return render_template("404.html", error=error), 404


# 服务错误
@App.errorhandler(500)
def page_server_error(error):
    return render_template("500.html", error=error), 500


def action_login_check(func):
    """
    Action安全认证
    """

    @wraps(func)
    def login_check(*args, **kwargs):
        if not current_user.is_authenticated:
            return {"code": -1, "msg": "用户未登录"}
        return func(*args, **kwargs)

    return login_check


# 主页面
@App.route('/', methods=['GET', 'POST'])
def login():
    def redirect_to_navigation():
        """
        跳转到导航页面
        """
        # 存储当前用户
        Config().current_user = current_user.username
        # 让当前用户生效
        MediaServer().init_config()
        # 跳转页面
        if GoPage and GoPage != 'web':
            return redirect('/web#' + GoPage)
        else:
            return redirect('/web')

    def redirect_to_login(errmsg=''):
        """
        跳转到登录页面
        """
        image_code, img_title, img_link = get_login_wallpaper()
        return render_template('login.html',
                               GoPage=GoPage,
                               image_code=image_code,
                               img_title=img_title,
                               img_link=img_link,
                               err_msg=errmsg)

    # 登录认证
    if request.method == 'GET':
        GoPage = request.args.get("next") or ""
        if GoPage.startswith('/'):
            GoPage = GoPage[1:]
        if current_user.is_authenticated:
            userid = current_user.id
            username = current_user.username
            if userid is None or username is None:
                return redirect_to_login()
            else:
                # 登录成功
                return redirect_to_navigation()
        else:
            return redirect_to_login()

    else:
        GoPage = request.form.get('next') or ""
        if GoPage.startswith('/'):
            GoPage = GoPage[1:]
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember')
        if not username:
            return redirect_to_login('请输入用户名')
        user_info = User().get_user(username)
        if not user_info:
            return redirect_to_login('用户名或密码错误')
        # 校验密码
        if user_info.verify_password(password):
            # 创建用户 Session
            login_user(user_info)
            session.permanent = True if remember else False
            # 登录成功
            return redirect_to_navigation()
        else:
            return redirect_to_login('用户名或密码错误')


@App.route('/web', methods=['POST', 'GET'])
@login_required
def web():
    # 跳转页面
    GoPage = request.args.get("next") or ""
    # 判断当前的运营环境
    SystemFlag = SystemUtils.get_system()
    SyncMod = Config().get_config('media').get('default_rmt_mode')
    TMDBFlag = 1 if Config().get_config('app').get('rmt_tmdbkey') else 0
    DefaultPath = Config().get_config('media').get('media_default_path')
    if not SyncMod:
        SyncMod = "link"
    RmtModeDict = WebAction().get_rmt_modes()
    RestypeDict = ModuleConf.TORRENT_SEARCH_PARAMS.get("restype")
    PixDict = ModuleConf.TORRENT_SEARCH_PARAMS.get("pix")
    SiteFavicons = Sites().get_site_favicon()
    Indexers = Indexer().get_indexers()
    SearchSource = "douban" if Config().get_config("laboratory").get("use_douban_titles") else "tmdb"
    CustomScriptCfg = SystemConfig().get(SystemConfigKey.CustomScript)
    CooperationSites = current_user.get_authsites()
    Menus = WebAction().get_user_menus().get("menus") or []
    Commands = WebAction().get_commands()
    return render_template('navigation.html',
                           GoPage=GoPage,
                           CurrentUser=current_user,
                           SystemFlag=SystemFlag.value,
                           TMDBFlag=TMDBFlag,
                           AppVersion=WebUtils.get_current_version(),
                           RestypeDict=RestypeDict,
                           PixDict=PixDict,
                           SyncMod=SyncMod,
                           SiteFavicons=SiteFavicons,
                           RmtModeDict=RmtModeDict,
                           Indexers=Indexers,
                           SearchSource=SearchSource,
                           CustomScriptCfg=CustomScriptCfg,
                           CooperationSites=CooperationSites,
                           DefaultPath=DefaultPath,
                           Menus=Menus,
                           Commands=Commands)


# 开始
@App.route('/index', methods=['POST', 'GET'])
@login_required
def index():
    # 媒体服务器类型
    MSType = Config().get_config('media').get('media_server')
    # 获取媒体数量
    MediaCounts = WebAction().get_library_mediacount()
    if MediaCounts.get("code") == 0:
        ServerSucess = True
    else:
        ServerSucess = False

    # 获得活动日志
    Activity = WebAction().get_library_playhistory().get("result")

    # 磁盘空间
    LibrarySpaces = WebAction().get_library_spacesize()

    # 媒体库
    Librarys = MediaServer().get_libraries()
    LibrarySyncConf = SystemConfig().get(SystemConfigKey.SyncLibrary) or []

    # 继续观看
    Resumes = MediaServer().get_resume()

    # 最近添加
    Latests = MediaServer().get_latest()

    return render_template("index.html",
                           ServerSucess=ServerSucess,
                           MediaCount={'MovieCount': MediaCounts.get("Movie"),
                                       'SeriesCount': MediaCounts.get("Series"),
                                       'SongCount': MediaCounts.get("Music"),
                                       "EpisodeCount": MediaCounts.get("Episodes")},
                           Activitys=Activity,
                           UserCount=MediaCounts.get("User"),
                           FreeSpace=LibrarySpaces.get("FreeSpace"),
                           TotalSpace=LibrarySpaces.get("TotalSpace"),
                           UsedSapce=LibrarySpaces.get("UsedSapce"),
                           UsedPercent=LibrarySpaces.get("UsedPercent"),
                           MediaServerType=MSType,
                           Librarys=Librarys,
                           LibrarySyncConf=LibrarySyncConf,
                           Resumes=Resumes,
                           Latests=Latests
                           )


# 资源搜索页面
@App.route('/search', methods=['POST', 'GET'])
@login_required
def search():
    # 权限
    if current_user.is_authenticated:
        username = current_user.username
        pris = User().get_user(username).get("pris")
    else:
        pris = ""
    # 结果
    res = WebAction().get_search_result()
    SearchResults = res.get("result")
    Count = res.get("total")
    return render_template("search.html",
                           UserPris=str(pris).split(","),
                           Count=Count,
                           Results=SearchResults,
                           SiteDict=Indexer().get_indexer_hash_dict(),
                           UPCHAR=chr(8593))


# 电影订阅页面
@App.route('/movie_rss', methods=['POST', 'GET'])
@login_required
def movie_rss():
    RssItems = WebAction().get_movie_rss_list().get("result")
    RuleGroups = {str(group["id"]): group["name"] for group in Filter().get_rule_groups()}
    DownloadSettings = Downloader().get_download_setting()
    return render_template("rss/movie_rss.html",
                           Count=len(RssItems),
                           RuleGroups=RuleGroups,
                           DownloadSettings=DownloadSettings,
                           Items=RssItems
                           )


# 电视剧订阅页面
@App.route('/tv_rss', methods=['POST', 'GET'])
@login_required
def tv_rss():
    RssItems = WebAction().get_tv_rss_list().get("result")
    RuleGroups = {str(group["id"]): group["name"] for group in Filter().get_rule_groups()}
    DownloadSettings = Downloader().get_download_setting()
    return render_template("rss/tv_rss.html",
                           Count=len(RssItems),
                           RuleGroups=RuleGroups,
                           DownloadSettings=DownloadSettings,
                           Items=RssItems
                           )


# 订阅历史页面
@App.route('/rss_history', methods=['POST', 'GET'])
@login_required
def rss_history():
    mtype = request.args.get("t")
    RssHistory = WebAction().get_rss_history({"type": mtype}).get("result")
    return render_template("rss/rss_history.html",
                           Count=len(RssHistory),
                           Items=RssHistory,
                           Type=mtype
                           )


# 订阅日历页面
@App.route('/rss_calendar', methods=['POST', 'GET'])
@login_required
def rss_calendar():
    Today = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
    # 电影订阅
    RssMovieItems = WebAction().get_movie_rss_items().get("result")
    # 电视剧订阅
    RssTvItems = WebAction().get_tv_rss_items().get("result")
    return render_template("rss/rss_calendar.html",
                           Today=Today,
                           RssMovieItems=RssMovieItems,
                           RssTvItems=RssTvItems)


# 站点维护页面
@App.route('/site', methods=['POST', 'GET'])
@login_required
def sites():
    CfgSites = Sites().get_sites()
    RuleGroups = {str(group["id"]): group["name"] for group in Filter().get_rule_groups()}
    DownloadSettings = {did: attr["name"] for did, attr in Downloader().get_download_setting().items()}
    ChromeOk = ChromeHelper().get_status()
    CookieCloudCfg = SystemConfig().get(SystemConfigKey.CookieCloud)
    CookieUserInfoCfg = SystemConfig().get(SystemConfigKey.CookieUserInfo)
    return render_template("site/site.html",
                           Sites=CfgSites,
                           RuleGroups=RuleGroups,
                           DownloadSettings=DownloadSettings,
                           ChromeOk=ChromeOk,
                           CookieCloudCfg=CookieCloudCfg,
                           CookieUserInfoCfg=CookieUserInfoCfg)


# 站点列表页面
@App.route('/sitelist', methods=['POST', 'GET'])
@login_required
def sitelist():
    IndexerSites = Indexer().get_indexers(check=False)
    return render_template("site/sitelist.html",
                           Sites=IndexerSites,
                           Count=len(IndexerSites))


# 站点资源页面
@App.route('/resources', methods=['POST', 'GET'])
@login_required
def resources():
    site_id = request.args.get("site")
    site_name = request.args.get("title")
    page = request.args.get("page") or 0
    keyword = request.args.get("keyword")
    Results = WebAction().list_site_resources({
        "id": site_id,
        "page": page,
        "keyword": keyword
    }).get("data") or []
    return render_template("site/resources.html",
                           Results=Results,
                           SiteId=site_id,
                           Title=site_name,
                           KeyWord=keyword,
                           TotalCount=len(Results),
                           PageRange=range(0, 10),
                           CurrentPage=int(page),
                           TotalPage=10)


# 推荐页面
@App.route('/recommend', methods=['POST', 'GET'])
@login_required
def recommend():
    Type = request.args.get("type") or ""
    SubType = request.args.get("subtype") or ""
    Title = request.args.get("title") or ""
    SubTitle = request.args.get("subtitle") or ""
    CurrentPage = request.args.get("page") or 1
    Week = request.args.get("week") or ""
    TmdbId = request.args.get("tmdbid") or ""
    PersonId = request.args.get("personid") or ""
    Keyword = request.args.get("keyword") or ""
    Source = request.args.get("source") or ""
    FilterKey = request.args.get("filter") or ""
    Params = json.loads(request.args.get("params")) if request.args.get("params") else {}
    return render_template("discovery/recommend.html",
                           Type=Type,
                           SubType=SubType,
                           Title=Title,
                           CurrentPage=CurrentPage,
                           Week=Week,
                           TmdbId=TmdbId,
                           PersonId=PersonId,
                           SubTitle=SubTitle,
                           Keyword=Keyword,
                           Source=Source,
                           Filter=FilterKey,
                           FilterConf=ModuleConf.DISCOVER_FILTER_CONF.get(FilterKey) if FilterKey else {},
                           Params=Params)


# 推荐页面
@App.route('/ranking', methods=['POST', 'GET'])
@login_required
def ranking():
    return render_template("discovery/ranking.html",
                           DiscoveryType="RANKING")


# 豆瓣电影
@App.route('/douban_movie', methods=['POST', 'GET'])
@login_required
def douban_movie():
    return render_template("discovery/recommend.html",
                           Type="DOUBANTAG",
                           SubType="MOV",
                           Title="豆瓣电影",
                           Filter="douban_movie",
                           FilterConf=ModuleConf.DISCOVER_FILTER_CONF.get('douban_movie'))


# 豆瓣电视剧
@App.route('/douban_tv', methods=['POST', 'GET'])
@login_required
def douban_tv():
    return render_template("discovery/recommend.html",
                           Type="DOUBANTAG",
                           SubType="TV",
                           Title="豆瓣电视剧",
                           Filter="douban_tv",
                           FilterConf=ModuleConf.DISCOVER_FILTER_CONF.get('douban_tv'))


@App.route('/tmdb_movie', methods=['POST', 'GET'])
@login_required
def tmdb_movie():
    return render_template("discovery/recommend.html",
                           Type="DISCOVER",
                           SubType="MOV",
                           Title="TMDB电影",
                           Filter="tmdb_movie",
                           FilterConf=ModuleConf.DISCOVER_FILTER_CONF.get('tmdb_movie'))


@App.route('/tmdb_tv', methods=['POST', 'GET'])
@login_required
def tmdb_tv():
    return render_template("discovery/recommend.html",
                           Type="DISCOVER",
                           SubType="TV",
                           Title="TMDB电视剧",
                           Filter="tmdb_tv",
                           FilterConf=ModuleConf.DISCOVER_FILTER_CONF.get('tmdb_tv'))


# Bangumi每日放送
@App.route('/bangumi', methods=['POST', 'GET'])
@login_required
def discovery_bangumi():
    return render_template("discovery/ranking.html",
                           DiscoveryType="BANGUMI")


# 媒体详情页面
@App.route('/media_detail', methods=['POST', 'GET'])
@login_required
def media_detail():
    TmdbId = request.args.get("id")
    Type = request.args.get("type")
    return render_template("discovery/mediainfo.html",
                           TmdbId=TmdbId,
                           Type=Type)


# 演职人员页面
@App.route('/discovery_person', methods=['POST', 'GET'])
@login_required
def discovery_person():
    TmdbId = request.args.get("tmdbid")
    Title = request.args.get("title")
    SubTitle = request.args.get("subtitle")
    Type = request.args.get("type")
    Keyword = request.args.get("keyword")
    return render_template("discovery/person.html",
                           TmdbId=TmdbId,
                           Title=Title,
                           SubTitle=SubTitle,
                           Type=Type,
                           Keyword=Keyword)


# 正在下载页面
@App.route('/downloading', methods=['POST', 'GET'])
@login_required
def downloading():
    DispTorrents = WebAction().get_downloading().get("result")
    return render_template("download/downloading.html",
                           DownloadCount=len(DispTorrents),
                           Torrents=DispTorrents)


# 近期下载页面
@App.route('/downloaded', methods=['POST', 'GET'])
@login_required
def downloaded():
    CurrentPage = request.args.get("page") or 1
    return render_template("discovery/recommend.html",
                           Type='DOWNLOADED',
                           Title='近期下载',
                           CurrentPage=CurrentPage)


@App.route('/torrent_remove', methods=['POST', 'GET'])
@login_required
def torrent_remove():
    Downloaders = Downloader().get_downloader_conf_simple()
    TorrentRemoveTasks = TorrentRemover().get_torrent_remove_tasks()
    return render_template("download/torrent_remove.html",
                           Downloaders=Downloaders,
                           DownloaderConfig=ModuleConf.TORRENTREMOVER_DICT,
                           Count=len(TorrentRemoveTasks),
                           TorrentRemoveTasks=TorrentRemoveTasks)


# 数据统计页面
@App.route('/statistics', methods=['POST', 'GET'])
@login_required
def statistics():
    # 刷新单个site
    refresh_site = request.args.getlist("refresh_site")
    # 强制刷新所有
    refresh_force = True if request.args.get("refresh_force") else False
    # 总上传下载
    TotalUpload = 0
    TotalDownload = 0
    TotalSeedingSize = 0
    TotalSeeding = 0
    # 站点标签及上传下载
    SiteNames = []
    SiteUploads = []
    SiteDownloads = []
    SiteRatios = []
    SiteErrs = {}
    # 站点上传下载
    SiteData = SiteUserInfo().get_site_data(specify_sites=refresh_site, force=refresh_force)
    if isinstance(SiteData, dict):
        for name, data in SiteData.items():
            if not data:
                continue
            up = data.get("upload", 0)
            dl = data.get("download", 0)
            ratio = data.get("ratio", 0)
            seeding = data.get("seeding", 0)
            seeding_size = data.get("seeding_size", 0)
            err_msg = data.get("err_msg", "")

            SiteErrs.update({name: err_msg})

            if not up and not dl and not ratio:
                continue
            if not str(up).isdigit() or not str(dl).isdigit():
                continue
            if name not in SiteNames:
                SiteNames.append(name)
                TotalUpload += int(up)
                TotalDownload += int(dl)
                TotalSeeding += int(seeding)
                TotalSeedingSize += int(seeding_size)
                SiteUploads.append(int(up))
                SiteDownloads.append(int(dl))
                SiteRatios.append(round(float(ratio), 1))

    # 近期上传下载各站点汇总
    # CurrentUpload, CurrentDownload, _, _, _ = SiteUserInfo().get_pt_site_statistics_history(
    #    days=2)

    # 站点用户数据
    SiteUserStatistics = WebAction().get_site_user_statistics({"encoding": "DICT"}).get("data")

    return render_template("site/statistics.html",
                           TotalDownload=TotalDownload,
                           TotalUpload=TotalUpload,
                           TotalSeedingSize=TotalSeedingSize,
                           TotalSeeding=TotalSeeding,
                           SiteDownloads=SiteDownloads,
                           SiteUploads=SiteUploads,
                           SiteRatios=SiteRatios,
                           SiteNames=SiteNames,
                           SiteErr=SiteErrs,
                           SiteUserStatistics=SiteUserStatistics)


# 刷流任务页面
@App.route('/brushtask', methods=['POST', 'GET'])
@login_required
def brushtask():
    # 站点列表
    CfgSites = Sites().get_sites(brush=True)
    # 下载器列表
    Downloaders = Downloader().get_downloader_conf_simple()
    # 任务列表
    Tasks = BrushTask().get_brushtask_info()
    return render_template("site/brushtask.html",
                           Count=len(Tasks),
                           Sites=CfgSites,
                           Tasks=Tasks,
                           Downloaders=Downloaders)


# 服务页面
@App.route('/service', methods=['POST', 'GET'])
@login_required
def service():
    # 所有规则组
    RuleGroups = Filter().get_rule_groups()
    # 所有同步目录
    SyncPaths = Sync().get_sync_path_conf()

    # 所有服务
    Services = current_user.get_services()
    pt = Config().get_config('pt')
    # RSS订阅
    if "rssdownload" in Services:
        pt_check_interval = pt.get('pt_check_interval')
        if str(pt_check_interval).isdigit():
            tim_rssdownload = str(round(int(pt_check_interval) / 60)) + " 分钟"
            rss_state = 'ON'
        else:
            tim_rssdownload = ""
            rss_state = 'OFF'
        Services['rssdownload'].update({
            'time': tim_rssdownload,
            'state': rss_state,
        })

    # RSS搜索
    if "subscribe_search_all" in Services:
        search_rss_interval = pt.get('search_rss_interval')
        if str(search_rss_interval).isdigit():
            if int(search_rss_interval) < 6:
                search_rss_interval = 6
            tim_rsssearch = str(int(search_rss_interval)) + " 小时"
            rss_search_state = 'ON'
        else:
            tim_rsssearch = ""
            rss_search_state = 'OFF'
        Services['subscribe_search_all'].update({
            'time': tim_rsssearch,
            'state': rss_search_state,
        })

    # 下载文件转移
    if "pttransfer" in Services:
        pt_monitor = Downloader().monitor_downloader_ids
        if pt_monitor:
            tim_pttransfer = str(round(PT_TRANSFER_INTERVAL / 60)) + " 分钟"
            sta_pttransfer = 'ON'
        else:
            tim_pttransfer = ""
            sta_pttransfer = 'OFF'
        Services['pttransfer'].update({
            'time': tim_pttransfer,
            'state': sta_pttransfer,
        })

    # 目录同步
    if "sync" in Services:
        if Sync().monitor_sync_path_ids:
            Services['sync'].update({
                'state': 'ON'
            })
        else:
            Services.pop('sync')

    # 系统进程
    if "processes" in Services:
        if not SystemUtils.is_docker() or not SystemUtils.get_all_processes():
            Services.pop('processes')

    return render_template("service.html",
                           Count=len(Services),
                           RuleGroups=RuleGroups,
                           SyncPaths=SyncPaths,
                           SchedulerTasks=Services)


# 历史记录页面
@App.route('/history', methods=['POST', 'GET'])
@login_required
def history():
    pagenum = request.args.get("pagenum")
    keyword = request.args.get("s") or ""
    current_page = request.args.get("page")
    Result = WebAction().get_transfer_history({"keyword": keyword, "page": current_page, "pagenum": pagenum})
    PageRange = WebUtils.get_page_range(current_page=Result.get("currentPage"),
                                        total_page=Result.get("totalPage"))

    return render_template("rename/history.html",
                           TotalCount=Result.get("total"),
                           Count=len(Result.get("result")),
                           Historys=Result.get("result"),
                           Search=keyword,
                           CurrentPage=Result.get("currentPage"),
                           TotalPage=Result.get("totalPage"),
                           PageRange=PageRange,
                           PageNum=Result.get("currentPage"))


# TMDB缓存页面
@App.route('/tmdbcache', methods=['POST', 'GET'])
@login_required
def tmdbcache():
    page_num = request.args.get("pagenum")
    if not page_num:
        page_num = 30
    search_str = request.args.get("s")
    if not search_str:
        search_str = ""
    current_page = request.args.get("page")
    if not current_page:
        current_page = 1
    else:
        current_page = int(current_page)
    total_count, tmdb_caches = MetaHelper().dump_meta_data(search_str, current_page, page_num)
    total_page = floor(total_count / page_num) + 1
    page_range = WebUtils.get_page_range(current_page=current_page,
                                         total_page=total_page)

    return render_template("rename/tmdbcache.html",
                           TotalCount=total_count,
                           Count=len(tmdb_caches),
                           TmdbCaches=tmdb_caches,
                           Search=search_str,
                           CurrentPage=current_page,
                           TotalPage=total_page,
                           PageRange=page_range,
                           PageNum=page_num)


# 手工识别页面
@App.route('/unidentification', methods=['POST', 'GET'])
@login_required
def unidentification():
    pagenum = request.args.get("pagenum")
    keyword = request.args.get("s") or ""
    current_page = request.args.get("page")
    Result = WebAction().get_unknown_list_by_page({"keyword": keyword, "page": current_page, "pagenum": pagenum})
    PageRange = WebUtils.get_page_range(current_page=Result.get("currentPage"),
                                        total_page=Result.get("totalPage"))
    return render_template("rename/unidentification.html",
                           TotalCount=Result.get("total"),
                           Count=len(Result.get("items")),
                           Items=Result.get("items"),
                           Search=keyword,
                           CurrentPage=Result.get("currentPage"),
                           TotalPage=Result.get("totalPage"),
                           PageRange=PageRange,
                           PageNum=Result.get("currentPage"))


# 文件管理页面
@App.route('/mediafile', methods=['POST', 'GET'])
@login_required
def mediafile():
    media_default_path = Config().get_config('media').get('media_default_path')
    if media_default_path:
        DirD = media_default_path
    else:
        download_dirs = Downloader().get_download_visit_dirs()
        if download_dirs:
            try:
                DirD = os.path.commonpath(download_dirs).replace("\\", "/")
            except Exception as err:
                print(str(err))
                DirD = "/"
        else:
            DirD = "/"
    DirR = request.args.get("dir")
    return render_template("rename/mediafile.html",
                           Dir=DirR or DirD)


# 基础设置页面
@App.route('/basic', methods=['POST', 'GET'])
@login_required
def basic():
    proxy = Config().get_config('app').get("proxies", {}).get("http")
    if proxy:
        proxy = proxy.replace("http://", "")
    RmtModeDict = WebAction().get_rmt_modes()
    CustomScriptCfg = SystemConfig().get(SystemConfigKey.CustomScript)
    ScraperConf = SystemConfig().get(SystemConfigKey.UserScraperConf) or {}
    return render_template("setting/basic.html",
                           Config=Config().get_config(),
                           Proxy=proxy,
                           RmtModeDict=RmtModeDict,
                           CustomScriptCfg=CustomScriptCfg,
                           CurrentUser=current_user,
                           ScraperNfo=ScraperConf.get("scraper_nfo") or {},
                           ScraperPic=ScraperConf.get("scraper_pic") or {},
                           TmdbDomains=TMDB_API_DOMAINS)


# 自定义识别词设置页面
@App.route('/customwords', methods=['POST', 'GET'])
@login_required
def customwords():
    groups = WebAction().get_customwords().get("result")
    return render_template("setting/customwords.html",
                           Groups=groups,
                           GroupsCount=len(groups))


# 目录同步页面
@App.route('/directorysync', methods=['POST', 'GET'])
@login_required
def directorysync():
    RmtModeDict = WebAction().get_rmt_modes()
    SyncPaths = Sync().get_sync_path_conf()
    return render_template("setting/directorysync.html",
                           SyncPaths=SyncPaths,
                           SyncCount=len(SyncPaths),
                           RmtModeDict=RmtModeDict)


# 下载器页面
@App.route('/downloader', methods=['POST', 'GET'])
@login_required
def downloader():
    DefaultDownloader = Downloader().default_downloader_id
    Downloaders = Downloader().get_downloader_conf()
    DownloadersCount = len(Downloaders)
    Categories = {
        x: WebAction().get_categories({
            "type": x
        }).get("category") for x in ["电影", "电视剧", "动漫"]
    }
    RmtModeDict = WebAction().get_rmt_modes()
    return render_template("setting/downloader.html",
                           Downloaders=Downloaders,
                           DefaultDownloader=DefaultDownloader,
                           DownloadersCount=DownloadersCount,
                           Categories=Categories,
                           RmtModeDict=RmtModeDict,
                           DownloaderConf=ModuleConf.DOWNLOADER_CONF)


# 下载设置页面
@App.route('/download_setting', methods=['POST', 'GET'])
@login_required
def download_setting():
    DefaultDownloadSetting = Downloader().default_download_setting_id
    Downloaders = Downloader().get_downloader_conf_simple()
    DownloadSetting = Downloader().get_download_setting()
    return render_template("setting/download_setting.html",
                           DownloadSetting=DownloadSetting,
                           DefaultDownloadSetting=DefaultDownloadSetting,
                           Downloaders=Downloaders,
                           Count=len(DownloadSetting))


# 索引器页面
@App.route('/indexer', methods=['POST', 'GET'])
@login_required
def indexer():
    # 只有选中的索引器才搜索
    indexers = Indexer().get_indexers(check=False)
    private_count = len([item.id for item in indexers if not item.public])
    public_count = len([item.id for item in indexers if item.public])
    indexer_sites = SystemConfig().get(SystemConfigKey.UserIndexerSites)
    return render_template("setting/indexer.html",
                           Config=Config().get_config(),
                           PrivateCount=private_count,
                           PublicCount=public_count,
                           Indexers=indexers,
                           IndexerConf=ModuleConf.INDEXER_CONF,
                           IndexerSites=indexer_sites)


# 媒体库页面
@App.route('/library', methods=['POST', 'GET'])
@login_required
def library():
    return render_template("setting/library.html",
                           Config=Config().get_config())


# 媒体服务器页面
@App.route('/mediaserver', methods=['POST', 'GET'])
@login_required
def mediaserver():
    return render_template("setting/mediaserver.html",
                           Config=Config().get_config(),
                           MediaServerConf=ModuleConf.MEDIASERVER_CONF)


# 通知消息页面
@App.route('/notification', methods=['POST', 'GET'])
@login_required
def notification():
    MessageClients = Message().get_message_client_info()
    Channels = ModuleConf.MESSAGE_CONF.get("client")
    Switchs = ModuleConf.MESSAGE_CONF.get("switch")
    return render_template("setting/notification.html",
                           Channels=Channels,
                           Switchs=Switchs,
                           ClientCount=len(MessageClients),
                           MessageClients=MessageClients)


# 用户管理页面
@App.route('/users', methods=['POST', 'GET'])
@login_required
def users():
    Users = WebAction().get_users().get("result")
    TopMenus = WebAction().get_top_menus().get("menus")
    return render_template("setting/users.html",
                           Users=Users,
                           UserCount=len(Users),
                           TopMenus=TopMenus)


# 过滤规则设置页面
@App.route('/filterrule', methods=['POST', 'GET'])
@login_required
def filterrule():
    result = WebAction().get_filterrules()
    return render_template("setting/filterrule.html",
                           Count=len(result.get("ruleGroups")),
                           RuleGroups=result.get("ruleGroups"),
                           Init_RuleGroups=result.get("initRules"))


# 自定义订阅页面
@App.route('/user_rss', methods=['POST', 'GET'])
@login_required
def user_rss():
    Tasks = RssChecker().get_rsstask_info()
    RssParsers = RssChecker().get_userrss_parser()
    RuleGroups = {str(group["id"]): group["name"] for group in Filter().get_rule_groups()}
    DownloadSettings = {did: attr["name"] for did, attr in Downloader().get_download_setting().items()}
    RestypeDict = ModuleConf.TORRENT_SEARCH_PARAMS.get("restype")
    PixDict = ModuleConf.TORRENT_SEARCH_PARAMS.get("pix")
    return render_template("rss/user_rss.html",
                           Tasks=Tasks,
                           Count=len(Tasks),
                           RssParsers=RssParsers,
                           RuleGroups=RuleGroups,
                           RestypeDict=RestypeDict,
                           PixDict=PixDict,
                           DownloadSettings=DownloadSettings)


# RSS解析器页面
@App.route('/rss_parser', methods=['POST', 'GET'])
@login_required
def rss_parser():
    RssParsers = RssChecker().get_userrss_parser()
    return render_template("rss/rss_parser.html",
                           RssParsers=RssParsers,
                           Count=len(RssParsers))


# 插件页面
@App.route('/plugin', methods=['POST', 'GET'])
@login_required
def plugin():
    Plugins = WebAction().get_plugins_conf().get("result")
    return render_template("setting/plugin.html",
                           Plugins=Plugins,
                           Count=len(Plugins))


# 事件响应
@App.route('/do', methods=['POST'])
@action_login_check
def do():
    try:
        content = request.get_json()
        cmd = content.get("cmd")
        data = content.get("data") or {}
        return WebAction().action(cmd, data)
    except Exception as e:
        ExceptionUtils.exception_traceback(e)
        return {"code": -1, "msg": str(e)}


# 目录事件响应
@App.route('/dirlist', methods=['POST'])
@login_required
def dirlist():
    r = ['<ul class="jqueryFileTree" style="display: none;">']
    try:
        r = ['<ul class="jqueryFileTree" style="display: none;">']
        in_dir = unquote(request.form.get('dir'))
        ft = request.form.get("filter")
        if not in_dir or in_dir == "/":
            if SystemUtils.get_system() == OsType.WINDOWS:
                partitions = SystemUtils.get_windows_drives()
                if partitions:
                    dirs = partitions
                else:
                    dirs = [os.path.join("C:/", f) for f in os.listdir("C:/")]
            else:
                dirs = [os.path.join("/", f) for f in os.listdir("/")]
        else:
            d = os.path.normpath(urllib.parse.unquote(in_dir))
            if not os.path.isdir(d):
                d = os.path.dirname(d)
            dirs = [os.path.join(d, f) for f in os.listdir(d)]
        for ff in dirs:
            f = os.path.basename(ff)
            if not f:
                f = ff
            if os.path.isdir(ff):
                r.append('<li class="directory collapsed"><a rel="%s/">%s</a></li>' % (
                    ff.replace("\\", "/"), f.replace("\\", "/")))
            else:
                if ft != "HIDE_FILES_FILTER":
                    e = os.path.splitext(f)[1][1:]
                    r.append('<li class="file ext_%s"><a rel="%s">%s</a></li>' % (
                        e, ff.replace("\\", "/"), f.replace("\\", "/")))
        r.append('</ul>')
    except Exception as e:
        ExceptionUtils.exception_traceback(e)
        r.append('加载路径失败: %s' % str(e))
    r.append('</ul>')
    return make_response(''.join(r), 200)


# 禁止搜索引擎
@App.route('/robots.txt', methods=['GET', 'POST'])
def robots():
    return send_from_directory("", "robots.txt")


# 响应企业微信消息
@App.route('/wechat', methods=['GET', 'POST'])
def wechat():
    # 当前在用的交互渠道
    interactive_client = Message().get_interactive_client(SearchType.WX)
    if not interactive_client:
        return make_response("NAStool没有启用微信交互", 200)
    conf = interactive_client.get("config")
    sToken = conf.get('token')
    sEncodingAESKey = conf.get('encodingAESKey')
    sCorpID = conf.get('corpid')
    if not sToken or not sEncodingAESKey or not sCorpID:
        return
    wxcpt = WXBizMsgCrypt(sToken, sEncodingAESKey, sCorpID)
    sVerifyMsgSig = request.args.get("msg_signature")
    sVerifyTimeStamp = request.args.get("timestamp")
    sVerifyNonce = request.args.get("nonce")

    if request.method == 'GET':
        if not sVerifyMsgSig and not sVerifyTimeStamp and not sVerifyNonce:
            return "NAStool微信交互服务正常！<br>微信回调配置步聚：<br>1、在微信企业应用接收消息设置页面生成Token和EncodingAESKey并填入设置->消息通知->微信对应项，打开微信交互开关。<br>2、保存并重启本工具，保存并重启本工具，保存并重启本工具。<br>3、在微信企业应用接收消息设置页面输入此地址：http(s)://IP:PORT/wechat（IP、PORT替换为本工具的外网访问地址及端口，需要有公网IP并做好端口转发，最好有域名）。"
        sVerifyEchoStr = request.args.get("echostr")
        log.info("收到微信验证请求: echostr= %s" % sVerifyEchoStr)
        ret, sEchoStr = wxcpt.VerifyURL(sVerifyMsgSig, sVerifyTimeStamp, sVerifyNonce, sVerifyEchoStr)
        if ret != 0:
            log.error("微信请求验证失败 VerifyURL ret: %s" % str(ret))
        # 验证URL成功，将sEchoStr返回给企业号
        return sEchoStr
    else:
        try:
            sReqData = request.data
            log.debug("收到微信请求：%s" % str(sReqData))
            ret, sMsg = wxcpt.DecryptMsg(sReqData, sVerifyMsgSig, sVerifyTimeStamp, sVerifyNonce)
            if ret != 0:
                log.error("解密微信消息失败 DecryptMsg ret = %s" % str(ret))
                return make_response("ok", 200)
            # 解析XML报文
            """
            1、消息格式：
            <xml>
               <ToUserName><![CDATA[toUser]]></ToUserName>
               <FromUserName><![CDATA[fromUser]]></FromUserName> 
               <CreateTime>1348831860</CreateTime>
               <MsgType><![CDATA[text]]></MsgType>
               <Content><![CDATA[this is a test]]></Content>
               <MsgId>1234567890123456</MsgId>
               <AgentID>1</AgentID>
            </xml>
            2、事件格式：
            <xml>
                <ToUserName><![CDATA[toUser]]></ToUserName>
                <FromUserName><![CDATA[UserID]]></FromUserName>
                <CreateTime>1348831860</CreateTime>
                <MsgType><![CDATA[event]]></MsgType>
                <Event><![CDATA[subscribe]]></Event>
                <AgentID>1</AgentID>
            </xml>            
            """
            dom_tree = xml.dom.minidom.parseString(sMsg.decode('UTF-8'))
            root_node = dom_tree.documentElement
            # 消息类型
            msg_type = DomUtils.tag_value(root_node, "MsgType")
            # Event event事件只有click才有效,enter_agent无效
            event = DomUtils.tag_value(root_node, "Event")
            # 用户ID
            user_id = DomUtils.tag_value(root_node, "FromUserName")
            # 没的消息类型和用户ID的消息不要
            if not msg_type or not user_id:
                log.info("收到微信心跳报文...")
                return make_response("ok", 200)
            # 解析消息内容
            content = ""
            if msg_type == "event" and event == "click":
                # 校验用户有权限执行交互命令
                if conf.get("adminUser") and not any(
                        user_id == admin_user for admin_user in str(conf.get("adminUser")).split(";")):
                    Message().send_channel_msg(channel=SearchType.WX, title="用户无权限执行菜单命令", user_id=user_id)
                    return make_response(content, 200)
                # 事件消息
                event_key = DomUtils.tag_value(root_node, "EventKey")
                if event_key:
                    log.info("点击菜单：%s" % event_key)
                    keys = event_key.split('#')
                    if len(keys) > 2:
                        content = ModuleConf.WECHAT_MENU.get(keys[2])
            elif msg_type == "text":
                # 文本消息
                content = DomUtils.tag_value(root_node, "Content", default="")
            if content:
                log.info(f"收到微信消息：userid={user_id}, text={content}")
                # 处理消息内容
                WebAction().handle_message_job(msg=content,
                                               in_from=SearchType.WX,
                                               user_id=user_id,
                                               user_name=user_id)
            return make_response(content, 200)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            log.error("微信消息处理发生错误：%s - %s" % (str(err), traceback.format_exc()))
            return make_response("ok", 200)


# Plex Webhook
@App.route('/plex', methods=['POST'])
@require_auth(force=False)
def plex_webhook():
    if not SecurityHelper().check_mediaserver_ip(request.remote_addr):
        log.warn(f"非法IP地址的媒体服务器消息通知：{request.remote_addr}")
        return '不允许的IP地址请求'
    request_json = json.loads(request.form.get('payload', {}))
    log.debug("收到Plex Webhook报文：%s" % str(request_json))
    # 事件类型
    event_match = request_json.get("event") in ["media.play", "media.stop"]
    # 媒体类型
    type_match = request_json.get("Metadata", {}).get("type") in ["movie", "episode"]
    # 是否直播
    is_live = request_json.get("Metadata", {}).get("live") == "1"
    # 如果事件类型匹配,媒体类型匹配,不是直播
    if event_match and type_match and not is_live:
        # 发送消息
        ThreadHelper().start_thread(MediaServer().webhook_message_handler,
                                    (request_json, MediaServerType.PLEX))
        # 触发事件
        EventManager().send_event(EventType.PlexWebhook, request_json)
    return 'Ok'


# Jellyfin Webhook
@App.route('/jellyfin', methods=['POST'])
@require_auth(force=False)
def jellyfin_webhook():
    if not SecurityHelper().check_mediaserver_ip(request.remote_addr):
        log.warn(f"非法IP地址的媒体服务器消息通知：{request.remote_addr}")
        return '不允许的IP地址请求'
    request_json = request.get_json()
    log.debug("收到Jellyfin Webhook报文：%s" % str(request_json))
    # 发送消息
    ThreadHelper().start_thread(MediaServer().webhook_message_handler,
                                (request_json, MediaServerType.JELLYFIN))
    # 触发事件
    EventManager().send_event(EventType.JellyfinWebhook, request_json)
    return 'Ok'


# Emby Webhook
@App.route('/emby', methods=['GET', 'POST'])
@require_auth(force=False)
def emby_webhook():
    if not SecurityHelper().check_mediaserver_ip(request.remote_addr):
        log.warn(f"非法IP地址的媒体服务器消息通知：{request.remote_addr}")
        return '不允许的IP地址请求'
    if request.method == 'POST':
        log.debug("Emby Webhook data: %s" % str(request.form.get('data', {})))
        request_json = json.loads(request.form.get('data', {}))
    else:
        log.debug("Emby Webhook data: %s" % str(dict(request.args)))
        request_json = dict(request.args)
    log.debug("收到Emby Webhook报文：%s" % str(request_json))
    # 发送消息
    ThreadHelper().start_thread(MediaServer().webhook_message_handler,
                                (request_json, MediaServerType.EMBY))
    # 触发事件
    EventManager().send_event(EventType.EmbyWebhook, request_json)
    return 'Ok'


# Telegram消息响应
@App.route('/telegram', methods=['POST'])
@require_auth(force=False)
def telegram():
    """
    {
        'update_id': ,
        'message': {
            'message_id': ,
            'from': {
                'id': ,
                'is_bot': False,
                'first_name': '',
                'username': '',
                'language_code': 'zh-hans'
            },
            'chat': {
                'id': ,
                'first_name': '',
                'username': '',
                'type': 'private'
            },
            'date': ,
            'text': ''
        }
    }
    """
    # 当前在用的交互渠道
    interactive_client = Message().get_interactive_client(SearchType.TG)
    if not interactive_client:
        return 'NAStool未启用Telegram交互'
    msg_json = request.get_json()
    if not SecurityHelper().check_telegram_ip(request.remote_addr):
        log.error("收到来自 %s 的非法Telegram消息：%s" % (request.remote_addr, msg_json))
        return '不允许的IP地址请求'
    if msg_json:
        message = msg_json.get("message", {})
        text = message.get("text")
        user_id = message.get("from", {}).get("id")
        # 获取用户名
        user_name = message.get("from", {}).get("username")
        if text:
            log.info(f"收到Telegram消息：userid={user_id}, username={user_name}, text={text}")
            # 检查权限
            if text.startswith("/"):
                if str(user_id) not in interactive_client.get("client").get_admin():
                    Message().send_channel_msg(channel=SearchType.TG,
                                               title="只有管理员才有权限执行此命令",
                                               user_id=user_id)
                    return '只有管理员才有权限执行此命令'
            else:
                if not str(user_id) in interactive_client.get("client").get_users():
                    Message().send_channel_msg(channel=SearchType.TG,
                                               title="你不在用户白名单中，无法使用此机器人",
                                               user_id=user_id)
                    return '你不在用户白名单中，无法使用此机器人'
            # 处理消息
            WebAction().handle_message_job(msg=text,
                                           in_from=SearchType.TG,
                                           user_id=user_id,
                                           user_name=user_name)
    return 'Ok'


# Synology Chat消息响应
@App.route('/synology', methods=['POST'])
@require_auth(force=False)
def synology():
    """
    token: bot token
    user_id
    username
    post_id
    timestamp
    text
    """
    # 当前在用的交互渠道
    interactive_client = Message().get_interactive_client(SearchType.SYNOLOGY)
    if not interactive_client:
        return 'NAStool未启用Synology Chat交互'
    msg_data = request.form
    if not SecurityHelper().check_synology_ip(request.remote_addr):
        log.error("收到来自 %s 的非法Synology Chat消息：%s" % (request.remote_addr, msg_data))
        return '不允许的IP地址请求'
    if msg_data:
        token = msg_data.get("token")
        if not interactive_client.get("client").check_token(token):
            log.error("收到来自 %s 的非法Synology Chat消息：token校验不通过！" % request.remote_addr)
            return 'token校验不通过'
        text = msg_data.get("text")
        user_id = int(msg_data.get("user_id"))
        # 获取用户名
        user_name = msg_data.get("username")
        if text:
            log.info(f"收到Synology Chat消息：userid={user_id}, username={user_name}, text={text}")
            WebAction().handle_message_job(msg=text,
                                           in_from=SearchType.SYNOLOGY,
                                           user_id=user_id,
                                           user_name=user_name)
    return 'Ok'


# Slack消息响应
@App.route('/slack', methods=['POST'])
@require_auth(force=False)
def slack():
    """
    # 消息
    {
        'client_msg_id': '',
        'type': 'message',
        'text': 'hello',
        'user': '',
        'ts': '1670143568.444289',
        'blocks': [{
            'type': 'rich_text',
            'block_id': 'i2j+',
            'elements': [{
                'type': 'rich_text_section',
                'elements': [{
                    'type': 'text',
                    'text': 'hello'
                }]
            }]
        }],
        'team': '',
        'client': '',
        'event_ts': '1670143568.444289',
        'channel_type': 'im'
    }
    # 快捷方式
    {
      "type": "shortcut",
      "token": "XXXXXXXXXXXXX",
      "action_ts": "1581106241.371594",
      "team": {
        "id": "TXXXXXXXX",
        "domain": "shortcuts-test"
      },
      "user": {
        "id": "UXXXXXXXXX",
        "username": "aman",
        "team_id": "TXXXXXXXX"
      },
      "callback_id": "shortcut_create_task",
      "trigger_id": "944799105734.773906753841.38b5894552bdd4a780554ee59d1f3638"
    }
    # 按钮点击
    {
      "type": "block_actions",
      "team": {
        "id": "T9TK3CUKW",
        "domain": "example"
      },
      "user": {
        "id": "UA8RXUSPL",
        "username": "jtorrance",
        "team_id": "T9TK3CUKW"
      },
      "api_app_id": "AABA1ABCD",
      "token": "9s8d9as89d8as9d8as989",
      "container": {
        "type": "message_attachment",
        "message_ts": "1548261231.000200",
        "attachment_id": 1,
        "channel_id": "CBR2V3XEX",
        "is_ephemeral": false,
        "is_app_unfurl": false
      },
      "trigger_id": "12321423423.333649436676.d8c1bb837935619ccad0f624c448ffb3",
      "client": {
        "id": "CBR2V3XEX",
        "name": "review-updates"
      },
      "message": {
        "bot_id": "BAH5CA16Z",
        "type": "message",
        "text": "This content can't be displayed.",
        "user": "UAJ2RU415",
        "ts": "1548261231.000200",
        ...
      },
      "response_url": "https://hooks.slack.com/actions/AABA1ABCD/1232321423432/D09sSasdasdAS9091209",
      "actions": [
        {
          "action_id": "WaXA",
          "block_id": "=qXel",
          "text": {
            "type": "plain_text",
            "text": "View",
            "emoji": true
          },
          "value": "click_me_123",
          "type": "button",
          "action_ts": "1548426417.840180"
        }
      ]
    }
    """
    # 只有本地转发请求能访问
    if not SecurityHelper().check_slack_ip(request.remote_addr):
        log.warn(f"非法IP地址的Slack消息通知：{request.remote_addr}")
        return '不允许的IP地址请求'

    # 当前在用的交互渠道
    interactive_client = Message().get_interactive_client(SearchType.SLACK)
    if not interactive_client:
        return 'NAStool未启用Slack交互'
    msg_json = request.get_json()
    if msg_json:
        if msg_json.get("type") == "message":
            userid = msg_json.get("user")
            text = msg_json.get("text")
            username = msg_json.get("user")
        elif msg_json.get("type") == "block_actions":
            userid = msg_json.get("user", {}).get("id")
            text = msg_json.get("actions")[0].get("value")
            username = msg_json.get("user", {}).get("name")
        elif msg_json.get("type") == "event_callback":
            userid = msg_json.get('event', {}).get('user')
            text = re.sub(r"<@[0-9A-Z]+>", "", msg_json.get("event", {}).get("text"), flags=re.IGNORECASE).strip()
            username = ""
        elif msg_json.get("type") == "shortcut":
            userid = msg_json.get("user", {}).get("id")
            text = msg_json.get("callback_id")
            username = msg_json.get("user", {}).get("username")
        else:
            return "Error"
        log.info(f"收到Slack消息：userid={userid}, username={username}, text={text}")
        WebAction().handle_message_job(msg=text,
                                       in_from=SearchType.SLACK,
                                       user_id=userid,
                                       user_name=username)
    return "Ok"


# Jellyseerr Overseerr订阅接口
@App.route('/subscribe', methods=['POST'])
@require_auth
def subscribe():
    """
    {
        "notification_type": "{{notification_type}}",
        "event": "{{event}}",
        "subject": "{{subject}}",
        "message": "{{message}}",
        "image": "{{image}}",
        "{{media}}": {
            "media_type": "{{media_type}}",
            "tmdbId": "{{media_tmdbid}}",
            "tvdbId": "{{media_tvdbid}}",
            "status": "{{media_status}}",
            "status4k": "{{media_status4k}}"
        },
        "{{request}}": {
            "request_id": "{{request_id}}",
            "requestedBy_email": "{{requestedBy_email}}",
            "requestedBy_username": "{{requestedBy_username}}",
            "requestedBy_avatar": "{{requestedBy_avatar}}"
        },
        "{{issue}}": {
            "issue_id": "{{issue_id}}",
            "issue_type": "{{issue_type}}",
            "issue_status": "{{issue_status}}",
            "reportedBy_email": "{{reportedBy_email}}",
            "reportedBy_username": "{{reportedBy_username}}",
            "reportedBy_avatar": "{{reportedBy_avatar}}"
        },
        "{{comment}}": {
            "comment_message": "{{comment_message}}",
            "commentedBy_email": "{{commentedBy_email}}",
            "commentedBy_username": "{{commentedBy_username}}",
            "commentedBy_avatar": "{{commentedBy_avatar}}"
        },
        "{{extra}}": []
    }
    """
    req_json = request.get_json()
    if not req_json:
        return make_response("非法请求！", 400)
    notification_type = req_json.get("notification_type")
    if notification_type not in ["MEDIA_APPROVED", "MEDIA_AUTO_APPROVED"]:
        return make_response("ok", 200)
    subject = req_json.get("subject")
    media_type = MediaType.MOVIE if req_json.get("media", {}).get("media_type") == "movie" else MediaType.TV
    tmdbId = req_json.get("media", {}).get("tmdbId")
    if not media_type or not tmdbId or not subject:
        return make_response("请求参数不正确！", 500)
    # 添加订阅
    code = 0
    msg = "ok"
    meta_info = MetaInfo(title=subject, mtype=media_type)
    user_name = req_json.get("request", {}).get("requestedBy_username")
    if media_type == MediaType.MOVIE:
        code, msg, _ = Subscribe().add_rss_subscribe(mtype=media_type,
                                                     name=meta_info.get_name(),
                                                     year=meta_info.year,
                                                     channel=RssType.Auto,
                                                     mediaid=tmdbId,
                                                     in_from=SearchType.API,
                                                     user_name=user_name)
    else:
        seasons = []
        for extra in req_json.get("extra", []):
            if extra.get("name") == "Requested Seasons":
                seasons = [int(str(sea).strip()) for sea in extra.get("value").split(", ") if str(sea).isdigit()]
                break
        for season in seasons:
            code, msg, _ = Subscribe().add_rss_subscribe(mtype=media_type,
                                                         name=meta_info.get_name(),
                                                         year=meta_info.year,
                                                         channel=RssType.Auto,
                                                         mediaid=tmdbId,
                                                         season=season,
                                                         in_from=SearchType.API,
                                                         user_name=user_name)
    if code == 0:
        return make_response("ok", 200)
    else:
        return make_response(msg, 500)


# 备份配置文件
@App.route('/backup', methods=['POST'])
@login_required
def backup():
    """
    备份用户设置文件
    :return: 备份文件.zip_file
    """
    zip_file = WebAction().backup()
    if not zip_file:
        return make_response("创建备份失败", 400)
    return send_file(zip_file)


# 上传文件到服务器
@App.route('/upload', methods=['POST'])
@login_required
def upload():
    try:
        files = request.files['file']
        temp_path = Config().get_temp_path()
        if not os.path.exists(temp_path):
            os.makedirs(temp_path)
        file_path = Path(temp_path) / files.filename
        files.save(str(file_path))
        return {"code": 0, "filepath": str(file_path)}
    except Exception as e:
        ExceptionUtils.exception_traceback(e)
        return {"code": 1, "msg": str(e), "filepath": ""}


@App.route('/ical')
@require_auth(force=False)
def ical():
    # 是否设置提醒开关
    remind = request.args.get("remind")
    cal = Calendar()
    RssItems = WebAction().get_ical_events().get("result")
    for item in RssItems:
        event = Event()
        event.add('summary', f'{item.get("type")}：{item.get("title")}')
        if not item.get("start"):
            continue
        event.add('dtstart',
                  datetime.datetime.strptime(item.get("start"),
                                             '%Y-%m-%d')
                  + datetime.timedelta(hours=8))
        event.add('dtend',
                  datetime.datetime.strptime(item.get("start"),
                                             '%Y-%m-%d')
                  + datetime.timedelta(hours=9))

        # 添加事件提醒
        if remind:
            alarm = Alarm()
            alarm.add('trigger', datetime.timedelta(minutes=30))
            alarm.add('action', 'DISPLAY')
            event.add_component(alarm)

        cal.add_component(event)

    # 返回日历文件
    response = Response(cal.to_ical(), mimetype='text/calendar')
    response.headers['Content-Disposition'] = 'attachment; filename=nastool.ics'
    return response


@App.route('/img')
@login_required
def Img():
    """
    图片中换服务
    """
    url = request.args.get('url')
    if not url:
        return make_response("参数错误", 400)
    # 计算Etag
    etag = hashlib.sha256(url.encode('utf-8')).hexdigest()
    # 检查协商缓存
    if_none_match = request.headers.get('If-None-Match')
    if if_none_match and if_none_match == etag:
        return make_response('', 304)
    # 获取图片数据
    response = Response(
        WebUtils.request_cache(url),
        mimetype='image/jpeg'
    )
    response.headers.set('Cache-Control', 'max-age=604800')
    response.headers.set('Etag', etag)
    return response


@App.route('/stream-logging')
@login_required
def stream_logging():
    """
    实时日志EventSources响应
    """
    def __logging(_source=""):
        """
        实时日志
        """
        global LoggingSource

        while True:
            with LoggingLock:
                if _source != LoggingSource:
                    LoggingSource = _source
                    log.LOG_INDEX = len(log.LOG_QUEUE)
                if log.LOG_INDEX > 0:
                    logs = list(log.LOG_QUEUE)[-log.LOG_INDEX:]
                    log.LOG_INDEX = 0
                    if _source:
                        logs = [lg for lg in logs if lg.get("source") == _source]
                else:
                    logs = []
                time.sleep(1)
                yield 'data: %s\n\n' % json.dumps(logs)

    return Response(
        __logging(request.args.get("source") or ""),
        mimetype='text/event-stream'
    )


@App.route('/stream-progress')
@login_required
def stream_progress():
    """
    实时日志EventSources响应
    """
    def __progress(_type):
        """
        实时日志
        """
        WA = WebAction()
        while True:
            time.sleep(0.2)
            detail = WA.refresh_process({"type": _type})
            yield 'data: %s\n\n' % json.dumps(detail)

    return Response(
        __progress(request.args.get("type")),
        mimetype='text/event-stream'
    )


@Sock.route('/message')
@login_required
def message_handler(ws):
    """
    消息中心WebSocket
    """
    while True:
        data = ws.receive()
        if not data:
            continue
        try:
            msgbody = json.loads(data)
        except Exception as err:
            print(str(err))
            continue
        if msgbody.get("text"):
            # 发送的消息
            WebAction().handle_message_job(msg=msgbody.get("text"),
                                           in_from=SearchType.WEB,
                                           user_id=current_user.username,
                                           user_name=current_user.username)
            ws.send((json.dumps({})))
        else:
            # 拉取消息
            system_msg = WebAction().get_system_message(lst_time=msgbody.get("lst_time"))
            messages = system_msg.get("message")
            lst_time = system_msg.get("lst_time")
            ret_messages = []
            for message in list(reversed(messages)):
                content = re.sub(r"#+", "<br>",
                                 re.sub(r"<[^>]+>", "",
                                        re.sub(r"<br/?>", "####", message.get("content"), flags=re.IGNORECASE)))
                ret_messages.append({
                    "level": "bg-red" if message.get("level") == "ERROR" else "",
                    "title": message.get("title"),
                    "content": content,
                    "time": message.get("time")
                })
            ws.send((json.dumps({
                "lst_time": lst_time,
                "message": ret_messages
            })))


# base64模板过滤器
@App.template_filter('b64encode')
def b64encode(s):
    return base64.b64encode(s.encode()).decode()


# split模板过滤器
@App.template_filter('split')
def split(string, char, pos):
    return string.split(char)[pos]


# 刷流规则过滤器
@App.template_filter('brush_rule_string')
def brush_rule_string(rules):
    return WebAction.parse_brush_rule_string(rules)


# 大小格式化过滤器
@App.template_filter('str_filesize')
def str_filesize(size):
    return StringUtils.str_filesize(size, pre=1)


# MD5 HASH过滤器
@App.template_filter('hash')
def md5_hash(text):
    return StringUtils.md5_hash(text)
