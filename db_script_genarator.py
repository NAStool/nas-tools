import os
from config import Config
from alembic.config import Config as alembic_config
from alembic.command import revision as alembic_revision

db_version = input("请输入版本号：")
config = Config()
db_location = os.path.join(config.get_config_path(), 'user.db').replace('\\', '/')
script_location = os.path.join(os.path.dirname(__file__), 'alembic').replace('\\', '/')
alembic_cfg = alembic_config()
alembic_cfg.set_main_option('script_location', script_location)
alembic_cfg.set_main_option('sqlalchemy.url', f"sqlite:///{db_location}")
alembic_revision(alembic_cfg, db_version, True)
