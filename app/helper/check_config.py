import os
import log


def check_config(config):
    """
    检查配置文件，如有错误进行日志输出
    """
    # 检查日志输出
    if config.get_config('app'):
        logtype = config.get_config('app').get('logtype')
        if logtype:
            log.console("日志输出类型为：%s" % logtype)
        if logtype == "server":
            logserver = config.get_config('app').get('logserver')
            if not logserver:
                log.console("【Config】日志中心地址未配置，无法正常输出日志")
            else:
                log.console("日志将上送到服务器：%s" % logserver)
        elif logtype == "file":
            logpath = config.get_config('app').get('logpath')
            if not logpath:
                log.console("【Config】日志文件路径未配置，无法正常输出日志")
            else:
                log.console("日志将写入文件：%s" % logpath)

        # 检查WEB端口
        web_port = config.get_config('app').get('web_port')
        if not web_port:
            log.error("WEB服务端口未设置，将使用默认3000端口")

        # 检查登录用户和密码
        login_user = config.get_config('app').get('login_user')
        login_password = config.get_config('app').get('login_password')
        if not login_user or not login_password:
            log.error("WEB管理用户或密码未设置，将使用默认用户：admin，密码：password")
        else:
            log.info("WEB管理页面用户：%s" % str(login_user))

        # 检查HTTPS
        ssl_cert = config.get_config('app').get('ssl_cert')
        ssl_key = config.get_config('app').get('ssl_key')
        if not ssl_cert or not ssl_key:
            log.info("未启用https，请使用 http://IP:%s 访问管理页面" % str(web_port))
        else:
            if not os.path.exists(ssl_cert):
                log.error("ssl_cert文件不存在：%s" % ssl_cert)
            if not os.path.exists(ssl_key):
                log.error("ssl_key文件不存在：%s" % ssl_key)
            log.info("已启用https，请使用 https://IP:%s 访问管理页面" % str(web_port))

        rmt_tmdbkey = config.get_config('app').get('rmt_tmdbkey')
        if not rmt_tmdbkey:
            log.error("TMDB API Key未配置，媒体整理、搜索下载等功能将无法正常运行！")
        rmt_match_mode = config.get_config('app').get('rmt_match_mode')
        if rmt_match_mode:
            rmt_match_mode = rmt_match_mode.upper()
        else:
            rmt_match_mode = "NORMAL"
        if rmt_match_mode == "STRICT":
            log.info("TMDB匹配模式：严格模式")
        else:
            log.info("TMDB匹配模式：正常模式")
    else:
        log.console("配置文件格式错误，找不到app配置项！")

    # 检查媒体库目录路径
    if config.get_config('media'):
        media_server = config.get_config('media').get('media_server')
        if media_server:
            log.info("媒体管理软件设置为：%s" % media_server)
            if media_server == "jellyfin":
                if not config.get_config('jellyfin'):
                    log.warn("jellyfin未配置")
                else:
                    if not config.get_config('jellyfin').get('host') or not config.get_config('jellyfin').get(
                            'api_key'):
                        log.warn("jellyfin配置不完整")
            else:
                if not config.get_config('emby'):
                    log.warn("emby未配置")
                else:
                    if not config.get_config('emby').get('host') or not config.get_config('emby').get('api_key'):
                        log.warn("emby配置不完整")

        movie_paths = config.get_config('media').get('movie_path')
        if not movie_paths:
            log.error("未配置电影媒体库目录")
        else:
            if not isinstance(movie_paths, list):
                movie_paths = [movie_paths]
            for movie_path in movie_paths:
                if not os.path.exists(movie_path):
                    log.error("电影媒体库目录不存在：%s" % movie_path)

        tv_paths = config.get_config('media').get('tv_path')
        if not tv_paths:
            log.error("未配置电视剧媒体库目录")
        else:
            if not isinstance(tv_paths, list):
                tv_paths = [tv_paths]
            for tv_path in tv_paths:
                if not os.path.exists(tv_path):
                    log.error("电视剧媒体库目录不存在：%s" % tv_path)

        anime_paths = config.get_config('media').get('anime_path')
        if anime_paths:
            if not isinstance(anime_paths, list):
                anime_paths = [anime_paths]
            for anime_path in anime_paths:
                if not os.path.exists(anime_path):
                    log.error("动漫媒体库目录不存在：%s" % anime_path)

        category = config.get_config('media').get('category')
        if not category:
            log.info("未配置分类策略")
    else:
        log.error("配置文件格式错误，找不到media配置项！")

    # 检查站点配置
    if config.get_config('pt'):
        pt_client = config.get_config('pt').get('pt_client')
        log.info("下载软件设置为：%s" % pt_client)

        rmt_mode = config.get_config('pt').get('rmt_mode', 'copy')
        if rmt_mode == "link":
            log.info("默认文件转移模式为：硬链接")
        elif rmt_mode == "softlink":
            log.info("默认文件转移模式为：软链接")
        elif rmt_mode == "move":
            log.info("默认文件转移模式为：移动")
        elif rmt_mode == "rclone":
            log.info("默认文件转移模式为：rclone移动")
        elif rmt_mode == "rclonecopy":
            log.info("默认文件转移模式为：rclone复制")
        else:
            log.info("默认文件转移模式为：复制")

        search_indexer = config.get_config('pt').get('search_indexer')
        if search_indexer:
            log.info("索引器设置为：%s" % search_indexer)

        search_auto = config.get_config('pt').get('search_auto')
        if search_auto:
            log.info("微信等移动端渠道搜索已开启自动择优下载")

        ptsignin_cron = config.get_config('pt').get('ptsignin_cron')
        if not ptsignin_cron:
            log.info("站点自动签到时间未配置，站点签到功能已关闭")

        pt_seeding_time = config.get_config('pt').get('pt_seeding_time')
        if not pt_seeding_time or pt_seeding_time == '0':
            log.info("保种时间未配置，自动删种功能已关闭")
        else:
            log.info("保种时间设置为：%s 天" % pt_seeding_time)

        pt_check_interval = config.get_config('pt').get('pt_check_interval')
        if not pt_check_interval:
            log.info("RSS订阅周期未配置，RSS订阅功能已关闭")

        pt_monitor = config.get_config('pt').get('pt_monitor')
        if not pt_monitor:
            log.info("下载软件监控未开启，下载器监控功能已关闭")
    else:
        log.error("配置文件格式错误，找不到pt配置项！")

    # 检查Douban配置
    if not config.get_config('douban'):
        log.info("豆瓣未配置")
    else:
        if not config.get_config('douban').get('users') or not config.get_config('douban').get(
                'types') or not config.get_config('douban').get('days'):
            log.info("豆瓣配置不完整")

    return True
