import os
import log
from config import Config
from .main_db import MainDb
from .main_db import DbPersist
from .media_db import MediaDb
from alembic.config import Config as AlembicConfig
from alembic.command import upgrade as alembic_upgrade


def init_db():
    """
    初始化数据库
    """
    log.console('开始初始化数据库...')
    MediaDb().init_db()
    MainDb().init_db()
    log.console('数据库初始化完成')


def init_data():
    """
    初始化数据
    """
    log.console('开始初始化数据...')
    MainDb().init_data()
    log.console('数据初始化完成')


def update_db():
    """
    更新数据库
    """
    db_location = os.path.join(Config().get_config_path(), 'user.db')
    script_location = os.path.join(Config().get_root_path(), 'db_scripts')
    log.console('开始更新数据库...')
    try:
        alembic_cfg = AlembicConfig()
        alembic_cfg.set_main_option('script_location', script_location)
        alembic_cfg.set_main_option('sqlalchemy.url', f"sqlite:///{db_location}")
        alembic_upgrade(alembic_cfg, 'head')
    except Exception as e:
        print(str(e))
    log.console('数据库更新完成')
