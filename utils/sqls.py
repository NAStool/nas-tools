import datetime
import os.path
import time
from enum import Enum

from rmt.meta.metabase import MetaBase
from utils.db_helper import update_by_sql, select_by_sql, update_by_sql_batch
from utils.functions import str_filesize, xstr, str_sql
from utils.types import MediaType, RmtMode


# 将返回信息插入数据库
def insert_search_results(media_items: list):
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
          "UPLOAD_VOLUME_FACTOR," \
          "DOWNLOAD_VOLUME_FACTOR) VALUES (" \
          " ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
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
                str_sql(media_item.org_string),
                str_sql(media_item.enclosure),
                str_sql(media_item.description),
                mtype,
                str_sql(media_item.title) or str_sql(media_item.get_name()),
                xstr(media_item.year),
                media_item.get_season_string(),
                media_item.get_episode_string(),
                media_item.get_season_episode_string(),
                media_item.vote_average or "0",
                media_item.get_backdrop_path(default=False),
                str_sql(media_item.poster_path),
                str_sql(media_item.tmdb_id),
                str_sql(media_item.overview),
                media_item.get_resource_type_string(),
                media_item.res_order,
                str_filesize(int(media_item.size)),
                media_item.seeders,
                media_item.peers,
                media_item.site,
                media_item.site_order,
                str_sql(media_item.page_url),
                media_item.upload_volume_factor,
                media_item.download_volume_factor
            )
        )
    return update_by_sql_batch(sql, data_list)


# 根据ID从数据库中查询检索结果的一条记录
def get_search_result_by_id(dl_id):
    sql = "SELECT ENCLOSURE,TITLE,YEAR,SEASON,EPISODE,VOTE,IMAGE,TYPE,TORRENT_NAME,DESCRIPTION,SIZE,TMDBID,POSTER,OVERVIEW,SITE,UPLOAD_VOLUME_FACTOR,DOWNLOAD_VOLUME_FACTOR" \
          " FROM SEARCH_RESULT_INFO" \
          " WHERE ID = ?"
    return select_by_sql(sql, (dl_id,))


# 查询检索结果的所有记录
def get_search_results():
    sql = "SELECT ID,TITLE||' ('||YEAR||') '||ES_STRING,RES_TYPE,SIZE,SEEDERS," \
          "ENCLOSURE,SITE,YEAR,ES_STRING,IMAGE,TYPE,VOTE*1,TORRENT_NAME,DESCRIPTION,TMDBID,POSTER,OVERVIEW,PAGEURL,OTHERINFO,UPLOAD_VOLUME_FACTOR,DOWNLOAD_VOLUME_FACTOR" \
          " FROM SEARCH_RESULT_INFO"
    return select_by_sql(sql)


# 查询RSS是否处理过，根据链接
def is_torrent_rssd_by_url(url):
    sql = "SELECT 1 FROM RSS_TORRENTS WHERE ENCLOSURE = ?"
    ret = select_by_sql(sql, (url,))
    if not ret:
        return False
    if len(ret) > 0:
        return True
    return False


# 查询RSS是否处理过，根据名称
def is_torrent_rssd(media_info: MetaBase):
    if not media_info:
        return True
    if media_info.type == MediaType.MOVIE:
        sql = "SELECT COUNT(1) FROM RSS_TORRENTS WHERE TITLE = ? AND YEAR = ?"
        rets = select_by_sql(sql, (str_sql(media_info.title), str_sql(media_info.year)))

    else:
        sql = "SELECT COUNT(1) FROM RSS_TORRENTS WHERE TITLE = ? AND YEAR = ? AND SEASON = ? AND EPISODE = ?"

        rets = select_by_sql(sql, (str_sql(media_info.title),
                                   str_sql(media_info.year),
                                   media_info.get_season_string(),
                                   media_info.get_episode_string()))

    if rets and rets[0][0] > 0:
        return True
    else:
        return False


# 删除所有搜索的记录
def delete_all_search_torrents():
    return update_by_sql("DELETE FROM SEARCH_RESULT_INFO")


# 将RSS的记录插入数据库
def insert_rss_torrents(media_info: MetaBase):
    sql = "INSERT INTO RSS_TORRENTS(TORRENT_NAME, ENCLOSURE, TYPE, TITLE, YEAR, SEASON, EPISODE) " \
          "VALUES (?, ?, ?, ?, ?, ?, ?)"
    return update_by_sql(sql, (str_sql(media_info.org_string),
                               media_info.enclosure,
                               media_info.type.value,
                               str_sql(media_info.title),
                               str_sql(media_info.year),
                               media_info.get_season_string(),
                               media_info.get_episode_string()))


