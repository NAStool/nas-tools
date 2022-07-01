import base64
import logging
import os.path
import traceback
from math import floor
from flask import Flask, request, json, render_template, make_response, session, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from werkzeug.security import check_password_hash
import xml.dom.minidom

import log
from pt.sites import Sites
from pt.downloader import Downloader
from pt.searcher import Searcher
from rmt.media import Media
from pt.media_server import MediaServer
from rmt.metainfo import MetaInfo
from config import WECHAT_MENU, PT_TRANSFER_INTERVAL, TORRENT_SEARCH_PARAMS
from utils.functions import *
from utils.meta_helper import MetaHelper
from utils.security import Security
from utils.sqls import *
from utils.types import *
from version import APP_VERSION
from web.action import WebAction
from web.backend.douban_hot import DoubanHot
from web.backend.web_utils import get_random_discover_backdrop
from web.backend.webhook_event import WebhookEvent
from utils.WXBizMsgCrypt3 import WXBizMsgCrypt

login_manager = LoginManager()
login_manager.login_view = "login"


def create_flask_app(config):
    """
    创建Flask实例，定时前端WEB的所有请求接口及页面访问
    """
    app_cfg = config.get_config('app') or {}
    admin_user = app_cfg.get('login_user') or "admin"
    admin_password = app_cfg.get('login_password') or "password"
    ADMIN_USERS = [{
        "id": 0,
        "name": admin_user,
        "password": admin_password[6:],
        "pris": "我的媒体库,资源搜索,推荐,站点管理,订阅管理,下载管理,媒体识别,服务,系统设置"
    }]

    App = Flask(__name__)
    App.config['JSON_AS_ASCII'] = False
    App.secret_key = os.urandom(24)
    App.permanent_session_lifetime = datetime.timedelta(days=30)
    applog = logging.getLogger('werkzeug')
    applog.setLevel(logging.ERROR)
    login_manager.init_app(App)

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
        for user in get_users():
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
            for user in get_users():
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
        SystemFlag = 0
        if get_system() == OsType.LINUX and check_process("supervisord"):
            SystemFlag = 1
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
                                           LoginWallpaper=get_random_discover_backdrop())
                else:
                    return render_template('navigation.html',
                                           GoPage=GoPage,
                                           UserName=username,
                                           UserPris=str(pris).split(","),
                                           SystemFlag=SystemFlag,
                                           AppVersion=APP_VERSION)
            else:
                return render_template('login.html',
                                       GoPage=GoPage,
                                       LoginWallpaper=get_random_discover_backdrop())

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
                                       LoginWallpaper=get_random_discover_backdrop(),
                                       err_msg="请输入用户名")
            user_info = get_user(username)
            if not user_info:
                return render_template('login.html',
                                       GoPage=GoPage,
                                       LoginWallpaper=get_random_discover_backdrop(),
                                       err_msg="用户名或密码错误")
            # 创建用户实体
            user = User(user_info)
            # 校验密码
            if user.verify_password(password):
                # 创建用户 Session
                login_user(user)
                session.permanent = True if remember else False
                pris = user_info.get("pris")
                return render_template('navigation.html',
                                       GoPage=GoPage,
                                       UserName=username,
                                       UserPris=str(pris).split(","),
                                       SystemFlag=SystemFlag,
                                       AppVersion=APP_VERSION)
            else:
                return render_template('login.html',
                                       GoPage=GoPage,
                                       LoginWallpaper=get_random_discover_backdrop(),
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

        # 查询媒体统计
        MovieChartLabels = []
        MovieNums = []
        TvChartData = {}
        TvNums = []
        AnimeNums = []
        for statistic in get_transfer_statistics():
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
                               AnimeNums=AnimeNums
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
        res = get_search_results()
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
            SiteDict.append(item[1])
        return render_template("search.html",
                               UserPris=str(pris).split(","),
                               SearchWord=SearchWord or "",
                               NeedSearch=NeedSearch or "",
                               Count=len(res),
                               Items=res,
                               MediaMTypes=MediaMTypes,
                               MediaSites=MediaSites,
                               MediaPixs=MediaPixs,
                               MediaSPStates=MediaSPStates,
                               MediaNames=MediaNames,
                               MediaRestypes=MediaRestypes,
                               RestypeDict=TORRENT_SEARCH_PARAMS.get("restype").keys(),
                               PixDict=TORRENT_SEARCH_PARAMS.get("pix").keys(),
                               SiteDict=SiteDict)

    # 媒体列表页面
    @App.route('/medialist', methods=['POST', 'GET'])
    @login_required
    def medialist():
        # 查询结果
        SearchWord = request.args.get("s")
        NeedSearch = request.args.get("f")
        OperType = request.args.get("t")
        medias = []
        if SearchWord and NeedSearch:
            meta_info = MetaInfo(title=SearchWord)
            tmdbinfos = Media().get_tmdb_infos(title=meta_info.get_name(), year=meta_info.year, num=20)
            for tmdbinfo in tmdbinfos:
                tmp_info = MetaInfo(title=SearchWord)
                tmp_info.set_tmdb_info(tmdbinfo)
                medias.append(tmp_info)
        return render_template("medialist.html",
                               SearchWord=SearchWord or "",
                               NeedSearch=NeedSearch or "",
                               OperType=OperType or "search",
                               Count=len(medias),
                               Medias=medias)

    # 电影订阅页面
    @App.route('/movie_rss', methods=['POST', 'GET'])
    @login_required
    def movie_rss():
        RssItems = get_rss_movies()
        RssSites = get_config_site()
        SearchSites = [item[1] for item in Searcher().indexer.get_indexers()]
        return render_template("rss/movie_rss.html",
                               Count=len(RssItems),
                               Items=RssItems,
                               Sites=RssSites,
                               SearchSites=SearchSites,
                               RestypeDict=TORRENT_SEARCH_PARAMS.get("restype").keys(),
                               PixDict=TORRENT_SEARCH_PARAMS.get("pix").keys()
                               )

    # 电视剧订阅页面
    @App.route('/tv_rss', methods=['POST', 'GET'])
    @login_required
    def tv_rss():
        RssItems = get_rss_tvs()
        RssSites = get_config_site()
        SearchSites = [item[1] for item in Searcher().indexer.get_indexers() or []]
        return render_template("rss/tv_rss.html",
                               Count=len(RssItems),
                               Items=RssItems,
                               Sites=RssSites,
                               SearchSites=SearchSites,
                               RestypeDict=TORRENT_SEARCH_PARAMS.get("restype").keys(),
                               PixDict=TORRENT_SEARCH_PARAMS.get("pix").keys()
                               )

    # 订阅日历页面
    @App.route('/rss_calendar', methods=['POST', 'GET'])
    @login_required
    def rss_calendar():
        Today = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
        RssMovieIds = [movie[2] for movie in get_rss_movies()]
        RssTvItems = [{"id": tv[3], "season": int(str(tv[2]).replace("S", "")), "name": tv[0]} for tv in get_rss_tvs() if tv[2]]
        return render_template("rss/rss_calendar.html",
                               Today=Today,
                               RssMovieIds=RssMovieIds,
                               RssTvItems=RssTvItems)

    # 站点维护页面
    @App.route('/site', methods=['POST', 'GET'])
    @login_required
    def site():
        CfgSites = get_config_site()
        return render_template("site/site.html",
                               Sites=CfgSites)

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
        elif RecommendType == "dbdh":
            # 豆瓣热门动画
            res_list = DoubanHot().get_douban_hot_anime()
        elif RecommendType == "dbnm":
            # 豆瓣最新电影
            res_list = DoubanHot().get_douban_new_movie()
        elif RecommendType == "dbzy":
            # 豆瓣最新电视剧
            res_list = DoubanHot().get_douban_hot_show()
        else:
            res_list = []

        Items = []
        TvKeys = ["%s" % key[0] for key in get_rss_tvs()]
        MovieKeys = ["%s" % key[0] for key in get_rss_movies()]
        for res in res_list:
            rid = res.get('id')
            if RecommendType in ['hm', 'nm', 'dbom', 'dbhm', 'dbnm']:
                title = res.get('title')
                date = res.get('release_date')
                if date:
                    year = date[0:4]
                else:
                    year = ''
                if title in MovieKeys:
                    # 已订阅
                    fav = 1
                elif is_media_downloaded(title, year):
                    # 已下载
                    fav = 2
                else:
                    # 未订阅、未下载
                    fav = 0
            else:
                title = res.get('name')
                date = res.get('first_air_date')
                if date:
                    year = date[0:4]
                else:
                    year = ''
                if MetaInfo(title=title).get_name() in TvKeys:
                    # 已订阅
                    fav = 1
                elif is_media_downloaded(MetaInfo(title=title).get_name(), year):
                    # 已下载
                    fav = 2
                else:
                    # 未订阅、未下载
                    fav = 0
            image = res.get('poster_path')
            if RecommendType in ['hm', 'nm', 'ht', 'nt']:
                image = "https://image.tmdb.org/t/p/original/%s" % image if image else ""
            else:
                # 替换图片分辨率
                image = image.replace("s_ratio_poster", "m_ratio_poster")
            vote = res.get('vote_average')
            overview = res.get('overview')
            item = {'id': rid, 'title': title, 'fav': fav, 'date': date, 'vote': vote,
                    'image': image, 'overview': overview, 'year': year}
            Items.append(item)

        return render_template("recommend.html",
                               Items=Items,
                               RecommendType=RecommendType,
                               CurrentPage=CurrentPage,
                               PageRange=PageRange)

    # 正在下载页面
    @App.route('/downloading', methods=['POST', 'GET'])
    @login_required
    def downloading():
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

        return render_template("download/downloading.html",
                               DownloadCount=DownloadCount,
                               Torrents=DispTorrents)

    # 近期下载页面
    @App.route('/downloaded', methods=['POST', 'GET'])
    @login_required
    def downloaded():
        Items = get_download_history()
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
        # 刷新指定站点
        Sites().refresh_pt(specify_sites=refresh_site)
        # 站点上传下载
        SiteData = Sites().get_pt_date()
        if isinstance(SiteData, dict):
            for name, data in SiteData.items():
                if not data:
                    continue
                up = data.get("upload") or 0
                dl = data.get("download") or 0
                ratio = data.get("ratio") or 0
                seeding = data.get("seeding") or 0
                seeding_size = data.get("seeding_size") or 0
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
        CurrentUpload, CurrentDownload, CurrentSiteLabels, CurrentSiteUploads, CurrentSiteDownloads = Sites().get_pt_site_statistics_history(
            days=2)

        # 站点用户数据
        SiteUserStatistics = Sites().get_pt_site_user_statistics()

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
                               CurrentSiteLabels=CurrentSiteLabels,
                               CurrentSiteUploads=CurrentSiteUploads,
                               CurrentSiteDownloads=CurrentSiteDownloads,
                               SiteUserStatistics=SiteUserStatistics)

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
        douban_cfg = config.get_config('douban')
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
                color = "pink"
                scheduler_cfg_list.append(
                    {'name': '豆瓣想看', 'time': interval, 'state': sta_douban, 'id': 'douban', 'svg': svg, 'color': color})

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
        Records = get_transfer_unknown_paths()
        TotalCount = len(Records)
        for rec in Records:
            if not rec[1]:
                continue
            Items.append({"id": rec[0], "path": rec[1], "to": rec[2], "name": rec[1]})
        return render_template("rename/unidentification.html",
                               TotalCount=TotalCount,
                               Items=Items)

    # 基础设置页面
    @App.route('/basic', methods=['POST', 'GET'])
    @login_required
    def basic():
        proxy = config.get_config('app').get("proxies", {}).get("http")
        if proxy:
            proxy = proxy.replace("http://", "")
        return render_template("setting/basic.html", Config=config.get_config(), Proxy=proxy)

    # 目录同步页面
    @App.route('/directorysync', methods=['POST', 'GET'])
    @login_required
    def directorysync():
        sync_paths = config.get_config("sync").get("sync_path")
        SyncPaths = []
        if sync_paths:
            if isinstance(sync_paths, list):
                for sync_path in sync_paths:
                    SyncPath = {}
                    is_rename = True
                    is_enabled = True
                    if sync_path.startswith("#"):
                        is_enabled = False
                        sync_path = sync_path[1:-1]
                    if sync_path.startswith("["):
                        is_rename = False
                        sync_path = sync_path[1:-1]
                    paths = sync_path.split("|")
                    if not paths:
                        continue
                    if len(paths) > 0:
                        if not paths[0]:
                            continue
                        SyncPath['from'] = paths[0]
                    if len(paths) > 1:
                        SyncPath['to'] = paths[1]
                    if len(paths) > 2:
                        SyncPath['unknown'] = paths[2]
                    SyncPath['rename'] = is_rename
                    SyncPath['enabled'] = is_enabled
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
        return render_template("setting/douban.html", Config=config.get_config())

    # 下载器页面
    @App.route('/downloader', methods=['POST', 'GET'])
    @login_required
    def downloader():
        # Qbittorrent
        qbittorrent = config.get_config('qbittorrent')
        save_path = qbittorrent.get("save_path")
        if isinstance(save_path, str):
            paths = save_path.split("|")
            if len(paths) > 1:
                path = paths[0]
                tag = paths[1]
            else:
                path = paths[0]
                tag = ""
            QbMovieSavePath = QbTvSavePath = QbAnimeSavePath = {"path": path, "tag": tag}
        else:
            # 电影保存目录
            movie_path = save_path.get("movie")
            if movie_path:
                paths = movie_path.split("|")
                if len(paths) > 1:
                    path = paths[0]
                    tag = paths[1]
                else:
                    path = paths[0]
                    tag = ""
            else:
                path = ""
                tag = ""
            QbMovieSavePath = {"path": path, "tag": tag}
            # 电视剧保存目录
            tv_path = save_path.get("tv")
            if tv_path:
                paths = tv_path.split("|")
                if len(paths) > 1:
                    path = paths[0]
                    tag = paths[1]
                else:
                    path = paths[0]
                    tag = ""
            else:
                path = ""
                tag = ""
            QbTvSavePath = {"path": path, "tag": tag}
            # 动漫保存目录
            anime_path = save_path.get("anime")
            if anime_path:
                paths = anime_path.split("|")
                if len(paths) > 1:
                    path = paths[0]
                    tag = paths[1]
                else:
                    path = paths[0]
                    tag = ""
            else:
                path = ""
                tag = ""
            QbAnimeSavePath = {"path": path, "tag": tag}
        contianer_path = qbittorrent.get('save_containerpath')
        if isinstance(contianer_path, str):
            QbMovieContainerPath = QbTvContainerPath = QbAnimeContainerPath = contianer_path
        else:
            if contianer_path:
                QbMovieContainerPath = contianer_path.get("movie")
                QbTvContainerPath = contianer_path.get("tv")
                QbAnimeContainerPath = contianer_path.get("anime")
            else:
                QbMovieContainerPath = QbTvContainerPath = QbAnimeContainerPath = ""

        # Transmission
        transmission = config.get_config('transmission')
        save_path = transmission.get("save_path")
        if isinstance(save_path, str):
            TrMovieSavePath = TrTvSavePath = TrAnimeSavePath = save_path
        else:
            TrMovieSavePath = save_path.get("movie")
            TrTvSavePath = save_path.get("tv")
            TrAnimeSavePath = save_path.get("anime")
        contianer_path = transmission.get('save_containerpath')
        if isinstance(contianer_path, str):
            TrMovieContainerPath = TrTvContainerPath = TrAnimeContainerPath = contianer_path
        else:
            if contianer_path:
                TrMovieContainerPath = contianer_path.get("movie")
                TrTvContainerPath = contianer_path.get("tv")
                TrAnimeContainerPath = contianer_path.get("anime")
            else:
                TrMovieContainerPath = TrTvContainerPath = TrAnimeContainerPath = ""

        return render_template("setting/downloader.html",
                               Config=config.get_config(),
                               QbMovieSavePath=QbMovieSavePath,
                               QbTvSavePath=QbTvSavePath,
                               QbAnimeSavePath=QbAnimeSavePath,
                               TrMovieSavePath=TrMovieSavePath,
                               TrTvSavePath=TrTvSavePath,
                               TrAnimeSavePath=TrAnimeSavePath,
                               QbMovieContainerPath=QbMovieContainerPath,
                               QbTvContainerPath=QbTvContainerPath,
                               QbAnimeContainerPath=QbAnimeContainerPath,
                               TrMovieContainerPath=TrMovieContainerPath,
                               TrTvContainerPath=TrTvContainerPath,
                               TrAnimeContainerPath=TrAnimeContainerPath)

    # 索引器页面
    @App.route('/indexer', methods=['POST', 'GET'])
    @login_required
    def indexer():
        return render_template("setting/indexer.html", Config=config.get_config())

    # 媒体库页面
    @App.route('/library', methods=['POST', 'GET'])
    @login_required
    def library():
        return render_template("setting/library.html", Config=config.get_config())

    # 媒体服务器页面
    @App.route('/mediaserver', methods=['POST', 'GET'])
    @login_required
    def mediaserver():
        return render_template("setting/mediaserver.html", Config=config.get_config())

    # 通知消息页面
    @App.route('/notification', methods=['POST', 'GET'])
    @login_required
    def notification():
        return render_template("setting/notification.html", Config=config.get_config())

    # 字幕设置页面
    @App.route('/subtitle', methods=['POST', 'GET'])
    @login_required
    def subtitle():
        return render_template("setting/subtitle.html", Config=config.get_config())

    # 用户管理页面
    @App.route('/users', methods=['POST', 'GET'])
    @login_required
    def users():
        user_list = get_users()
        user_count = len(user_list)
        Users = []
        for user in user_list:
            pris = str(user[3]).split(",")
            Users.append({"id": user[0], "name": user[1], "pris": pris})
        return render_template("setting/users.html", Users=Users, UserCount=user_count)

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

    # 禁止搜索引擎
    @App.route('/robots.txt', methods=['GET', 'POST'])
    def robots():
        return send_from_directory("", "robots.txt")

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
                msg_type = tag_value(root_node, "MsgType")
                # 用户ID
                user_id = tag_value(root_node, "FromUserName")
                # 没的消息类型和用户ID的消息不要
                if not msg_type or not user_id:
                    log.info("收到微信心跳报文...")
                    return make_response("ok", 200)
                # 解析消息内容
                content = ""
                if msg_type == "event":
                    # 事件消息
                    event_key = tag_value(root_node, "EventKey")
                    if event_key:
                        log.info("点击菜单：%s" % event_key)
                        keys = event_key.split('#')
                        if len(keys) > 2:
                            content = WECHAT_MENU.get(keys[2])
                elif msg_type == "text":
                    # 文本消息
                    content = tag_value(root_node, "Content", default="")
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

    # 自定义模板过滤器
    @App.template_filter('b64encode')
    def b64encode(s):
        return base64.b64encode(s.encode()).decode()

    # 站点信息拆分模板过滤器
    @App.template_filter('rss_sites_string')
    def rss_sites_string(notes):
        return WebAction().parse_sites_string(notes)

    # RSS过滤规则拆分模板过滤器
    @App.template_filter('rss_filter_string')
    def rss_filter_string(notes):
        return WebAction().parse_filter_string(notes)

    return App
