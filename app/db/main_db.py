import os
import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import SingletonThreadPool

from app.db.models import Base
from config import Config
from app.utils import PathUtils

lock = threading.Lock()
Engine = create_engine(f"sqlite:///{os.path.join(Config().get_config_path(), 'user.db')}?check_same_thread=False",
                       echo=False,
                       poolclass=SingletonThreadPool,
                       pool_pre_ping=True,
                       pool_size=5,
                       pool_recycle=60 * 30
                       )
Session = scoped_session(sessionmaker(bind=Engine,
                                      autoflush=True,
                                      autocommit=True))


class MainDb:
    __engine = None
    __session = None

    def __init__(self):
        self.__session = Session()

    @property
    def session(self):
        return self.__session

    @staticmethod
    def init_db():
        with lock:
            Base.metadata.create_all(Engine)

    def init_data(self):
        """
        读取config目录下的sql文件，并初始化到数据库，只处理一次
        """
        config = Config().get_config()
        init_files = Config().get_config("app").get("init_files") or []
        config_dir = os.path.join(Config().get_root_path(), "config")
        sql_files = PathUtils.get_dir_level1_files(in_path=config_dir, exts=".sql")
        config_flag = False
        for sql_file in sql_files:
            if os.path.basename(sql_file) not in init_files:
                config_flag = True
                with open(sql_file, "r", encoding="utf-8") as f:
                    sql_list = f.read().split(';\n')
                    for sql in sql_list:
                        self.excute(sql)
                init_files.append(os.path.basename(sql_file))
        if config_flag:
            config['app']['init_files'] = init_files
            Config().save_config(config)

    def insert(self, data):
        """
        插入数据
        """
        if not data:
            return False
        try:
            if isinstance(data, list):
                self.session.add_all(data)
            else:
                self.session.add(data)
            return True
        except Exception as e:
            print(str(e))
        return False

    def query(self, *obj):
        """
        查询对象
        """
        return self.session.query(*obj)

    def excute(self, sql):
        """
        执行SQL语句
        """
        if not sql:
            return False
        try:
            self.session.execute(sql)
            return True
        except Exception as e:
            print(str(e))
        return False
