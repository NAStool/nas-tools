import datetime
import os.path
import time
from enum import Enum

from app.db.db_helper import DBHelper
from app.utils import StringUtils
from app.utils.types import MediaType, RmtMode


class SqlHelper:

    @staticmethod
    def insert_search_results(media_items: list):
        """
        将返回信息插入数据库
        """
        if not media_items:
            return
        sql = "INSERT INTO SEARCH_RESULT_INFO(" \
              "TORRENT_NAME," \
              "ENCLOSURE," \
              "DESCRIPTION," \
              "TYPE," \
              "TITLE," \
              "YEAR," \
              "SEASON," \
              "EPISODE," \
              "ES_STRING," \
              "VOTE," \
              "IMAGE," \
              "POSTER," \
              "TMDBID," \
              "OVERVIEW," \
              "RES_TYPE," \
              "RES_ORDER," \
              "SIZE," \
              "SEEDERS," \
              "PEERS," \
              "SITE," \
              "SITE_ORDER," \
              "PAGEURL," \
              "OTHERINFO," \
              "UPLOAD_VOLUME_FACTOR," \
              "DOWNLOAD_VOLUME_FACTOR) VALUES (" \
              " ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        data_list = []
        for media_item in media_items:
            if media_item.type == MediaType.TV:
                mtype = "TV"
            elif media_item.type == MediaType.MOVIE:
                mtype = "MOV"
            else:
                mtype = "ANI"
            data_list.append(
                (
                    StringUtils.str_sql(media_item.org_string),
                    StringUtils.str_sql(media_item.enclosure),
                    StringUtils.str_sql(media_item.description),
                    mtype,
                    StringUtils.str_sql(media_item.title) or StringUtils.str_sql(media_item.get_name()),
                    StringUtils.xstr(media_item.year),
                    media_item.get_season_string(),
                    media_item.get_episode_string(),
                    media_item.get_season_episode_string(),
                    media_item.vote_average or "0",
                    media_item.get_backdrop_image(default=False),
                    media_item.get_poster_image(),
                    StringUtils.str_sql(media_item.tmdb_id),
                    StringUtils.str_sql(media_item.overview),
                    media_item.get_resource_type_string(),
                    media_item.res_order,
                    StringUtils.str_filesize(int(media_item.size)),
                    media_item.seeders,
                    media_item.peers,
                    media_item.site,
                    media_item.site_order,
                    StringUtils.str_sql(media_item.page_url),
                    media_item.resource_team,
                    media_item.upload_volume_factor,
                    media_item.download_volume_factor
                )
            )
        return DBHelper().update_by_sql_batch(sql, data_list)

    @staticmethod
    def get_search_result_by_id(dl_id):
        """
        根据ID从数据库中查询检索结果的一条记录
        """
        sql = "SELECT ENCLOSURE,TITLE,YEAR,SEASON,EPISODE,VOTE,IMAGE,TYPE,TORRENT_NAME,DESCRIPTION,SIZE,TMDBID,POSTER,OVERVIEW,SITE,UPLOAD_VOLUME_FACTOR,DOWNLOAD_VOLUME_FACTOR,PAGEURL" \
              " FROM SEARCH_RESULT_INFO" \
              " WHERE ID = ?"
        return DBHelper().select_by_sql(sql, (dl_id,))

    @staticmethod
    def get_search_results():
        """
        查询检索结果的所有记录
        """
        sql = "SELECT ID,TITLE||' ('||YEAR||') '||ES_STRING,RES_TYPE,SIZE,SEEDERS," \
              "ENCLOSURE,SITE,YEAR,ES_STRING,IMAGE,TYPE,VOTE*1,TORRENT_NAME,DESCRIPTION,TMDBID,POSTER,OVERVIEW,PAGEURL,OTHERINFO,UPLOAD_VOLUME_FACTOR,DOWNLOAD_VOLUME_FACTOR,TITLE" \
              " FROM SEARCH_RESULT_INFO"
        return DBHelper().select_by_sql(sql)

    @staticmethod
    def is_torrent_rssd(enclosure):
        """
        查询RSS是否处理过，根据名称
        """
        if not enclosure:
            return True
        sql = "SELECT COUNT(1) FROM RSS_TORRENTS WHERE ENCLOSURE = ?"
        rets = DBHelper().select_by_sql(sql, (enclosure,))
        if rets and rets[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def is_userrss_finished(torrent_name, enclosure):
        """
        查询RSS是否处理过，根据名称
        """
        if not torrent_name and not enclosure:
            return True
        if enclosure:
            sql = "SELECT COUNT(1) FROM RSS_TORRENTS WHERE ENCLOSURE = ?"
            rets = DBHelper().select_by_sql(sql, (enclosure,))
        else:
            sql = "SELECT COUNT(1) FROM RSS_TORRENTS WHERE TORRENT_NAME = ?"
            rets = DBHelper().select_by_sql(sql, (torrent_name,))
        if rets and rets[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def delete_all_search_torrents():
        """
        删除所有搜索的记录
        """
        return DBHelper().update_by_sql("DELETE FROM SEARCH_RESULT_INFO")

    @staticmethod
    def insert_rss_torrents(media_info):
        """
        将RSS的记录插入数据库
        """
        sql = "INSERT INTO RSS_TORRENTS(TORRENT_NAME, ENCLOSURE, TYPE, TITLE, YEAR, SEASON, EPISODE) " \
              "VALUES (?, ?, ?, ?, ?, ?, ?)"
        return DBHelper().update_by_sql(sql, (StringUtils.str_sql(media_info.org_string),
                                              media_info.enclosure,
                                              media_info.type.value,
                                              StringUtils.str_sql(media_info.title),
                                              StringUtils.str_sql(media_info.year),
                                              media_info.get_season_string(),
                                              media_info.get_episode_string()))

    @staticmethod
    def insert_douban_media_state(media, state):
        """
        将豆瓣的数据插入数据库
        """
        if not media.year:
            sql = "DELETE FROM DOUBAN_MEDIAS WHERE NAME = ?"
            DBHelper().update_by_sql(sql, (StringUtils.str_sql(media.get_name()),))
        else:
            sql = "DELETE FROM DOUBAN_MEDIAS WHERE NAME = ? AND YEAR = ?"
            DBHelper().update_by_sql(sql, (StringUtils.str_sql(media.get_name()), StringUtils.str_sql(media.year)))

        sql = "INSERT INTO DOUBAN_MEDIAS(NAME, YEAR, TYPE, RATING, IMAGE, STATE) VALUES (?, ?, ?, ?, ?, ?)"
        # 再插入
        return DBHelper().update_by_sql(sql, (StringUtils.str_sql(media.get_name()),
                                              StringUtils.str_sql(media.year),
                                              media.type.value,
                                              media.vote_average,
                                              media.get_poster_image(),
                                              state))

    @staticmethod
    def update_douban_media_state(media, state):
        """
        标记豆瓣数据的状态
        """
        sql = "UPDATE DOUBAN_MEDIAS SET STATE = ? WHERE NAME = ? AND YEAR = ?"
        return DBHelper().update_by_sql(sql, (state, StringUtils.str_sql(media.title), StringUtils.str_sql(media.year)))

    @staticmethod
    def get_douban_search_state(title, year):
        """
        查询未检索的豆瓣数据
        """
        sql = "SELECT STATE FROM DOUBAN_MEDIAS WHERE NAME = ? AND YEAR = ?"
        return DBHelper().select_by_sql(sql, (StringUtils.str_sql(title), StringUtils.str_sql(year)))

    @staticmethod
    def is_transfer_history_exists(file_path, file_name, title, se):
        """
        查询识别转移记录
        """
        if not file_path:
            return False
        sql = "SELECT COUNT(1) FROM TRANSFER_HISTORY WHERE FILE_PATH = ? AND FILE_NAME = ? AND TITLE = ? AND SE = ?"
        ret = DBHelper().select_by_sql(sql, (
            StringUtils.str_sql(file_path), StringUtils.str_sql(file_name), StringUtils.str_sql(title),
            StringUtils.str_sql(se)))
        if ret and ret[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_transfer_history(in_from: Enum, rmt_mode: RmtMode, in_path, dest, media_info):
        """
        插入识别转移记录
        """
        if not media_info or not media_info.tmdb_info:
            return
        if in_path:
            in_path = os.path.normpath(in_path)
        else:
            return False
        if not dest:
            dest = ""
        file_path = os.path.dirname(in_path)
        file_name = os.path.basename(in_path)
        if SqlHelper.is_transfer_history_exists(file_path, file_name, media_info.title, media_info.get_season_string()):
            return True
        timestr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        sql = "INSERT INTO TRANSFER_HISTORY" \
              "(SOURCE, MODE, TYPE, FILE_PATH, FILE_NAME, TITLE, CATEGORY, YEAR, SE, DEST, DATE)" \
              " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        return DBHelper().update_by_sql(sql, (in_from.value,
                                              rmt_mode.value,
                                              media_info.type.value,
                                              StringUtils.str_sql(file_path),
                                              StringUtils.str_sql(file_name),
                                              StringUtils.str_sql(media_info.title),
                                              media_info.category,
                                              StringUtils.str_sql(media_info.year),
                                              media_info.get_season_string(),
                                              dest,
                                              timestr))

    @staticmethod
    def get_transfer_history(search, page, rownum):
        """
        查询识别转移记录
        """
        if page == 1:
            begin_pos = 0
        else:
            begin_pos = (page - 1) * rownum

        if search:
            search = f"%{search}%"
            count_sql = "SELECT COUNT(1) FROM TRANSFER_HISTORY WHERE FILE_NAME LIKE ? OR TITLE LIKE ?"
            sql = "SELECT SOURCE, MODE, TYPE, FILE_NAME, TITLE, CATEGORY, YEAR, SE, DEST, DATE, ID" \
                  " FROM TRANSFER_HISTORY" \
                  " WHERE FILE_NAME LIKE ? OR TITLE LIKE ? ORDER BY DATE DESC LIMIT ? OFFSET ?"
            return DBHelper().select_by_sql(count_sql, (search, search)), DBHelper().select_by_sql(sql, (
                search, search, rownum, begin_pos))
        else:
            count_sql = "SELECT COUNT(1) FROM TRANSFER_HISTORY"
            sql = "SELECT SOURCE, MODE, TYPE, FILE_NAME, TITLE, CATEGORY, YEAR, SE, DEST, DATE, ID" \
                  " FROM TRANSFER_HISTORY" \
                  " ORDER BY DATE DESC LIMIT ? OFFSET ?"
        return DBHelper().select_by_sql(count_sql), DBHelper().select_by_sql(sql, (rownum, begin_pos))

    @staticmethod
    def get_transfer_path_by_id(logid):
        """
        根据logid查询PATH
        """
        sql = "SELECT FILE_PATH, FILE_NAME, DEST, TITLE, CATEGORY, YEAR, SE, TYPE FROM TRANSFER_HISTORY WHERE ID = ?"
        return DBHelper().select_by_sql(sql, (logid,))

    @staticmethod
    def delete_transfer_log_by_id(logid):
        """
        根据logid删除记录
        """
        sql = "DELETE FROM TRANSFER_HISTORY WHERE ID = ?"
        return DBHelper().update_by_sql(sql, (logid,))

    @staticmethod
    def get_transfer_unknown_paths():
        """
        查询未识别的记录列表
        """
        sql = "SELECT ID, PATH, DEST FROM TRANSFER_UNKNOWN WHERE STATE = 'N'"
        return DBHelper().select_by_sql(sql)

    @staticmethod
    def update_transfer_unknown_state(path):
        """
        更新未识别记录为识别
        """
        if not path:
            return False
        path = os.path.normpath(path)
        sql = "UPDATE TRANSFER_UNKNOWN SET STATE = 'Y' WHERE PATH = ?"
        return DBHelper().update_by_sql(sql, (StringUtils.str_sql(path),))

    @staticmethod
    def delete_transfer_unknown(tid):
        """
        删除未识别记录
        """
        if not tid:
            return False
        sql = "DELETE FROM TRANSFER_UNKNOWN WHERE ID = ?"
        return DBHelper().update_by_sql(sql, (tid,))

    @staticmethod
    def get_unknown_path_by_id(tid):
        """
        查询未识别记录
        """
        if not tid:
            return False
        sql = "SELECT PATH,DEST FROM TRANSFER_UNKNOWN WHERE ID = ?"
        return DBHelper().select_by_sql(sql, (tid,))

    @staticmethod
    def is_transfer_unknown_exists(path):
        """
        查询未识别记录是否存在
        """
        if not path:
            return False
        path = os.path.normpath(path)
        sql = "SELECT COUNT(1) FROM TRANSFER_UNKNOWN WHERE PATH = ?"
        ret = DBHelper().select_by_sql(sql, (StringUtils.str_sql(path),))
        if ret and ret[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_transfer_unknown(path, dest):
        """
        插入未识别记录
        """
        if not path:
            return False
        if SqlHelper.is_transfer_unknown_exists(path):
            return False
        else:
            path = os.path.normpath(path)
            if dest:
                dest = os.path.normpath(dest)
            else:
                dest = ""
            sql = "INSERT INTO TRANSFER_UNKNOWN(PATH, DEST, STATE) VALUES (?, ?, ?)"
            return DBHelper().update_by_sql(sql, (StringUtils.str_sql(path), StringUtils.str_sql(dest), 'N'))

    @staticmethod
    def is_transfer_in_blacklist(path):
        """
        查询是否为黑名单
        """
        if not path:
            return False
        path = os.path.normpath(path)
        sql = "SELECT COUNT(1) FROM TRANSFER_BLACKLIST WHERE PATH = ?"
        ret = DBHelper().select_by_sql(sql, (StringUtils.str_sql(path),))
        if ret and ret[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def is_transfer_notin_blacklist(path):
        """
        查询是否为黑名单
        """
        return not SqlHelper.is_transfer_in_blacklist(path)

    @staticmethod
    def insert_transfer_blacklist(path):
        """
        插入黑名单记录
        """
        if not path:
            return False
        if SqlHelper.is_transfer_in_blacklist(path):
            return False
        else:
            path = os.path.normpath(path)
            sql = "INSERT INTO TRANSFER_BLACKLIST(PATH) VALUES (?)"
            return DBHelper().update_by_sql(sql, (StringUtils.str_sql(path),))

    @staticmethod
    def truncate_transfer_blacklist():
        """
        清空黑名单记录
        """
        DBHelper().update_by_sql("DELETE FROM TRANSFER_BLACKLIST")
        DBHelper().update_by_sql("DELETE FROM SYNC_HISTORY")

    @staticmethod
    def truncate_rss_history():
        """
        清空RSS历史记录
        """
        DBHelper().update_by_sql("DELETE FROM RSS_TORRENTS")

    @staticmethod
    def truncate_rss_episodes():
        """
        清空RSS历史记录
        """
        DBHelper().update_by_sql("DELETE FROM RSS_TV_EPISODES")

    @staticmethod
    def get_config_site():
        """
        查询所有站点信息
        """
        return DBHelper().select_by_sql(
            "SELECT ID,NAME,PRI,RSSURL,SIGNURL,COOKIE,INCLUDE,EXCLUDE,SIZE,NOTE"
            " FROM CONFIG_SITE"
            " ORDER BY CAST(PRI AS DECIMAL) ASC")

    @staticmethod
    def get_site_by_id(tid):
        """
        查询1个站点信息
        """
        return DBHelper().select_by_sql(
            "SELECT ID,NAME,PRI,RSSURL,SIGNURL,COOKIE,INCLUDE,EXCLUDE,SIZE,NOTE FROM CONFIG_SITE WHERE ID = ?", (tid,))

    @staticmethod
    def get_site_by_name(name):
        """
        基于站点名称查询站点信息
        :return:
        """
        return DBHelper().select_by_sql(
            "SELECT ID,NAME,SIGNURL FROM CONFIG_SITE WHERE NAME = ?", (name,))

    @staticmethod
    def insert_config_site(name, site_pri, rssurl, signurl, cookie, note, rss_uses):
        """
        插入站点信息
        """
        if not name:
            return
        sql = "INSERT INTO CONFIG_SITE(NAME,PRI,RSSURL,SIGNURL,COOKIE,NOTE, INCLUDE) VALUES " \
              "(?, ?, ?, ?, ?, ?, ?)"
        return DBHelper().update_by_sql(sql, (StringUtils.str_sql(name),
                                              StringUtils.str_sql(site_pri),
                                              StringUtils.str_sql(rssurl),
                                              StringUtils.str_sql(signurl),
                                              StringUtils.str_sql(cookie),
                                              StringUtils.str_sql(note),
                                              StringUtils.str_sql(rss_uses)))

    @staticmethod
    def delete_config_site(tid):
        """
        删除站点信息
        """
        if not tid:
            return False
        return DBHelper().update_by_sql("DELETE FROM CONFIG_SITE WHERE ID = ?", (tid,))

    @staticmethod
    def update_config_site(tid, name, site_pri, rssurl, signurl, cookie, note, rss_uses):
        """
        更新站点信息
        """
        if not tid:
            return
        sql = "UPDATE CONFIG_SITE SET NAME=?,PRI=?,RSSURL=?,SIGNURL=?,COOKIE=?,NOTE=?,INCLUDE=? WHERE ID=?"
        return DBHelper().update_by_sql(sql, (StringUtils.str_sql(name),
                                              StringUtils.str_sql(site_pri),
                                              StringUtils.str_sql(rssurl),
                                              StringUtils.str_sql(signurl),
                                              StringUtils.str_sql(cookie),
                                              StringUtils.str_sql(note),
                                              StringUtils.str_sql(rss_uses),
                                              tid))

    @staticmethod
    def get_config_filter_group():
        """
        查询过滤规则组
        """
        return DBHelper().select_by_sql("SELECT ID,GROUP_NAME,IS_DEFAULT,NOTE FROM CONFIG_FILTER_GROUP")

    @staticmethod
    def get_config_filter_rule(groupid=None):
        """
        查询过滤规则
        """
        if not groupid:
            return DBHelper().select_by_sql("SELECT "
                                            "ID,GROUP_ID,ROLE_NAME,PRIORITY,INCLUDE,EXCLUDE,SIZE_LIMIT,NOTE "
                                            "FROM CONFIG_FILTER_RULES "
                                            "ORDER BY GROUP_ID, CAST(PRIORITY AS DECIMAL) ASC")
        else:
            return DBHelper().select_by_sql("SELECT "
                                            "ID,GROUP_ID,ROLE_NAME,PRIORITY,INCLUDE,EXCLUDE,SIZE_LIMIT,NOTE "
                                            "FROM CONFIG_FILTER_RULES "
                                            "WHERE GROUP_ID = ? "
                                            "ORDER BY CAST(PRIORITY AS DECIMAL) ASC", (groupid,))

    @staticmethod
    def get_rss_movies(state=None, rssid=None):
        """
        查询订阅电影信息
        """
        if rssid:
            sql = "SELECT NAME,YEAR,TMDBID,IMAGE,DESC,STATE,ID FROM RSS_MOVIES WHERE ID = ?"
            return DBHelper().select_by_sql(sql, (rssid,))
        else:
            if not state:
                sql = "SELECT NAME,YEAR,TMDBID,IMAGE,DESC,STATE,ID FROM RSS_MOVIES"
                return DBHelper().select_by_sql(sql)
            else:
                sql = "SELECT NAME,YEAR,TMDBID,IMAGE,DESC,STATE,ID FROM RSS_MOVIES WHERE STATE = ?"
                return DBHelper().select_by_sql(sql, (state,))

    @staticmethod
    def get_rss_movie_id(title, year, tmdbid=None):
        """
        获取订阅电影ID
        """
        if not title:
            return ""
        sql = "SELECT ID FROM RSS_MOVIES WHERE NAME=? AND YEAR = ?"
        ret = DBHelper().select_by_sql(sql, (StringUtils.str_sql(title), StringUtils.str_sql(year)))
        if ret:
            return ret[0][0]
        else:
            if tmdbid:
                sql = "SELECT ID FROM RSS_MOVIES WHERE TMDBID=?"
                ret = DBHelper().select_by_sql(sql, (tmdbid,))
                if ret:
                    return ret[0][0]
        return ""

    @staticmethod
    def get_rss_movie_sites(rssid):
        """
        获取订阅电影站点
        """
        if not rssid:
            return ""
        sql = "SELECT DESC FROM RSS_MOVIES WHERE ID = ?"
        ret = DBHelper().select_by_sql(sql, (rssid,))
        if ret:
            return ret[0][0]
        return ""

    @staticmethod
    def update_rss_movie_tmdb(rid, tmdbid, title, year, image):
        """
        更新订阅电影的TMDBID
        """
        if not tmdbid:
            return False
        sql = "UPDATE RSS_MOVIES SET TMDBID = ?, NAME = ?, YEAR = ?, IMAGE = ? WHERE ID = ?"
        return DBHelper().update_by_sql(sql, (
            tmdbid, StringUtils.str_sql(title), StringUtils.str_sql(year), StringUtils.str_sql(image), rid))

    @staticmethod
    def is_exists_rss_movie(title, year):
        """
        判断RSS电影是否存在
        """
        if not title:
            return False
        sql = "SELECT COUNT(1) FROM RSS_MOVIES WHERE NAME=? AND YEAR = ?"
        ret = DBHelper().select_by_sql(sql, (StringUtils.str_sql(title), StringUtils.str_sql(year)))
        if ret and ret[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_rss_movie(media_info,
                         state='D',
                         sites: list = None,
                         search_sites: list = None,
                         over_edition=False,
                         rss_restype=None,
                         rss_pix=None,
                         rss_team=None,
                         rss_rule=None):
        """
        新增RSS电影
        """
        if not media_info:
            return False
        if not media_info.title:
            return False
        if SqlHelper.is_exists_rss_movie(media_info.title, media_info.year):
            return True
        sql = "INSERT INTO RSS_MOVIES(NAME,YEAR,TMDBID,IMAGE,DESC,STATE) VALUES (?, ?, ?, ?, ?, ?)"
        desc = "#".join(["|".join(sites or []),
                         "|".join(search_sites or []),
                         "Y" if over_edition else "N",
                         "@".join([StringUtils.str_sql(rss_restype),
                                   StringUtils.str_sql(rss_pix),
                                   StringUtils.str_sql(rss_rule),
                                   StringUtils.str_sql(rss_team)])])
        return DBHelper().update_by_sql(sql, (StringUtils.str_sql(media_info.title),
                                              StringUtils.str_sql(media_info.year),
                                              StringUtils.str_sql(media_info.tmdb_id),
                                              StringUtils.str_sql(media_info.get_message_image()),
                                              desc,
                                              state))

    @staticmethod
    def delete_rss_movie(title=None, year=None, rssid=None, tmdbid=None):
        """
        删除RSS电影
        """
        if not title and not rssid:
            return False
        if rssid:
            return DBHelper().update_by_sql("DELETE FROM RSS_MOVIES WHERE ID = ?", (rssid,))
        else:
            if tmdbid:
                DBHelper().update_by_sql("DELETE FROM RSS_MOVIES WHERE TMDBID = ?", (tmdbid,))
            return DBHelper().update_by_sql("DELETE FROM RSS_MOVIES WHERE NAME = ? AND YEAR = ?",
                                            (StringUtils.str_sql(title), StringUtils.str_sql(year)))

    @staticmethod
    def update_rss_movie_state(title=None, year=None, rssid=None, state='R'):
        """
        更新电影订阅状态
        """
        if not title and not rssid:
            return False
        if rssid:
            sql = "UPDATE RSS_MOVIES SET STATE = ? WHERE ID = ?"
            return DBHelper().update_by_sql(sql, (state, rssid))
        else:
            sql = "UPDATE RSS_MOVIES SET STATE = ? WHERE NAME = ? AND YEAR = ?"
            return DBHelper().update_by_sql(sql, (state, StringUtils.str_sql(title), StringUtils.str_sql(year)))

    @staticmethod
    def get_rss_tvs(state=None, rssid=None):
        """
        查询订阅电视剧信息
        """
        if rssid:
            sql = "SELECT NAME,YEAR,SEASON,TMDBID,IMAGE,DESC,TOTAL,LACK,STATE" \
                  ",((CAST(TOTAL AS FLOAT)-CAST(LACK AS FLOAT))/CAST(TOTAL AS FLOAT))*100,ID" \
                  " FROM RSS_TVS" \
                  " WHERE ID = ?"
            return DBHelper().select_by_sql(sql, (rssid,))
        else:
            if not state:
                sql = "SELECT NAME,YEAR,SEASON,TMDBID,IMAGE,DESC,TOTAL,LACK,STATE" \
                      ",((CAST(TOTAL AS FLOAT)-CAST(LACK AS FLOAT))/CAST(TOTAL AS FLOAT))*100,ID" \
                      " FROM RSS_TVS"
                return DBHelper().select_by_sql(sql)
            else:
                sql = "SELECT NAME,YEAR,SEASON,TMDBID,IMAGE,DESC,TOTAL,LACK,STATE" \
                      ",((CAST(TOTAL AS FLOAT)-CAST(LACK AS FLOAT))/CAST(TOTAL AS FLOAT))*100,ID" \
                      " FROM RSS_TVS WHERE STATE = ?"
                return DBHelper().select_by_sql(sql, (state,))

    @staticmethod
    def get_rss_tv_id(title, year, season=None, tmdbid=None):
        """
        获取订阅电影ID
        """
        if not title:
            return ""
        if season:
            sql = "SELECT ID FROM RSS_TVS WHERE NAME = ? AND YEAR = ? AND SEASON = ?"
            ret = DBHelper().select_by_sql(sql, (StringUtils.str_sql(title), StringUtils.str_sql(year), season))
            if ret:
                return ret[0][0]
            else:
                if tmdbid:
                    sql = "SELECT ID FROM RSS_TVS WHERE TMDBID=? AND SEASON = ?"
                    ret = DBHelper().select_by_sql(sql, (tmdbid, season))
                    if ret:
                        return ret[0][0]
        else:
            sql = "SELECT ID FROM RSS_TVS WHERE NAME = ? AND YEAR = ?"
            ret = DBHelper().select_by_sql(sql, (StringUtils.str_sql(title), StringUtils.str_sql(year)))
            if ret:
                return ret[0][0]
            else:
                if tmdbid:
                    sql = "SELECT ID FROM RSS_TVS WHERE TMDBID=?"
                    ret = DBHelper().select_by_sql(sql, (tmdbid,))
                    if ret:
                        return ret[0][0]
        return ""

    @staticmethod
    def get_rss_tv_sites(rssid):
        """
        获取订阅电视剧站点
        """
        if not rssid:
            return ""
        sql = "SELECT DESC FROM RSS_TVS WHERE ID = ?"
        ret = DBHelper().select_by_sql(sql, (rssid,))
        if ret:
            return ret[0][0]
        return ""

    @staticmethod
    def update_rss_tv_tmdb(rid, tmdbid, title, year, total, lack, image):
        """
        更新订阅电影的TMDBID
        """
        if not tmdbid:
            return False
        sql = "UPDATE RSS_TVS SET TMDBID = ?, NAME = ?, YEAR = ?, TOTAL = ?, LACK = ?, IMAGE = ? WHERE ID = ?"
        return DBHelper().update_by_sql(sql,
                                        (tmdbid, StringUtils.str_sql(title), year, total, lack,
                                         StringUtils.str_sql(image), rid))

    @staticmethod
    def is_exists_rss_tv(title, year, season=None):
        """
        判断RSS电视剧是否存在
        """
        if not title:
            return False
        if season:
            sql = "SELECT COUNT(1) FROM RSS_TVS WHERE NAME = ? AND YEAR = ? AND SEASON = ?"
            ret = DBHelper().select_by_sql(sql, (StringUtils.str_sql(title), StringUtils.str_sql(year), season))
        else:
            sql = "SELECT COUNT(1) FROM RSS_TVS WHERE NAME = ? AND YEAR = ?"
            ret = DBHelper().select_by_sql(sql, (StringUtils.str_sql(title), StringUtils.str_sql(year)))
        if ret and ret[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_rss_tv(media_info, total, lack=0, state="D",
                      sites: list = None,
                      search_sites: list = None,
                      over_edition=False,
                      rss_restype=None,
                      rss_pix=None,
                      rss_team=None,
                      rss_rule=None,
                      match=False
                      ):
        """
        新增RSS电视剧
        """
        if not media_info:
            return False
        if not media_info.title:
            return False
        if match and media_info.begin_season is None:
            season_str = ""
        else:
            season_str = media_info.get_season_string()
        if SqlHelper.is_exists_rss_tv(media_info.title, media_info.year, season_str):
            return True
        # 插入订阅数据
        sql = "INSERT INTO RSS_TVS(NAME,YEAR,SEASON,TMDBID,IMAGE,DESC,TOTAL,LACK,STATE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        desc = "#".join(["|".join(sites or []),
                         "|".join(search_sites or []),
                         "Y" if over_edition else "N",
                         "@".join([StringUtils.str_sql(rss_restype),
                                   StringUtils.str_sql(rss_pix),
                                   StringUtils.str_sql(rss_rule),
                                   StringUtils.str_sql(rss_team)])])
        return DBHelper().update_by_sql(sql, (StringUtils.str_sql(media_info.title),
                                              StringUtils.str_sql(media_info.year),
                                              season_str,
                                              StringUtils.str_sql(media_info.tmdb_id),
                                              StringUtils.str_sql(media_info.get_message_image()),
                                              desc,
                                              total,
                                              lack,
                                              state))

    @staticmethod
    def update_rss_tv_lack(title=None, year=None, season=None, rssid=None, lack_episodes: list = None):
        """
        更新电视剧缺失的集数
        """
        if not title and not rssid:
            return False
        if not lack_episodes:
            lack = 0
        else:
            lack = len(lack_episodes)
        if rssid:
            SqlHelper.update_rss_tv_episodes(rssid, lack_episodes)
            sql = "UPDATE RSS_TVS SET LACK=? WHERE ID = ?"
            return DBHelper().update_by_sql(sql, (lack, rssid))
        else:
            sql = "UPDATE RSS_TVS SET LACK=? WHERE NAME = ? AND YEAR = ? AND SEASON = ?"
            return DBHelper().update_by_sql(sql, (lack, StringUtils.str_sql(title), StringUtils.str_sql(year), season))

    @staticmethod
    def delete_rss_tv(title=None, year=None, season=None, rssid=None, tmdbid=None):
        """
        删除RSS电视剧
        """
        if not title and not rssid:
            return False
        if rssid:
            SqlHelper.delete_rss_tv_episodes(rssid)
            return DBHelper().update_by_sql("DELETE FROM RSS_TVS WHERE ID = ?", (rssid,))
        else:
            rssid = SqlHelper.get_rss_tv_id(title=title, year=year, tmdbid=tmdbid, season=season)
            if rssid:
                SqlHelper.delete_rss_tv_episodes(rssid)
                return SqlHelper.delete_rss_tv(rssid=rssid)
            return False

    @staticmethod
    def is_exists_rss_tv_episodes(rid):
        """
        判断RSS电视剧是否存在
        """
        if not rid:
            return False
        sql = "SELECT COUNT(1) FROM RSS_TV_EPISODES WHERE RSSID = ?"
        ret = DBHelper().select_by_sql(sql, (rid,))
        if ret and ret[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def update_rss_tv_episodes(rid, episodes):
        """
        插入或更新电视剧订阅缺失剧集
        """
        if not rid:
            return
        if not episodes:
            episodes = []
        else:
            episodes = [str(epi) for epi in episodes]
        if SqlHelper.is_exists_rss_tv_episodes(rid):
            sql = "UPDATE RSS_TV_EPISODES SET EPISODES = ? WHERE RSSID = ?"
            ret = DBHelper().update_by_sql(sql, (",".join(episodes), rid))
        else:
            sql = "INSERT INTO RSS_TV_EPISODES(RSSID, EPISODES) VALUES(?, ?)"
            ret = DBHelper().update_by_sql(sql, (rid, ",".join(episodes)))
        return ret

    @staticmethod
    def get_rss_tv_episodes(rid):
        """
        查询电视剧订阅缺失剧集
        """
        if not rid:
            return []
        sql = "SELECT EPISODES FROM RSS_TV_EPISODES WHERE RSSID = ?"
        ret = DBHelper().select_by_sql(sql, (rid,))
        if ret:
            return [int(epi) for epi in str(ret[0][0]).split(',')]
        else:
            return None

    @staticmethod
    def delete_rss_tv_episodes(rid):
        """
        删除电视剧订阅缺失剧集
        """
        if not rid:
            return []
        sql = "DELETE FROM RSS_TV_EPISODES WHERE RSSID = ?"
        return DBHelper().update_by_sql(sql, (rid,))

    @staticmethod
    def update_rss_tv_state(title=None, year=None, season=None, rssid=None, state='R'):
        """
        更新电视剧订阅状态
        """
        if not title and not rssid:
            return False
        if rssid:
            sql = "UPDATE RSS_TVS SET STATE = ? WHERE ID = ?"
            return DBHelper().update_by_sql(sql, (state, rssid))
        else:
            sql = "UPDATE RSS_TVS SET STATE = ? WHERE NAME = ? AND YEAR = ? AND SEASON = ?"
            return DBHelper().update_by_sql(sql, (state, StringUtils.str_sql(title), StringUtils.str_sql(year), season))

    @staticmethod
    def is_sync_in_history(path, dest):
        """
        查询是否存在同步历史记录
        """
        if not path:
            return False
        path = os.path.normpath(path)
        dest = os.path.normpath(dest)
        sql = "SELECT COUNT(1) FROM SYNC_HISTORY WHERE PATH = ? AND DEST = ?"
        ret = DBHelper().select_by_sql(sql, (StringUtils.str_sql(path), StringUtils.str_sql(dest)))
        if ret and ret[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_sync_history(path, src, dest):
        """
        插入黑名单记录
        """
        if not path or not dest:
            return False
        if SqlHelper.is_sync_in_history(path, dest):
            return False
        else:
            path = os.path.normpath(path)
            src = os.path.normpath(src)
            dest = os.path.normpath(dest)
            sql = "INSERT INTO SYNC_HISTORY(PATH, SRC, DEST) VALUES (?, ?, ?)"
            return DBHelper().update_by_sql(sql, (
                StringUtils.str_sql(path), StringUtils.str_sql(src), StringUtils.str_sql(dest)))

    @staticmethod
    def get_users():
        """
        查询用户列表
        """
        sql = "SELECT ID,NAME,PASSWORD,PRIS FROM CONFIG_USERS"
        return DBHelper().select_by_sql(sql)

    @staticmethod
    def is_user_exists(name):
        """
        判断用户是否存在
        """
        if not name:
            return False
        sql = "SELECT COUNT(1) FROM CONFIG_USERS WHERE NAME = ?"
        ret = DBHelper().select_by_sql(sql, (name,))
        if ret and ret[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_user(name, password, pris):
        """
        新增用户
        """
        if not name or not password:
            return False
        if SqlHelper.is_user_exists(name):
            return False
        else:
            sql = "INSERT INTO CONFIG_USERS(NAME,PASSWORD,PRIS) VALUES (?, ?, ?)"
            return DBHelper().update_by_sql(sql,
                                            (StringUtils.str_sql(name), StringUtils.str_sql(password),
                                             StringUtils.str_sql(pris)))

    @staticmethod
    def delete_user(name):
        """
        删除用户
        """
        return DBHelper().update_by_sql("DELETE FROM CONFIG_USERS WHERE NAME = ?", (StringUtils.str_sql(name),))

    @staticmethod
    def get_transfer_statistics(days=30):
        """
        查询历史记录统计
        """
        begin_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        sql = "SELECT TYPE,SUBSTR(DATE, 1, 10),COUNT(1)" \
              " FROM TRANSFER_HISTORY" \
              " WHERE DATE > ? GROUP BY TYPE,SUBSTR(DATE, 1, 10)"
        return DBHelper().select_by_sql(sql, (begin_date,))

    @staticmethod
    def update_site_user_statistics_site_name(new_name, old_name):
        """
        更新站点用户数据中站点名称
        :param old_name:
        :return:
        """
        sql = "UPDATE SITE_USER_INFO_STATS SET SITE = ? WHERE SITE = ?"

        return DBHelper().update_by_sql(sql, (new_name, old_name))

    @staticmethod
    def update_site_user_statistics(site_user_infos: list):
        """
        更新站点用户粒度数据
        """
        if not site_user_infos:
            return
        update_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        sql = "INSERT OR REPLACE INTO SITE_USER_INFO_STATS(SITE, USERNAME, USER_LEVEL," \
              " JOIN_AT, UPDATE_AT," \
              " UPLOAD, DOWNLOAD, RATIO," \
              " SEEDING, LEECHING, SEEDING_SIZE," \
              " BONUS," \
              " URL, FAVICON, MSG_UNREAD) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

        data_list = []

        for site_user_info in site_user_infos:
            site = site_user_info.site_name
            username = site_user_info.username
            user_level = site_user_info.user_level
            join_at = site_user_info.join_at
            upload = site_user_info.upload
            download = site_user_info.download
            ratio = site_user_info.ratio
            seeding = site_user_info.seeding
            seeding_size = site_user_info.seeding_size
            leeching = site_user_info.leeching
            bonus = site_user_info.bonus
            url = site_user_info.site_url
            favicon = site_user_info.site_favicon
            msg_unread = site_user_info.message_unread

            data_list.append((
                StringUtils.str_sql(site), username, user_level, join_at, update_at, upload, download, ratio, seeding,
                leeching,
                seeding_size, bonus, url, favicon, msg_unread))
        return DBHelper().update_by_sql_batch(sql, data_list)

    @staticmethod
    def update_site_seed_info_site_name(new_name, old_name):
        """
        更新站点做种数据中站点名称
        :param new_name: 新的站点名称
        :param old_name: 原始站点名称
        :return:
        """
        sql = "UPDATE SITE_USER_SEEDING_INFO SET SITE = ? WHERE SITE = ?"

        return DBHelper().update_by_sql(sql, (new_name, old_name))

    @staticmethod
    def update_site_seed_info(site_user_infos: list):
        """
        更新站点做种数据
        """
        if not site_user_infos:
            return
        update_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        sql = "INSERT OR REPLACE INTO SITE_USER_SEEDING_INFO(SITE, UPDATE_AT," \
              " SEEDING_INFO," \
              " URL) VALUES (?, ?, ?, ?)"

        data_list = []
        for site_user_info in site_user_infos:
            data_list.append((StringUtils.str_sql(site_user_info.site_name), update_at, site_user_info.seeding_info,
                              site_user_info.site_url))

        return DBHelper().update_by_sql_batch(sql, data_list)

    @staticmethod
    def is_site_user_statistics_exists(url):
        """
        判断站点用户数据是否存在
        """
        if not url:
            return False
        sql = "SELECT COUNT(1) FROM SITE_USER_INFO_STATS WHERE URL = ? "
        ret = DBHelper().select_by_sql(sql, (url,))
        if ret and ret[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def get_site_user_statistics(num=100, strict_urls=None):
        """
        查询站点数据历史
        """
        if strict_urls is None:
            strict_urls = []

        sql = "SELECT SITE, USERNAME, USER_LEVEL," \
              " JOIN_AT, UPDATE_AT," \
              " UPLOAD, DOWNLOAD, RATIO," \
              " SEEDING, LEECHING, SEEDING_SIZE," \
              " BONUS, URL, FAVICON, MSG_UNREAD" \
              " FROM SITE_USER_INFO_STATS LIMIT ?"
        if strict_urls:
            sql = "SELECT SITE, USERNAME, USER_LEVEL," \
                  " JOIN_AT, UPDATE_AT," \
                  " UPLOAD, DOWNLOAD, RATIO," \
                  " SEEDING, LEECHING, SEEDING_SIZE," \
                  " BONUS, URL, FAVICON, MSG_UNREAD" \
                  " FROM SITE_USER_INFO_STATS WHERE URL in {} LIMIT ?".format(tuple(strict_urls + ["__DUMMY__"]))

        return DBHelper().select_by_sql(sql, (num,))

    @staticmethod
    def is_site_statistics_history_exists(url, date):
        """
        判断站点历史数据是否存在
        """
        if not url or not date:
            return False
        sql = "SELECT COUNT(1) FROM SITE_STATISTICS_HISTORY WHERE URL = ? AND DATE = ?"
        ret = DBHelper().select_by_sql(sql, (url, date))
        if ret and ret[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def update_site_statistics_site_name(new_name, old_name):
        """
        更新站点做种数据中站点名称
        :param new_name: 新站点名称
        :param old_name: 原始站点名称
        :return:
        """
        sql = "UPDATE SITE_STATISTICS_HISTORY SET SITE = ? WHERE SITE = ?"

        return DBHelper().update_by_sql(sql, (new_name, old_name))

    @staticmethod
    def insert_site_statistics_history(site_user_infos: list):
        """
        插入站点数据
        """
        if not site_user_infos:
            return

        date_now = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        sql = "INSERT OR REPLACE INTO SITE_STATISTICS_HISTORY(SITE, USER_LEVEL, DATE, UPLOAD, DOWNLOAD, RATIO," \
              " SEEDING, LEECHING, SEEDING_SIZE," \
              " BONUS," \
              " URL) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

        data_list = []
        for site_user_info in site_user_infos:
            site = site_user_info.site_name
            upload = site_user_info.upload
            user_level = site_user_info.user_level
            download = site_user_info.download
            ratio = site_user_info.ratio
            seeding = site_user_info.seeding
            seeding_size = site_user_info.seeding_size
            leeching = site_user_info.leeching
            bonus = site_user_info.bonus
            url = site_user_info.site_url

            data_list.append(
                (StringUtils.str_sql(site), user_level, date_now, upload, download, ratio, seeding, leeching,
                 seeding_size, bonus, url))

        return DBHelper().update_by_sql_batch(sql, data_list)

    @staticmethod
    def get_site_statistics_history(site, days=30):
        """
        查询站点数据历史
        """
        sql = "SELECT DATE, UPLOAD, DOWNLOAD, BONUS, SEEDING, SEEDING_SIZE " \
              "FROM SITE_STATISTICS_HISTORY WHERE SITE = ? ORDER BY DATE ASC LIMIT ?"
        return DBHelper().select_by_sql(sql, (site, days,))

    @staticmethod
    def get_site_seeding_info(site):
        """
        查询站点做种信息
        """
        sql = "SELECT SEEDING_INFO " \
              "FROM SITE_USER_SEEDING_INFO WHERE SITE = ? LIMIT 1"
        return DBHelper().select_by_sql(sql, (site,))

    @staticmethod
    def get_site_statistics_recent_sites(days=7, strict_urls=None):
        """
        查询近期上传下载量
        """
        # 查询最大最小日期
        if strict_urls is None:
            strict_urls = []

        b_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        date_sql = "SELECT MAX(DATE), MIN(DATE) FROM SITE_STATISTICS_HISTORY WHERE DATE > ? "
        date_ret = DBHelper().select_by_sql(date_sql, (b_date,))
        if date_ret:
            total_upload = 0
            total_download = 0
            ret_sites = []
            ret_site_uploads = []
            ret_site_downloads = []
            min_date = date_ret[0][1]
            # 查询开始值
            sql = """SELECT SITE, MIN(UPLOAD), MIN(DOWNLOAD), MAX(UPLOAD), MAX(DOWNLOAD)
                     FROM (SELECT SITE, DATE, SUM(UPLOAD) as UPLOAD, SUM(DOWNLOAD) as DOWNLOAD FROM SITE_STATISTICS_HISTORY WHERE DATE >= ? GROUP BY SITE, DATE) X 
                     GROUP BY SITE"""
            if strict_urls:
                sql = """
                     SELECT SITE, MIN(UPLOAD), MIN(DOWNLOAD), MAX(UPLOAD), MAX(DOWNLOAD)
                     FROM (SELECT SITE, DATE, SUM(UPLOAD) as UPLOAD, SUM(DOWNLOAD) as DOWNLOAD FROM SITE_STATISTICS_HISTORY WHERE DATE >= ? AND URL in {} GROUP BY SITE, DATE) X 
                     GROUP BY SITE""".format(tuple(strict_urls + ["__DUMMY__"]))
            for ret_b in DBHelper().select_by_sql(sql, (min_date,)):
                # 如果最小值都是0，可能时由于近几日没有更新数据，或者cookie过期，正常有数据的话，第二天能正常
                ret_b = list(ret_b)
                if ret_b[1] == 0 and ret_b[2] == 0:
                    ret_b[1] = ret_b[3]
                    ret_b[2] = ret_b[4]
                ret_sites.append(ret_b[0])
                if int(ret_b[1]) < int(ret_b[3]):
                    total_upload += int(ret_b[3]) - int(ret_b[1])
                    ret_site_uploads.append(int(ret_b[3]) - int(ret_b[1]))
                else:
                    ret_site_uploads.append(0)
                if int(ret_b[2]) < int(ret_b[4]):
                    total_download += int(ret_b[4]) - int(ret_b[2])
                    ret_site_downloads.append(int(ret_b[4]) - int(ret_b[2]))
                else:
                    ret_site_downloads.append(0)
            return total_upload, total_download, ret_sites, ret_site_uploads, ret_site_downloads
        else:
            return 0, 0, [], [], []

    @staticmethod
    def is_exists_download_history(title, tmdbid, mtype=None):
        """
        查询下载历史是否存在
        """
        if not title or not tmdbid:
            return False
        if mtype:
            sql = "SELECT COUNT(1) FROM DOWNLOAD_HISTORY WHERE (TITLE = ? OR TMDBID = ?) AND TYPE = ?"
            ret = DBHelper().select_by_sql(sql, (StringUtils.str_sql(title), StringUtils.str_sql(tmdbid), mtype))
        else:
            sql = "SELECT COUNT(1) FROM DOWNLOAD_HISTORY WHERE TITLE = ? OR TMDBID = ?"
            ret = DBHelper().select_by_sql(sql, (StringUtils.str_sql(title), StringUtils.str_sql(tmdbid)))
        if ret and ret[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_download_history(media_info):
        """
        新增下载历史
        """
        if not media_info:
            return False
        if not media_info.title or not media_info.tmdb_id:
            return False
        if SqlHelper.is_exists_download_history(media_info.title, media_info.tmdb_id, media_info.type.value):
            sql = "UPDATE DOWNLOAD_HISTORY SET TORRENT = ?, ENCLOSURE = ?, DESC = ?, DATE = ?, SITE = ? WHERE TITLE = ? AND TMDBID = ? AND TYPE = ?"
            return DBHelper().update_by_sql(sql, (StringUtils.str_sql(media_info.org_string),
                                                  StringUtils.str_sql(media_info.enclosure),
                                                  StringUtils.str_sql(media_info.description),
                                                  time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                                                  StringUtils.str_sql(media_info.site),
                                                  StringUtils.str_sql(media_info.title),
                                                  StringUtils.str_sql(media_info.tmdb_id),
                                                  media_info.type.value))
        else:
            sql = "INSERT INTO DOWNLOAD_HISTORY(TITLE,YEAR,TYPE,TMDBID,VOTE,POSTER,OVERVIEW,TORRENT,ENCLOSURE,DESC,DATE,SITE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            return DBHelper().update_by_sql(sql, (StringUtils.str_sql(media_info.title),
                                                  StringUtils.str_sql(media_info.year),
                                                  media_info.type.value,
                                                  media_info.tmdb_id,
                                                  media_info.vote_average,
                                                  media_info.get_poster_image(),
                                                  StringUtils.str_sql(media_info.overview),
                                                  StringUtils.str_sql(media_info.org_string),
                                                  StringUtils.str_sql(media_info.enclosure),
                                                  StringUtils.str_sql(media_info.description),
                                                  time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                                                  StringUtils.str_sql(media_info.site)))

    @staticmethod
    def get_download_history(date=None, hid=None, num=30, page=1):
        """
        查询下载历史
        """
        if hid:
            sql = "SELECT ID,TITLE,YEAR,TYPE,TMDBID,VOTE,POSTER,OVERVIEW,TORRENT,ENCLOSURE,DESC,DATE,SITE FROM DOWNLOAD_HISTORY WHERE ID = ?"
            return DBHelper().select_by_sql(sql, (hid,))
        elif date:
            sql = "SELECT ID,TITLE,YEAR,TYPE,TMDBID,VOTE,POSTER,OVERVIEW,TORRENT,ENCLOSURE,DESC,DATE,SITE FROM DOWNLOAD_HISTORY WHERE DATE > ? ORDER BY DATE DESC"
            return DBHelper().select_by_sql(sql, (date,))
        else:
            offset = (int(page) - 1) * int(num)
            sql = "SELECT ID,TITLE,YEAR,TYPE,TMDBID,VOTE,POSTER,OVERVIEW,TORRENT,ENCLOSURE,DESC,DATE,SITE FROM DOWNLOAD_HISTORY ORDER BY DATE DESC LIMIT ? OFFSET ?"
            return DBHelper().select_by_sql(sql, (num, offset))

    @staticmethod
    def is_media_downloaded(title, tmdbid):
        """
        根据标题和年份检查是否下载过
        """
        if SqlHelper.is_exists_download_history(title, tmdbid):
            return True
        sql = "SELECT COUNT(1) FROM TRANSFER_HISTORY WHERE TITLE = ?"
        ret = DBHelper().select_by_sql(sql, (StringUtils.str_sql(title),))
        if ret and ret[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_brushtask(brush_id, item):
        """
        新增刷流任务
        """
        if not brush_id:
            sql = '''
                INSERT INTO SITE_BRUSH_TASK(
                    NAME,
                    SITE,
                    FREELEECH,
                    RSS_RULE,
                    REMOVE_RULE,
                    SEED_SIZE,
                    INTEVAL,
                    DOWNLOADER,
                    TRANSFER,
                    DOWNLOAD_COUNT,
                    REMOVE_COUNT,
                    DOWNLOAD_SIZE,
                    UPLOAD_SIZE,
                    STATE,
                    LST_MOD_DATE
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            '''
            return DBHelper().update_by_sql(sql, (item.get('name'),
                                                  item.get('site'),
                                                  item.get('free'),
                                                  str(item.get('rss_rule')),
                                                  str(item.get('remove_rule')),
                                                  item.get('seed_size'),
                                                  item.get('interval'),
                                                  item.get('downloader'),
                                                  item.get('transfer'),
                                                  0,
                                                  0,
                                                  0,
                                                  0,
                                                  item.get('state'),
                                                  time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))))
        else:
            sql = '''
                UPDATE SITE_BRUSH_TASK SET
                    NAME = ?,
                    SITE = ?,
                    FREELEECH = ?,
                    RSS_RULE = ?,
                    REMOVE_RULE = ?,
                    SEED_SIZE = ?,
                    INTEVAL = ?,
                    DOWNLOADER = ?,
                    TRANSFER = ?,
                    STATE = ?,
                    LST_MOD_DATE = ?
                WHERE ID = ?
            '''
            return DBHelper().update_by_sql(sql, (item.get('name'),
                                                  item.get('site'),
                                                  item.get('free'),
                                                  str(item.get('rss_rule')),
                                                  str(item.get('remove_rule')),
                                                  item.get('seed_size'),
                                                  item.get('interval'),
                                                  item.get('downloader'),
                                                  item.get('transfer'),
                                                  item.get('state'),
                                                  time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                                                  brush_id))

    @staticmethod
    def delete_brushtask(brush_id):
        """
        删除刷流任务
        """
        sql = "DELETE FROM SITE_BRUSH_TASK WHERE ID = ?"
        DBHelper().update_by_sql(sql, (brush_id,))
        sql = "DELETE FROM SITE_BRUSH_TORRENTS WHERE TASK_ID = ?"
        DBHelper().update_by_sql(sql, (brush_id,))

    @staticmethod
    def get_brushtasks(brush_id=None):
        """
        查询刷流任务
        """
        if brush_id:
            sql = "SELECT T.ID,T.NAME,T.SITE,'',T.INTEVAL,T.STATE,T.DOWNLOADER,T.TRANSFER," \
                  "T.FREELEECH,T.RSS_RULE,T.REMOVE_RULE,T.SEED_SIZE," \
                  "T.DOWNLOAD_COUNT,T.REMOVE_COUNT,T.DOWNLOAD_SIZE,T.UPLOAD_SIZE,T.LST_MOD_DATE,D.NAME " \
                  "FROM SITE_BRUSH_TASK T " \
                  "LEFT JOIN SITE_BRUSH_DOWNLOADERS D ON D.ID = T.DOWNLOADER " \
                  "WHERE T.ID = ?"
            return DBHelper().select_by_sql(sql, (brush_id,))
        else:
            sql = "SELECT T.ID,T.NAME,T.SITE,'',T.INTEVAL,T.STATE,T.DOWNLOADER,T.TRANSFER," \
                  "T.FREELEECH,T.RSS_RULE,T.REMOVE_RULE,T.SEED_SIZE," \
                  "T.DOWNLOAD_COUNT,T.REMOVE_COUNT,T.DOWNLOAD_SIZE,T.UPLOAD_SIZE,T.LST_MOD_DATE,D.NAME " \
                  "FROM SITE_BRUSH_TASK T " \
                  "LEFT JOIN SITE_BRUSH_DOWNLOADERS D ON D.ID = T.DOWNLOADER "
            return DBHelper().select_by_sql(sql)

    @staticmethod
    def get_brushtask_totalsize(brush_id):
        """
        查询刷流任务总体积
        """
        if not brush_id:
            return 0
        sql = "SELECT SUM(CAST(S.TORRENT_SIZE AS DECIMAL)) FROM SITE_BRUSH_TORRENTS S WHERE S.TASK_ID = ? AND S.DOWNLOAD_ID <> '0'"
        ret = DBHelper().select_by_sql(sql, (brush_id,))
        if ret and ret[0][0]:
            return int(ret[0][0])
        else:
            return 0

    @staticmethod
    def add_brushtask_download_count(brush_id):
        """
        增加刷流下载数
        """
        if not brush_id:
            return
        sql = "UPDATE SITE_BRUSH_TASK SET DOWNLOAD_COUNT = DOWNLOAD_COUNT + 1, LST_MOD_DATE = ? WHERE ID = ?"
        return DBHelper().update_by_sql(sql,
                                        (time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), brush_id))

    @staticmethod
    def get_brushtask_remove_size(brush_id):
        """
        获取已删除种子的上传量
        """
        if not brush_id:
            return 0
        sql = "SELECT S.TORRENT_SIZE FROM SITE_BRUSH_TORRENTS S WHERE S.TASK_ID = ? AND S.DOWNLOAD_ID = '0'"
        return DBHelper().select_by_sql(sql, (brush_id,))

    @staticmethod
    def add_brushtask_upload_count(brush_id, upload_size, download_size, remove_count):
        """
        更新上传下载量和删除种子数
        """
        if not brush_id:
            return
        delete_upsize = 0
        delete_dlsize = 0
        remove_sizes = SqlHelper.get_brushtask_remove_size(brush_id)
        for remove_size in remove_sizes:
            if not remove_size[0]:
                continue
            if str(remove_size[0]).find(",") != -1:
                sizes = str(remove_size[0]).split(",")
                delete_upsize += int(sizes[0] or 0)
                if len(sizes) > 1:
                    delete_dlsize += int(sizes[1] or 0)
            else:
                delete_upsize += int(remove_size[0])
        sql = "UPDATE SITE_BRUSH_TASK SET REMOVE_COUNT = REMOVE_COUNT + ?, UPLOAD_SIZE = ?, DOWNLOAD_SIZE = ? WHERE ID = ?"
        return DBHelper().update_by_sql(sql,
                                        (remove_count, int(upload_size) + delete_upsize,
                                         int(download_size) + delete_dlsize,
                                         brush_id))

    @staticmethod
    def insert_brushtask_torrent(brush_id, title, enclosure, downloader, download_id, size):
        """
        增加刷流下载的种子信息
        """
        if not brush_id:
            return
        sql = '''
            INSERT INTO SITE_BRUSH_TORRENTS(
                TASK_ID,
                TORRENT_NAME,
                TORRENT_SIZE,
                ENCLOSURE,
                DOWNLOADER,
                DOWNLOAD_ID,
                LST_MOD_DATE
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?
            )
        '''
        if SqlHelper.is_brushtask_torrent_exists(brush_id, title, enclosure):
            return False
        return DBHelper().update_by_sql(sql, (brush_id,
                                              title,
                                              size,
                                              enclosure,
                                              downloader,
                                              download_id,
                                              time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))))

    @staticmethod
    def get_brushtask_torrents(brush_id):
        """
        查询刷流任务所有种子
        """
        if not brush_id:
            return []
        sql = "SELECT ID,TASK_ID,TORRENT_NAME,TORRENT_SIZE,ENCLOSURE,DOWNLOADER,DOWNLOAD_ID,LST_MOD_DATE " \
              "FROM SITE_BRUSH_TORRENTS " \
              "WHERE TASK_ID = ? " \
              "AND DOWNLOAD_ID <> '0'"
        return DBHelper().select_by_sql(sql, (brush_id,))

    @staticmethod
    def is_brushtask_torrent_exists(brush_id, title, enclosure):
        """
        查询刷流任务种子是否已存在
        """
        if not brush_id:
            return False
        sql = "SELECT COUNT(1) FROM SITE_BRUSH_TORRENTS WHERE TASK_ID = ? AND TORRENT_NAME = ? AND ENCLOSURE = ?"
        ret = DBHelper().select_by_sql(sql, (brush_id, title, enclosure))
        if ret and ret[0][0] > 0:
            return True
        else:
            return False

    @staticmethod
    def update_brushtask_torrent_state(ids: list):
        """
        更新刷流种子的状态
        """
        if not ids:
            return
        sql = "UPDATE SITE_BRUSH_TORRENTS SET TORRENT_SIZE = ?, DOWNLOAD_ID = '0' WHERE TASK_ID = ? AND DOWNLOAD_ID = ?"
        return DBHelper().update_by_sql_batch(sql, ids)

    @staticmethod
    def delete_brushtask_torrent(brush_id, download_id):
        """
        删除刷流种子记录
        """
        if not download_id or not brush_id:
            return
        sql = "DELETE FROM SITE_BRUSH_TORRENTS WHERE TASK_ID = ? AND DOWNLOAD_ID = ?"
        return DBHelper().update_by_sql(sql, (brush_id, download_id))

    @staticmethod
    def get_user_downloaders(did=None):
        """
        查询自定义下载器
        """
        if did:
            sql = "SELECT ID,NAME,TYPE,HOST,PORT,USERNAME,PASSWORD,SAVE_DIR,NOTE FROM SITE_BRUSH_DOWNLOADERS WHERE ID = ?"
            return DBHelper().select_by_sql(sql, (did,))
        else:
            sql = "SELECT ID,NAME,TYPE,HOST,PORT,USERNAME,PASSWORD,SAVE_DIR,NOTE FROM SITE_BRUSH_DOWNLOADERS"
            return DBHelper().select_by_sql(sql)

    @staticmethod
    def update_user_downloader(did, name, dtype, user_config, note):
        """
        新增自定义下载器
        """
        if did:
            sql = "UPDATE SITE_BRUSH_DOWNLOADERS SET NAME=?, TYPE=?, HOST=?, PORT=?, USERNAME=?, PASSWORD=?, SAVE_DIR=?, NOTE=? " \
                  "WHERE ID=?"
            return DBHelper().update_by_sql(sql, (StringUtils.str_sql(name),
                                                  dtype,
                                                  StringUtils.str_sql(user_config.get("host")),
                                                  StringUtils.str_sql(user_config.get("port")),
                                                  StringUtils.str_sql(user_config.get("username")),
                                                  StringUtils.str_sql(user_config.get("password")),
                                                  StringUtils.str_sql(user_config.get("save_dir")),
                                                  StringUtils.str_sql(note),
                                                  did))
        else:
            sql = "INSERT INTO SITE_BRUSH_DOWNLOADERS (NAME,TYPE,HOST,PORT,USERNAME,PASSWORD,SAVE_DIR,NOTE)" \
                  "VALUES (?,?,?,?,?,?,?,?)"
            return DBHelper().update_by_sql(sql, (StringUtils.str_sql(name),
                                                  dtype,
                                                  StringUtils.str_sql(user_config.get("host")),
                                                  StringUtils.str_sql(user_config.get("port")),
                                                  StringUtils.str_sql(user_config.get("username")),
                                                  StringUtils.str_sql(user_config.get("password")),
                                                  StringUtils.str_sql(user_config.get("save_dir")),
                                                  StringUtils.str_sql(note)))

    @staticmethod
    def delete_user_downloader(did):
        """
        删除自定义下载器
        """
        sql = "DELETE FROM SITE_BRUSH_DOWNLOADERS WHERE ID = ?"
        return DBHelper().update_by_sql(sql, (did,))

    @staticmethod
    def add_filter_group(name, default='N'):
        """
        新增规则组
        """
        if default == 'Y':
            SqlHelper.set_default_filtergroup(0)
        sql = "INSERT INTO CONFIG_FILTER_GROUP (GROUP_NAME, IS_DEFAULT) VALUES (?, ?)"
        DBHelper().update_by_sql(sql, (StringUtils.str_sql(name), default))
        return True

    @staticmethod
    def set_default_filtergroup(groupid):
        """
        设置默认的规则组
        """
        sql = "UPDATE CONFIG_FILTER_GROUP SET IS_DEFAULT = 'Y' WHERE ID = ?"
        DBHelper().update_by_sql(sql, (groupid,))
        sql = "UPDATE CONFIG_FILTER_GROUP SET IS_DEFAULT = 'N' WHERE ID <> ?"
        return DBHelper().update_by_sql(sql, (groupid,))

    @staticmethod
    def delete_filtergroup(groupid):
        """
        删除规则组
        """
        sql = "DELETE FROM CONFIG_FILTER_RULES WHERE GROUP_ID = ?"
        DBHelper().update_by_sql(sql, (groupid,))
        sql = "DELETE FROM CONFIG_FILTER_GROUP WHERE ID = ?"
        return DBHelper().update_by_sql(sql, (groupid,))

    @staticmethod
    def delete_filterrule(ruleid):
        """
        删除规则
        """
        sql = "DELETE FROM CONFIG_FILTER_RULES WHERE ID = ?"
        return DBHelper().update_by_sql(sql, (ruleid,))

    @staticmethod
    def insert_filter_rule(ruleid, item):
        """
        新增规则
        """
        if ruleid:
            sql = "UPDATE CONFIG_FILTER_RULES " \
                  "SET ROLE_NAME=?,PRIORITY=?,INCLUDE=?,EXCLUDE=?,SIZE_LIMIT=?,NOTE=?" \
                  "WHERE ID=?"
            return DBHelper().update_by_sql(sql, (item.get("name"),
                                                  item.get("pri"),
                                                  item.get("include"),
                                                  item.get("exclude"),
                                                  item.get("size"),
                                                  item.get("free"),
                                                  ruleid))
        else:
            sql = "INSERT INTO CONFIG_FILTER_RULES " \
                  "(GROUP_ID, ROLE_NAME, PRIORITY, INCLUDE, EXCLUDE, SIZE_LIMIT, NOTE)" \
                  "VALUES (?, ?, ?, ?, ?, ?, ?)"
            return DBHelper().update_by_sql(sql, (item.get("group"),
                                                  item.get("name"),
                                                  item.get("pri"),
                                                  item.get("include"),
                                                  item.get("exclude"),
                                                  item.get("size"),
                                                  item.get("free")))

    @staticmethod
    def get_userrss_tasks(taskid=None):
        if taskid:
            return DBHelper().select_by_sql(
                "SELECT ID,NAME,ADDRESS,PARSER,INTERVAL,USES,INCLUDE,EXCLUDE,FILTER,UPDATE_TIME,PROCESS_COUNT,STATE,NOTE "
                "FROM CONFIG_USER_RSS "
                "WHERE ID = ?", (taskid,))
        else:
            return DBHelper().select_by_sql(
                "SELECT ID,NAME,ADDRESS,PARSER,INTERVAL,USES,INCLUDE,EXCLUDE,FILTER,UPDATE_TIME,PROCESS_COUNT,STATE,NOTE "
                "FROM CONFIG_USER_RSS")

    @staticmethod
    def delete_userrss_task(tid):
        if not tid:
            return False
        return DBHelper().update_by_sql(
            "DELETE FROM CONFIG_USER_RSS WHERE ID = ?", (tid,))

    @staticmethod
    def update_userrss_task_info(tid, count):
        if not tid:
            return False
        return DBHelper().update_by_sql(
            "UPDATE CONFIG_USER_RSS SET PROCESS_COUNT = PROCESS_COUNT + ?, UPDATE_TIME = ? WHERE ID = ?",
            (count, time.strftime('%Y-%m-%d %H:%M:%S',
                                  time.localtime(time.time())), tid))

    @staticmethod
    def update_userrss_task(item):
        if item.get("id") and SqlHelper.get_userrss_tasks(item.get("id")):
            return DBHelper().update_by_sql("UPDATE CONFIG_USER_RSS "
                                            "SET NAME=?,ADDRESS=?,PARSER=?,INTERVAL=?,USES=?,INCLUDE=?,EXCLUDE=?,FILTER=?,UPDATE_TIME=?,STATE=?,NOTE=?"
                                            "WHERE ID=?", (item.get("name"),
                                                           item.get("address"),
                                                           item.get("parser"),
                                                           item.get("interval"),
                                                           item.get("uses"),
                                                           item.get("include"),
                                                           item.get("exclude"),
                                                           item.get("filterrule"),
                                                           time.strftime('%Y-%m-%d %H:%M:%S',
                                                                         time.localtime(time.time())),
                                                           item.get("state"),
                                                           item.get("note"),
                                                           item.get("id")))
        else:
            return DBHelper().update_by_sql("INSERT INTO CONFIG_USER_RSS"
                                            "(NAME,ADDRESS,PARSER,INTERVAL,USES,INCLUDE,EXCLUDE,FILTER,UPDATE_TIME,PROCESS_COUNT,STATE,NOTE) "
                                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (item.get("name"),
                                                                                 item.get("address"),
                                                                                 item.get("parser"),
                                                                                 item.get("interval"),
                                                                                 item.get("uses"),
                                                                                 item.get("include"),
                                                                                 item.get("exclude"),
                                                                                 item.get("filterrule"),
                                                                                 time.strftime('%Y-%m-%d %H:%M:%S',
                                                                                               time.localtime(
                                                                                                   time.time())),
                                                                                 "0",
                                                                                 item.get("state"),
                                                                                 item.get("note")))

    @staticmethod
    def get_userrss_parser(pid=None):
        if pid:
            return DBHelper().select_by_sql(
                "SELECT ID,NAME,TYPE,FORMAT,PARAMS,NOTE FROM CONFIG_RSS_PARSER WHERE ID = ?", (pid,))
        else:
            return DBHelper().select_by_sql(
                "SELECT ID,NAME,TYPE,FORMAT,PARAMS,NOTE FROM CONFIG_RSS_PARSER")

    @staticmethod
    def delete_userrss_parser(pid):
        if not pid:
            return False
        return DBHelper().update_by_sql(
            "DELETE FROM CONFIG_RSS_PARSER WHERE ID = ?", (pid,))

    @staticmethod
    def update_userrss_parser(item):
        if not item:
            return False
        if item.get("id") and SqlHelper.get_userrss_parser(item.get("id")):
            return DBHelper().update_by_sql("UPDATE CONFIG_RSS_PARSER "
                                            "SET NAME=?,TYPE=?,FORMAT=?,PARAMS=? "
                                            "WHERE ID=?", (item.get("name"),
                                                           item.get("type"),
                                                           item.get("format"),
                                                           item.get("params"),
                                                           item.get("id")))
        else:
            return DBHelper().update_by_sql("INSERT INTO CONFIG_RSS_PARSER(NAME, TYPE, FORMAT, PARAMS) "
                                            "VALUES (?,?,?,?)", (item.get("name"),
                                                                 item.get("type"),
                                                                 item.get("format"),
                                                                 item.get("params")))

    @staticmethod
    def excute(sql):
        return DBHelper().update_by_sql(sql)
