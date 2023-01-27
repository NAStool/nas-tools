import base64
import datetime
import os.path
import re
import shutil
import sqlite3
import time
import traceback
import urllib
import xml.dom.minidom
from functools import wraps
from math import floor
from pathlib import Path
from threading import Lock
from urllib import parse

from flask import Flask, request, json, render_template, make_response, session, send_from_directory, send_file
from flask_compress import Compress
from flask_login import LoginManager, login_user, login_required, current_user

import log
from app.brushtask import BrushTask
from app.conf import ModuleConf, SystemConfig
from app.downloader import Downloader
from app.filter import Filter
from app.helper import SecurityHelper, MetaHelper, ChromeHelper
from app.indexer import Indexer
from app.media.meta import MetaInfo
from app.mediaserver import WebhookEvent
from app.message import Message
from app.rsschecker import RssChecker
from app.sites import Sites
from app.subscribe import Subscribe
from app.sync import Sync
from app.torrentremover import TorrentRemover
from app.utils import DomUtils, SystemUtils, ExceptionUtils, StringUtils
from app.utils.types import *
from config import PT_TRANSFER_INTERVAL, Config
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
App.config['JSON_AS_ASCII'] = False
App.secret_key = os.urandom(24)
App.permanent_session_lifetime = datetime.timedelta(days=30)

# 启用压缩
Compress(App)

# 登录管理模块
LoginManager = LoginManager()
LoginManager.login_view = "login"
LoginManager.init_app(App)

# API注册
App.register_blueprint(apiv1_bp, url_prefix="/api/v1")