# 将豆瓣的数据插入数据库
def insert_douban_media_state(media: MetaBase, state):
    if not media.year:
        sql = "DELETE FROM DOUBAN_MEDIAS WHERE NAME = ?"
        update_by_sql(sql, (str_sql(media.get_name()),))
    else:
        sql = "DELETE FROM DOUBAN_MEDIAS WHERE NAME = ? AND YEAR = ?"
        update_by_sql(sql, (str_sql(media.get_name()), str_sql(media.year)))

    sql = "INSERT INTO DOUBAN_MEDIAS(NAME, YEAR, TYPE, RATING, IMAGE, STATE) VALUES (?, ?, ?, ?, ?, ?)"
    # 再插入
    return update_by_sql(sql, (str_sql(media.get_name()),
                               str_sql(media.year),
                               media.type.value,
                               media.vote_average,
                               str_sql(media.poster_path),
                               state))


# 标记豆瓣数据的状态
def update_douban_media_state(media: MetaBase, state):
    sql = "UPDATE DOUBAN_MEDIAS SET STATE = ? WHERE NAME = ? AND YEAR = ?"
    return update_by_sql(sql, (state, str_sql(media.title), str_sql(media.year)))


# 查询未检索的豆瓣数据
def get_douban_search_state(title, year):
    sql = "SELECT STATE FROM DOUBAN_MEDIAS WHERE NAME = ? AND YEAR = ?"
    return select_by_sql(sql, (str_sql(title), str_sql(year)))


# 查询识别转移记录
def is_transfer_history_exists(file_path, file_name, title, se):
    if not file_path:
        return False
    sql = "SELECT COUNT(1) FROM TRANSFER_HISTORY WHERE FILE_PATH = ? AND FILE_NAME = ? AND TITLE = ? AND SE = ?"
    ret = select_by_sql(sql, (str_sql(file_path), str_sql(file_name), str_sql(title), str_sql(se)))
    if ret and ret[0][0] > 0:
        return True
    else:
        return False


# 插入识别转移记录
def insert_transfer_history(in_from: Enum, rmt_mode: RmtMode, in_path, dest, media_info: MetaBase):
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
    if is_transfer_history_exists(file_path, file_name, media_info.title, media_info.get_season_string()):
        return True
    timestr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    sql = "INSERT INTO TRANSFER_HISTORY" \
          "(SOURCE, MODE, TYPE, FILE_PATH, FILE_NAME, TITLE, CATEGORY, YEAR, SE, DEST, DATE)" \
          " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    return update_by_sql(sql, (in_from.value,
                               rmt_mode.value,
                               media_info.type.value,
                               str_sql(file_path),
                               str_sql(file_name),
                               str_sql(media_info.title),
                               media_info.category,
                               str_sql(media_info.year),
                               media_info.get_season_string(),
                               dest,
                               timestr))


# 查询识别转移记录
def get_transfer_history(search, page, rownum):
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
        return select_by_sql(count_sql, (search, search)), select_by_sql(sql, (search, search, rownum, begin_pos))
    else:
        count_sql = "SELECT COUNT(1) FROM TRANSFER_HISTORY"
        sql = "SELECT SOURCE, MODE, TYPE, FILE_NAME, TITLE, CATEGORY, YEAR, SE, DEST, DATE, ID" \
              " FROM TRANSFER_HISTORY" \
              " ORDER BY DATE DESC LIMIT ? OFFSET ?"
    return select_by_sql(count_sql), select_by_sql(sql, (rownum, begin_pos))


# 根据logid查询PATH
def get_transfer_path_by_id(logid):
    sql = "SELECT FILE_PATH, FILE_NAME, DEST, TITLE, CATEGORY, YEAR, SE, TYPE FROM TRANSFER_HISTORY WHERE ID = ?"
    return select_by_sql(sql, (logid,))


# 根据logid删除记录
def delete_transfer_log_by_id(logid):
    sql = "DELETE FROM TRANSFER_HISTORY WHERE ID = ?"
    return update_by_sql(sql, (logid,))


# 查询未识别的记录列表
def get_transfer_unknown_paths():
    sql = "SELECT ID, PATH, DEST FROM TRANSFER_UNKNOWN WHERE STATE = 'N'"
    return select_by_sql(sql)


