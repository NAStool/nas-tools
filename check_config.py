import json
import os
from werkzeug.security import generate_password_hash
from app.helper import DbHelper
from app.utils import StringUtils, ExceptionUtils
from config import Config


def check_config():
    """
    检查配置文件，如有错误进行日志输出
    """
    # 检查日志输出
    if Config().get_config('app'):
        logtype = Config().get_config('app').get('logtype')
        if logtype:
            print("日志输出类型为：%s" % logtype)
        if logtype == "server":
            logserver = Config().get_config('app').get('logserver')
            if not logserver:
                print("【Config】日志中心地址未配置，无法正常输出日志")
            else:
                print("日志将上送到服务器：%s" % logserver)
        elif logtype == "file":
            logpath = Config().get_config('app').get('logpath')
            if not logpath:
                print("【Config】日志文件路径未配置，无法正常输出日志")
            else:
                print("日志将写入文件：%s" % logpath)

        # 检查WEB端口
        web_port = Config().get_config('app').get('web_port')
        if not web_port:
            print("WEB服务端口未设置，将使用默认3000端口")

        # 检查登录用户和密码
        login_user = Config().get_config('app').get('login_user')
        login_password = Config().get_config('app').get('login_password')
        if not login_user or not login_password:
            print("WEB管理用户或密码未设置，将使用默认用户：admin，密码：password")
        else:
            print("WEB管理页面用户：%s" % str(login_user))

        # 检查HTTPS
        ssl_cert = Config().get_config('app').get('ssl_cert')
        ssl_key = Config().get_config('app').get('ssl_key')
        if not ssl_cert or not ssl_key:
            print("未启用https，请使用 http://IP:%s 访问管理页面" % str(web_port))
        else:
            if not os.path.exists(ssl_cert):
                print("ssl_cert文件不存在：%s" % ssl_cert)
            if not os.path.exists(ssl_key):
                print("ssl_key文件不存在：%s" % ssl_key)
            print("已启用https，请使用 https://IP:%s 访问管理页面" % str(web_port))

        rmt_tmdbkey = Config().get_config('app').get('rmt_tmdbkey')
        if not rmt_tmdbkey:
            print("TMDB API Key未配置，媒体整理、搜索下载等功能将无法正常运行！")
        rmt_match_mode = Config().get_config('app').get('rmt_match_mode')
        if rmt_match_mode:
            rmt_match_mode = rmt_match_mode.upper()
        else:
            rmt_match_mode = "NORMAL"
        if rmt_match_mode == "STRICT":
            print("TMDB匹配模式：严格模式")
        else:
            print("TMDB匹配模式：正常模式")
    else:
        print("配置文件格式错误，找不到app配置项！")

    # 检查媒体库目录路径
    if Config().get_config('media'):
        media_server = Config().get_config('media').get('media_server')
        if media_server:
            print("媒体管理软件设置为：%s" % media_server)
            if media_server == "jellyfin":
                if not Config().get_config('jellyfin'):
                    print("jellyfin未配置")
                else:
                    if not Config().get_config('jellyfin').get('host') \
                            or not Config().get_config('jellyfin').get('api_key'):
                        print("jellyfin配置不完整")
            elif media_server == "plex":
                if not Config().get_config('plex'):
                    print("plex未配置")
                else:
                    if not Config().get_config('plex').get('token') \
                            and not Config().get_config('plex').get('username'):
                        print("plex配置不完整")
            else:
                if not Config().get_config('emby'):
                    print("emby未配置")
                else:
                    if not Config().get_config('emby').get('host') \
                            or not Config().get_config('emby').get('api_key'):
                        print("emby配置不完整")

        movie_paths = Config().get_config('media').get('movie_path')
        if not movie_paths:
            print("未配置电影媒体库目录")
        else:
            if not isinstance(movie_paths, list):
                movie_paths = [movie_paths]
            for movie_path in movie_paths:
                if not os.path.exists(movie_path):
                    print("电影媒体库目录不存在：%s" % movie_path)

        tv_paths = Config().get_config('media').get('tv_path')
        if not tv_paths:
            print("未配置电视剧媒体库目录")
        else:
            if not isinstance(tv_paths, list):
                tv_paths = [tv_paths]
            for tv_path in tv_paths:
                if not os.path.exists(tv_path):
                    print("电视剧媒体库目录不存在：%s" % tv_path)

        anime_paths = Config().get_config('media').get('anime_path')
        if anime_paths:
            if not isinstance(anime_paths, list):
                anime_paths = [anime_paths]
            for anime_path in anime_paths:
                if not os.path.exists(anime_path):
                    print("动漫媒体库目录不存在：%s" % anime_path)

        category = Config().get_config('media').get('category')
        if not category:
            print("未配置分类策略")
    else:
        print("配置文件格式错误，找不到media配置项！")

    # 检查站点配置
    if Config().get_config('pt'):
        pt_client = Config().get_config('pt').get('pt_client')
        print("下载软件设置为：%s" % pt_client)

        rmt_mode = Config().get_config('pt').get('rmt_mode', 'copy')
        if rmt_mode == "link":
            print("默认文件转移模式为：硬链接")
        elif rmt_mode == "softlink":
            print("默认文件转移模式为：软链接")
        elif rmt_mode == "move":
            print("默认文件转移模式为：移动")
        elif rmt_mode == "rclone":
            print("默认文件转移模式为：rclone移动")
        elif rmt_mode == "rclonecopy":
            print("默认文件转移模式为：rclone复制")
        else:
            print("默认文件转移模式为：复制")

        search_indexer = Config().get_config('pt').get('search_indexer')
        if search_indexer:
            print("索引器设置为：%s" % search_indexer)

        search_auto = Config().get_config('pt').get('search_auto')
        if search_auto:
            print("微信等移动端渠道搜索已开启自动择优下载")

        ptsignin_cron = Config().get_config('pt').get('ptsignin_cron')
        if not ptsignin_cron:
            print("站点自动签到时间未配置，站点签到功能已关闭")

        pt_check_interval = Config().get_config('pt').get('pt_check_interval')
        if not pt_check_interval:
            print("RSS订阅周期未配置，RSS订阅功能已关闭")

        pt_monitor = Config().get_config('pt').get('pt_monitor')
        if not pt_monitor:
            print("下载软件监控未开启，下载器监控功能已关闭")
    else:
        print("配置文件格式错误，找不到pt配置项！")

    # 检查Douban配置
    if not Config().get_config('douban'):
        print("豆瓣未配置")
    else:
        if not Config().get_config('douban').get('users') \
                or not Config().get_config('douban').get('types') \
                or not Config().get_config('douban').get('days'):
            print("豆瓣配置不完整")


