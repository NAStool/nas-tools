import os
import log
from rmt.category import Category


# 检查配置信息
def check_config(cfg):
    # 剑查日志输出
    config = cfg.get_config()
    if config.get('app'):
        logtype = config['app'].get('logtype')
        if logtype:
            log.console("日志输出类型为：%s" % logtype)
        if logtype == "server":
            logserver = config['app'].get('logserver')
            if not logserver:
                log.console("【ERROR】logserver未配置，无法正常输出日志")
            else:
                log.console("日志将上送到服务器：%s" % logserver)
        elif logtype == "file":
            logpath = config['app'].get('logpath')
            if not logpath:
                log.console("【ERROR】logpath未配置，无法正常输出日志")
            else:
                log.console("日志将写入文件：%s" % logpath)

        # 检查WEB端口
        web_port = config['app'].get('web_port')
        if not web_port:
            log.error("web_port未设置")
        else:
            log.info("WEB管瑞页面监听端口：%s" % str(web_port))

        # 检查登录用户和密码
        login_user = config['app'].get('login_user')
        login_password = config['app'].get('login_password')
        if not login_user or not login_password:
            log.error("login_user或login_password未设置")
        else:
            log.info("WEB管瑞页面用户：%s" % str(login_user))

        # 检查HTTPS
        ssl_cert = config['app'].get('ssl_cert')
        ssl_key = config['app'].get('ssl_key')
        if not ssl_cert or not ssl_key:
            log.info("未启用https，请使用 http://IP:%s 访问管理页面" % str(web_port))
        else:
            if not os.path.exists(ssl_cert):
                log.error("ssl_cert文件不存在：%s" % ssl_cert)
            if not os.path.exists(ssl_key):
                log.error("ssl_key文件不存在：%s" % ssl_key)
            log.info("已启用https，请使用 https://IP:%s 访问管理页面" % str(web_port))

        rmt_tmdbkey = config['app'].get('rmt_tmdbkey')
        if not rmt_tmdbkey:
            log.error("rmt_tmdbkey未配置")
        rmt_match_mode = config['app'].get('rmt_match_mode')
        if rmt_match_mode:
            rmt_match_mode = rmt_match_mode.upper()
        else:
            rmt_match_mode = "NORMAL"
        if rmt_match_mode == "STRICT":
            log.info("TMDB匹配模式：严格模式")
        else:
            log.info("TMDB匹配模式：正常模式")
    else:
        log.console("app配置不存在")

    # 检查媒体库目录路径
    if config.get('media'):
        media_server = config['media'].get('media_server')
        if media_server:
            log.info("媒体管理软件设置为：%s" % media_server)
            if media_server == "jellyfin":
                if not config.get('jellyfin'):
                    log.warn("jellyfin未配置，部分功能将无法使用")
                else:
                    if not config['jellyfin'].get('host') or not config['jellyfin'].get('api_key'):
                        log.warn("jellyfin配置不完整，部分功能将无法使用")
            else:
                if not config.get('emby'):
                    log.warn("emby未配置，部分功能将无法使用")
                else:
                    if not config['emby'].get('host') or not config['emby'].get('api_key'):
                        log.warn("emby配置不完整，部分功能将无法使用")

        movie_paths = config['media'].get('movie_path')
        if not movie_paths:
            log.error("未配置movie_path")
        else:
            if not isinstance(movie_paths, list):
                movie_paths = [movie_paths]
            for movie_path in movie_paths:
                if not os.path.exists(movie_path):
                    log.error("movie_path目录不存在：%s" % movie_path)

        tv_paths = config['media'].get('tv_path')
        if not tv_paths:
            log.error("未配置tv_path")
        else:
            if not isinstance(tv_paths, list):
                tv_paths = [tv_paths]
            for tv_path in tv_paths:
                if not os.path.exists(tv_path):
                    log.error("tv_path目录不存在：%s" % tv_path)

        anime_paths = config['media'].get('anime_path')
        if anime_paths:
            if not isinstance(anime_paths, list):
                anime_paths = [anime_paths]
            for anime_path in anime_paths:
                if not os.path.exists(anime_path):
                    log.error("anime_path目录不存在：%s" % anime_path)

        category = config['media'].get('category')
        if not category:
            log.warn("未配置分类策略")
        else:
            cates = Category()
            if cates.get_movie_categorys():
                log.info("电影分类：%s" % " ".join(cates.get_movie_categorys()))
            if cates.get_tv_categorys():
                log.info("电视剧分类：%s" % " ".join(cates.get_tv_categorys()))
            if cates.get_anime_categorys():
                log.info("动漫分类：%s" % " ".join(cates.get_anime_categorys()))
    else:
        log.error("media配置不存在")

    # 检查消息配置
    if config.get('message'):
        msg_channel = config['message'].get('msg_channel')
        if not msg_channel:
            log.warn("msg_channel未配置，将无法接收到通知消息")
        elif msg_channel == "wechat":
            corpid = config['message'].get('wechat', {}).get('corpid')
            corpsecret = config['message'].get('wechat', {}).get('corpsecret')
            agentid = config['message'].get('wechat', {}).get('agentid')
            if not corpid or not corpsecret or not agentid:
                log.warn("wechat配置不完整，将无法接收到通知消息")
            Token = config['message'].get('wechat', {}).get('Token')
            EncodingAESKey = config['message'].get('wechat', {}).get('EncodingAESKey')
            if not Token or not EncodingAESKey:
                log.warn("Token、EncodingAESKey未配置，微信控制功能将无法使用")
        elif msg_channel == "serverchan":
            sckey = config['message'].get('serverchan', {}).get('sckey')
            if not sckey:
                log.warn("sckey未配置，将无法接收到通知消息")
        elif msg_channel == "telegram":
            telegram_token = config['message'].get('telegram', {}).get('telegram_token')
            telegram_chat_id = config['message'].get('telegram', {}).get('telegram_chat_id')
            if not telegram_token or not telegram_chat_id:
                log.warn("telegram配置不完整，将无法接收到通知消息")
    else:
        log.warn("message未配置，将无法接收到通知消息")

    # 检查目录同步
    if config.get('sync'):
        sync_paths = config['sync'].get('sync_path')
        if sync_paths:
            for sync_path in sync_paths:
                if not sync_path:
                    continue
                if sync_path.startswith("["):
                    sync_path = sync_path[1:-1]
                if sync_path.find('|') != -1:
                    sync_path = sync_path.split("|")[0]
                if not os.path.exists(sync_path):
                    log.warn("sync_path目录不存在，目录同步功能已关闭：%s" % sync_path)

        sync_mod = config['sync'].get('sync_mod')
        if sync_mod:
            sync_mod = sync_mod.upper()
        else:
            sync_mod = "COPY"
        if sync_mod == "LINK":
            log.info("目录同步转移模式为：硬链接")
        elif sync_mod == "SOFTLINK":
            log.info("目录同步转移模式为：软链接")
        else:
            log.info("目录同步转移模式为：复制")

    # 检查PT配置
    if config.get('pt'):
        pt_client = config['pt'].get('pt_client')
        log.info("PT下载软件设置为：%s" % pt_client)
        if pt_client == "qbittorrent":
            # 检查qbittorrent配置
            if not config.get('qbittorrent'):
                log.error("qbittorrent未配置")
            else:
                save_path = config['qbittorrent'].get('save_path')
                if not save_path:
                    log.warn("qbittorrent save_path未设置，请检查配置：%s" % save_path)
                else:
                    if isinstance(save_path, dict):
                        if not save_path.get('tv') or not save_path.get('movie'):
                            log.warn("qbittorrent save_path配置不完整，请检查配置")
        elif pt_client == "transmission":
            # 检查qbittorrent配置
            if not config.get('transmission'):
                log.error("transmission未配置")
            else:
                save_path = config['transmission'].get('save_path')
                if not save_path:
                    log.warn("transmission save_path未设置，请检查配置！")
                else:
                    if isinstance(save_path, dict):
                        if not save_path.get('tv') or not save_path.get('movie'):
                            log.warn("transmission save_path配置不完整，请检查配置！")
                            
        rmt_mode = config['pt'].get('rmt_mode')
        if rmt_mode:
            rmt_mode = rmt_mode.upper()
        else:
            rmt_mode = "COPY"
        if rmt_mode == "LINK":
            log.info("PT下载文件转移模式为：硬链接")
        elif rmt_mode == "SOFTLINK":
            log.info("目录同步转移模式为：软链接")
        else:
            log.info("PT下载文件转移模式为：复制")

        rss_chinese = config['pt'].get('rss_chinese')
        if rss_chinese:
            log.info("rss_chinese配置为true，将只会下载含中文标题的影视资源")            

        search_indexer = config['pt'].get('search_indexer')
        if search_indexer:
            log.info("PT检索软件设置为：%s" % search_indexer)

        search_auto = config['pt'].get('search_auto')
        if search_auto:
            log.info("微信等移动端渠道搜索已开启自动择优下载")

        ptsignin_cron = config['pt'].get('ptsignin_cron')
        if not ptsignin_cron:
            log.info("ptsignin_cron未配置，PT站签到功能已关闭")

        pt_seeding_time = config['pt'].get('pt_seeding_time')
        if not pt_seeding_time:
            log.info("pt_seeding_time未配置，自动删种功能已关闭")
        else:
            log.info("PT保种时间设置为：%s 小时" % str(round(int(pt_seeding_time) / 3600)))

        pt_check_interval = config['pt'].get('pt_check_interval')
        if not pt_check_interval:
            log.info("pt_check_interval未配置，RSS订阅自动更新功能已关闭")

        pt_monitor = config['pt'].get('pt_monitor')
        if not pt_monitor:
            log.info("pt_monitor未配置，PT下载监控功能已关闭")
    else:
        log.warn("pt未配置，部分功能将无法使用")

    # 检查Douban配置
    if not config.get('douban'):
        log.warn("douban未配置，豆瓣同步功能将无法使用")
    else:
        if not config['douban'].get('users') or not config['douban'].get('types') or not config['douban'].get('days'):
            log.warn("douban配置不完整，豆瓣同步功能将无法使用")

    return True