# 更新未识别记录为识别
def update_transfer_unknown_state(path):
    if not path:
        return False
    path = os.path.normpath(path)
    sql = "UPDATE TRANSFER_UNKNOWN SET STATE = 'Y' WHERE PATH = ?"
    return update_by_sql(sql, (str_sql(path),))


# 删除未识别记录
def delete_transfer_unknown(tid):
    if not tid:
        return False
    sql = "DELETE FROM TRANSFER_UNKNOWN WHERE ID = ?"
    return update_by_sql(sql, (tid,))


# 查询未识别记录
def get_unknown_path_by_id(tid):
    if not tid:
        return False
    sql = "SELECT PATH,DEST FROM TRANSFER_UNKNOWN WHERE ID = ?"
    return select_by_sql(sql, (tid,))


# 查询未识别记录是否存在
def is_transfer_unknown_exists(path):
    if not path:
        return False
    path = os.path.normpath(path)
    sql = "SELECT COUNT(1) FROM TRANSFER_UNKNOWN WHERE PATH = ?"
    ret = select_by_sql(sql, (str_sql(path),))
    if ret and ret[0][0] > 0:
        return True
    else:
        return False


# 插入未识别记录
def insert_transfer_unknown(path, dest):
    if not path:
        return False
    if is_transfer_unknown_exists(path):
        return False
    else:
        path = os.path.normpath(path)
        if dest:
            dest = os.path.normpath(dest)
        else:
            dest = ""
        sql = "INSERT INTO TRANSFER_UNKNOWN(PATH, DEST, STATE) VALUES (?, ?, ?)"
        return update_by_sql(sql, (str_sql(path), str_sql(dest), 'N'))


# 查询是否为黑名单
def is_transfer_in_blacklist(path):
    if not path:
        return False
    path = os.path.normpath(path)
    sql = "SELECT COUNT(1) FROM TRANSFER_BLACKLIST WHERE PATH = ?"
    ret = select_by_sql(sql, (str_sql(path),))
    if ret and ret[0][0] > 0:
        return True
    else:
        return False


# 查询是否为黑名单
def is_transfer_notin_blacklist(path):
    return not is_transfer_in_blacklist(path)


# 插入黑名单记录
def insert_transfer_blacklist(path):
    if not path:
        return False
    if is_transfer_in_blacklist(path):
        return False
    else:
        path = os.path.normpath(path)
        sql = "INSERT INTO TRANSFER_BLACKLIST(PATH) VALUES (?)"
        return update_by_sql(sql, (str_sql(path),))


# 查询所有站点信息
def get_config_site():
    return select_by_sql(
        "SELECT ID,NAME,PRI,RSSURL,SIGNURL,COOKIE,INCLUDE,EXCLUDE,SIZE,NOTE"
        " FROM CONFIG_SITE"
        " ORDER BY CAST(PRI AS DECIMAL) ASC")


# 查询1个站点信息
def get_site_by_id(tid):
    return select_by_sql(
        "SELECT ID,NAME,PRI,RSSURL,SIGNURL,COOKIE,INCLUDE,EXCLUDE,SIZE,NOTE FROM CONFIG_SITE WHERE ID = ?", (tid,))


# 插入站点信息
def insert_config_site(name, site_pri, rssurl, signurl, cookie, include, exclude, size, note):
    if not name:
        return
    sql = "INSERT INTO CONFIG_SITE(NAME,PRI,RSSURL,SIGNURL,COOKIE,INCLUDE,EXCLUDE,SIZE,NOTE) VALUES " \
          "(?, ?, ?, ?, ?, ?, ?, ?, ?)"
    return update_by_sql(sql, (str_sql(name),
                               str_sql(site_pri),
                               str_sql(rssurl),
                               str_sql(signurl),
                               str_sql(cookie),
                               str_sql(include),
                               str_sql(exclude),
                               str_sql(size),
                               str_sql(note)))


# 删除站点信息
def delete_config_site(tid):
    if not tid:
        return False
    return update_by_sql("DELETE FROM CONFIG_SITE WHERE ID = ?", (tid,))


# 更新站点信息
def update_config_site(tid, name, site_pri, rssurl, signurl, cookie, include, exclude, size, note):
    delete_config_site(tid)
    insert_config_site(name, site_pri, rssurl, signurl, cookie, include, exclude, size, note)


# 查询搜索过滤规则
def get_config_search_rule():
    return select_by_sql("SELECT INCLUDE,EXCLUDE,NOTE,SIZE FROM CONFIG_SEARCH_RULE")


