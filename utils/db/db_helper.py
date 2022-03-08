import sqlite3
import threading

import log
lock = threading.Lock()


class DBHelper:
    __connection = None
    __instance = None

    def __init__(self):
        self.__connection = sqlite3.connect(":memory:")
        self.__init_tables()

    @staticmethod
    def get_instance():
        if DBHelper.__instance:
            return DBHelper.__instance
        try:
            lock.acquire()
            if not DBHelper.__instance:
                DBHelper.__instance = DBHelper()
        finally:
            lock.release()
        return DBHelper.__instance

    def __init_tables(self):
        cursor = self.__connection.cursor()
        try:
            cursor.execute('''CREATE TABLE IF NOT EXISTS JACKETT_TORRENTS
                   (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                   TORRENT_NAME    TEXT,
                   ENCLOSURE    TEXT,
                   DESCRIPTION    TEXT,
                   TYPE TEXT,
                   TITLE    TEXT,
                   YEAR    TEXT,
                   SEASON    TEXT,
                   EPISODE    TEXT,
                   VOTE    TEXT,
                   IMAGE    TEXT,
                   RES_TYPE    TEXT,
                   RES_ORDER    TEXT,
                   SIZE    INTEGER,
                   SEEDERS    INTEGER,
                   PEERS    INTEGER,                   
                   SITE    TEXT,
                   SITE_ORDER    TEXT);''')
            self.__connection.commit()
        except Exception as e:
            log.error("【DB】创建数据库错误：%s" % str(e))
        finally:
            cursor.close()

    def excute(self, sql):
        if not sql:
            return False
        cursor = self.__connection.cursor()
        try:
            cursor.execute(sql)
            self.__connection.commit()
        except Exception as e:
            log.error("【DB】执行SQL出错：%s，%s" % (sql, str(e)))
            return False
        finally:
            cursor.close()
        return True

    def select(self, sql):
        if not sql:
            return False
        cursor = self.__connection.cursor()
        try:
            res = cursor.execute(sql)
            ret = res.fetchall()
        except Exception as e:
            log.error("【DB】执行SQL出错：%s，%s" % (sql, str(e)))
            return []
        finally:
            cursor.close()
        return ret


def select_by_sql(sql):
    return DBHelper.get_instance().select(sql)


def update_by_sql(sql):
    return DBHelper.get_instance().excute(sql)


if __name__ == "__main__":
    update_by_sql("DELETE FROM JACKETT_TORRENTS")
    update_by_sql("INSERT INTO JACKETT_TORRENTS(TITLE) VALUES('未检索到资源')")
    print(select_by_sql("SELECT * FROM JACKETT_TORRENTS"))
