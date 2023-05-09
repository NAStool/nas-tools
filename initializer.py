import json
import os
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from werkzeug.security import generate_password_hash

import log
from app.conf import SystemConfig
from app.helper import DbHelper, PluginHelper
from app.plugins import PluginManager
from app.media import Category
from app.utils import ConfigLoadCache, CategoryLoadCache, ExceptionUtils, StringUtils
from app.utils.commons import INSTANCES
from app.utils.types import SystemConfigKey
from config import Config
from web.action import WebAction

_observer = Observer(timeout=10)


def check_config():
    """
    检查配置文件，如有错误进行日志输出
    """
    # 检查日志输出
    if Config().get_config('app'):
        logtype = Config().get_config('app').get('logtype')
        if logtype:
            log.info(f"日志输出类型为：{logtype}")
        if logtype == "server":
            logserver = Config().get_config('app').get('logserver')
            if not logserver:
                log.warn("【Config】日志中心地址未配置，无法正常输出日志")
            else:
                log.info("日志将上送到服务器：{logserver}")
        elif logtype == "file":
            logpath = Config().get_config('app').get('logpath')
            if not logpath:
                log.warn("【Config】日志文件路径未配置，无法正常输出日志")
            else:
                log.info(f"日志将写入文件：{logpath}")

        # 检查WEB端口
        web_port = Config().get_config('app').get('web_port')
        if not web_port:
            log.warn("【Config】WEB服务端口未设置，将使用默认3000端口")

        # 检查登录用户和密码
        login_user = Config().get_config('app').get('login_user')
        login_password = Config().get_config('app').get('login_password')
        if not login_user or not login_password:
            log.warn("【Config】WEB管理用户或密码未设置，将使用默认用户：admin，密码：password")
        else:
            log.info(f"WEB管理页面用户：{str(login_user)}")

        # 检查HTTPS
        ssl_cert = Config().get_config('app').get('ssl_cert')
        ssl_key = Config().get_config('app').get('ssl_key')
        if not ssl_cert or not ssl_key:
            log.info(f"未启用https，请使用 http://IP:{str(web_port)} 访问管理页面")
        else:
            if not os.path.exists(ssl_cert):
                log.warn(f"【Config】ssl_cert文件不存在：{ssl_cert}")
            if not os.path.exists(ssl_key):
                log.warn(f"【Config】ssl_key文件不存在：{ssl_key}")
            log.info(f"已启用https，请使用 https://IP:{str(web_port)} 访问管理页面")
    else:
        log.error("【Config】配置文件格式错误，找不到app配置项！")


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
        _config['app']['login_password'] = "[hash]%s" % generate_password_hash(
            login_password)
        overwrite_cofig = True

    # API密钥初始化
    if not _config.get("security", {}).get("api_key"):
        _config['security']['api_key'] = StringUtils.generate_random_str(32)
        overwrite_cofig = True

    # 字幕兼容旧配置
    try:
        subtitle = Config().get_config('subtitle') or {}
        if subtitle:
            if subtitle.get("server") == "opensubtitles":
                PluginManager().save_plugin_config(pid="OpenSubtitles",
                                                   conf={
                                                       "enable": subtitle.get("opensubtitles", {}).get("enable")
                                                   })
            else:
                chinesesubfinder = subtitle.get("chinesesubfinder", {})
                PluginManager().save_plugin_config(pid="ChineseSubFinder", conf={
                    "host": chinesesubfinder.get("host"),
                    "api_key": chinesesubfinder.get("api_key"),
                    "local_path": chinesesubfinder.get("local_path"),
                    "remote_path": chinesesubfinder.get("remote_path")
                })
            # 删除旧配置
            _config.pop("subtitle")
            overwrite_cofig = True

    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # 自定义制作组/字幕组兼容旧配置
    try:
        custom_release_groups = (Config().get_config('laboratory') or {}).get('release_groups')
        if custom_release_groups:
            PluginManager().save_plugin_config(pid="CustomReleaseGroups", conf={
                "release_groups": custom_release_groups
            })
            # 删除旧配置
            _config["laboratory"].pop("release_groups")
            overwrite_cofig = True

    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # 下载器兼容旧配置
    try:
        # pt
        pt = Config().get_config('pt')
        pt_client = pt.get("pt_client")
        pt_monitor = pt.get("pt_monitor")
        pt_monitor_only = pt.get("pt_monitor_only")
        rmt_mode = pt.get("rmt_mode")
        # downloaddir
        download_dir_conf = []
        downloaddir = Config().get_config('downloaddir')
        if downloaddir:
            for dl_dir in downloaddir:
                download_dir_conf.append({
                    "save_path": dl_dir.get("save_path"),
                    "type": dl_dir.get("type"),
                    "category": dl_dir.get("category"),
                    "container_path": dl_dir.get("container_path"),
                    "label": dl_dir.get("label")
                })
            _config.pop("downloaddir")
            overwrite_cofig = True
        downloaddir = json.dumps(download_dir_conf)
        # qbittorrent
        qbittorrent = Config().get_config('qbittorrent')
        if qbittorrent:
            enabled = 1 if pt_client == "qbittorrent" else 0
            transfer = 1 if pt_monitor else 0
            only_nastool = 1 if pt_monitor_only else 0
            config = json.dumps({
                "host": qbittorrent.get("qbhost"),
                "port": qbittorrent.get("qbport"),
                "username": qbittorrent.get("qbusername"),
                "password": qbittorrent.get("qbpassword")
            })
            _dbhelper.update_downloader(did=None,
                                        name="Qbittorrent",
                                        dtype="qbittorrent",
                                        enabled=enabled,
                                        transfer=transfer,
                                        only_nastool=only_nastool,
                                        rmt_mode=rmt_mode,
                                        config=config,
                                        download_dir=downloaddir)
            _config.pop("qbittorrent")
            overwrite_cofig = True
        # transmission
        transmission = Config().get_config('transmission')
        if transmission:
            enabled = 1 if pt_client == "transmission" else 0
            transfer = 1 if pt_monitor else 0
            only_nastool = 1 if pt_monitor_only else 0
            config = json.dumps({
                "host": transmission.get("trhost"),
                "port": transmission.get("trport"),
                "username": transmission.get("trusername"),
                "password": transmission.get("trpassword")
            })
            _dbhelper.update_downloader(did=None,
                                        name="Transmission",
                                        dtype="transmission",
                                        enabled=enabled,
                                        transfer=transfer,
                                        only_nastool=only_nastool,
                                        rmt_mode=rmt_mode,
                                        config=config,
                                        download_dir=downloaddir)
            _config.pop("transmission")
            overwrite_cofig = True
        # pt
        if pt_client is not None:
            pt.pop("pt_client")
        if pt_monitor is not None:
            pt.pop("pt_monitor")
        if pt_monitor_only is not None:
            pt.pop("pt_monitor_only")
        if rmt_mode is not None:
            pt.pop("rmt_mode")

    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # 站点数据刷新时间默认配置
    try:
        if "ptrefresh_date_cron" not in _config['pt']:
            _config['pt']['ptrefresh_date_cron'] = '6'
            overwrite_cofig = True
    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # 豆瓣配置转为插件
    try:
        douban = Config().get_config('douban')
        if douban:
            _enable = True if douban.get("users") and douban.get("interval") and douban.get("types") else False
            PluginManager().save_plugin_config(pid="DoubanSync", conf={
                "onlyonce": False,
                "enable": _enable,
                "interval": douban.get("interval"),
                "auto_search": douban.get("auto_search"),
                "auto_rss": douban.get("auto_rss"),
                "cookie": douban.get("cookie"),
                "users": douban.get("users"),
                "days": douban.get("days"),
                "types": douban.get("types")
            })
            # 删除旧配置
            _config.pop("douban")
            overwrite_cofig = True
    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # 刮削配置改为存数据库
    try:
        scraper_conf = {}
        # Nfo
        scraper_nfo = Config().get_config("scraper_nfo")
        if scraper_nfo:
            scraper_conf["scraper_nfo"] = scraper_nfo
            _config.pop("scraper_nfo")
            overwrite_cofig = True
        # 图片
        scraper_pic = Config().get_config("scraper_pic")
        if scraper_pic:
            scraper_conf["scraper_pic"] = scraper_pic
            _config.pop("scraper_pic")
            overwrite_cofig = True
        # 保存
        if scraper_conf:
            SystemConfig().set(SystemConfigKey.UserScraperConf,
                               scraper_conf)
    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # 内建索引器配置改为存数据库
    try:
        indexer_sites = Config().get_config("pt").get("indexer_sites")
        if indexer_sites:
            SystemConfig().set(SystemConfigKey.UserIndexerSites,
                               indexer_sites)
            _config['pt'].pop("indexer_sites")
            overwrite_cofig = True
    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # 站点签到转为插件
    try:
        ptsignin_cron = Config().get_config("pt").get("ptsignin_cron")
        if ptsignin_cron:
            # 转换周期
            ptsignin_cron = str(ptsignin_cron).strip()
            if ptsignin_cron.isdigit():
                cron = f"0 */{ptsignin_cron} * * *"
            elif ptsignin_cron.count(" ") == 4:
                cron = ptsignin_cron
            elif "-" in ptsignin_cron:
                ptsignin_cron = ptsignin_cron.split("-")[0]
                hour = int(ptsignin_cron.split(":")[0])
                minute = int(ptsignin_cron.split(":")[1])
                cron = f"{minute} {hour} * * *"
            elif ptsignin_cron.count(":"):
                hour = int(ptsignin_cron.split(":")[0])
                minute = int(ptsignin_cron.split(":")[1])
                cron = f"{minute} {hour} * * *"
            else:
                cron = "30 8 * * *"
            # 安装插件
            WebAction().install_plugin(data={"id": "AutoSignIn"}, reload=False)
            # 保存配置
            PluginManager().save_plugin_config(pid="AutoSignIn", conf={
                "enabled": True,
                "cron": cron,
                "retry_keyword": '',
                "sign_sites": [],
                "special_sites": [],
                "notify": True,
                "onlyonce": False,
                "queue_cnt": 10
            })
            _config['pt'].pop("ptsignin_cron")
            overwrite_cofig = True
    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # 存量插件安装情况统计
    try:
        plugin_report_state = SystemConfig().get(SystemConfigKey.UserInstalledPluginsReport)
        installed_plugins = SystemConfig().get(SystemConfigKey.UserInstalledPlugins)
        if not plugin_report_state and installed_plugins:
            ret = PluginHelper().report(installed_plugins)
            if ret:
                SystemConfig().set(SystemConfigKey.UserInstalledPluginsReport, '1')
    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # TMDB代理服务开关迁移
    try:
        tmdb_proxy = Config().get_config('laboratory').get("tmdb_proxy")
        if tmdb_proxy:
            _config['app']['tmdb_domain'] = 'tmdb.nastool.cn'
            _config['laboratory'].pop("tmdb_proxy")
            overwrite_cofig = True
    except Exception as e:
        ExceptionUtils.exception_traceback(e)

    # 重写配置文件
    if overwrite_cofig:
        Config().save_config(_config)