# 更新搜索过滤规则
def update_config_search_rule(include, exclude, note, size):
    update_by_sql("DELETE FROM CONFIG_SEARCH_RULE")
    return update_by_sql(
        "INSERT INTO CONFIG_SEARCH_RULE(INCLUDE,EXCLUDE,NOTE,SIZE) VALUES "
        "(?, ?, ?, ?)", (str_sql(include),
                         str_sql(exclude),
                         str_sql(note),
                         str_sql(size)))


# 查询RSS全局过滤规则
def get_config_rss_rule():
    return select_by_sql("SELECT ID,NOTE FROM CONFIG_RSS_RULE")


# 更新RSS全局过滤规则
def update_config_rss_rule(note):
    update_by_sql("DELETE FROM CONFIG_RSS_RULE")
    return update_by_sql("INSERT INTO CONFIG_RSS_RULE(NOTE) VALUES (?)", (str_sql(note),))


# 查询订阅电影信息
def get_rss_movies(state=None, rssid=None):
    if rssid:
        sql = "SELECT NAME,YEAR,TMDBID,IMAGE,DESC,STATE,ID FROM RSS_MOVIES WHERE ID = ?"
        return select_by_sql(sql, (rssid,))
    else:
        if not state:
            sql = "SELECT NAME,YEAR,TMDBID,IMAGE,DESC,STATE,ID FROM RSS_MOVIES"
            return select_by_sql(sql)
        else:
            sql = "SELECT NAME,YEAR,TMDBID,IMAGE,DESC,STATE,ID FROM RSS_MOVIES WHERE STATE = ?"
            return select_by_sql(sql, (state,))


# 获取订阅电影ID
def get_rss_movie_id(title, year):
    if not title:
        return ""
    sql = "SELECT ID FROM RSS_MOVIES WHERE NAME=? AND YEAR = ?"
    ret = select_by_sql(sql, (str_sql(title), str_sql(year)))
    if ret:
        return ret[0][0]
    return ""


# 获取订阅电影站点
def get_rss_movie_sites(rssid):
    if not rssid:
        return ""
    sql = "SELECT DESC FROM RSS_MOVIES WHERE ID = ?"
    ret = select_by_sql(sql, (rssid,))
    if ret:
        return ret[0][0]
    return ""


# 更新订阅电影的TMDBID
def update_rss_movie_tmdbid(rid, tmdbid):
    if not tmdbid:
        return False
    sql = "UPDATE RSS_MOVIES SET TMDBID = ? WHERE ID = ?"
    return update_by_sql(sql, (tmdbid, rid))


# 判断RSS电影是否存在
def is_exists_rss_movie(title, year):
    if not title:
        return False
    sql = "SELECT COUNT(1) FROM RSS_MOVIES WHERE NAME=? AND YEAR = ?"
    ret = select_by_sql(sql, (str_sql(title), str_sql(year)))
    if ret and ret[0][0] > 0:
        return True
    else:
        return False


# 新增RSS电影
def insert_rss_movie(media_info: MetaBase, state='D', sites: list = None, search_sites: list = None):
    if not media_info:
        return False
    if not media_info.title:
        return False
    if is_exists_rss_movie(media_info.title, media_info.year):
        return True
    sql = "INSERT INTO RSS_MOVIES(NAME,YEAR,TMDBID,IMAGE,DESC,STATE) VALUES (?, ?, ?, ?, ?, ?)"
    return update_by_sql(sql, (str_sql(media_info.title),
                               str_sql(media_info.year),
                               str_sql(media_info.tmdb_id),
                               str_sql(media_info.get_backdrop_path()),
                               "|".join(sites or []) + "|#|" + "|".join(search_sites or []),
                               state))


# 删除RSS电影
def delete_rss_movie(title, year, rssid=None):
    if not title and not rssid:
        return False
    if rssid:
        sql = "DELETE FROM RSS_MOVIES WHERE ID = ?"
        return update_by_sql(sql, (rssid,))
    else:
        sql = "DELETE FROM RSS_MOVIES WHERE NAME = ? AND YEAR = ?"
        return update_by_sql(sql, (str_sql(title), str_sql(year)))


# 更新电影订阅状态
def update_rss_movie_state(title, year, state):
    if not title:
        return False
    sql = "UPDATE RSS_MOVIES SET STATE = ? WHERE NAME = ? AND YEAR = ?"
    return update_by_sql(sql, (state, str_sql(title), str_sql(year)))