def update_config():
    """
    升级配置文件
    """
    _config = Config().get_config()
    _dbhelper = DbHelper()
    overwrite_cofig = False

    # 密码初始化
    login_password = _config.get("app", {}).get("login_password") or "password"
    if login_password and not login_password.startswith("[hash]"):
        _config['app']['login_password'] = "[hash]%s" % generate_password_hash(login_password)
        overwrite_cofig = True

    # 实验室配置初始化
    if not _config.get("laboratory"):
        _config['laboratory'] = {
            'search_keyword': False,
            'tmdb_cache_expire': True,
            'use_douban_titles': False,
            'search_en_title': True,
            'chrome_browser': False
        }
        overwrite_cofig = True

    # 安全配置初始化
    if not _config.get("security"):
        _config['security'] = {
            'media_server_webhook_allow_ip': {
                'ipv4': '0.0.0.0/0',
                'ipv6': '::/0'
            },
            'telegram_webhook_allow_ip': {
                'ipv4': '127.0.0.1',
                'ipv6': '::/0'
            }
        }
        overwrite_cofig = True

    # Synology Chat安全配置初始化
    if not _config.get("security", {}).get("synology_webhook_allow_ip"):
        _config['security']['synology_webhook_allow_ip'] = {
            'ipv4': '127.0.0.1',
            'ipv6': '::/0'
        }
        overwrite_cofig = True

    # API密钥初始化
    if not _config.get("security", {}).get("api_key"):
        _config['security']['api_key'] = _config.get("security",
                                                     {}).get("subscribe_token") \
                                         or StringUtils.generate_random_str()
        if _config.get('security', {}).get('subscribe_token'):
            _config['security'].pop('subscribe_token')
        overwrite_cofig = True

    # 刮削NFO配置初始化
    if not _config.get("scraper_nfo"):
        _config['scraper_nfo'] = {
            "movie": {
                "basic": True,
                "credits": True,
                "credits_chinese": False},
            "tv": {
                "basic": True,
                "credits": True,
                "credits_chinese": False,
                "season_basic": True,
                "episode_basic": True,
                "episode_credits": True}
        }
        overwrite_cofig = True

    # 刮削图片配置初始化
    if not _config.get("scraper_pic"):
        _config['scraper_pic'] = {
            "movie": {
                "poster": True,
                "backdrop": True,
                "background": True,
                "logo": True,
                "disc": True,
                "banner": True,
                "thumb": True},
            "tv": {
                "poster": True,
                "backdrop": True,
                "background": True,
                "logo": True,
                "clearart": True,
                "banner": True,
                "thumb": True,
                "season_poster": True,
                "season_banner": True,
                "season_thumb": True}
        }
        overwrite_cofig = True

    # 下载目录配置初始化
    if not _config.get('downloaddir'):
        dl_client = _config.get('pt', {}).get('pt_client')
        if dl_client and _config.get(dl_client):
            save_path = _config.get(dl_client).get('save_path')
            if not isinstance(save_path, dict):
                save_path = {"movie": save_path, "tv": save_path, "anime": save_path}
            container_path = _config.get(dl_client).get('save_containerpath')
            if not isinstance(container_path, dict):
                container_path = {"movie": container_path, "tv": container_path, "anime": container_path}
            downloaddir = []
            type_dict = {"movie": "电影", "tv": "电视剧", "anime": "动漫"}
            for mtype, path in save_path.items():
                if not path:
                    continue
                save_dir = path.split('|')[0]
                save_label = None
                if len(path.split('|')) > 1:
                    save_label = path.split('|')[1]
                container_dir = container_path.get(mtype)
                if save_dir:
                    downloaddir.append({"save_path": save_dir,
                                        "type": type_dict.get(mtype),
                                        "category": "",
                                        "container_path": container_dir,
                                        "label": save_label})
            _config['downloaddir'] = downloaddir
        if _config.get('qbittorrent', {}).get('save_path'):
            _config['qbittorrent'].pop('save_path')
        if _config.get('qbittorrent', {}).get('save_containerpath'):
            _config['qbittorrent'].pop('save_containerpath')
        if _config.get('transmission', {}).get('save_path'):
            _config['transmission'].pop('save_path')
        if _config.get('transmission', {}).get('save_containerpath'):
            _config['transmission'].pop('save_containerpath')
        if _config.get('client115', {}).get('save_path'):
            _config['client115'].pop('save_path')
        if _config.get('client115', {}).get('save_containerpath'):
            _config['client115'].pop('save_containerpath')
        if _config.get('aria2', {}).get('save_path'):
            _config['aria2'].pop('save_path')
        if _config.get('aria2', {}).get('save_containerpath'):
            _config['aria2'].pop('save_containerpath')
        overwrite_cofig = True
    elif isinstance(_config.get('downloaddir'), dict):
        downloaddir_list = []
        for path, attr in _config.get('downloaddir').items():
            downloaddir_list.append({"save_path": path,
                                     "type": attr.get("type"),
                                     "category": attr.get("category"),
                                     "container_path": attr.get("path"),
                                     "label": attr.get("label")})
        _config['downloaddir'] = downloaddir_list
        overwrite_cofig = True

    # 自定义识别词兼容旧配置
    try:
        ignored_words = Config().get_config('laboratory').get("ignored_words")
        if ignored_words:
            ignored_words = ignored_words.split("||")
            for ignored_word in ignored_words:
                if not _dbhelper.is_custom_words_existed(replaced=ignored_word):
                    _dbhelper.insert_custom_word(replaced=ignored_word,
                                                 replace="",
                                                 front="",
                                                 back="",
                                                 offset=0,
                                                 wtype=1,
                                                 gid=-1,
                                                 season=-2,
                                                 enabled=1,
                                                 regex=1,
                                                 whelp="")
            _config['laboratory'].pop('ignored_words')
            overwrite_cofig = True
        replaced_words = Config().get_config('laboratory').get("replaced_words")
        if replaced_words:
            replaced_words = replaced_words.split("||")
            for replaced_word in replaced_words:
                replaced_word = replaced_word.split("@")
                if not _dbhelper.is_custom_words_existed(replaced=replaced_word[0]):
                    _dbhelper.insert_custom_word(replaced=replaced_word[0],
                                                 replace=replaced_word[1],
                                                 front="",
                                                 back="",
                                                 offset=0,
                                                 wtype=2,
                                                 gid=-1,
                                                 season=-2,
                                                 enabled=1,
                                                 regex=1,
                                                 whelp="")
            _config['laboratory'].pop('replaced_words')
            overwrite_cofig = True
        offset_words = Config().get_config('laboratory').get("offset_words")
        if offset_words:
            offset_words = offset_words.split("||")
            for offset_word in offset_words:
                offset_word = offset_word.split("@")
                if not _dbhelper.is_custom_words_existed(front=offset_word[0], back=offset_word[1]):
                    _dbhelper.insert_custom_word(replaced="",
                                                 replace="",
                                                 front=offset_word[0],
                                                 back=offset_word[1],
                                                 offset=offset_word[2],
                                                 wtype=4,
                                                 gid=-1,
                                                 season=-2,
                                                 enabled=1,
                                                 regex=1,
                                                 whelp="")
            _config['laboratory'].pop('offset_words')
            overwrite_cofig = True
    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # 目录同步兼容旧配置
    try:
        sync_paths = Config().get_config('sync').get('sync_path')
        rmt_mode = Config().get_config('pt').get('sync_mod')
        if sync_paths:
            if isinstance(sync_paths, list):
                for sync_items in sync_paths:
                    SyncPath = {'from': "",
                                'to': "",
                                'unknown': "",
                                'syncmod': rmt_mode,
                                'rename': 1,
                                'enabled': 1}
                    # 是否启用
                    if sync_items.startswith("#"):
                        SyncPath['enabled'] = 0
                        sync_items = sync_items[1:-1]
                    # 是否重命名
                    if sync_items.startswith("["):
                        SyncPath['rename'] = 0
                        sync_items = sync_items[1:-1]
                    # 转移方式
                    config_items = sync_items.split("@")
                    if not config_items:
                        continue
                    if len(config_items) > 1:
                        SyncPath['syncmod'] = config_items[-1]
                    else:
                        SyncPath['syncmod'] = rmt_mode
                    if not SyncPath['syncmod']:
                        continue
                    # 源目录|目的目录|未知目录
                    paths = config_items[0].split("|")
                    if not paths:
                        continue
                    if len(paths) > 0:
                        if not paths[0]:
                            continue
                        SyncPath['from'] = os.path.normpath(paths[0])
                    if len(paths) > 1:
                        SyncPath['to'] = os.path.normpath(paths[1])
                    if len(paths) > 2:
                        SyncPath['unknown'] = os.path.normpath(paths[2])
                    # 相同from的同步目录不能同时开启
                    if SyncPath['enabled'] == 1:
                        _dbhelper.check_config_sync_paths(source=SyncPath['from'],
                                                          enabled=0)
                    _dbhelper.insert_config_sync_path(source=SyncPath['from'],
                                                      dest=SyncPath['to'],
                                                      unknown=SyncPath['unknown'],
                                                      mode=SyncPath['syncmod'],
                                                      rename=SyncPath['rename'],
                                                      enabled=SyncPath['enabled'])
            else:
                _dbhelper.insert_config_sync_path(source=sync_paths,
                                                  dest="",
                                                  unknown="",
                                                  mode=rmt_mode,
                                                  rename=1,
                                                  enabled=0)
            _config['sync'].pop('sync_path')
            overwrite_cofig = True
    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # 消息服务兼容旧配置
    try:
        message = Config().get_config('message') or {}
        msg_channel = message.get('msg_channel')
        if msg_channel:
            switchs = []
            switch = message.get('switch')
            if switch:
                if switch.get("download_start"):
                    switchs.append("download_start")
                if switch.get("download_fail"):
                    switchs.append("download_fail")
                if switch.get("transfer_finished"):
                    switchs.append("transfer_finished")
                if switch.get("transfer_fail"):
                    switchs.append("transfer_fail")
                if switch.get("rss_added"):
                    switchs.append("rss_added")
                if switch.get("rss_finished"):
                    switchs.append("rss_finished")
                if switch.get("site_signin"):
                    switchs.append("site_signin")
                switchs.append('site_message')
                switchs.append('brushtask_added')
                switchs.append('brushtask_remove')
                switchs.append('mediaserver_message')
            if message.get('telegram'):
                token = message.get('telegram', {}).get('telegram_token')
                chat_id = message.get('telegram', {}).get('telegram_chat_id')
                user_ids = message.get('telegram', {}).get('telegram_user_ids')
                webhook = message.get('telegram', {}).get('webhook')
                if token and chat_id:
                    name = "Telegram"
                    ctype = 'telegram'
                    enabled = 1 if msg_channel == ctype else 0
                    interactive = 1 if enabled else 0
                    client_config = json.dumps({
                        'token': token,
                        'chat_id': chat_id,
                        'user_ids': user_ids,
                        'webhook': webhook
                    })
                    _dbhelper.insert_message_client(name=name,
                                                    ctype=ctype,
                                                    config=client_config,
                                                    switchs=switchs,
                                                    interactive=interactive,
                                                    enabled=enabled)
            if message.get('wechat'):
                corpid = message.get('wechat', {}).get('corpid')
                corpsecret = message.get('wechat', {}).get('corpsecret')
                agent_id = message.get('wechat', {}).get('agentid')
                default_proxy = message.get('wechat', {}).get('default_proxy')
                token = message.get('wechat', {}).get('Token')
                encodingAESkey = message.get('wechat', {}).get('EncodingAESKey')
                if corpid and corpsecret and agent_id:
                    name = "WeChat"
                    ctype = 'wechat'
                    enabled = 1 if msg_channel == ctype else 0
                    interactive = 1 if enabled else 0
                    client_config = json.dumps({
                        'corpid': corpid,
                        'corpsecret': corpsecret,
                        'agentid': agent_id,
                        'default_proxy': default_proxy,
                        'token': token,
                        'encodingAESKey': encodingAESkey
                    })
                    _dbhelper.insert_message_client(name=name,
                                                    ctype=ctype,
                                                    config=client_config,
                                                    switchs=switchs,
                                                    interactive=interactive,
                                                    enabled=enabled)
            if message.get('serverchan'):
                sckey = message.get('serverchan', {}).get('sckey')
                if sckey:
                    name = "ServerChan"
                    ctype = 'serverchan'
                    interactive = 0
                    enabled = 1 if msg_channel == ctype else 0
                    client_config = json.dumps({
                        'sckey': sckey
                    })
                    _dbhelper.insert_message_client(name=name,
                                                    ctype=ctype,
                                                    config=client_config,
                                                    switchs=switchs,
                                                    interactive=interactive,
                                                    enabled=enabled)
            if message.get('bark'):
                server = message.get('bark', {}).get('server')
                apikey = message.get('bark', {}).get('apikey')
                if server and apikey:
                    name = "Bark"
                    ctype = 'bark'
                    interactive = 0
                    enabled = 1 if msg_channel == ctype else 0
                    client_config = json.dumps({
                        'server': server,
                        'apikey': apikey
                    })
                    _dbhelper.insert_message_client(name=name,
                                                    ctype=ctype,
                                                    config=client_config,
                                                    switchs=switchs,
                                                    interactive=interactive,
                                                    enabled=enabled)
            if message.get('pushplus'):
                token = message.get('pushplus', {}).get('push_token')
                topic = message.get('pushplus', {}).get('push_topic')
                channel = message.get('pushplus', {}).get('push_channel')
                webhook = message.get('pushplus', {}).get('push_webhook')
                if token and channel:
                    name = "PushPlus"
                    ctype = 'pushplus'
                    interactive = 0
                    enabled = 1 if msg_channel == ctype else 0
                    client_config = json.dumps({
                        'token': token,
                        'topic': topic,
                        'channel': channel,
                        'webhook': webhook
                    })
                    _dbhelper.insert_message_client(name=name,
                                                    ctype=ctype,
                                                    config=client_config,
                                                    switchs=switchs,
                                                    interactive=interactive,
                                                    enabled=enabled)
            if message.get('iyuu'):
                token = message.get('iyuu', {}).get('iyuu_token')
                if token:
                    name = "IyuuMsg"
                    ctype = 'iyuu'
                    interactive = 0
                    enabled = 1 if msg_channel == ctype else 0
                    client_config = json.dumps({
                        'token': token
                    })
                    _dbhelper.insert_message_client(name=name,
                                                    ctype=ctype,
                                                    config=client_config,
                                                    switchs=switchs,
                                                    interactive=interactive,
                                                    enabled=enabled)
            # 删除旧配置
            if _config.get('message', {}).get('msg_channel'):
                _config['message'].pop('msg_channel')
            if _config.get('message', {}).get('switch'):
                _config['message'].pop('switch')
            if _config.get('message', {}).get('wechat'):
                _config['message'].pop('wechat')
            if _config.get('message', {}).get('telegram'):
                _config['message'].pop('telegram')
            if _config.get('message', {}).get('serverchan'):
                _config['message'].pop('serverchan')
            if _config.get('message', {}).get('bark'):
                _config['message'].pop('bark')
            if _config.get('message', {}).get('pushplus'):
                _config['message'].pop('pushplus')
            if _config.get('message', {}).get('iyuu'):
                _config['message'].pop('iyuu')
            overwrite_cofig = True
    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # 站点兼容旧配置
    try:
        sites = _dbhelper.get_config_site()
        for site in sites:
            if not site.NOTE or str(site.NOTE).find('{') != -1:
                continue
            # 是否解析种子详情为|分隔的第1位
            site_parse = str(site.NOTE).split("|")[0] or "Y"
            # 站点过滤规则为|分隔的第2位
            rule_groupid = str(site.NOTE).split("|")[1] if site.NOTE and len(str(site.NOTE).split("|")) > 1 else ""
            # 站点未读消息为|分隔的第3位
            site_unread_msg_notify = str(site.NOTE).split("|")[2] if site.NOTE and len(
                str(site.NOTE).split("|")) > 2 else "Y"
            # 自定义UA为|分隔的第4位
            ua = str(site.NOTE).split("|")[3] if site.NOTE and len(str(site.NOTE).split("|")) > 3 else ""
            # 是否开启浏览器仿真为|分隔的第5位
            chrome = str(site.NOTE).split("|")[4] if site.NOTE and len(str(site.NOTE).split("|")) > 4 else "N"
            # 是否使用代理为|分隔的第6位
            proxy = str(site.NOTE).split("|")[5] if site.NOTE and len(str(site.NOTE).split("|")) > 5 else "N"
            _dbhelper.update_config_site_note(tid=site.ID, note=json.dumps({
                "parse": site_parse,
                "rule": rule_groupid,
                "message": site_unread_msg_notify,
                "ua": ua,
                "chrome": chrome,
                "proxy": proxy
            }))

    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # 订阅兼容旧配置
    try:
        def __parse_rss_desc(desc):
            rss_sites = []
            search_sites = []
            over_edition = False
            restype = None
            pix = None
            team = None
            rule = None
            total = None
            current = None
            notes = str(desc).split('#')
            # 订阅站点
            if len(notes) > 0:
                if notes[0]:
                    rss_sites = [s for s in str(notes[0]).split('|') if s and len(s) < 20]
            # 搜索站点
            if len(notes) > 1:
                if notes[1]:
                    search_sites = [s for s in str(notes[1]).split('|') if s]
            # 洗版
            if len(notes) > 2:
                over_edition = notes[2]
            # 过滤条件
            if len(notes) > 3:
                if notes[3]:
                    filters = notes[3].split('@')
                    if len(filters) > 0:
                        restype = filters[0]
                    if len(filters) > 1:
                        pix = filters[1]
                    if len(filters) > 2:
                        rule = int(filters[2]) if filters[2].isdigit() else None
                    if len(filters) > 3:
                        team = filters[3]
            # 总集数及当前集数
            if len(notes) > 4:
                if notes[4]:
                    ep_info = notes[4].split('@')
                    if len(ep_info) > 0:
                        total = int(ep_info[0]) if ep_info[0] else None
                    if len(ep_info) > 1:
                        current = int(ep_info[1]) if ep_info[1] else None
            return {
                "rss_sites": rss_sites,
                "search_sites": search_sites,
                "over_edition": over_edition,
                "restype": restype,
                "pix": pix,
                "team": team,
                "rule": rule,
                "total": total,
                "current": current
            }

        # 电影订阅
        rss_movies = _dbhelper.get_rss_movies()
        for movie in rss_movies:
            if not movie.DESC or str(movie.DESC).find('#') == -1:
                continue
            # 更新到具体字段
            _dbhelper.update_rss_movie_desc(
                rid=movie.ID,
                desc=json.dumps(__parse_rss_desc(movie.DESC))
            )
        # 电视剧订阅
        rss_tvs = _dbhelper.get_rss_tvs()
        for tv in rss_tvs:
            if not tv.DESC or str(tv.DESC).find('#') == -1:
                continue
            # 更新到具体字段
            _dbhelper.update_rss_tv_desc(
                rid=tv.ID,
                desc=json.dumps(__parse_rss_desc(tv.DESC))
            )

    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # 重写配置文件
    if overwrite_cofig:
        Config().save_config(_config)
