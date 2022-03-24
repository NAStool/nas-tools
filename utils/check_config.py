# 检查配置信息
import os

import qbittorrentapi
import transmission_rpc

import log


def check_config(cfg):
    # 剑查日志输出
    config = cfg.get_config()
    if config.get('app'):
        logtype = config['app'].get('logtype', 'CONSOLE')
        print("【RUN】日志输出类型为：%s" % logtype)
        if logtype == "SERVER":
            logserver = config['app'].get('logserver')
            if not logserver:
                print("【RUN】logserver未配置，无法正常输出日志")
            else:
                print("【RUN】日志将上送到服务器：%s" % logserver)
        elif logtype == "FILE":
            logpath = config['app'].get('logpath')
            if not logpath:
                print("【RUN】logpath未配置，无法正常输出日志")
            else:
                print("【RUN】日志将写入文件：%s" % logpath)

        # 检查WEB端口
        web_port = config['app'].get('web_port')
        if not web_port:
            log.error("【RUN】web_port未设置，程序无法启动")
            return False
        else:
            log.info("【RUN】WEB管瑞页面监听端口：%s" % str(web_port))

        # 检查登录用户和密码
        login_user = config['app'].get('login_user')
        login_password = config['app'].get('login_password')
        if not login_user or not login_password:
            log.error("【RUN】login_user或login_password未设置，程序无法启动")
            return False
        else:
            log.info("【RUN】WEB管瑞页面用户：%s" % str(login_user))

        # 检查HTTPS
        ssl_cert = config['app'].get('ssl_cert')
        ssl_key = config['app'].get('ssl_key')
        if not ssl_cert or not ssl_key:
            log.info("【RUN】未启用https，请使用 http://IP:%s 访问管理页面" % str(web_port))
        else:
            if not os.path.exists(ssl_cert):
                log.error("【RUN】ssl_cert文件不存在：%s" % ssl_cert)
                return False
            if not os.path.exists(ssl_key):
                log.error("【RUN】ssl_key文件不存在：%s" % ssl_key)
                return False
            log.info("【RUN】已启用https，请使用 https://IP:%s 访问管理页面" % str(web_port))

        rmt_tmdbkey = config['app'].get('rmt_tmdbkey')
        if not rmt_tmdbkey:
            log.error("【RUN】rmt_tmdbkey未配置，程序无法启动")
            return False
    else:
        print("【RUN】app配置不存在，程序无法启动")
        return False

    # 检查媒体库目录路径
    if config.get('media'):
        movie_path = config['media'].get('movie_path')
        if not movie_path:
            log.error("【RUN】未配置movie_path，程序无法启动")
            return False
        elif not os.path.exists(movie_path):
            log.error("【RUN】movie_path目录不存在，程序无法启动：%s" % movie_path)
            return False

        tv_path = config['media'].get('tv_path')
        if not tv_path:
            log.error("【RUN】未配置tv_path，程序无法启动")
            return False
        elif not os.path.exists(tv_path):
            log.error("【RUN】tv_path目录不存在，程序无法启动：%s" % tv_path)
            return False

        movie_subtypedir = config['media'].get('movie_subtypedir', True)
        if not movie_subtypedir:
            log.warn("【RUN】电影自动分类功能已关闭")
        else:
            log.info("【RUN】电影自动分类功能已开启")
        tv_subtypedir = config['media'].get('tv_subtypedir', True)
        if not tv_subtypedir:
            log.warn("【RUN】电视剧自动分类功能已关闭")
        else:
            log.info("【RUN】电视剧自动分类功能已开启")
    else:
        log.error("【RUN】media配置不存在，程序无法启动")
        return False

    if config.get('sync'):
        sync_paths = config['sync'].get('sync_path')
        if sync_paths:
            for sync_path in sync_paths:
                if sync_path.find('|') != -1:
                    sync_path = sync_path.split("|")[0]
                if not os.path.exists(sync_path):
                    log.warn("【RUN】sync_path目录不存在，该目录监控资源同步功能将禁用：%s" % sync_path)
        else:
            log.warn("【RUN】未配置sync_path，目录监控资源同步功能将禁用")

        sync_mod = config['sync'].get('sync_mod', 'COPY').upper()
        if sync_mod == "LINK":
            log.info("【RUN】目录监控转移模式为：硬链接")
        elif sync_mod == "SOFTLINK":
            log.info("【RUN】目录监控转移模式为：软链接")
        else:
            log.info("【RUN】目录监控转移模式为：复制")

    # 检查Emby配置
    if not config.get('emby'):
        log.warn("【RUN】emby未配置，部分功能将无法使用")
    else:
        if not config['emby'].get('host') or not config['emby'].get('api_key'):
            log.warn("【RUN】emby配置不完整，部分功能将无法使用")

    # 检查Douban配置
    if not config.get('douban'):
        log.warn("【RUN】douban未配置，豆瓣同步功能将无法使用")
    else:
        if not config['douban'].get('users') or not config['douban'].get('types') or not config['douban'].get('days'):
            log.warn("【RUN】douban配置不完整，豆瓣同步功能将无法使用")

    # 检查消息配置
    if config.get('message'):
        msg_channel = config['message'].get('msg_channel')
        if not msg_channel:
            log.warn("【RUN】msg_channel未配置，将无法接收到通知消息")
        elif msg_channel == "wechat":
            corpid = config['message'].get('wechat', {}).get('corpid')
            corpsecret = config['message'].get('wechat', {}).get('corpsecret')
            agentid = config['message'].get('wechat', {}).get('agentid')
            if not corpid or not corpsecret or not agentid:
                log.warn("【RUN】wechat配置不完整，将无法接收到微信通知消息")
            Token = config['message'].get('wechat', {}).get('Token')
            EncodingAESKey = config['message'].get('wechat', {}).get('EncodingAESKey')
            if not Token or not EncodingAESKey:
                log.warn("【RUN】Token、EncodingAESKey未配置，微信控制功能将无法使用")
        elif msg_channel == "serverchan":
            sckey = config['message'].get('serverchan', {}).get('sckey')
            if not sckey:
                log.warn("【RUN】sckey未配置，将无法接收到Server酱通知消息")
        elif msg_channel == "telegram":
            telegram_token = config['message'].get('telegram', {}).get('telegram_token')
            telegram_chat_id = config['message'].get('telegram', {}).get('telegram_chat_id')
            if not telegram_token or not telegram_chat_id:
                log.warn("【RUN】telegram配置不完整，将无法接收到通知消息")
    else:
        log.warn("【RUN】message未配置，将无法接收到通知消息")

    # 检查PT配置
    if config.get('pt'):
        rmt_mode = config['pt'].get('rmt_mode', 'COPY').upper()
        if rmt_mode == "LINK":
            log.info("【RUN】PT下载文件转移模式为：硬链接")
        elif rmt_mode == "SOFTLINK":
            log.info("【RUN】目录监控转移模式为：软链接")
        else:
            log.info("【RUN】PT下载文件转移模式为：复制")

        rss_chinese = config['pt'].get('rss_chinese')
        if rss_chinese:
            log.info("【RUN】rss_chinese配置为true，将只会下载含中文标题的影视资源")

        ptsignin_cron = config['pt'].get('ptsignin_cron')
        if not ptsignin_cron:
            log.warn("【RUN】ptsignin_cron未配置，将无法使用PT站签到功能")

        pt_seeding_time = config['pt'].get('pt_seeding_time')
        if not pt_seeding_time:
            log.warn("【RUN】pt_seeding_time未配置，自动删种功能将禁用")
        else:
            log.info("【RUN】PT保种时间设置为：%s 小时" % str(round(pt_seeding_time / 3600)))

        pt_check_interval = config['pt'].get('pt_check_interval')
        if not pt_check_interval:
            log.warn("【RUN】pt_check_interval未配置，RSS订阅自动更新功能将禁用")

        pt_monitor = config['pt'].get('pt_monitor')
        if not pt_monitor:
            log.info("【RUN】pt_monitor未配置，PT下载监控已关闭")

        pt_client = config['pt'].get('pt_client')
        log.info("【RUN】PT下载软件设置为：%s" % pt_client)
        if pt_client == "qbittorrent":
            # 检查qbittorrent配置并测试连通性
            if not config.get('qbittorrent'):
                log.error("qbittorrent未配置，程序无法启动")
                return False
            qbhost = config['qbittorrent'].get('qbhost')
            qbport = config['qbittorrent'].get('qbport')
            qbusername = config['qbittorrent'].get('qbusername')
            qbpassword = config['qbittorrent'].get('qbpassword')
            try:
                qbt = qbittorrentapi.Client(host=qbhost,
                                            port=qbport,
                                            username=qbusername,
                                            password=qbpassword,
                                            VERIFY_WEBUI_CERTIFICATE=False)
                qbt.auth_log_in()
            except Exception as err:
                log.warn("【RUN】qBittorrent无法连接，请检查配置：%s" % str(err))
            save_path = config['qbittorrent'].get('save_path')
            if not save_path:
                log.warn("【RUN】qbittorrent save_path未设置，请检查配置：%s" % save_path)
            else:
                if isinstance(save_path, dict):
                    if not save_path.get('tv') or not save_path.get('movie'):
                        log.warn("【RUN】qbittorrent save_path配置不完整，请检查配置！")
            save_containerpath = config['qbittorrent'].get('save_containerpath')

            if not save_containerpath:
                log.warn("【RUN】qbittorrent save_path未设置，如果是Docker容器使用则必须配置该项，否则无法正常转移文件")
            else:
                if isinstance(save_containerpath, dict):
                    if not save_containerpath.get('tv') or not save_containerpath.get('movie'):
                        log.warn("【RUN】qbittorrent save_containerpath配置不完整，如果是Docker容器使用则必须配置该项，否则无法正常转移文件")
        elif pt_client == "transmission":
            # 检查qbittorrent配置并测试连通性
            if not config.get('transmission'):
                log.error("【RUN】transmission未配置，程序无法启动")
                return False
            trhost = config['transmission'].get('trhost')
            trport = config['transmission'].get('trport')
            trusername = config['transmission'].get('trusername')
            trpassword = config['transmission'].get('trpassword')
            try:
                trt = transmission_rpc.Client(username=trusername, password=trpassword, host=trhost,
                                              port=trport)
                rpc_version = trt.rpc_version
                if not rpc_version:
                    log.warn("【RUN】transmission无法连接，请检查配置")
            except Exception as err:
                log.warn("【RUN】transmission无法连接，请检查配置：%s" % str(err))
            save_path = config['transmission'].get('save_path')
            if not save_path:
                log.warn("【RUN】transmission save_path未设置，请检查配置！")
            else:
                if isinstance(save_path, dict):
                    if not save_path.get('tv') or not save_path.get('movie'):
                        log.warn("【RUN】transmission save_path配置不完整，请检查配置！")
            save_containerpath = config['transmission'].get('save_containerpath')
            if not save_containerpath:
                log.warn("【RUN】transmission save_path未设置，如果是Docker容器使用则必须配置该项，否则无法正常转移文件")
            else:
                if isinstance(save_containerpath, dict):
                    if not save_containerpath.get('tv') or not save_containerpath.get('movie'):
                        log.warn("【RUN】transmission save_containerpath配置不完整，如果是Docker容器使用则必须配置该项，否则无法正常转移文件")

        sites = config['pt'].get('sites')
        if sites:
            for key, value in sites.items():
                rssurl = sites.get(key, {}).get('rssurl')
                if not rssurl:
                    log.warn("【RUN】%s 的 rssurl 未配置，该PT站的RSS订阅下载功能将禁用" % key)
                signin_url = sites.get(key, {}).get('signin_url')
                if not signin_url:
                    log.warn("【RUN】%s 的 signin_url 未配置，该PT站的自动签到功能将禁用" % key)
                cookie = sites.get(key, {}).get('cookie')
                if not cookie:
                    log.warn("【RUN】%s 的 cookie 未配置，该PT站的自动签到功能将禁用" % key)
        else:
            log.warn("【RUN】sites未配置，RSS订阅下载功能将禁用")
    else:
        log.warn("pt未配置，部分功能将无法使用")

    return True