# 查询订阅电视剧信息
def get_rss_tvs(state=None, rssid=None):
    if rssid:
        sql = "SELECT NAME,YEAR,SEASON,TMDBID,IMAGE,DESC,TOTAL,LACK,STATE" \
              ",((CAST(TOTAL AS FLOAT)-CAST(LACK AS FLOAT))/CAST(TOTAL AS FLOAT))*100,ID" \
              " FROM RSS_TVS" \
              " WHERE ID = ?"
        return select_by_sql(sql, (rssid,))
    else:
        if not state:
            sql = "SELECT NAME,YEAR,SEASON,TMDBID,IMAGE,DESC,TOTAL,LACK,STATE" \
                  ",((CAST(TOTAL AS FLOAT)-CAST(LACK AS FLOAT))/CAST(TOTAL AS FLOAT))*100,ID" \
                  " FROM RSS_TVS"
            return select_by_sql(sql)
        else:
            sql = "SELECT NAME,YEAR,SEASON,TMDBID,IMAGE,DESC,TOTAL,LACK,STATE" \
                  ",((CAST(TOTAL AS FLOAT)-CAST(LACK AS FLOAT))/CAST(TOTAL AS FLOAT))*100,ID" \
                  " FROM RSS_TVS WHERE STATE = ?"
            return select_by_sql(sql, (state,))


# 获取订阅电影ID
def get_rss_tv_id(title, year, season=None):
    if not title:
        return ""
    if season:
        sql = "SELECT ID FROM RSS_TVS WHERE NAME = ? AND YEAR = ? AND SEASON = ?"
        ret = select_by_sql(sql, (str_sql(title), str_sql(year), season))
    else:
        sql = "SELECT ID FROM RSS_TVS WHERE NAME = ? AND YEAR = ?"
        ret = select_by_sql(sql, (str_sql(title), str_sql(year)))
    if ret:
        return ret[0][0]
    return ""


# 获取订阅电视剧站点
def get_rss_tv_sites(rssid):
    if not rssid:
        return ""
    sql = "SELECT DESC FROM RSS_TVS WHERE ID = ?"
    ret = select_by_sql(sql, (rssid,))
    if ret:
        return ret[0][0]
    return ""


# 更新订阅电影的TMDBID
def update_rss_tv_tmdbid(rid, tmdbid):
    if not tmdbid:
        return False
    sql = "UPDATE RSS_TVS SET TMDBID = ? WHERE ID = ?"
    return update_by_sql(sql, (tmdbid, rid))


# 判断RSS电视剧是否存在
def is_exists_rss_tv(title, year, season=None):
    if not title:
        return False
    if season:
        sql = "SELECT COUNT(1) FROM RSS_TVS WHERE NAME = ? AND YEAR = ? AND SEASON = ?"
        ret = select_by_sql(sql, (str_sql(title), str_sql(year), season))
    else:
        sql = "SELECT COUNT(1) FROM RSS_TVS WHERE NAME = ? AND YEAR = ?"
        ret = select_by_sql(sql, (str_sql(title), str_sql(year)))
    if ret and ret[0][0] > 0:
        return True
    else:
        return False


# 新增RSS电视剧
def insert_rss_tv(media_info: MetaBase, total, lack=0, state="D", sites: list = None, search_sites: list = None):
    if not media_info:
        return False
    if not media_info.title:
        return False
    if is_exists_rss_tv(media_info.title, media_info.year, media_info.get_season_string()):
        return True
    sql = "INSERT INTO RSS_TVS(NAME,YEAR,SEASON,TMDBID,IMAGE,DESC,TOTAL,LACK,STATE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"

    return update_by_sql(sql, (str_sql(media_info.title),
                               str_sql(media_info.year),
                               media_info.get_season_string(),
                               str_sql(media_info.tmdb_id),
                               str_sql(media_info.get_backdrop_path()),
                               "|".join(sites or []) + "|#|" + "|".join(search_sites or []),
                               total,
                               lack,
                               state))


# 更新电视剧缺失的集数
def update_rss_tv_lack(title, year, season, lack):
    if not title:
        return False
    sql = "UPDATE RSS_TVS SET LACK=? WHERE NAME = ? AND YEAR = ? AND SEASON = ?"
    return update_by_sql(sql, (lack, str_sql(title), str_sql(year), season))


