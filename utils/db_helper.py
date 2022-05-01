import os
import sqlite3
import threading

import log
from config import Config
from utils.functions import singleton

lock = threading.Lock()


@singleton
class DBHelper:
    __connection = None
    __db_path = None

    def __init__(self):
        self.init_config()
        self.__init_tables()

    def init_config(self):
        config = Config()
        config_path = config.get_config_path()
        if not config_path:
            log.console("【ERROR】NASTOOL_CONFIG 环境变量未设置，程序无法工作，正在退出...")
            quit()
        self.__db_path = os.path.join(os.path.dirname(config_path), 'user.db')
        self.__connection = sqlite3.connect(self.__db_path, check_same_thread=False)

    def __init_tables(self):
        cursor = self.__connection.cursor()
        try:
            # Jackett搜索结果表
            cursor.execute('''CREATE TABLE IF NOT EXISTS SEARCH_TORRENTS
                                   (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                                   TORRENT_NAME    TEXT,
                                   ENCLOSURE    TEXT,
                                   DESCRIPTION    TEXT,
                                   TYPE TEXT,
                                   TITLE    TEXT,
                                   YEAR    TEXT,
                                   SEASON    TEXT,
                                   EPISODE    TEXT,
                                   ES_STRING    TEXT,
                                   VOTE    TEXT,
                                   IMAGE    TEXT,
                                   RES_TYPE    TEXT,
                                   RES_ORDER    TEXT,
                                   SIZE    INTEGER,
                                   SEEDERS    INTEGER,
                                   PEERS    INTEGER,                   
                                   SITE    TEXT,
                                   SITE_ORDER    TEXT);''')
            # RSS下载记录表
            cursor.execute('''CREATE TABLE IF NOT EXISTS RSS_TORRENTS
                                   (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                                   TORRENT_NAME    TEXT,
                                   ENCLOSURE    TEXT,
                                   TYPE TEXT,
                                   TITLE    TEXT,
                                   YEAR    TEXT,
                                   SEASON    TEXT,
                                   EPISODE    TEXT);''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_RSS_TORRENTS_NAME ON RSS_TORRENTS (TITLE, YEAR, SEASON, EPISODE);''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_RSS_TORRENTS_URL ON RSS_TORRENTS (ENCLOSURE);''')
            # 电影订阅表
            # STATE: D-队列中 S-正在检索 R-正在订阅 F-完成
            cursor.execute('''CREATE TABLE IF NOT EXISTS RSS_MOVIES
                                   (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                                   NAME    TEXT,
                                   YEAR    TEXT,
                                   TMDBID   TEXT,
                                   IMAGE    TEXT,
                                   DESC    TEXT,
                                   STATE    TEXT);''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_RSS_MOVIES_NAME ON RSS_MOVIES(NAME);''')
            # 电视剧订阅表
            # STATE: D-队列中 S-正在检索 R-正在订阅 F-完成
            cursor.execute('''CREATE TABLE IF NOT EXISTS RSS_TVS
                                   (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                                   NAME    TEXT,
                                   YEAR    TEXT,
                                   SEASON    TEXT,
                                   TMDBID   TEXT,
                                   IMAGE    TEXT,
                                   DESC    TEXT,
                                   TOTAL    INTEGER,
                                   LACK    INTEGER,
                                   STATE    TEXT);''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_RSS_TVS_NAME ON RSS_TVS(NAME);''')
            # 豆瓣关注信息表
            cursor.execute('''CREATE TABLE IF NOT EXISTS DOUBAN_MEDIAS
                                   (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                                   NAME    TEXT,
                                   YEAR    TEXT,
                                   TYPE    TEXT,
                                   RATING   TEXT,
                                   IMAGE    TEXT,
                                   STATE    TEXT);''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_DOUBAN_MEDIAS_NAME ON DOUBAN_MEDIAS (NAME, YEAR);''')
            # 识别转移历史记录表
            cursor.execute('''CREATE TABLE IF NOT EXISTS TRANSFER_HISTORY
                                   (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                                   SOURCE    TEXT,
                                   MODE    TEXT,
                                   TYPE    TEXT,
                                   FILE_PATH    TEXT,
                                   FILE_NAME    TEXT,
                                   TITLE   TEXT,
                                   CATEGORY   TEXT,
                                   YEAR    TEXT,
                                   SE    TEXT,
                                   DEST    TEXT,
                                   DATE    );''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_TRANSFER_HISTORY_PATH ON TRANSFER_HISTORY (FILE_PATH);''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_TRANSFER_HISTORY_NAME ON TRANSFER_HISTORY (FILE_NAME);''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_TRANSFER_HISTORY_TITLE ON TRANSFER_HISTORY (TITLE);''')
            # 无法识别的文件列表
            # STATE N-未处理 Y-已处理
            cursor.execute('''CREATE TABLE IF NOT EXISTS TRANSFER_UNKNOWN
                                   (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                                   PATH    TEXT,
                                   DEST    TEXT,
                                   STATE    TEXT);''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_TRANSFER_UNKNOWN ON TRANSFER_UNKNOWN (PATH);''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_TRANSFER_UNKNOWN_STATE ON TRANSFER_UNKNOWN (STATE);''')
            # 识别黑名单
            cursor.execute('''CREATE TABLE IF NOT EXISTS TRANSFER_BLACKLIST
                                   (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                                   PATH    TEXT);''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_TRANSFER_BLACKLIST ON TRANSFER_BLACKLIST (PATH);''')
            # 站点配置表
            cursor.execute('''CREATE TABLE IF NOT EXISTS CONFIG_SITE
                                   (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                                   NAME    TEXT,
                                   PRI    TEXT,
                                   RSSURL   TEXT,
                                   SIGNURL  TEXT,
                                   COOKIE   TEXT,
                                   INCLUDE  TEXT,
                                   EXCLUDE  TEXT,
                                   SIZE    TEXT,
                                   NOTE    TEXT);''')
            # 搜索过滤规则表
            cursor.execute('''CREATE TABLE IF NOT EXISTS CONFIG_SEARCH_RULE
                                   (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                                   INCLUDE  TEXT,
                                   EXCLUDE  TEXT,
                                   SIZE    TEXT,
                                   NOTE    TEXT);''')
            # RSS全局规则表
            cursor.execute('''CREATE TABLE IF NOT EXISTS CONFIG_RSS_RULE
                                               (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                                               NOTE    TEXT);''')
            # 目录同步记录表
            cursor.execute('''CREATE TABLE IF NOT EXISTS SYNC_HISTORY
                                               (ID INTEGER PRIMARY KEY AUTOINCREMENT     NOT NULL,
                                               PATH    TEXT,
                                               SRC    TEXT,
                                               DEST    TEXT);''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS INDX_SYNC_HISTORY ON SYNC_HISTORY (PATH);''')

            # 提交
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
    return DBHelper().select(sql)


def update_by_sql(sql):
    return DBHelper().excute(sql)
