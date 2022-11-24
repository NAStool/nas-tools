import os

import log
from app.db import MediaDb, MainDb
from alembic.config import Config as AlembicConfig
from alembic.command import upgrade as alembic_upgrade


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
    db_location = os.path.join(cfg.get_config_path(), 'user.db')
    script_location = os.path.join(cfg.get_root_path(), 'db_scripts')
    log.console('数据库更新...')
    try:
        alembic_cfg = AlembicConfig()
        alembic_cfg.set_main_option('script_location', script_location)
        alembic_cfg.set_main_option('sqlalchemy.url', f"sqlite:///{db_location}")
        alembic_upgrade(alembic_cfg, 'head')
    except Exception as e:
        print(str(e))
    log.console('数据库更新已完成')