# 删除RSS电视剧
def delete_rss_tv(title, year, season, rssid=None):
    if not title and not rssid:
        return False
    if rssid:
        sql = "DELETE FROM RSS_TVS WHERE ID = ?"
        return update_by_sql(sql, (rssid,))
    else:
        sql = "DELETE FROM RSS_TVS WHERE NAME = ? AND YEAR = ? AND SEASON = ?"
        return update_by_sql(sql, (str_sql(title), str_sql(year), season))


# 更新电视剧订阅状态
def update_rss_tv_state(title, year, season, state):
    if not title:
        return False
    sql = "UPDATE RSS_TVS SET STATE = ? WHERE NAME = ? AND YEAR = ? AND SEASON = ?"
    return update_by_sql(sql, (state, str_sql(title), str_sql(year), season))


# 查询是否存在同步历史记录
def is_sync_in_history(path, dest):
    if not path:
        return False
    path = os.path.normpath(path)
    dest = os.path.normpath(dest)
    sql = "SELECT COUNT(1) FROM SYNC_HISTORY WHERE PATH = ? AND DEST = ?"
    ret = select_by_sql(sql, (str_sql(path), str_sql(dest)))
    if ret and ret[0][0] > 0:
        return True
    else:
        return False


# 插入黑名单记录
def insert_sync_history(path, src, dest):
    if not path or not dest:
        return False
    if is_sync_in_history(path, dest):
        return False
    else:
        path = os.path.normpath(path)
        src = os.path.normpath(src)
        dest = os.path.normpath(dest)
        sql = "INSERT INTO SYNC_HISTORY(PATH, SRC, DEST) VALUES (?, ?, ?)"
        return update_by_sql(sql, (str_sql(path), str_sql(src), str_sql(dest)))


# 查询用户列表
def get_users():
    sql = "SELECT ID,NAME,PASSWORD,PRIS FROM CONFIG_USERS"
    return select_by_sql(sql)


# 判断用户是否存在
def is_user_exists(name):
    if not name:
        return False
    sql = "SELECT COUNT(1) FROM CONFIG_USERS WHERE NAME = ?"
    ret = select_by_sql(sql, (name,))
    if ret and ret[0][0] > 0:
        return True
    else:
        return False


# 新增用户
def insert_user(name, password, pris):
    if not name or not password:
        return False
    if is_user_exists(name):
        return False
    else:
        sql = "INSERT INTO CONFIG_USERS(NAME,PASSWORD,PRIS) VALUES (?, ?, ?)"
        return update_by_sql(sql, (str_sql(name), str_sql(password), str_sql(pris)))


# 删除用户
def delete_user(name):
    return update_by_sql("DELETE FROM CONFIG_USERS WHERE NAME = ?", (str_sql(name),))


# 查询历史记录统计
def get_transfer_statistics(days=30):
    begin_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    sql = "SELECT TYPE,SUBSTR(DATE, 1, 10),COUNT(1)" \
          " FROM TRANSFER_HISTORY" \
          " WHERE DATE > ? GROUP BY TYPE,SUBSTR(DATE, 1, 10)"
    return select_by_sql(sql, (begin_date,))


# 插入消息中心
def insert_system_message(level, title, content):
    if not level or not title:
        return
    if title:
        title = title.replace("\n", "<br/>")
    if content:
        content = content.replace("\n", "<br/>")
    timestr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    sql = "INSERT INTO MESSAGES(LEVEL, TITLE, CONTENT, DATE) VALUES (?, ?, ?, ?)"
    return update_by_sql(sql, (str_sql(level), str_sql(title), str_sql(content), timestr))


# 查询消息中心
def get_system_messages(num=20, lst_time=None):
    if not lst_time:
        sql = "SELECT ID, LEVEL, TITLE, CONTENT, DATE FROM MESSAGES ORDER BY DATE DESC LIMIT ?"
        return select_by_sql(sql, (num,))
    else:
        sql = "SELECT ID, LEVEL, TITLE, CONTENT, DATE FROM MESSAGES WHERE DATE > ? ORDER BY DATE DESC"
        return select_by_sql(sql, (lst_time,))


