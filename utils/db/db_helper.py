import os.path
import sqlite3

import log


class DBHelper:
    __db_path = None
    __connection = None

    def __init__(self):
        self.__db_path = os.path.join(os.environ.get('NASTOOL_CONFIG'), "user.db")
        self.__connection = sqlite3.connect(self.__db_path)
        self.__init_tables()

    def __init_tables(self):
        cursor = self.__connection.cursor()
        try:
            cursor.execute('''CREATE TABLE IF NOT EXISTS JACKETT_TORRENTS
                   (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                   TORRENT_NAME    TEXT    NOT NULL,
                   NAME    TEXT    NOT NULL,
                   ENCLOSURE    TEXT    NOT NULL,
                   TITLE    TEXT,
                   YEAR    TEXT,
                   DESCRIPTION    TEXT,
                   SITE_ORDER    INTEGER    NOT NULL,
                   RES_TYPE    TEXT,
                   RES_ORDER    INTEGER    NOT NULL,
                   SIZE    INTEGER,
                   SEEDERS    INTEGER,
                   PEERS    INTEGER,
                   SEASON    TEXT,
                   EPISODE    TEXT,
                   SITE    TEXT);''')
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
        except Exception as e:
            log.error("【DB】执行SQL出错：%s，%s" % (sql, str(e)))
            return None
        finally:
            cursor.close()
        return res


