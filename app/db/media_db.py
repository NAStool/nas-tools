import os
import sqlite3
import threading

from app.utils.commons import singleton
from config import Config

lock = threading.Lock


@singleton
class MediaDb:
    _db_path = None
    _mediadb = None

    def __init__(self):
        self._db_path = os.path.join(Config().get_config_path(), 'media.db')
        self._mediadb = sqlite3.connect(database=self._db_path, timeout=5, check_same_thread=False)
        self.__init_tables()

    def __init_tables(self):
        pass

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
                return False
            finally:
                cursor.close()
            return True

    def __excute_many(self, sql, data_list):
        if not sql or not data_list:
            return False
        with lock:
            cursor = self._mediadb.cursor()
            try:
                cursor.executemany(sql, data_list)
                self._mediadb.commit()
            except Exception as e:
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
                return []
            finally:
                cursor.close()
            return ret

    def insert(self):
        pass

    def get(self):
        pass

    def exist(self):
        pass

    def delete(self):
        pass
