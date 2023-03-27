import json
import os
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from werkzeug.security import generate_password_hash

import log
from app.helper import DbHelper
from app.plugins import PluginManager
from app.utils import ConfigLoadCache
from app.utils import ExceptionUtils
from app.utils.commons import INSTANCES
from config import Config

_observer = Observer(timeout=10)


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
    else:
        print("配置文件格式错误，找不到app配置项！")


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
        if not event.is_directory \
                and os.path.basename(event.src_path) == "config.yaml":
            # 10秒内只能加载一次
            if ConfigLoadCache.get(event.src_path):
                return
            ConfigLoadCache.set(event.src_path, True)
            log.console("进程 %s 检测到配置文件已修改，正在重新加载..." % os.getpid())
            time.sleep(1)
            # 重新加载配置
            Config().init_config()
            # 重载singleton服务
            for instance in INSTANCES.values():
                if hasattr(instance, "init_config"):
                    instance.init_config()


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