class ConfigMonitor(FileSystemEventHandler):
    """
    配置文件变化响应
    """

    def __init__(self):
        FileSystemEventHandler.__init__(self)

    def on_modified(self, event):
        if event.is_directory:
            return
        src_path = event.src_path
        file_name = os.path.basename(src_path)
        file_head, file_ext = os.path.splitext(os.path.basename(file_name))
        if file_ext != ".yaml":
            return
        # 配置文件10秒内只能加载一次
        if file_name == "config.yaml" and not ConfigLoadCache.get(src_path):
            ConfigLoadCache.set(src_path, True)
            CategoryLoadCache.set("ConfigLoadBlock", True, ConfigLoadCache.ttl)
            log.warn(f"【System】进程 {os.getpid()} 检测到系统配置文件已修改，正在重新加载...")
            time.sleep(1)
            # 重新加载配置
            Config().init_config()
            # 重载singleton服务
            for instance in INSTANCES.values():
                if hasattr(instance, "init_config"):
                    instance.init_config()
        # 正在使用的二级分类策略文件3秒内只能加载一次，配置文件加载时，二级分类策略文件不加载
        elif file_name == os.path.basename(Config().category_path) \
                and not CategoryLoadCache.get(src_path) \
                and not CategoryLoadCache.get("ConfigLoadBlock"):
            CategoryLoadCache.set(src_path, True)
            log.warn(f"【System】进程 {os.getpid()} 检测到二级分类策略 {file_head} 配置文件已修改，正在重新加载...")
            time.sleep(1)
            # 重新加载二级分类策略
            Category().init_config()


def start_config_monitor():
    """
    启动服务
    """
    global _observer
    # 配置文件监听
    _observer.schedule(ConfigMonitor(), path=Config().get_config_path(), recursive=False)
    _observer.daemon = True
    _observer.start()


def stop_config_monitor():
    """
    停止服务
    """
    global _observer
    try:
        if _observer:
            _observer.stop()
            _observer.join()
    except Exception as err:
        print(str(err))
