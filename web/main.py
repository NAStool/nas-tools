import base64
import datetime
import logging
import os.path
import shutil
import sqlite3
import time
import traceback
import urllib
import xml.dom.minidom
from math import floor
from pathlib import Path
from urllib import parse

import cn2an
from flask import Flask, request, json, render_template, make_response, session, send_from_directory, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from werkzeug.security import check_password_hash

import re
import log
from app.brushtask import BrushTask
from app.mediaserver import WebhookEvent
from app.message import Message
from app.rsschecker import RssChecker
from app.utils import StringUtils, DomUtils, SystemUtils, WebUtils
from app.helper import Security, MetaHelper
from config import WECHAT_MENU, PT_TRANSFER_INTERVAL, TORRENT_SEARCH_PARAMS, TMDB_IMAGE_W500_URL, NETTEST_TARGETS, \
    Config
from app.media.douban import DouBan
from app.downloader import Downloader
from app.filterrules import FilterRule
from app.indexer import BuiltinIndexer
from app.mediaserver import MediaServer
from app.searcher import Searcher
from app.sites import Sites
from app.media import MetaInfo, Media
from web.apiv1 import apiv1, authorization
from web.backend.WXBizMsgCrypt3 import WXBizMsgCrypt
from web.action import WebAction
from app.subscribe import Subscribe
from app.helper import SqlHelper, DictHelper
from app.utils.types import *
from web.backend.wallpaper import get_login_wallpaper

login_manager = LoginManager()
login_manager.login_view = "login"


