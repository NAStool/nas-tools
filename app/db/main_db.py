import os
import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import SingletonThreadPool

from app.db.models import Base
from config import Config
from app.utils.commons import singleton
from app.utils import PathUtils

lock = threading.Lock()


@singleton
class MainDb:
    __engine = None
    __session = None

    def __init__(self):
        self.init_config()
        self.__init_db()
        self.__init_data()

    def init_config(self):
        config = Config()
        if not config.get_config_path():
            print("【Config】NASTOOL_CONFIG 环境变量未设置，程序无法工作，正在退出...")
            quit()
        self.__engine = create_engine(f"sqlite:///{os.path.join(config.get_config_path(), 'user.db')}?check_same_thread=False",
                                      echo=False,
                                      poolclass=SingletonThreadPool,
                                      pool_size=5,
                                      pool_recycle=60 * 30
                                      )
        self.__session = scoped_session(sessionmaker(bind=self.__engine))()

    def __init_db(self):
        with lock:
            Base.metadata.create_all(self.__engine)

    def __init_data(self):
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
                self.__session.add_all(data)
            else:
                self.__session.add(data)
            return True
        except Exception as e:
            print(str(e))
        finally:
            self.__session.commit()
        return False

    def query(self, *obj):
        """
        查询对象
        """
        return self.__session.query(*obj)

    def excute(self, sql):
        """
        执行SQL语句
        """
        if not sql:
            return False
        try:
            self.__session.execute(sql)
            return True
        except Exception as e:
            print(str(e))
        finally:
            self.__session.commit()
        return False
