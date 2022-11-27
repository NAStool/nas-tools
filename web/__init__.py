import os
from datetime import datetime
from threading import Lock

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import Config
from .apiv1 import apiv1_bp
from .main import App
import log
from app.brushtask import BrushTask
from app.db import init_db, update_db
from app.helper import IndexerHelper
from app.rsschecker import RssChecker
from app.scheduler import run_scheduler
from app.sync import run_monitor
from check_config import update_config, check_config
from version import APP_VERSION

ConfigLock = Lock()


def init_system():
    # 配置
    log.console('NAStool 当前版本号：%s' % APP_VERSION)
    # 数据库初始化
    init_db()
    # 数据库更新
    update_db()
    # 升级配置文件
    update_config()
    # 检查配置文件
    check_config()


def start_service():
    log.console("开始启动进程...")
    # 启动定时服务
    run_scheduler()
    # 启动监控服务
    run_monitor()
    # 启动刷流服务
    BrushTask()
    # 启动自定义订阅服务
    RssChecker()
    # 加载索引器配置
    IndexerHelper()


# 系统初始化
init_system()


# 启动服务
start_service()


# 配置文件加载时间
LST_CONFIG_LOAD_TIME = datetime.now()


class ConfigHandler(FileSystemEventHandler):
    """
    配置文件变化响应
    """

    def __init__(self):
        FileSystemEventHandler.__init__(self)

    def on_modified(self, event):
        global ConfigLock
        global LST_CONFIG_LOAD_TIME
        if not event.is_directory \
                and os.path.basename(event.src_path) == "config.yaml":
            with ConfigLock:
                if (datetime.now() - LST_CONFIG_LOAD_TIME).seconds <= 1:
                    return
                print("进程 %s 检测到配置文件已修改，正在重新加载..." % os.getpid())
                Config().init_config()
                LST_CONFIG_LOAD_TIME = datetime.now()


# 配置文件监听
ConfigObserver = Observer(timeout=10)
ConfigObserver.schedule(ConfigHandler(), path=Config().get_config_path(), recursive=False)
ConfigObserver.setDaemon(True)
ConfigObserver.start()
