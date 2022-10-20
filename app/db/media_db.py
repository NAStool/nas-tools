import os
import threading
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import SingletonThreadPool
from app.db.models import BaseMedia
from app.utils.commons import singleton
from config import Config

lock = threading.Lock()


@singleton
class MediaDb:
    __engine = None
    __session = None

    def __init__(self):
        self.__engine = create_engine(f"sqlite:///{os.path.join(Config().get_config_path(), 'media.db')}?check_same_thread=False",
                                      echo=False,
                                      poolclass=SingletonThreadPool,
                                      pool_size=5,
                                      pool_recycle=60 * 30
                                      )
        self.__session = scoped_session(sessionmaker(bind=self.__engine))()
        self.__init_db()

    def __init_db(self):
        with lock:
            BaseMedia.metadata.create_all(self.__engine)

    def __excute(self, sql, data=None):
        if not sql:
            return False
        with lock:
            try:
                if data:
                    self.__session.execute(sql, data)
                else:
                    self.__session.execute(sql)
            except Exception as e:
                print(str(e))
                return False
            return True

    def __select(self, sql, data):
        if not sql:
            return False
        with lock:
            try:
                if data:
                    return self.__session.execute(sql, data).fetchall()
                else:
                    return self.__session.execute(sql).fetchall()
            except Exception as e:
                print(str(e))
                return []

    def insert(self, server_type, iteminfo):
        if not server_type or not iteminfo:
            return False
        self.delete(server_type, iteminfo.get("id"))
        return self.__excute("INSERT INTO MEDIASYNC_ITEMS "
                             "(SERVER, LIBRARY, ITEM_ID, ITEM_TYPE, TITLE, ORGIN_TITLE, YEAR, TMDBID, IMDBID, PATH, JSON) "
                             "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (server_type,
                              iteminfo.get("library"),
                              iteminfo.get("id"),
                              iteminfo.get("type"),
                              iteminfo.get("title"),
                              iteminfo.get("originalTitle"),
                              iteminfo.get("year"),
                              iteminfo.get("tmdbid"),
                              iteminfo.get("imdbid"),
                              iteminfo.get("path"),
                              iteminfo.get("json")
                              ))

    def delete(self, server_type, itemid):
        if not server_type or not itemid:
            return False
        return self.__excute("DELETE FROM MEDIASYNC_ITEMS WHERE SERVER = ? AND ITEM_ID = ?",
                             (server_type, itemid))

    def empty(self, server_type=None, library=None):
        if server_type and library:
            return self.__excute("DELETE FROM MEDIASYNC_ITEMS WHERE SERVER = ? AND LIBRARY = ?",
                                 (server_type, library))
        else:
            return self.__excute("DELETE FROM MEDIASYNC_ITEMS")

    def statistics(self, server_type, total_count, movie_count, tv_count):
        if not server_type:
            return False
        self.__excute("DELETE FROM MEDIASYNC_STATISTICS WHERE SERVER = ?", (server_type,))
        return self.__excute("INSERT INTO MEDIASYNC_STATISTICS "
                             "(SERVER, TOTAL_COUNT, MOVIE_COUNT, TV_COUNT, UPDATE_TIME) "
                             "VALUES (?, ?, ?, ?, ?)", (server_type,
                                                        total_count,
                                                        movie_count,
                                                        tv_count,
                                                        time.strftime('%Y-%m-%d %H:%M:%S',
                                                                      time.localtime(time.time()))))

    def exists(self, server_type, title, year, tmdbid):
        if not server_type or not title:
            return False
        if title and year:
            ret = self.__select("SELECT COUNT(1) FROM MEDIASYNC_ITEMS WHERE SERVER = ? AND TITLE = ? AND YEAR = ?",
                                (server_type, title, year))
        else:
            ret = self.__select("SELECT COUNT(1) FROM MEDIASYNC_ITEMS WHERE SERVER = ? AND TITLE = ?",
                                (server_type, title))
        if ret and ret[0][0] > 0:
            return True
        elif tmdbid:
            ret = self.__select("SELECT COUNT(1) FROM MEDIASYNC_ITEMS WHERE TMDBID = ?",
                                (tmdbid,))
            if ret and ret[0][0] > 0:
                return True
        return False

    def get_statistics(self, server_type):
        if not server_type:
            return None
        return self.__select("SELECT TOTAL_COUNT, MOVIE_COUNT, TV_COUNT, UPDATE_TIME FROM MEDIASYNC_STATISTICS WHERE SERVER = ?", (server_type,))