# 更新站点用户粒度数据
def update_site_user_statistics(site, username, upload, download, ratio, seeding, leeching, bonus, url, seeding_size=0,
                                user_level="", join_at=""):
    if not site or not url:
        return
    update_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    if not is_site_user_statistics_exists(url):
        sql = "INSERT INTO SITE_USER_STATISTICS(SITE, USERNAME, USER_LEVEL," \
              " JOIN_AT, UPDATE_AT," \
              " UPLOAD, DOWNLOAD, RATIO," \
              " SEEDING, LEECHING, SEEDING_SIZE," \
              " BONUS," \
              " URL) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    else:
        sql = "UPDATE SITE_USER_STATISTICS SET SITE = ?, USERNAME = ?, USER_LEVEL = ?," \
              " JOIN_AT = ?, UPDATE_AT = ?," \
              " UPLOAD = ?, DOWNLOAD = ?, RATIO = ?," \
              " SEEDING = ?, LEECHING = ?, SEEDING_SIZE = ?," \
              " BONUS = ? WHERE URL = ?"

    return update_by_sql(sql, (
            str_sql(site), username, user_level, join_at, update_at, upload, download, ratio, seeding, leeching,
            seeding_size, bonus, url))


# 判断站点用户数据是否存在
def is_site_user_statistics_exists(url):
    if not url:
        return False
    sql = "SELECT COUNT(1) FROM SITE_USER_STATISTICS WHERE URL = ? "
    ret = select_by_sql(sql, (url,))
    if ret and ret[0][0] > 0:
        return True
    else:
        return False


# 查询站点数据历史
def get_site_user_statistics(num=100):
    sql = "SELECT SITE, USERNAME, USER_LEVEL," \
          " JOIN_AT, UPDATE_AT," \
          " UPLOAD, DOWNLOAD, RATIO," \
          " SEEDING, LEECHING, SEEDING_SIZE," \
          " BONUS, URL" \
          " FROM SITE_USER_STATISTICS LIMIT ?"
    return select_by_sql(sql, (num,))


# 判断站点历史数据是否存在
def is_site_statistics_history_exists(url, date):
    if not url or not date:
        return False
    sql = "SELECT COUNT(1) FROM SITE_STATISTICS WHERE URL = ? AND DATE = ?"
    ret = select_by_sql(sql, (url, date))
    if ret and ret[0][0] > 0:
        return True
    else:
        return False


# 插入站点数据
def insert_site_statistics_history(site, upload, download, ratio, url):
    if not site or not url:
        return
    timestr = time.strftime('%Y-%m-%d', time.localtime(time.time()))
    if not is_site_statistics_history_exists(url, timestr):
        sql = "INSERT INTO SITE_STATISTICS(SITE, DATE, UPLOAD, DOWNLOAD, RATIO, URL) VALUES (?, ?, ?, ?, ?, ?)"
        return update_by_sql(sql, (str_sql(site), timestr, upload, download, ratio, url))
    else:
        sql = "UPDATE SITE_STATISTICS SET SITE = ?, UPLOAD = ?, DOWNLOAD = ?, RATIO = ? WHERE URL = ? AND DATE = ?"
        return update_by_sql(sql, (str_sql(site), upload, download, ratio, url, timestr))


# 查询站点数据历史
def get_site_statistics_history(days=30):
    sql = "SELECT DATE, SUM(UPLOAD), SUM(DOWNLOAD) FROM SITE_STATISTICS GROUP BY DATE ORDER BY DATE ASC LIMIT ?"
    return select_by_sql(sql, (days,))


# 查询近期上传下载量
def get_site_statistics_recent_sites(days=7):
    # 查询最大最小日期
    b_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    date_sql = "SELECT MAX(DATE), MIN(DATE) FROM SITE_STATISTICS WHERE DATE > ?"
    date_ret = select_by_sql(date_sql, (b_date,))
    if date_ret:
        total_upload = 0
        total_download = 0
        ret_sites = []
        ret_site_uploads = []
        ret_site_downloads = []
        max_date = date_ret[0][0]
        min_date = date_ret[0][1]
        # 查询开始值
        site_b_data = {}
        sql = "SELECT SITE, SUM(UPLOAD), SUM(DOWNLOAD) FROM SITE_STATISTICS WHERE DATE = ? GROUP BY SITE"
        for ret_b in select_by_sql(sql, (min_date,)):
            site_b_data[ret_b[0]] = {"upload": int(ret_b[1]), "download": int(ret_b[2])}
        # 查询结束值
        for ret_e in select_by_sql(sql, (max_date,)):
            ret_sites.append(ret_e[0])
            if site_b_data.get(ret_e[0]):
                b_upload = site_b_data[ret_e[0]].get("upload")
                if b_upload < int(ret_e[1]):
                    total_upload += int(ret_e[1]) - b_upload
                    ret_site_uploads.append(round((int(ret_e[1]) - b_upload) / 1024 / 1024 / 1024, 1))
                else:
                    ret_site_uploads.append(0)
                b_download = site_b_data[ret_e[0]].get("download")
                if b_download < int(ret_e[2]):
                    total_download += int(ret_e[2]) - b_download
                    ret_site_downloads.append(round((int(ret_e[2]) - b_download) / 1024 / 1024 / 1024, 1))
                else:
                    ret_site_downloads.append(0)
            else:
                ret_site_uploads.append(round(int(ret_e[1]) / 1024 / 1024 / 1024, 1))
                ret_site_downloads.append(round(int(ret_e[2]) / 1024 / 1024 / 1024, 1))

        return total_upload, total_download, ret_sites, ret_site_uploads, ret_site_downloads
    else:
        return 0, 0, [], [], []