@App.after_request
def add_header(r):
    """
    统一添加Http头，标用缓存，避免Flask多线程+Chrome内核会发生的静态资源加载出错的问题
    """
    r.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
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
    def redirect_to_navigation(userinfo):
        """
        跳转到导航页面
        """
        # 判断当前的运营环境
        SystemFlag = SystemUtils.get_system()
        SyncMod = Config().get_config('pt').get('rmt_mode')
        TMDBFlag = 1 if Config().get_config('app').get('rmt_tmdbkey') else 0
        if not SyncMod:
            SyncMod = "link"
        RmtModeDict = WebAction().get_rmt_modes()
        RestypeDict = ModuleConf.TORRENT_SEARCH_PARAMS.get("restype")
        PixDict = ModuleConf.TORRENT_SEARCH_PARAMS.get("pix")
        SiteFavicons = Sites().get_site_favicon()
        SiteDict = Indexer().get_indexer_hash_dict()
        return render_template('navigation.html',
                               GoPage=GoPage,
                               UserName=userinfo.username,
                               UserPris=str(userinfo.pris).split(","),
                               SystemFlag=SystemFlag.value,
                               TMDBFlag=TMDBFlag,
                               AppVersion=WebUtils.get_current_version(),
                               RestypeDict=RestypeDict,
                               PixDict=PixDict,
                               SyncMod=SyncMod,
                               SiteFavicons=SiteFavicons,
                               RmtModeDict=RmtModeDict,
                               SiteDict=SiteDict)

    def redirect_to_login(errmsg=''):
        """
        跳转到登录页面
        """
        return render_template('login.html',
                               GoPage=GoPage,
                               LoginWallpaper=get_login_wallpaper(),
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
                return redirect_to_navigation(User().get_user(username))
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
            return redirect_to_navigation(user_info)
        else:
            return redirect_to_login('用户名或密码错误')


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

    # 转移历史统计
    TransferStatistics = WebAction().get_transfer_statistics()

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
                           MovieChartLabels=TransferStatistics.get("MovieChartLabels"),
                           TvChartLabels=TransferStatistics.get("TvChartLabels"),
                           MovieNums=TransferStatistics.get("MovieNums"),
                           TvNums=TransferStatistics.get("TvNums"),
                           AnimeNums=TransferStatistics.get("AnimeNums"),
                           MediaServerType=MSType
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
    RssMovieItems = [
        {
            "tmdbid": movie.get("tmdbid"),
            "rssid": movie.get("id")
        } for movie in Subscribe().get_subscribe_movies().values() if movie.get("tmdbid")
    ]
    # 电视剧订阅
    RssTvItems = [
        {
            "id": tv.get("tmdbid"),
            "rssid": tv.get("id"),
            "season": int(str(tv.get('season')).replace("S", "")),
            "name": tv.get("name"),
        } for tv in Subscribe().get_subscribe_tvs().values() if tv.get('season') and tv.get("tmdbid")
    ]
    # 自定义订阅
    RssTvItems += RssChecker().get_userrss_mediainfos()
    # 电视剧订阅去重
    Uniques = set()
    UniqueTvItems = []
    for item in RssTvItems:
        unique = f"{item.get('id')}_{item.get('season')}"
        if unique not in Uniques:
            Uniques.add(unique)
            UniqueTvItems.append(item)
    return render_template("rss/rss_calendar.html",
                           Today=Today,
                           RssMovieItems=RssMovieItems,
                           RssTvItems=UniqueTvItems)


# 站点维护页面
@App.route('/site', methods=['POST', 'GET'])
@login_required
def sites():
    CfgSites = Sites().get_sites()
    RuleGroups = {str(group["id"]): group["name"] for group in Filter().get_rule_groups()}
    DownloadSettings = {did: attr["name"] for did, attr in Downloader().get_download_setting().items()}
    ChromeOk = ChromeHelper().get_status()
    CookieCloudCfg = SystemConfig().get_system_config('CookieCloud')
    return render_template("site/site.html",
                           Sites=CfgSites,
                           RuleGroups=RuleGroups,
                           DownloadSettings=DownloadSettings,
                           ChromeOk=ChromeOk,
                           CookieCloudCfg=CookieCloudCfg)


# 站点列表页面
@App.route('/sitelist', methods=['POST', 'GET'])
@login_required
def sitelist():
    IndexerSites = Indexer().get_builtin_indexers(check=False, public=False)
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
    Results = WebAction().action("list_site_resources", {"id": site_id, "page": page, "keyword": keyword}).get(
        "data") or []
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
    return render_template("discovery/recommend.html",
                           Type=Type,
                           SubType=SubType,
                           Title=Title,
                           CurrentPage=CurrentPage,
                           Week=Week,
                           TmdbId=TmdbId,
                           PersonId=PersonId,
                           SubTitle=SubTitle,
                           Keyword=Keyword)


# 电影推荐页面
@App.route('/discovery_movie', methods=['POST', 'GET'])
@login_required
def discovery_movie():
    return render_template("discovery/discovery.html",
                           DiscoveryType="MOV")


# 电视剧推荐页面
@App.route('/discovery_tv', methods=['POST', 'GET'])
@login_required
def discovery_tv():
    return render_template("discovery/discovery.html",
                           DiscoveryType="TV")


# Bangumi每日放送
@App.route('/discovery_bangumi', methods=['POST', 'GET'])
@login_required
def discovery_bangumi():
    return render_template("discovery/discovery.html",
                           DiscoveryType="BANGUMI")


# 媒体详情页面
@App.route('/discovery_detail', methods=['POST', 'GET'])
@login_required
def discovery_detail():
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
    return render_template("discovery/person.html",
                           TmdbId=TmdbId,
                           Title=Title,
                           SubTitle=SubTitle,
                           Type=Type)


# 正在下载页面
@App.route('/downloading', methods=['POST', 'GET'])
@login_required
def downloading():
    DispTorrents = WebAction().get_downloading().get("result")
    return render_template("download/downloading.html",
                           DownloadCount=len(DispTorrents),
                           Torrents=DispTorrents,
                           Client=Config().get_config("pt").get("pt_client"))


# 近期下载页面
@App.route('/downloaded', methods=['POST', 'GET'])
@login_required
def downloaded():
    Items = WebAction().get_downloaded({"page": 1}).get("Items")
    return render_template("download/downloaded.html",
                           Count=len(Items),
                           Items=Items)


@App.route('/torrent_remove', methods=['POST', 'GET'])
@login_required
def torrent_remove():
    TorrentRemoveTasks = TorrentRemover().get_torrent_remove_tasks()
    return render_template("download/torrent_remove.html",
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
    SiteData = Sites().get_pt_date(specify_sites=refresh_site, force=refresh_force)
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
    CurrentUpload, CurrentDownload, _, _, _ = Sites().get_pt_site_statistics_history(
        days=2)

    # 站点用户数据
    SiteUserStatistics = WebAction().get_site_user_statistics({"encoding": "DICT"}).get("data")

    return render_template("site/statistics.html",
                           CurrentDownload=CurrentDownload,
                           CurrentUpload=CurrentUpload,
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
    Downloaders = BrushTask().get_downloader_info()
    # 任务列表
    Tasks = BrushTask().get_brushtask_info()
    return render_template("site/brushtask.html",
                           Count=len(Tasks),
                           Sites=CfgSites,
                           Tasks=Tasks,
                           Downloaders=Downloaders)


# 自定义下载器页面
@App.route('/userdownloader', methods=['POST', 'GET'])
@login_required
def userdownloader():
    downloaders = BrushTask().get_downloader_info()
    return render_template("download/userdownloader.html",
                           Count=len(downloaders),
                           Downloaders=downloaders)


# 服务页面
@App.route('/service', methods=['POST', 'GET'])
@login_required
def service():
    scheduler_cfg_list = []
    RuleGroups = Filter().get_rule_groups()
    pt = Config().get_config('pt')
    if pt:
        # RSS订阅
        pt_check_interval = pt.get('pt_check_interval')
        if str(pt_check_interval).isdigit():
            tim_rssdownload = str(round(int(pt_check_interval) / 60)) + " 分钟"
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

        scheduler_cfg_list.append(
            {'name': 'RSS订阅', 'time': tim_rssdownload, 'state': rss_state, 'id': 'rssdownload', 'svg': svg,
             'color': "blue"})

        search_rss_interval = pt.get('search_rss_interval')
        if str(search_rss_interval).isdigit():
            if int(search_rss_interval) < 6:
                search_rss_interval = 6
            tim_rsssearch = str(int(search_rss_interval)) + " 小时"
            rss_search_state = 'ON'
        else:
            tim_rsssearch = ""
            rss_search_state = 'OFF'

        svg = '''
            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-search" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                <circle cx="10" cy="10" r="7"></circle>
                <line x1="21" y1="21" x2="15" y2="15"></line>
            </svg>
        '''

        scheduler_cfg_list.append(
            {'name': '订阅搜索', 'time': tim_rsssearch, 'state': rss_search_state, 'id': 'subscribe_search_all',
             'svg': svg,
             'color': "blue"})

        # 下载文件转移
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
        scheduler_cfg_list.append(
            {'name': '下载文件转移', 'time': tim_pttransfer, 'state': sta_pttransfer, 'id': 'pttransfer', 'svg': svg,
             'color': "green"})

        # 删种
        torrent_remove_tasks = TorrentRemover().get_torrent_remove_tasks()
        if torrent_remove_tasks:
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
            scheduler_cfg_list.append(
                {'name': '自动删种', 'state': sta_autoremovetorrents,
                 'id': 'autoremovetorrents', 'svg': svg, 'color': "twitter"})

        # 自动签到
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
            scheduler_cfg_list.append(
                {'name': '站点签到', 'time': tim_ptsignin, 'state': sta_ptsignin, 'id': 'ptsignin', 'svg': svg,
                 'color': "facebook"})

    # 目录同步
    sync_paths = Sync().get_sync_dirs()
    if sync_paths:
        sta_sync = 'ON'
        svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-refresh" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
                <path d="M20 11a8.1 8.1 0 0 0 -15.5 -2m-.5 -4v4h4"></path>
                <path d="M4 13a8.1 8.1 0 0 0 15.5 2m.5 4v-4h-4"></path>
        </svg>
        '''
        scheduler_cfg_list.append(
            {'name': '目录同步', 'time': '实时监控', 'state': sta_sync, 'id': 'sync', 'svg': svg,
             'color': "orange"})
    # 豆瓣同步
    douban_cfg = Config().get_config('douban')
    if douban_cfg:
        interval = douban_cfg.get('interval')
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
            scheduler_cfg_list.append(
                {'name': '豆瓣想看', 'time': interval, 'state': sta_douban, 'id': 'douban', 'svg': svg,
                 'color': "pink"})

    # 清理文件整理缓存
    svg = '''
    <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-eraser" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
       <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
       <path d="M19 20h-10.5l-4.21 -4.3a1 1 0 0 1 0 -1.41l10 -10a1 1 0 0 1 1.41 0l5 5a1 1 0 0 1 0 1.41l-9.2 9.3"></path>
       <path d="M18 13.3l-6.3 -6.3"></path>
    </svg>
    '''
    scheduler_cfg_list.append(
        {'name': '清理转移缓存', 'time': '手动', 'state': 'OFF', 'id': 'blacklist', 'svg': svg, 'color': 'red'})

    # 清理RSS缓存
    svg = '''
            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-eraser" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
               <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
               <path d="M19 20h-10.5l-4.21 -4.3a1 1 0 0 1 0 -1.41l10 -10a1 1 0 0 1 1.41 0l5 5a1 1 0 0 1 0 1.41l-9.2 9.3"></path>
               <path d="M18 13.3l-6.3 -6.3"></path>
            </svg>
            '''
    scheduler_cfg_list.append(
        {'name': '清理RSS缓存', 'time': '手动', 'state': 'OFF', 'id': 'rsshistory', 'svg': svg, 'color': 'purple'})

    # 名称识别测试
    svg = '''
    <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-alphabet-greek" width="40" height="40" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
       <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
       <path d="M10 10v7"></path>
       <rect x="5" y="10" width="5" height="7" rx="2"></rect>
       <path d="M14 20v-11a2 2 0 0 1 2 -2h1a2 2 0 0 1 2 2v1a2 2 0 0 1 -2 2a2 2 0 0 1 2 2v1a2 2 0 0 1 -2 2"></path>
    </svg>
    '''
    scheduler_cfg_list.append(
        {'name': '名称识别测试', 'time': '', 'state': 'OFF', 'id': 'nametest', 'svg': svg, 'color': 'lime'})

    # 过滤规则测试
    svg = '''
    <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-adjustments-horizontal" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
       <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
       <circle cx="14" cy="6" r="2"></circle>
       <line x1="4" y1="6" x2="12" y2="6"></line>
       <line x1="16" y1="6" x2="20" y2="6"></line>
       <circle cx="8" cy="12" r="2"></circle>
       <line x1="4" y1="12" x2="6" y2="12"></line>
       <line x1="10" y1="12" x2="20" y2="12"></line>
       <circle cx="17" cy="18" r="2"></circle>
       <line x1="4" y1="18" x2="15" y2="18"></line>
       <line x1="19" y1="18" x2="20" y2="18"></line>
    </svg>
    '''
    scheduler_cfg_list.append(
        {'name': '过滤规则测试', 'time': '', 'state': 'OFF', 'id': 'ruletest', 'svg': svg, 'color': 'yellow'})

    # 网络连通性测试
    svg = '''
    <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-network" width="40" height="40" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
       <path stroke="none" d="M0 0h24v24H0z" fill="none"></path>
       <circle cx="12" cy="9" r="6"></circle>
       <path d="M12 3c1.333 .333 2 2.333 2 6s-.667 5.667 -2 6"></path>
       <path d="M12 3c-1.333 .333 -2 2.333 -2 6s.667 5.667 2 6"></path>
       <path d="M6 9h12"></path>
       <path d="M3 19h7"></path>
       <path d="M14 19h7"></path>
       <circle cx="12" cy="19" r="2"></circle>
       <path d="M12 15v2"></path>
    </svg>
    '''
    targets = ModuleConf.NETTEST_TARGETS
    scheduler_cfg_list.append(
        {'name': '网络连通性测试', 'time': '', 'state': 'OFF', 'id': 'nettest', 'svg': svg, 'color': 'cyan',
         "targets": targets})

    # 备份
    svg = '''
    <svg t="1660720525544" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="1559" width="16" height="16">
    <path d="M646 1024H100A100 100 0 0 1 0 924V258a100 100 0 0 1 100-100h546a100 100 0 0 1 100 100v31a40 40 0 1 1-80 0v-31a20 20 0 0 0-20-20H100a20 20 0 0 0-20 20v666a20 20 0 0 0 20 20h546a20 20 0 0 0 20-20V713a40 40 0 0 1 80 0v211a100 100 0 0 1-100 100z" fill="#ffffff" p-id="1560"></path>
    <path d="M924 866H806a40 40 0 0 1 0-80h118a20 20 0 0 0 20-20V100a20 20 0 0 0-20-20H378a20 20 0 0 0-20 20v8a40 40 0 0 1-80 0v-8A100 100 0 0 1 378 0h546a100 100 0 0 1 100 100v666a100 100 0 0 1-100 100z" fill="#ffffff" p-id="1561"></path>
    <path d="M469 887a40 40 0 0 1-27-10L152 618a40 40 0 0 1 1-60l290-248a40 40 0 0 1 66 30v128a367 367 0 0 0 241-128l94-111a40 40 0 0 1 70 35l-26 109a430 430 0 0 1-379 332v142a40 40 0 0 1-40 40zM240 589l189 169v-91a40 40 0 0 1 40-40c144 0 269-85 323-214a447 447 0 0 1-323 137 40 40 0 0 1-40-40v-83z" fill="#ffffff" p-id="1562"></path>
    </svg>
    '''
    scheduler_cfg_list.append(
        {'name': '备份&恢复', 'time': '', 'state': 'OFF', 'id': 'backup', 'svg': svg, 'color': 'green'})
    return render_template("service.html",
                           Count=len(scheduler_cfg_list),
                           RuleGroups=RuleGroups,
                           SchedulerTasks=scheduler_cfg_list)


# 历史记录页面
@App.route('/history', methods=['POST', 'GET'])
@login_required
def history():
    pagenum = request.args.get("pagenum")
    keyword = request.args.get("s") or ""
    current_page = request.args.get("page")
    Result = WebAction().get_transfer_history({"keyword": keyword, "page": current_page, "pagenum": pagenum})
    if Result.get("totalPage") <= 5:
        StartPage = 1
        EndPage = Result.get("totalPage")
    else:
        if Result.get("currentPage") <= 3:
            StartPage = 1
            EndPage = 5
        elif Result.get("currentPage") >= Result.get("totalPage") - 2:
            StartPage = Result.get("totalPage") - 4
            EndPage = Result.get("totalPage")
        else:
            StartPage = Result.get("currentPage") - 2
            if Result.get("totalPage") > Result.get("currentPage") + 2:
                EndPage = Result.get("currentPage") + 2
            else:
                EndPage = Result.get("totalPage")
    PageRange = range(StartPage, EndPage + 1)

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

    if total_page <= 5:
        start_page = 1
        end_page = total_page
    else:
        if current_page <= 3:
            start_page = 1
            end_page = 5
        else:
            start_page = current_page - 3
            if total_page > current_page + 3:
                end_page = current_page + 3
            else:
                end_page = total_page

    page_range = range(start_page, end_page + 1)

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
    Items = WebAction().get_unknown_list().get("items")
    return render_template("rename/unidentification.html",
                           TotalCount=len(Items),
                           Items=Items)


# 文件管理页面
@App.route('/mediafile', methods=['POST', 'GET'])
@login_required
def mediafile():
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
    return render_template("setting/basic.html",
                           Config=Config().get_config(),
                           Proxy=proxy,
                           RmtModeDict=RmtModeDict)


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
    SyncPaths = WebAction().get_directorysync().get("result")
    return render_template("setting/directorysync.html",
                           SyncPaths=SyncPaths,
                           SyncCount=len(SyncPaths),
                           RmtModeDict=RmtModeDict)


# 豆瓣页面
@App.route('/douban', methods=['POST', 'GET'])
@login_required
def douban():
    DoubanHistory = WebAction().get_douban_history().get("result")
    return render_template("setting/douban.html",
                           Config=Config().get_config(),
                           HistoryCount=len(DoubanHistory),
                           DoubanHistory=DoubanHistory)


# 下载器页面
@App.route('/downloader', methods=['POST', 'GET'])
@login_required
def downloader():
    return render_template("setting/downloader.html",
                           Config=Config().get_config(),
                           DownloaderConf=ModuleConf.DOWNLOADER_CONF)


# 下载设置页面
@App.route('/download_setting', methods=['POST', 'GET'])
@login_required
def download_setting():
    DownloadSetting = Downloader().get_download_setting()
    DefaultDownloadSetting = Downloader().get_default_download_setting()
    Count = len(DownloadSetting)
    return render_template("setting/download_setting.html",
                           DownloadSetting=DownloadSetting,
                           DefaultDownloadSetting=DefaultDownloadSetting,
                           DownloaderTypes=DownloaderType,
                           Count=Count)


# 索引器页面
@App.route('/indexer', methods=['POST', 'GET'])
@login_required
def indexer():
    indexers = Indexer().get_builtin_indexers(check=False)
    private_count = len([item.id for item in indexers if not item.public])
    public_count = len([item.id for item in indexers if item.public])
    return render_template("setting/indexer.html",
                           Config=Config().get_config(),
                           PrivateCount=private_count,
                           PublicCount=public_count,
                           Indexers=indexers,
                           IndexerConf=ModuleConf.INDEXER_CONF)


# 媒体库页面
@App.route('/library', methods=['POST', 'GET'])
@login_required
def library():
    return render_template("setting/library.html", Config=Config().get_config())


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


# 字幕设置页面
@App.route('/subtitle', methods=['POST', 'GET'])
@login_required
def subtitle():
    ChromeOk = ChromeHelper().get_status()
    return render_template("setting/subtitle.html",
                           Config=Config().get_config(),
                           ChromeOk=ChromeOk)


# 用户管理页面
@App.route('/users', methods=['POST', 'GET'])
@login_required
def users():
    Users = WebAction().get_users().get("result")
    return render_template("setting/users.html", Users=Users, UserCount=len(Users))


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


# 事件响应
@App.route('/do', methods=['POST'])
@action_login_check
def do():
    try:
        cmd = request.form.get("cmd")
        data = request.form.get("data")
    except Exception as e:
        ExceptionUtils.exception_traceback(e)
        return {"code": -1, "msg": str(e)}
    if data:
        data = json.loads(data)
    return WebAction().action(cmd, data)


# 目录事件响应
@App.route('/dirlist', methods=['POST'])
@login_required
def dirlist():
    r = ['<ul class="jqueryFileTree" style="display: none;">']
    try:
        r = ['<ul class="jqueryFileTree" style="display: none;">']
        in_dir = request.form.get('dir')
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
        log.debug("收到微信验证请求: echostr= %s" % sVerifyEchoStr)
        ret, sEchoStr = wxcpt.VerifyURL(sVerifyMsgSig, sVerifyTimeStamp, sVerifyNonce, sVerifyEchoStr)
        if ret != 0:
            log.error("微信请求验证失败 VerifyURL ret: %s" % str(ret))
        # 验证URL成功，将sEchoStr返回给企业号
        return sEchoStr
    else:
        try:
            sReqData = request.data
            log.debug("收到微信消息：%s" % str(sReqData))
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
            # 用户ID
            user_id = DomUtils.tag_value(root_node, "FromUserName")
            # 没的消息类型和用户ID的消息不要
            if not msg_type or not user_id:
                log.info("收到微信心跳报文...")
                return make_response("ok", 200)
            # 解析消息内容
            content = ""
            if msg_type == "event":
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
def plex_webhook():
    if not SecurityHelper().check_mediaserver_ip(request.remote_addr):
        log.warn(f"非法IP地址的媒体服务器消息通知：{request.remote_addr}")
        return '不允许的IP地址请求'
    request_json = json.loads(request.form.get('payload', {}))
    log.debug("收到Plex Webhook报文：%s" % str(request_json))
    WebhookEvent().plex_action(request_json)
    return 'Ok'


# Emby Webhook
@App.route('/jellyfin', methods=['POST'])
def jellyfin_webhook():
    if not SecurityHelper().check_mediaserver_ip(request.remote_addr):
        log.warn(f"非法IP地址的媒体服务器消息通知：{request.remote_addr}")
        return '不允许的IP地址请求'
    request_json = request.get_json()
    log.debug("收到Jellyfin Webhook报文：%s" % str(request_json))
    WebhookEvent().jellyfin_action(request_json)
    return 'Ok'


@App.route('/emby', methods=['POST'])
# Emby Webhook
def emby_webhook():
    if not SecurityHelper().check_mediaserver_ip(request.remote_addr):
        log.warn(f"非法IP地址的媒体服务器消息通知：{request.remote_addr}")
        return '不允许的IP地址请求'
    request_json = json.loads(request.form.get('data', {}))
    log.debug("收到Emby Webhook报文：%s" % str(request_json))
    WebhookEvent().emby_action(request_json)
    return 'Ok'


# Telegram消息响应
@App.route('/telegram', methods=['POST', 'GET'])
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
        log.info("收到Telegram消息：from=%s, text=%s" % (user_id, text))
        # 获取用户名
        user_name = message.get("from", {}).get("username")
        if text:
            # 检查权限
            if text.startswith("/"):
                if str(user_id) not in interactive_client.get("client").get_admin():
                    Message().send_channel_msg(channel=SearchType.TG,
                                               title="只有管理员才有权限执行此命令",
                                               user_id=user_id)
                    return '只有管理员才有权限执行此命令'
            else:
                if not str(user_id) in interactive_client.get("client").get_users():
                    message.send_channel_msg(channel=SearchType.TG,
                                             title="你不在用户白名单中，无法使用此机器人",
                                             user_id=user_id)
                    return '你不在用户白名单中，无法使用此机器人'
            WebAction().handle_message_job(msg=text,
                                           in_from=SearchType.TG,
                                           user_id=user_id,
                                           user_name=user_name)
    return 'Ok'


# Synology Chat消息响应
@App.route('/synology', methods=['POST', 'GET'])
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
        log.info("收到Synology Chat消息：from=%s, text=%s" % (user_id, text))
        # 获取用户名
        user_name = msg_data.get("username")
        if text:
            WebAction().handle_message_job(msg=text,
                                           in_from=SearchType.SYNOLOGY,
                                           user_id=user_id,
                                           user_name=user_name)
    return 'Ok'


# Slack消息响应
@App.route('/slack', methods=['POST'])
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
            channel = msg_json.get("client")
            text = msg_json.get("text")
            username = ""
        elif msg_json.get("type") == "block_actions":
            channel = msg_json.get("client", {}).get("id")
            text = msg_json.get("actions")[0].get("value")
            username = msg_json.get("user", {}).get("name")
        elif msg_json.get("type") == "event_callback":
            channel = msg_json.get("event", {}).get("client")
            text = re.sub(r"<@[0-9A-Z]+>", "", msg_json.get("event", {}).get("text"), flags=re.IGNORECASE).strip()
            username = ""
        elif msg_json.get("type") == "shortcut":
            channel = ""
            text = msg_json.get("callback_id")
            username = msg_json.get("user", {}).get("username")
        else:
            return "Error"
        WebAction().handle_message_job(msg=text,
                                       in_from=SearchType.SLACK,
                                       user_id=channel,
                                       user_name=username)
    return "Ok"


# Jellyseerr Overseerr订阅接口
@App.route('/subscribe', methods=['POST', 'GET'])
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
    if media_type == MediaType.MOVIE:
        code, msg, meta_info = Subscribe().add_rss_subscribe(mtype=media_type,
                                                             name=meta_info.get_name(),
                                                             year=meta_info.year,
                                                             mediaid=tmdbId)
        meta_info.user_name = req_json.get("request", {}).get("requestedBy_username")
        Message().send_rss_success_message(in_from=SearchType.API,
                                           media_info=meta_info)
    else:
        seasons = []
        for extra in req_json.get("extra", []):
            if extra.get("name") == "Requested Seasons":
                seasons = [int(str(sea).strip()) for sea in extra.get("value").split(", ") if str(sea).isdigit()]
                break
        for season in seasons:
            code, msg, meta_info = Subscribe().add_rss_subscribe(mtype=media_type,
                                                                 name=meta_info.get_name(),
                                                                 year=meta_info.year,
                                                                 mediaid=tmdbId,
                                                                 season=season)
            Message().send_rss_success_message(in_from=SearchType.API,
                                               media_info=meta_info)
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
    try:
        # 创建备份文件夹
        config_path = Path(Config().get_config_path())
        backup_file = f"bk_{time.strftime('%Y%m%d%H%M%S')}"
        backup_path = config_path / "backup_file" / backup_file
        backup_path.mkdir(parents=True)
        # 把现有的相关文件进行copy备份
        shutil.copy(f'{config_path}/config.yaml', backup_path)
        shutil.copy(f'{config_path}/default-category.yaml', backup_path)
        shutil.copy(f'{config_path}/user.db', backup_path)
        conn = sqlite3.connect(f'{backup_path}/user.db')
        cursor = conn.cursor()
        # 执行操作删除不需要备份的表
        table_list = [
            'SEARCH_RESULT_INFO',
            'RSS_TORRENTS',
            'DOUBAN_MEDIAS',
            'TRANSFER_HISTORY',
            'TRANSFER_UNKNOWN',
            'TRANSFER_BLACKLIST',
            'SYNC_HISTORY',
            'DOWNLOAD_HISTORY',
            'alembic_version'
        ]
        for table in table_list:
            cursor.execute(f"""DROP TABLE IF EXISTS {table};""")
        conn.commit()
        cursor.close()
        conn.close()
        zip_file = str(backup_path) + '.zip'
        if os.path.exists(zip_file):
            zip_file = str(backup_path) + '.zip'
        shutil.make_archive(str(backup_path), 'zip', str(backup_path))
        shutil.rmtree(str(backup_path))
    except Exception as e:
        ExceptionUtils.exception_traceback(e)
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