# 检查硬链接模式的配置信息
def check_simple_config(cfg):
    config = cfg.get_config()
    app = config.get('app')
    if not app:
        print("【RUN】app配置不存在，程序无法启动")
        return False

    rmt_tmdbkey = config['app'].get('rmt_tmdbkey')
    if not rmt_tmdbkey:
        log.error("【RUN】rmt_tmdbkey未配置，程序无法启动")
        return False

    # 检查媒体库目录路径
    if config.get('media'):
        movie_path = config['media'].get('movie_path')
        if not movie_path:
            log.error("【RUN】未配置movie_path，程序无法启动")
            return False
        elif not os.path.exists(movie_path):
            log.error("【RUN】movie_path目录不存在，程序无法启动：%s" % movie_path)
            return False

        tv_path = config['media'].get('tv_path')
        if not tv_path:
            log.error("【RUN】未配置tv_path，程序无法启动")
            return False
        elif not os.path.exists(tv_path):
            log.error("【RUN】tv_path目录不存在，程序无法启动：%s" % tv_path)
            return False

        movie_subtypedir = config['media'].get('movie_subtypedir', True)
        if not movie_subtypedir:
            log.warn("【RUN】电影自动分类功能已关闭")
        else:
            log.info("【RUN】电影自动分类功能已开启")

        tv_subtypedir = config['media'].get('tv_subtypedir', True)
        if not tv_subtypedir:
            log.warn("【RUN】电视剧自动分类功能已关闭")
        else:
            log.info("【RUN】电视剧自动分类功能已开启")
    else:
        log.error("media配置不存在，程序无法启动")
        return False

    if config.get('sync'):
        sync_paths = config['sync'].get('sync_path')
        if sync_paths:
            for sync_path in sync_paths:
                if sync_path.find('|') != -1:
                    sync_path = sync_path.split("|")[0]
                if not os.path.exists(sync_path):
                    log.warn("【RUN】sync_path目录不存在，该目录监控资源同步功能将禁用：%s" % sync_path)
        else:
            log.warn("【RUN】未配置sync_path，目录监控资源同步功能将禁用")
        # 检查Sync配置
        sync_mod = config['sync'].get('sync_mod', 'COPY').upper()
        if sync_mod == "LINK":
            log.info("【RUN】目录监控转移模式为：硬链接")
        elif sync_mod == "SOFTLINK":
            log.info("【RUN】目录监控转移模式为：软链接")
        else:
            log.info("【RUN】目录监控转移模式为：复制")

    if config.get('pt'):
        # 检查PT配置
        rmt_mode = config['pt'].get('rmt_mode', 'COPY').upper()
        if rmt_mode == "LINK":
            log.info("【RUN】PT下载文件转移模式为：硬链接")
        elif rmt_mode == "SOFTLINK":
            log.info("【RUN】目录监控转移模式为：软链接")
        else:
            log.info("【RUN】PT下载文件转移模式为：复制")

        pt_monitor = config['pt'].get('pt_monitor')
        if not pt_monitor:
            log.info("【RUN】pt_monitor未配置，PT下载监控已关闭")

        pt_client = config['pt'].get('pt_client')
        if pt_client == "qbittorrent":
            # 检查qbittorrent配置并测试连通性
            if not config.get('qbittorrent'):
                log.error("qbittorrent未配置，程序无法启动")
                return False
            qbhost = config['qbittorrent'].get('qbhost')
            qbport = config['qbittorrent'].get('qbport')
            qbusername = config['qbittorrent'].get('qbusername')
            qbpassword = config['qbittorrent'].get('qbpassword')
            try:
                qbt = qbittorrentapi.Client(host=qbhost,
                                            port=qbport,
                                            username=qbusername,
                                            password=qbpassword,
                                            VERIFY_WEBUI_CERTIFICATE=False)
                qbt.auth_log_in()
            except Exception as err:
                log.warn("【RUN】qBittorrent无法连接，请检查配置：%s" % str(err))
            save_path = config['qbittorrent'].get('save_path')
            if not save_path:
                log.warn("【RUN】qbittorrent save_path未设置，请检查配置！")
            else:
                if isinstance(save_path, dict):
                    if not save_path.get('tv') or not save_path.get('movie'):
                        log.warn("【RUN】qbittorrent save_path配置不完整，请检查配置！")
            save_containerpath = config['qbittorrent'].get('save_containerpath')
            if not save_containerpath:
                log.warn("【RUN】qbittorrent save_path未设置，如果是Docker容器使用则必须配置该项，否则无法正常转移文件")
            else:
                if isinstance(save_containerpath, dict):
                    if not save_containerpath.get('tv') or not save_containerpath.get('movie'):
                        log.warn("【RUN】qbittorrent save_containerpath配置不完整，如果是Docker容器使用则必须配置该项，否则无法正常转移文件")
        elif pt_client == "transmission":
            # 检查qbittorrent配置并测试连通性
            if not config.get('transmission'):
                log.error("【RUN】transmission未配置，程序无法启动")
                return False
            trhost = config['transmission'].get('trhost')
            trport = config['transmission'].get('trport')
            trusername = config['transmission'].get('trusername')
            trpassword = config['transmission'].get('trpassword')
            try:
                trt = transmission_rpc.Client(username=trusername, password=trpassword, host=trhost,
                                              port=trport)
                rpc_version = trt.rpc_version
                if not rpc_version:
                    log.warn("【RUN】transmission无法连接，请检查配置")
            except Exception as err:
                log.warn("【RUN】transmission无法连接，请检查配置：%s" % str(err))
            save_path = config['transmission'].get('save_path')
            if not save_path:
                log.warn("【RUN】transmission save_path未设置，请检查配置！")
            else:
                if isinstance(save_path, dict):
                    if not save_path.get('tv') or not save_path.get('movie'):
                        log.warn("【RUN】transmission save_path配置不完整，请检查配置！")
            save_containerpath = config['transmission'].get('save_containerpath')
            if not save_containerpath:
                log.warn("【RUN】transmission save_path未设置，如果是Docker容器使用则必须配置该项，否则无法正常转移文件")
            else:
                if isinstance(save_containerpath, dict):
                    if not save_containerpath.get('tv') or not save_containerpath.get('movie'):
                        log.warn("【RUN】transmission save_containerpath配置不完整，如果是Docker容器使用则必须配置该项，否则无法正常转移文件")
    return True