# 查询下载历史是否存在
def is_exists_download_history(title, year, mtype=None):
    if not title:
        return False
    if mtype:
        sql = "SELECT COUNT(1) FROM DOWNLOAD_HISTORY WHERE TITLE = ? AND YEAR = ? AND TYPE = ?"
        ret = select_by_sql(sql, (str_sql(title), str_sql(year), mtype))
    else:
        sql = "SELECT COUNT(1) FROM DOWNLOAD_HISTORY WHERE TITLE = ? AND YEAR = ?"
        ret = select_by_sql(sql, (str_sql(title), str_sql(year)))
    if ret and ret[0][0] > 0:
        return True
    else:
        return False


# 新增下载历史
def insert_download_history(media_info: MetaBase):
    if not media_info:
        return False
    if not media_info.title or not media_info.year:
        return False
    if is_exists_download_history(media_info.title, media_info.year, media_info.type.value):
        sql = "UPDATE DOWNLOAD_HISTORY SET TORRENT = ?, ENCLOSURE = ?, DESC = ?, DATE = ?, SITE = ? WHERE TITLE = ? AND YEAR = ? AND TYPE = ?"
        return update_by_sql(sql, (str_sql(media_info.org_string),
                                   str_sql(media_info.enclosure),
                                   str_sql(media_info.description),
                                   time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                                   str_sql(media_info.site),
                                   str_sql(media_info.title),
                                   str_sql(media_info.year),
                                   media_info.type.value,))
    else:
        sql = "INSERT INTO DOWNLOAD_HISTORY(TITLE,YEAR,TYPE,TMDBID,VOTE,POSTER,OVERVIEW,TORRENT,ENCLOSURE,DESC,DATE,SITE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        return update_by_sql(sql, (str_sql(media_info.title),
                                   str_sql(media_info.year),
                                   media_info.type.value,
                                   media_info.tmdb_id,
                                   media_info.vote_average,
                                   str_sql(media_info.poster_path),
                                   str_sql(media_info.overview),
                                   str_sql(media_info.org_string),
                                   str_sql(media_info.enclosure),
                                   str_sql(media_info.description),
                                   time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                                   str_sql(media_info.site),))


# 查询下载历史
def get_download_history(date=None, hid=None, num=100):
    if hid:
        sql = "SELECT ID,TITLE,YEAR,TYPE,TMDBID,VOTE,POSTER,OVERVIEW,TORRENT,ENCLOSURE,DESC,DATE,SITE FROM DOWNLOAD_HISTORY WHERE ID = ?"
        return select_by_sql(sql, (hid,))
    elif date:
        sql = "SELECT ID,TITLE,YEAR,TYPE,TMDBID,VOTE,POSTER,OVERVIEW,TORRENT,ENCLOSURE,DESC,DATE,SITE FROM DOWNLOAD_HISTORY WHERE DATE > ? ORDER BY DATE DESC"
        return select_by_sql(sql, (date,))
    else:
        sql = "SELECT ID,TITLE,YEAR,TYPE,TMDBID,VOTE,POSTER,OVERVIEW,TORRENT,ENCLOSURE,DESC,DATE,SITE FROM DOWNLOAD_HISTORY ORDER BY DATE DESC LIMIT ?"
        return select_by_sql(sql, (num,))


# 根据标题和年份检查是否下载过
def is_media_downloaded(title, year):
    if is_exists_download_history(title, year):
        return True
    sql = "SELECT COUNT(1) FROM TRANSFER_HISTORY WHERE TITLE = ? AND YEAR = ?"
    ret = select_by_sql(sql, (str_sql(title), str_sql(year)))
    if ret and ret[0][0] > 0:
        return True
    else:
        return False
