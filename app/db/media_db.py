import os
import sqlite3
import threading
import time

import log
from app.utils.commons import singleton
from config import Config

lock = threading.Lock()


@singleton
class MediaDb:
    _db_path = None
    _mediadb = None

    def __init__(self):
        self._db_path = os.path.join(Config().get_config_path(), 'media.db')
        self._mediadb = sqlite3.connect(database=self._db_path, timeout=5, check_same_thread=False)
        self.__init_tables()

    def __init_tables(self):
        with lock:
            cursor = self._mediadb.cursor()
            try:
                # 媒体库同步信息表
                cursor.execute('''CREATE TABLE IF NOT EXISTS MEDIASYNC_STATISTICS
                                                   (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                                                   SERVER    TEXT,
                                                   TOTAL_COUNT  TEXT,
                                                   MOVIE_COUNT    TEXT,
                                                   TV_COUNT    TEXT,
                                                   UPDATE_TIME     TEXT);''')
                cursor.execute(
                    '''CREATE INDEX IF NOT EXISTS INDX_MEDIASYNC_STATISTICS ON MEDIASYNC_STATISTICS (SERVER);''')
                # 媒体数据表
                cursor.execute('''CREATE TABLE IF NOT EXISTS MEDIASYNC_ITEMS
                                                                   (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                                                                   SERVER   TEXT,
                                                                   LIBRARY    TEXT,
                                                                   ITEM_ID  TEXT,
                                                                   ITEM_TYPE    TEXT,
                                                                   TITLE    TEXT,
                                                                   ORGIN_TITLE     TEXT,
                                                                   YEAR     TEXT,
                                                                   TMDBID     TEXT,
                                                                   IMDBID     TEXT,
                                                                   PATH     TEXT,
                                                                   NOTE     TEXT,
                                                                   JSON     TEXT);''')
                cursor.execute(
                    '''CREATE INDEX IF NOT EXISTS INDX_MEDIASYNC_ITEMS_SL ON MEDIASYNC_ITEMS (SERVER, LIBRARY);''')
                cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_MEDIASYNC_ITEMS_LT ON MEDIASYNC_ITEMS (TITLE);''')
                cursor.execute(
                    '''CREATE INDEX IF NOT EXISTS INDX_MEDIASYNC_ITEMS_OT ON MEDIASYNC_ITEMS (ORGIN_TITLE);''')
                cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_MEDIASYNC_ITEMS_TI ON MEDIASYNC_ITEMS (TMDBID);''')
                cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_MEDIASYNC_ITEMS_II ON MEDIASYNC_ITEMS (ITEM_ID);''')
                self._mediadb.commit()
            except Exception as e:
                log.error(f"【Db】创建数据库错误：{e}")
            finally:
                cursor.close()

    def __excute(self, sql, data=None):
        if not sql:
            return False
        with lock:
            cursor = self._mediadb.cursor()
            try:
                if data:
                    cursor.execute(sql, data)
                else:
                    cursor.execute(sql)
                self._mediadb.commit()
            except Exception as e:
                print(str(e))
                return False
            finally:
                cursor.close()
            return True

    def __select(self, sql, data):
        if not sql:
            return False
        with lock:
            cursor = self._mediadb.cursor()
            try:
                if data:
                    res = cursor.execute(sql, data)
                else:
                    res = cursor.execute(sql)
                ret = res.fetchall()
            except Exception as e:
                print(str(e))
                return []
            finally:
                cursor.close()
            return ret

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
