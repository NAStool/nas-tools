import _thread
from flask import Flask, request, json, render_template, make_response, redirect
import log
from pt.downloader import Downloader
from pt.jackett import Jackett
from rmt.filetransfer import FileTransfer
from rmt.media import Media
from scheduler.autoremove_torrents import AutoRemoveTorrents
from scheduler.pt_signin import PTSignin
from scheduler.pt_transfer import PTTransfer
from scheduler.rss_download import RSSDownloader
from utils.db_helper import select_by_sql
from message.send import Message
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

from config import WECHAT_MENU, get_config, save_config, PT_TRANSFER_INTERVAL
from utils.functions import get_used_of_partition
from utils.types import MediaType
from version import APP_VERSION
from web.backend.emby import EmbyEvent, Emby
from web.backend.search_torrents import search_medias_for_web
from web.backend.WXBizMsgCrypt3 import WXBizMsgCrypt
import xml.etree.cElementTree as ETree


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
    auth = HTTPBasicAuth()
    users = {str(config['app'].get('login_user')): generate_password_hash(config['app'].get('login_password'))}

    EmbyClient = Emby()

    @auth.verify_password
    def verify_password(username, password):
        if username in users and \
                check_password_hash(users.get(username), str(password)):
            return username

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
        event = EmbyEvent(request_json)
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

    # 主页面
    @app.before_request
    def before_request():
        if request.url.startswith('http://'):
            ssl_cert = config['app'].get('ssl_cert')
            if ssl_cert:
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)

    # 开始页面
    @app.route('/', methods=['POST', 'GET'])
    @auth.login_required
    def index():
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
            FreeSpace = "{:,} TB".format(round((TotalSpace - UsedSapce) / 1024 / 1024 / 1024 / 1024), 2)
            # 总使用空间 格式化
            UsedSapce = "{:,} TB".format(round(UsedSapce / 1024 / 1024 / 1024 / 1024), 2)
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
    @auth.login_required
    def search():
        # 查询结果
        sql = "SELECT ID,TITLE||' ('||YEAR||') '||ES_STRING,RES_TYPE,SIZE,SEEDERS,ENCLOSURE,SITE,YEAR,ES_STRING,IMAGE,TYPE FROM JACKETT_TORRENTS ORDER BY TITLE, SEEDERS DESC"
        res = select_by_sql(sql)
        return render_template("search.html",
                               Count=len(res),
                               Items=res,
                               AppVersion=APP_VERSION)

    # 站点订阅页面
    @app.route('/sites', methods=['POST', 'GET'])
    @auth.login_required
    def sites():
        # 获取订阅关键字
        # 读取RSS关键字
        movie_key_list = []
        if config.get('pt'):
            movie_keys = config['pt'].get('movie_keys')
            if movie_keys:
                if not isinstance(movie_keys, list):
                    movie_key_list = [movie_keys]
                else:
                    movie_key_list = movie_keys

        tv_key_list = []
        if config.get('pt'):
            tv_keys = config['pt'].get('tv_keys')
            if tv_keys:
                if not isinstance(tv_keys, list):
                    tv_key_list = [tv_keys]
                else:
                    tv_key_list = tv_keys

        return render_template("sites.html",
                               MovieKeys=','.join('%s' % key for key in movie_key_list),
                               TvKeys=','.join('%s' % key for key in tv_key_list),
                               AppVersion=APP_VERSION)

    # 推荐页面
    @app.route('/recommend', methods=['POST', 'GET'])
    @auth.login_required
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
        TvKeys = []
        MovieKeys = []
        if config.get('pt'):
            if config['pt'].get('movie_keys'):
                MovieKeys = config['pt'].get('movie_keys')
            if config['pt'].get('tv_keys'):
                TvKeys = config['pt'].get('tv_keys')

        for res in res_list:
            rid = res.get('id')
            if RecommendType in ['hm', 'nm']:
                title = res.get('title')
                if title in MovieKeys:
                    fav = 1
                else:
                    fav = 0
                date = res.get('release_date')
                image = res.get('poster_path')
            else:
                title = res.get('name')
                if title in TvKeys:
                    fav = 1
                else:
                    fav = 0
                date = res.get('first_air_date')
                image = res.get('poster_path')
            item = {'id': rid, 'title': title, 'fav': fav, 'date': date, 'image': "https://image.tmdb.org/t/p/original/%s" % image}
            Items.append(item)

        return render_template("recommend.html",
                               Items=Items,
                               RecommendType=RecommendType,
                               CurrentPage=CurrentPage,
                               PageRange=PageRange,
                               AppVersion=APP_VERSION)

    # 服务页面
    @app.route('/service', methods=['POST', 'GET'])
    @auth.login_required
    def service():
        scheduler_cfg_list = []
        if config.get('pt'):
            # RSS下载
            pt_check_interval = config['pt'].get('pt_check_interval')
            if pt_check_interval:
                tim_rssdownload = str(round(pt_check_interval / 60)) + " 分"
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
                tim_pttransfer = str(round(PT_TRANSFER_INTERVAL / 60)) + " 分"
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
                return {"retmsg": "执行完成！", "item": sch_item}

            # 设置订阅关键字
            if cmd == "key":
                movie_keys = data.get("movie_keys")
                # 电影关键字
                if movie_keys:
                    if movie_keys.find(',') != -1:
                        if movie_keys.endswith(','):
                            movie_keys = movie_keys[0, -1]
                        movie_keys = movie_keys.split(',')
                    config['pt']['movie_keys'] = movie_keys
                # 电视剧关键字
                tv_keys = data.get("tv_keys")
                if tv_keys:
                    if tv_keys.find(',') != -1:
                        if tv_keys.endswith(','):
                            tv_keys = tv_keys[0, -1]
                        tv_keys = tv_keys.split(',')
                    config['pt']['tv_keys'] = tv_keys
                # 保存
                save_config(config)
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
                sql = "SELECT ENCLOSURE,TITLE,YEAR,SEASON,EPISODE,VOTE,IMAGE,TYPE FROM JACKETT_TORRENTS WHERE ID=%s" % dl_id
                results = select_by_sql(sql)
                for res in results:
                    Downloader().add_pt_torrent(res[0])
                    if res[7] == "TV":
                        mtype = MediaType.TV
                    else:
                        mtype = MediaType.MOVIE
                    msg_item = {"title": res[1], "vote_average": res[5], "year": res[2], "backdrop_path": res[6],
                                "type": mtype}
                    Message().send_download_message("WEB搜索", msg_item, "%s%s" % (res[3], res[4]))
                return {"retcode": 0}

            # 添加RSS关键字
            if cmd == "addrss":
                name = data.get("name")
                mtype = data.get("type")
                if name and mtype:
                    if mtype in ['nm', 'hm']:
                        movie_keys = config['pt'].get('movie_keys')
                        if movie_keys:
                            if name not in movie_keys:
                                movie_keys.append(name)
                        else:
                            movie_keys = name
                        config['pt']['movie_keys'] = movie_keys
                        save_config(config)
                    else:
                        tv_keys = config['pt'].get('tv_keys')
                        if tv_keys:
                            if name not in tv_keys:
                                tv_keys.append(name)
                        else:
                            tv_keys = name
                        config['pt']['tv_keys'] = tv_keys
                        save_config(config)
                return {"retcode": 0}

            # 删除RSS关键字
            if cmd == "delrss":
                name = data.get("name")
                mtype = data.get("type")
                if name and mtype:
                    if mtype in ['nm', 'hm']:
                        movie_keys = config['pt'].get('movie_keys')
                        if movie_keys:
                            if name in movie_keys:
                                movie_keys.remove(name)
                                config['pt']['movie_keys'] = movie_keys
                                save_config(config)
                    else:
                        tv_keys = config['pt'].get('tv_keys')
                        if tv_keys:
                            if name in tv_keys:
                                tv_keys.remove(name)
                                config['pt']['tv_keys'] = tv_keys
                                save_config(config)
                return {"retcode": 0}

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
            elif content.startswith("http://") or content.startswith("https://") or content.startswith("magnet:"):
                _thread.start_new_thread(Downloader().add_pt_torrent, (content,))
            else:
                _thread.start_new_thread(Jackett().search_one_media, (content,))

            return make_response(reponse_text, 200)

    return app
