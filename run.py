import os
import signal
import sys
from alembic.config import Config as AlembicConfig
from alembic.command import upgrade as alembic_upgrade
from pyvirtualdisplay import Display
from werkzeug.security import generate_password_hash

# 添加第三方库入口,按首字母顺序，引入brushtask时涉及第三方库，需提前引入
with open(os.path.join(os.path.dirname(__file__),
                       "third_party.txt"), "r") as f:
    third_party = f.readlines()
    for third_party_lib in third_party:
        sys.path.append(os.path.join(os.path.dirname(__file__),
                                     "third_party",
                                     third_party_lib.strip()).replace("\\", "/"))

# 运行环境判断
is_windows_exe = getattr(sys, 'frozen', False) and (os.name == "nt")
if is_windows_exe:
    # 托盘相关库
    import threading
    from windows.trayicon import trayicon

    # 初始化环境变量
    os.environ["NASTOOL_CONFIG"] = os.path.join(os.path.dirname(sys.executable),
                                                "config",
                                                "config.yaml").replace("\\", "/")
    os.environ["NASTOOL_LOG"] = os.path.join(os.path.dirname(sys.executable),
                                             "config",
                                             "logs").replace("\\", "/")
    try:
        config_dir = os.path.join(os.path.dirname(sys.executable),
                                  "config").replace("\\", "/")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        feapder_tmpdir = os.path.join(os.path.dirname(__file__),
                                      "feapder",
                                      "network",
                                      "proxy_file").replace("\\", "/")
        if not os.path.exists(feapder_tmpdir):
            os.makedirs(feapder_tmpdir)
    except Exception as err:
        print(str(err))

# 启动虚拟显示
is_docker = os.path.exists('/.dockerenv')
if is_docker:
    try:
        display = Display(visible=False, size=(1920, 1080))
        display.start()
        os.environ['NASTOOL_DISPLAY'] = 'YES'
    except Exception as err:
        print(str(err))
else:
    display = None

import warnings
import log
from config import Config
from app.utils import StringUtils
from app.brushtask import BrushTask
from app.sync import run_monitor, stop_monitor
from app.scheduler import run_scheduler, stop_scheduler
from app.helper import check_config, IndexerHelper, DbHelper
from version import APP_VERSION
from web.app import FlaskApp
from app.rsschecker import RssChecker
from app.db import MainDb, MediaDb

warnings.filterwarnings('ignore')


def sigal_handler(num, stack):
    """
    信号处理
    """
    if is_docker:
        log.warn('捕捉到退出信号：%s，开始退出...' % num)
        # 停止定时服务
        stop_scheduler()
        # 停止监控
        stop_monitor()
        # 停止虚拟显示
        if display:
            display.stop()
        # 退出主进程
        sys.exit()


def init_db():
    """
    初始化数据库
    """
    log.console('数据库初始化...')
    MediaDb().init_db()
    MainDb().init_db()
    MainDb().init_data()
    log.console('数据库初始化已完成')


def update_db(cfg):
    """
    更新数据库
    """
    db_location = os.path.normpath(os.path.join(cfg.get_config_path(), 'user.db'))
    script_location = os.path.normpath(os.path.join(os.path.dirname(__file__), 'alembic'))
    log.console('数据库更新...')
    try:
        alembic_cfg = AlembicConfig()
        alembic_cfg.set_main_option('script_location', script_location)
        alembic_cfg.set_main_option('sqlalchemy.url', f"sqlite:///{db_location}")
        alembic_upgrade(alembic_cfg, 'head')
    except Exception as e:
        print(str(e))
    log.console('数据库更新已完成')


def update_config(cfg):
    """
    升级配置文件
    """
    _dbhelper = DbHelper()
    _config = cfg.get_config()
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
    # API密钥初始化
    if not _config.get("security", {}).get("api_key"):
        _config['security']['api_key'] = _config.get("security",
                                                     {}).get("subscribe_token") \
                                         or StringUtils.generate_random_str()
        if _config.get('security', {}).get('subscribe_token'):
            _config['security'].pop('subscribe_token')
        overwrite_cofig = True
    # 消息推送开关初始化
    if not _config.get("message", {}).get("switch"):
        _config['message']['switch'] = {
            "download_start": True,
            "download_fail": True,
            "transfer_finished": True,
            "transfer_fail": True,
            "rss_added": True,
            "rss_finished": True,
            "site_signin": True
        }
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
        print(str(e))
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
                        SyncPath['from'] = paths[0].replace("\\", "/")
                    if len(paths) > 1:
                        SyncPath['to'] = paths[1].replace("\\", "/")
                    if len(paths) > 2:
                        SyncPath['unknown'] = paths[2].replace("\\", "/")
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
        print(str(e))
    # 重写配置文件
    if overwrite_cofig:
        cfg.save_config(_config)


if __name__ == "__main__":

    # 参数
    os.environ['TZ'] = 'Asia/Shanghai'
    log.console("配置文件地址：%s" % os.environ.get('NASTOOL_CONFIG'))
    log.console('NASTool 当前版本号：%s' % APP_VERSION)

    config = Config()

    # 数据库初始化
    init_db()

    # 数据库更新
    update_db(config)

    # 升级配置文件
    update_config(config)

    # 检查配置文件
    if not check_config(config):
        sys.exit()

    # 启动进程
    log.console("开始启动进程...")

    # 退出事件
    signal.signal(signal.SIGINT, sigal_handler)
    signal.signal(signal.SIGTERM, sigal_handler)

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

    # Windows启动托盘
    if is_windows_exe:
        homepage = config.get_config('app').get('domain')
        if not homepage:
            homepage = "http://localhost:%s" % str(config.get_config('app').get('web_port'))
        log_path = os.environ.get("NASTOOL_LOG")


        def traystart():
            trayicon(homepage, log_path)


        if len(os.popen("tasklist| findstr %s" % os.path.basename(sys.executable), 'r').read().splitlines()) <= 2:
            p1 = threading.Thread(target=traystart, daemon=True)
            p1.start()

    # 启动主WEB服务
    FlaskApp().run_service()