def create_flask_app():
    """
    创建Flask实例，定时前端WEB的所有请求接口及页面访问
    """
    app_cfg = Config().get_config('app') or {}
    admin_user = app_cfg.get('login_user') or "admin"
    admin_password = app_cfg.get('login_password') or "password"
    ADMIN_USERS = [{
        "id": 0,
        "name": admin_user,
        "password": admin_password[6:],
        "pris": "我的媒体库,资源搜索,推荐,站点管理,订阅管理,下载管理,媒体整理,服务,系统设置"
    }]

    App = Flask(__name__)
    App.config['JSON_AS_ASCII'] = False
    App.secret_key = os.urandom(24)
    App.permanent_session_lifetime = datetime.timedelta(days=30)
    applog = logging.getLogger('werkzeug')
    applog.setLevel(logging.ERROR)
    login_manager.init_app(App)

    # API注册
    App.register_blueprint(apiv1, url_prefix="/api/v1")

    @App.after_request
    def add_header(r):
        """
        统一添加Http头，标用缓存，避免Flask多线程+Chrome内核会发生的静态资源加载出错的问题
        """
        r.headers["Cache-Control"] = "no-cache, no-store, max-age=0"
        r.headers["Pragma"] = "no-cache"
        r.headers["Expires"] = "0"
        return r

    def get_user(user_name):
        """
        根据用户名获得用户记录
        """
        for user in ADMIN_USERS:
            if user.get("name") == user_name:
                return user
        for user in SqlHelper.get_users():
            if user[1] == user_name:
                return {"id": user[0], "name": user[1], "password": user[2], "pris": user[3]}
        return {}

    class User(UserMixin):
        """
        用户
        """

        def __init__(self, user):
            self.username = user.get('name')
            self.password_hash = user.get('password')
            self.id = user.get('id')

        def verify_password(self, password):
            """
            验证密码
            """
            if self.password_hash is None:
                return False
            return check_password_hash(self.password_hash, password)

        def get_id(self):
            """
            获取用户ID
            """
            return self.id

        @staticmethod
        def get(user_id):
            """
            根据用户ID获取用户实体，为 login_user 方法提供支持
            """
            if user_id is None:
                return None
            for user in ADMIN_USERS:
                if user.get('id') == user_id:
                    return User(user)
            for user in SqlHelper.get_users():
                if not user:
                    continue
                if user[0] == user_id:
                    return User({"id": user[0], "name": user[1], "password": user[2], "pris": user[3]})
            return None

    # 定义获取登录用户的方法
    @login_manager.user_loader
    def load_user(user_id):
        return User.get(user_id)

    # 页面不存在
    @App.errorhandler(404)
    def page_not_found(error):
        return render_template("404.html", error=error), 404

    # 服务错误
    @App.errorhandler(500)
    def page_server_error(error):
        return render_template("500.html", error=error), 500

    # 主页面
    @App.route('/', methods=['GET', 'POST'])
    def login():
        # 判断当前的运营环境
        SystemFlag = 1 if SystemUtils.get_system() == OsType.LINUX else 0
        if request.method == 'GET':
            GoPage = request.args.get("next") or ""
            if GoPage.startswith('/'):
                GoPage = GoPage[1:]
            if current_user.is_authenticated:
                userid = current_user.id
                username = current_user.username
                pris = get_user(username).get("pris")
                if userid is None or username is None:
                    return render_template('login.html',
                                           GoPage=GoPage,
                                           LoginWallpaper=get_login_wallpaper())
                else:
                    RssSites = Sites().get_sites(rss=True)
                    SearchSites = [{"id": item.id, "name": item.name} for item in Searcher().indexer.get_indexers()]
                    RuleGroups = FilterRule().get_rule_groups()
                    RestypeDict = TORRENT_SEARCH_PARAMS.get("restype").keys()
                    PixDict = TORRENT_SEARCH_PARAMS.get("pix").keys()
                    return render_template('navigation.html',
                                           GoPage=GoPage,
                                           UserName=username,
                                           UserPris=str(pris).split(","),
                                           SystemFlag=SystemFlag,
                                           AppVersion=WebUtils.get_current_version(),
                                           RssSites=RssSites,
                                           SearchSites=SearchSites,
                                           RuleGroups=RuleGroups,
                                           RestypeDict=RestypeDict,
                                           PixDict=PixDict)
            else:
                return render_template('login.html',
                                       GoPage=GoPage,
                                       LoginWallpaper=get_login_wallpaper())

        else:
            GoPage = request.form.get('next') or ""
            if GoPage.startswith('/'):
                GoPage = GoPage[1:]
            username = request.form.get('username')
            password = request.form.get('password')
            remember = request.form.get('remember')
            if not username:
                return render_template('login.html',
                                       GoPage=GoPage,
                                       LoginWallpaper=get_login_wallpaper(),
                                       err_msg="请输入用户名")
            user_info = get_user(username)
            if not user_info:
                return render_template('login.html',
                                       GoPage=GoPage,
                                       LoginWallpaper=get_login_wallpaper(),
                                       err_msg="用户名或密码错误")
            # 创建用户实体
            user = User(user_info)
            # 校验密码
            if user.verify_password(password):
                # 创建用户 Session
                login_user(user)
                session.permanent = True if remember else False
                pris = user_info.get("pris")
                RssSites = Sites().get_sites(rss=True)
                SearchSites = [{"id": item.id, "name": item.name} for item in Searcher().indexer.get_indexers()]
                RuleGroups = FilterRule().get_rule_groups()
                RestypeDict = TORRENT_SEARCH_PARAMS.get("restype").keys()
                PixDict = TORRENT_SEARCH_PARAMS.get("pix").keys()
                return render_template('navigation.html',
                                       GoPage=GoPage,
                                       UserName=username,
                                       UserPris=str(pris).split(","),
                                       SystemFlag=SystemFlag,
                                       AppVersion=WebUtils.get_current_version(),
                                       RssSites=RssSites,
                                       SearchSites=SearchSites,
                                       RuleGroups=RuleGroups,
                                       RestypeDict=RestypeDict,
                                       PixDict=PixDict)
            else:
                return render_template('login.html',
                                       GoPage=GoPage,
                                       LoginWallpaper=get_login_wallpaper(),
                                       err_msg="用户名或密码错误")

    # 开始
    @App.route('/index', methods=['POST', 'GET'])
    @login_required
    def index():
        # 获取媒体数量
        ServerSucess = True
        MovieCount = 0
        SeriesCount = 0
        EpisodeCount = 0
        SongCount = 0
        MediaServerClient = MediaServer()
        media_count = MediaServerClient.get_medias_count()
        MSType = Config().get_config('media').get('media_server')
        if media_count:
            MovieCount = "{:,}".format(media_count.get('MovieCount'))
            SeriesCount = "{:,}".format(media_count.get('SeriesCount'))
            SongCount = "{:,}".format(media_count.get('SongCount'))
            if media_count.get('EpisodeCount'):
                EpisodeCount = "{:,}".format(media_count.get('EpisodeCount'))
            else:
                EpisodeCount = ""
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

        # 查询媒体统计
        MovieChartLabels = []
        MovieNums = []
        TvChartData = {}
        TvNums = []
        AnimeNums = []
        for statistic in SqlHelper.get_transfer_statistics():
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

        return render_template("index.html",
                               ServerSucess=ServerSucess,
                               MediaCount={'MovieCount': MovieCount, 'SeriesCount': SeriesCount,
                                           'SongCount': SongCount, "EpisodeCount": EpisodeCount},
                               Activitys=Activity,
                               UserCount=UserCount,
                               FreeSpace=FreeSpace,
                               TotalSpace=TotalSpace,
                               UsedSapce=UsedSapce,
                               UsedPercent=UsedPercent,
                               MovieChartLabels=MovieChartLabels,
                               TvChartLabels=TvChartLabels,
                               MovieNums=MovieNums,
                               TvNums=TvNums,
                               AnimeNums=AnimeNums,
                               MediaServerType=MSType
                               )

    # 资源搜索页面
    @App.route('/search', methods=['POST', 'GET'])
    @login_required
    def search():
        # 权限
        if current_user.is_authenticated:
            username = current_user.username
            pris = get_user(username).get("pris")
        else:
            pris = ""
        # 查询结果
        SearchWord = request.args.get("s")
        NeedSearch = request.args.get("f")
        res = SqlHelper.get_search_results()
        # 类型字典
        MeidaTypeDict = {}
        # 站点字典
        MediaSiteDict = {}
        # 资源类型字典
        MediaRestypeDict = {}
        # 分辨率字典
        MediaPixDict = {}
        # 促销信息
        MediaSPStateDict = {}
        # 名称
        MediaNameDict = {}
        # 结果
        SearchResults = []
        # 查询统计值
        for item in res:
            # 资源类型
            if str(item[2]).find(" ") != -1:
                restypes = str(item[2]).split(" ")
                if len(restypes) > 0:
                    if not MediaRestypeDict.get(restypes[0]):
                        MediaRestypeDict[restypes[0]] = 1
                    else:
                        MediaRestypeDict[restypes[0]] += 1
                # 分辨率
                if len(restypes) > 1:
                    if not MediaPixDict.get(restypes[1]):
                        MediaPixDict[restypes[1]] = 1
                    else:
                        MediaPixDict[restypes[1]] += 1
            # 类型
            if item[10]:
                mtype = {"MOV": "电影", "TV": "电视剧", "ANI": "动漫"}.get(item[10])
                if not MeidaTypeDict.get(mtype):
                    MeidaTypeDict[mtype] = 1
                else:
                    MeidaTypeDict[mtype] += 1
            # 站点
            if item[6]:
                if not MediaSiteDict.get(item[6]):
                    MediaSiteDict[item[6]] = 1
                else:
                    MediaSiteDict[item[6]] += 1
            # 促销信息
            sp_key = f"{item[19]} {item[20]}"
            if sp_key not in MediaSPStateDict:
                MediaSPStateDict[sp_key] = 1
            else:
                MediaSPStateDict[sp_key] += 1
            # 名称
            if item[1]:
                name = item[1].split("(")[0].strip()
                if name not in MediaNameDict:
                    MediaNameDict[name] = 1
                else:
                    MediaNameDict[name] += 1
            # 是否已存在
            if item[14]:
                exist_flag = MediaServer().check_item_exists(title=item[21], year=item[7], tmdbid=item[14])
            else:
                exist_flag = False
            # 结果
            SearchResults.append({
                "id": item[0],
                "title_string": item[1],
                "restype": item[2],
                "size": item[3],
                "seeders": item[4],
                "enclosure": item[5],
                "site": item[6],
                "year": item[7],
                "es_string": item[8],
                "image": item[9],
                "type": item[10],
                "vote": item[11],
                "torrent_name": item[12],
                "description": item[13],
                "tmdbid": item[14],
                "poster": item[15],
                "overview": item[16],
                "pageurl": item[17],
                "releasegroup": item[18],
                "uploadvalue": item[19],
                "downloadvalue": item[20],
                "title": item[21],
                "exist": exist_flag
            })

        # 展示类型
        MediaMTypes = []
        for k, v in MeidaTypeDict.items():
            MediaMTypes.append({"name": k, "num": v})
        MediaMTypes = sorted(MediaMTypes, key=lambda x: int(x.get("num")), reverse=True)
        # 展示站点
        MediaSites = []
        for k, v in MediaSiteDict.items():
            MediaSites.append({"name": k, "num": v})
        MediaSites = sorted(MediaSites, key=lambda x: int(x.get("num")), reverse=True)
        # 展示分辨率
        MediaPixs = []
        for k, v in MediaPixDict.items():
            MediaPixs.append({"name": k, "num": v})
        MediaPixs = sorted(MediaPixs, key=lambda x: int(x.get("num")), reverse=True)
        # 展示质量
        MediaRestypes = []
        for k, v in MediaRestypeDict.items():
            MediaRestypes.append({"name": k, "num": v})
        MediaRestypes = sorted(MediaRestypes, key=lambda x: int(x.get("num")), reverse=True)
        # 展示促销
        MediaSPStates = [{"name": k, "num": v} for k, v in MediaSPStateDict.items()]
        MediaSPStates = sorted(MediaSPStates, key=lambda x: int(x.get("num")), reverse=True)
        # 展示名称
        MediaNames = []
        for k, v in MediaNameDict.items():
            MediaNames.append({"name": k, "num": v})

        # 站点列表
        SiteDict = []
        Indexers = Searcher().indexer.get_indexers() or []
        for item in Indexers:
            SiteDict.append({"id": item.id, "name": item.name})

        # 下载目录
        SaveDirs = Downloader().get_download_dirs()
        return render_template("search.html",
                               UserPris=str(pris).split(","),
                               SearchWord=SearchWord or "",
                               NeedSearch=NeedSearch or "",
                               Count=len(SearchResults),
                               Items=SearchResults,
                               MediaMTypes=MediaMTypes,
                               MediaSites=MediaSites,
                               MediaPixs=MediaPixs,
                               MediaSPStates=MediaSPStates,
                               MediaNames=MediaNames,
                               MediaRestypes=MediaRestypes,
                               RestypeDict=TORRENT_SEARCH_PARAMS.get("restype").keys(),
                               PixDict=TORRENT_SEARCH_PARAMS.get("pix").keys(),
                               SiteDict=SiteDict,
                               SaveDirs=SaveDirs,
                               UPCHAR=chr(8593))

    # 媒体列表页面
    @App.route('/medialist', methods=['POST', 'GET'])
    @login_required
    def medialist():
        # 查询结果
        SearchWord = request.args.get("s")
        NeedSearch = request.args.get("f")
        OperType = request.args.get("t")
        medias = []
        use_douban_titles = Config().get_config("laboratory").get("use_douban_titles")
        if SearchWord and NeedSearch:
            if use_douban_titles:
                _, key_word, season_num, episode_num, _, _ = StringUtils.get_keyword_from_string(SearchWord)
                medias = DouBan().search_douban_medias(keyword=key_word,
                                                       season=season_num,
                                                       episode=episode_num)
            else:
                meta_info = MetaInfo(title=SearchWord)
                tmdbinfos = Media().get_tmdb_infos(title=meta_info.get_name(), year=meta_info.year, num=20)
                for tmdbinfo in tmdbinfos:
                    tmp_info = MetaInfo(title=SearchWord)
                    tmp_info.set_tmdb_info(tmdbinfo)
                    if meta_info.type == MediaType.TV and tmp_info.type != MediaType.TV:
                        continue
                    if tmp_info.begin_season:
                        tmp_info.title = "%s 第%s季" % (tmp_info.title, cn2an.an2cn(meta_info.begin_season, mode='low'))
                    if tmp_info.begin_episode:
                        tmp_info.title = "%s 第%s集" % (tmp_info.title, meta_info.begin_episode)
                    tmp_info.poster_path = TMDB_IMAGE_W500_URL % tmp_info.poster_path
                    medias.append(tmp_info)
        return render_template("medialist.html",
                               SearchWord=SearchWord or "",
                               NeedSearch=NeedSearch or "",
                               OperType=OperType,
                               Count=len(medias),
                               Medias=medias)

    # 电影订阅页面
    @App.route('/movie_rss', methods=['POST', 'GET'])
    @login_required
    def movie_rss():
        RssItems = SqlHelper.get_rss_movies()
        return render_template("rss/movie_rss.html",
                               Count=len(RssItems),
                               Items=RssItems
                               )

    # 电视剧订阅页面
    @App.route('/tv_rss', methods=['POST', 'GET'])
    @login_required
    def tv_rss():
        RssItems = SqlHelper.get_rss_tvs()
        return render_template("rss/tv_rss.html",
                               Count=len(RssItems),
                               Items=RssItems
                               )

    # 订阅历史页面
    @App.route('/rss_history', methods=['POST', 'GET'])
    @login_required
    def rss_history():
        mtype = request.args.get("t")
        RssHistory = SqlHelper.get_rss_history(mtype)
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
        RssMovieIds = [movie[2] for movie in SqlHelper.get_rss_movies()]
        RssTvItems = [{"id": tv[3], "season": int(str(tv[2]).replace("S", "")), "name": tv[0]} for tv in
                      SqlHelper.get_rss_tvs()
                      if tv[2]]
        return render_template("rss/rss_calendar.html",
                               Today=Today,
                               RssMovieIds=RssMovieIds,
                               RssTvItems=RssTvItems)

    # 站点维护页面
    @App.route('/site', methods=['POST', 'GET'])
    @login_required
    def site():
        CfgSites = Sites().get_sites()
        RuleGroups = FilterRule().get_rule_groups()
        return render_template("site/site.html",
                               Sites=CfgSites,
                               RuleGroups=RuleGroups)

    # 站点列表页面
    @App.route('/sitelist', methods=['POST', 'GET'])
    @login_required
    def sitelist():
        IndexerSites = BuiltinIndexer().get_indexers(check=False, public=False)
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
        SaveDirs = Downloader().get_download_dirs()
        return render_template("site/resources.html",
                               Results=Results,
                               SiteId=site_id,
                               Title=site_name,
                               KeyWord=keyword,
                               SaveDirs=SaveDirs,
                               TotalCount=len(Results),
                               PageRange=range(0, 10),
                               CurrentPage=int(page),
                               TotalPage=10)

    # 推荐页面
    @App.route('/recommend', methods=['POST', 'GET'])
    @login_required
    def recommend():
        RecommendType = request.args.get("t")
        CurrentPage = request.args.get("page") or 1
        Items = WebAction().get_recommend({"type": RecommendType, "page": CurrentPage}).get("Items")
        return render_template("recommend.html",
                               Items=Items,
                               RecommendType=RecommendType,
                               CurrentPage=CurrentPage)

    # 正在下载页面
    @App.route('/downloading', methods=['POST', 'GET'])
    @login_required
    def downloading():
        DownloadCount = 0
        Client, Torrents = Downloader().get_downloading_torrents()
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
                    dlspeed = StringUtils.str_filesize(torrent.get('dlspeed'))
                    upspeed = StringUtils.str_filesize(torrent.get('upspeed'))
                    if progress >= 100:
                        speed = "%s%sB/s %s%sB/s" % (chr(8595), dlspeed, chr(8593), upspeed)
                    else:
                        eta = StringUtils.str_timelong(torrent.get('eta'))
                        speed = "%s%sB/s %s%sB/s %s" % (chr(8595), dlspeed, chr(8593), upspeed, eta)
                # 主键
                key = torrent.get('hash')
            elif Client == DownloaderType.Client115:
                name = torrent.get('name')
                # 进度
                progress = round(torrent.get('percentDone'), 1)
                state = "Downloading"
                dlspeed = StringUtils.str_filesize(torrent.get('peers'))
                upspeed = StringUtils.str_filesize(torrent.get('rateDownload'))
                speed = "%s%sB/s %s%sB/s" % (chr(8595), dlspeed, chr(8593), upspeed)
                # 主键
                key = torrent.get('info_hash')
            elif Client == DownloaderType.Aria2:
                name = torrent.get('bittorrent', {}).get('info', {}).get("name")
                # 进度
                progress = round(int(torrent.get('completedLength')) / int(torrent.get("totalLength")), 1) * 100
                state = "Downloading"
                dlspeed = StringUtils.str_filesize(torrent.get('downloadSpeed'))
                upspeed = StringUtils.str_filesize(torrent.get('uploadSpeed'))
                speed = "%s%sB/s %s%sB/s" % (chr(8595), dlspeed, chr(8593), upspeed)
                # 主键
                key = torrent.get('gid')
            else:
                name = torrent.name
                if torrent.status in ['stopped']:
                    state = "Stoped"
                    speed = "已暂停"
                else:
                    state = "Downloading"
                    dlspeed = StringUtils.str_filesize(torrent.rateDownload)
                    upspeed = StringUtils.str_filesize(torrent.rateUpload)
                    speed = "%s%sB/s %s%sB/s" % (chr(8595), dlspeed, chr(8593), upspeed)
                # 进度
                progress = round(torrent.progress)
                # 主键
                key = torrent.id

            if not name:
                continue
            # 识别
            media_info = Media().get_media_info(title=name)
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
            torrent_info = {'id': key, 'title': title, 'speed': speed, 'image': poster_path or "", 'state': state,
                            'progress': progress}
            if torrent_info not in DispTorrents:
                DownloadCount += 1
                DispTorrents.append(torrent_info)

        return render_template("download/downloading.html",
                               DownloadCount=DownloadCount,
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

    # 数据统计页面
    @App.route('/statistics', methods=['POST', 'GET'])
    @login_required
    def statistics():
        # 刷新单个site
        refresh_site = request.args.getlist("refresh_site")
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
        # 刷新指定站点
        Sites().refresh_pt(specify_sites=refresh_site)
        # 站点上传下载
        SiteData = Sites().get_pt_date()
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
        SiteUserStatistics = Sites().get_site_user_statistics()

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
        downloaders = SqlHelper.get_user_downloaders() or []
        # 任务列表
        brushtasks = SqlHelper.get_brushtasks() or []
        Tasks = []
        for task in brushtasks:
            sendmessage_switch = DictHelper.get(SystemDictType.BrushMessageSwitch.value, task[2])
            forceupload_switch = DictHelper.get(SystemDictType.BrushForceUpSwitch.value, task[2])
            site_info = Sites().get_sites(siteid=task[2])
            scheme, netloc = StringUtils.get_url_netloc(site_info.get("signurl") or site_info.get("rssurl"))
            downloader_info = BrushTask().get_downloader_config(task[6])
            Tasks.append({
                "id": task[0],
                "name": task[1],
                "site": site_info.get("name"),
                "interval": task[4],
                "state": task[5],
                "downloader": downloader_info.get("name"),
                "transfer": task[7],
                "free": task[8],
                "rss_rule": eval(task[9]),
                "remove_rule": eval(task[10]),
                "seed_size": task[11],
                "download_count": task[12],
                "remove_count": task[13],
                "download_size": StringUtils.str_filesize(task[14]),
                "upload_size": StringUtils.str_filesize(task[15]),
                "lst_mod_date": task[16],
                "site_url": "%s://%s" % (scheme, netloc),
                "sendmessage": sendmessage_switch,
                "forceupload": forceupload_switch
            })

        return render_template("site/brushtask.html",
                               Count=len(Tasks),
                               Sites=CfgSites,
                               Tasks=Tasks,
                               Downloaders=downloaders)

    # 自定义下载器页面
    @App.route('/userdownloader', methods=['POST', 'GET'])
    @login_required
    def userdownloader():
        downloaders = SqlHelper.get_user_downloaders()
        return render_template("download/userdownloader.html",
                               Count=len(downloaders),
                               Downloaders=downloaders)

    # 服务页面
    @App.route('/service', methods=['POST', 'GET'])
    @login_required
    def service():
        scheduler_cfg_list = []
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
                tim_rsssearch = str(int(search_rss_interval)) + " 天"
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
                {'name': '订阅搜索', 'time': tim_rsssearch, 'state': rss_search_state, 'id': 'rsssearch_all', 'svg': svg,
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
            pt_seeding_config_time = pt.get('pt_seeding_time')
            if pt_seeding_config_time and pt_seeding_config_time != '0':
                pt_seeding_time = "%s 天" % pt_seeding_config_time
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
                    {'name': '删种', 'time': pt_seeding_time, 'state': sta_autoremovetorrents,
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
        sync = Config().get_config('sync')
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
        targets = NETTEST_TARGETS
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
        totalCount, historys = SqlHelper.get_transfer_history(SearchStr, CurrentPage, PageNum)
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

        return render_template("rename/history.html",
                               TotalCount=totalCount,
                               Count=len(historys),
                               Historys=historys,
                               Search=SearchStr,
                               CurrentPage=CurrentPage,
                               TotalPage=TotalPage,
                               PageRange=PageRange,
                               PageNum=PageNum)

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
        Items = []
        Records = SqlHelper.get_transfer_unknown_paths()
        TotalCount = len(Records)
        SyncMod = Config().get_config('pt').get('rmt_mode')
        if not SyncMod:
            SyncMod = "link"
        for rec in Records:
            if not rec[1]:
                continue
            path = rec[1].replace("\\", "/") if rec[1] else ""
            path_to = rec[2].replace("\\", "/") if rec[2] else ""
            Items.append({"id": rec[0], "path": path, "to": path_to, "name": path})
        return render_template("rename/unidentification.html",
                               TotalCount=TotalCount,
                               Items=Items,
                               SyncMod=SyncMod)

    # 基础设置页面
    @App.route('/basic', methods=['POST', 'GET'])
    @login_required
    def basic():
        proxy = Config().get_config('app').get("proxies", {}).get("http")
        if proxy:
            proxy = proxy.replace("http://", "")
        return render_template("setting/basic.html",
                               Config=Config().get_config(),
                               Proxy=proxy)

    # 自定义识别词设置页面
    @App.route('/customwords', methods=['POST', 'GET'])
    @login_required
    def customwords():
        words = []
        words_info = SqlHelper.get_custom_words(gid=-1)
        for word_info in words_info:
            words.append({"id": word_info[0],
                          "replaced": word_info[1],
                          "replace": word_info[2],
                          "front": word_info[3],
                          "back": word_info[4],
                          "offset": word_info[5],
                          "type": word_info[6],
                          "group_id": word_info[7],
                          "season": word_info[8],
                          "enabled": word_info[9],
                          "regex": word_info[10],
                          "help": word_info[11], })
        groups = [{"id": "-1",
                   "name": "通用",
                   "link": "",
                   "type": "1",
                   "seasons": "0",
                   "words": words}]
        groups_info = SqlHelper.get_custom_word_groups()
        for group_info in groups_info:
            gid = group_info[0]
            name = "%s（%s）" % (group_info[1], group_info[2])
            gtype = group_info[3]
            if gtype == 1:
                link = "https://www.themoviedb.org/movie/%s" % group_info[4]
            else:
                link = "https://www.themoviedb.org/tv/%s" % group_info[4]
            words = []
            words_info = SqlHelper.get_custom_words(gid=gid)
            for word_info in words_info:
                words.append({"id": word_info[0],
                              "replaced": word_info[1],
                              "replace": word_info[2],
                              "front": word_info[3],
                              "back": word_info[4],
                              "offset": word_info[5],
                              "type": word_info[6],
                              "group_id": word_info[7],
                              "season": word_info[8],
                              "enabled": word_info[9],
                              "regex": word_info[10],
                              "help": word_info[11], })
            groups.append({"id": gid,
                           "name": name,
                           "link": link,
                           "type": group_info[3],
                           "seasons": group_info[5],
                           "words": words})
        return render_template("setting/customwords.html",
                               Groups=groups,
                               GroupsCount=len(groups))

    # 目录同步页面
    @App.route('/directorysync', methods=['POST', 'GET'])
    @login_required
    def directorysync():
        sync_paths = Config().get_config("sync").get("sync_path")
        rmt_mode = Config().get_config("sync").get("sync_mod")
        SyncPaths = []
        if sync_paths:
            if isinstance(sync_paths, list):
                for sync_items in sync_paths:
                    SyncPath = {'enabled': True, 'rename': True}
                    # 是否启用
                    if sync_items.startswith("#"):
                        SyncPath['enabled'] = False
                        sync_items = sync_items[1:-1]
                    # 是否重命名
                    if sync_items.startswith("["):
                        SyncPath['rename'] = False
                        sync_items = sync_items[1:-1]
                    # 转移方式
                    config_items = sync_items.split("@")
                    if not config_items:
                        continue
                    if len(config_items) > 1:
                        SyncPath['syncmod'] = config_items[-1]
                    else:
                        SyncPath['syncmod'] = rmt_mode
                    SyncPath['syncmod_name'] = RmtMode[SyncPath['syncmod'].upper()].value
                    if not SyncPath['syncmod']:
                        continue
                    # 源目录|目的目录|未知目录
                    paths = config_items[0].split("|")
                    if not paths:
                        continue
                    if len(paths) > 0:
                        if not paths[0]:
                            continue
                        SyncPath['from'] = paths[0].replace("\\", "/")
                    if len(paths) > 1:
                        SyncPath['to'] = paths[1].replace("\\", "/")
                    if len(paths) > 2:
                        SyncPath['unknown'] = paths[2].replace("\\", "/")
                    SyncPaths.append(SyncPath)
            else:
                SyncPaths = [{"from": sync_paths}]
        SyncPaths = sorted(SyncPaths, key=lambda o: o.get("from"))
        SyncCount = len(SyncPaths)
        return render_template("setting/directorysync.html", SyncPaths=SyncPaths, SyncCount=SyncCount)

    # 豆瓣页面
    @App.route('/douban', methods=['POST', 'GET'])
    @login_required
    def douban():
        return render_template("setting/douban.html", Config=Config().get_config())

    # 下载器页面
    @App.route('/downloader', methods=['POST', 'GET'])
    @login_required
    def downloader():
        return render_template("setting/downloader.html",
                               Config=Config().get_config())

    # 索引器页面
    @App.route('/indexer', methods=['POST', 'GET'])
    @login_required
    def indexer():
        indexers = BuiltinIndexer().get_indexers(check=False)
        private_count = len([item.id for item in indexers if not item.public])
        public_count = len([item.id for item in indexers if item.public])
        return render_template("setting/indexer.html",
                               Config=Config().get_config(),
                               PrivateCount=private_count,
                               PublicCount=public_count,
                               Indexers=indexers)

    # 媒体库页面
    @App.route('/library', methods=['POST', 'GET'])
    @login_required
    def library():
        return render_template("setting/library.html", Config=Config().get_config())

    # 媒体服务器页面
    @App.route('/mediaserver', methods=['POST', 'GET'])
    @login_required
    def mediaserver():
        return render_template("setting/mediaserver.html", Config=Config().get_config())

    # 通知消息页面
    @App.route('/notification', methods=['POST', 'GET'])
    @login_required
    def notification():
        return render_template("setting/notification.html", Config=Config().get_config())

    # 字幕设置页面
    @App.route('/subtitle', methods=['POST', 'GET'])
    @login_required
    def subtitle():
        return render_template("setting/subtitle.html", Config=Config().get_config())

    # 用户管理页面
    @App.route('/users', methods=['POST', 'GET'])
    @login_required
    def users():
        user_list = SqlHelper.get_users()
        user_count = len(user_list)
        Users = []
        for user in user_list:
            pris = str(user[3]).split(",")
            Users.append({"id": user[0], "name": user[1], "pris": pris})
        return render_template("setting/users.html", Users=Users, UserCount=user_count)

    # 过滤规则设置页面
    @App.route('/filterrule', methods=['POST', 'GET'])
    @login_required
    def filterrule():
        RuleGroups = FilterRule().get_rule_infos()
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
        return render_template("setting/filterrule.html",
                               Count=len(RuleGroups),
                               RuleGroups=RuleGroups,
                               Init_RuleGroups=Init_RuleGroups)

    # 自定义订阅页面
    @App.route('/user_rss', methods=['POST', 'GET'])
    @login_required
    def user_rss():
        Tasks = RssChecker().get_rsstask_info()
        RssParsers = RssChecker().get_userrss_parser()
        FilterRules = FilterRule().get_rule_groups()
        return render_template("rss/user_rss.html",
                               Tasks=Tasks,
                               Count=len(Tasks),
                               RssParsers=RssParsers,
                               FilterRules=FilterRules)

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
    @login_required
    def do():
        try:
            cmd = request.form.get("cmd")
            data = request.form.get("data")
        except Exception as e:
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
            d = os.path.normpath(urllib.parse.unquote(request.form.get('dir', '/')))
            ft = request.form.get("filter")
            if not os.path.isdir(d):
                d = os.path.dirname(d)
            for f in os.listdir(d):
                ff = os.path.join(d, f)
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
        message = Config().get_config('message')
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
            if not sVerifyMsgSig and not sVerifyTimeStamp and not sVerifyNonce:
                return "放心吧，服务是正常的！<br>微信回调配置步聚：<br>1、在微信企业应用接收消息设置页面生成Token和EncodingAESKey并填入设置->消息通知->微信对应项。<br>2、保存并重启本工具，保存并重启本工具，保存并重启本工具。<br>3、在微信企业应用接收消息设置页面输入此地址：http(s)://IP:PORT/wechat（IP、PORT替换为本工具的外网访问地址及端口，需要有公网IP并做好端口转发，最好有域名）。"
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
                            content = WECHAT_MENU.get(keys[2])
                elif msg_type == "text":
                    # 文本消息
                    content = DomUtils.tag_value(root_node, "Content", default="")
                if content:
                    # 处理消息内容
                    WebAction().handle_message_job(content, SearchType.WX, user_id)
                return make_response(content, 200)
            except Exception as err:
                log.error("微信消息处理发生错误：%s - %s" % (str(err), traceback.format_exc()))
                return make_response("ok", 200)

    # Plex Webhook
    @App.route('/plex', methods=['POST'])
    def plex_webhook():
        if not Security().check_mediaserver_ip(request.remote_addr):
            log.warn(f"非法IP地址的媒体服务器消息通知：{request.remote_addr}")
            return 'Reject'
        request_json = json.loads(request.form.get('payload', {}))
        log.debug("收到Plex Webhook报文：%s" % str(request_json))
        WebhookEvent().plex_action(request_json)
        return 'Success'

    # Emby Webhook
    @App.route('/jellyfin', methods=['POST'])
    def jellyfin_webhook():
        if not Security().check_mediaserver_ip(request.remote_addr):
            log.warn(f"非法IP地址的媒体服务器消息通知：{request.remote_addr}")
            return 'Reject'
        request_json = request.get_json()
        log.debug("收到Jellyfin Webhook报文：%s" % str(request_json))
        WebhookEvent().jellyfin_action(request_json)
        return 'Success'

    @App.route('/emby', methods=['POST'])
    # Emby Webhook
    def emby_webhook():
        if not Security().check_mediaserver_ip(request.remote_addr):
            log.warn(f"非法IP地址的媒体服务器消息通知：{request.remote_addr}")
            return 'Reject'
        request_json = json.loads(request.form.get('data', {}))
        log.debug("收到Emby Webhook报文：%s" % str(request_json))
        WebhookEvent().emby_action(request_json)
        return 'Success'

    # Telegram消息
    @App.route('/telegram', methods=['POST', 'GET'])
    def telegram():
        msg_json = request.get_json()
        if not Security().check_telegram_ip(request.remote_addr):
            log.error("收到来自 %s 的非法Telegram消息：%s" % (request.remote_addr, msg_json))
            return 'Reject'
        if msg_json:
            message = msg_json.get("message", {})
            text = message.get("text")
            user_id = message.get("from", {}).get("id")
            log.info("收到Telegram消息：from=%s, text=%s" % (user_id, text))
            if text:
                WebAction().handle_message_job(text, SearchType.TG, user_id)
        return 'Success'

    # Jellyseerr Overseerr订阅接口
    @App.route('/subscribe', methods=['POST', 'GET'])
    @authorization
    def subscribe():
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
            code, msg, meta_info = Subscribe.add_rss_subscribe(mtype=media_type,
                                                               name=meta_info.get_name(),
                                                               year=meta_info.year,
                                                               tmdbid=tmdbId)
            Message().send_rss_success_message(in_from=SearchType.API,
                                               media_info=meta_info)
        else:
            seasons = []
            for extra in req_json.get("extra", []):
                if extra.get("name") == "Requested Seasons":
                    seasons = [int(str(sea).strip()) for sea in extra.get("value").split(", ") if str(sea).isdigit()]
                    break
            for season in seasons:
                code, msg, meta_info = Subscribe.add_rss_subscribe(mtype=media_type,
                                                                   name=meta_info.get_name(),
                                                                   year=meta_info.year,
                                                                   tmdbid=tmdbId,
                                                                   season=season)
                Message().send_rss_success_message(in_from=SearchType.API,
                                                   media_info=meta_info)
        if code == 0:
            return make_response("ok", 200)
        else:
            return make_response(msg, 500)

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
            log.debug(e)
            return make_response("创建备份失败", 400)
        return send_file(zip_file)

    @App.route('/upload', methods=['POST'])
    @login_required
    def upload():
        try:
            files = request.files['file']
            zip_file = Path(Config().get_config_path()) / files.filename
            files.save(str(zip_file))
            return {"code": 0, "filepath": str(zip_file)}
        except Exception as e:
            log.debug(e)
            return {"code": 1, "msg": str(e), "filepath": ""}

    # base64模板过滤器
    @App.template_filter('b64encode')
    def b64encode(s):
        return base64.b64encode(s.encode()).decode()

    # split模板过滤器
    @App.template_filter('split')
    def split(string, char, pos):
        return string.split(char)[pos]

    # 站点信息拆分模板过滤器
    @App.template_filter('rss_sites_string')
    def rss_sites_string(notes):
        return WebAction().parse_sites_string(notes)

    # RSS过滤规则拆分模板过滤器
    @App.template_filter('rss_filter_string')
    def rss_filter_string(notes):
        return WebAction().parse_filter_string(notes)

    # 刷流规则过滤器
    @App.template_filter('brush_rule_string')
    def brush_rule_string(rules):
        return WebAction.parse_brush_rule_string(rules)

    # 大小格式化过滤器
    @App.template_filter('str_filesize')
    def str_filesize(size):
        return WebAction.str_filesize(size)

    return App
