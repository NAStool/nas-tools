import os.path
import time

from utils.db_helper import update_by_sql, select_by_sql
from utils.functions import str_filesize, xstr, str_sql
from utils.types import MediaType


# 将返回信息插入数据库
def insert_search_results(media_item):
    if media_item.type == MediaType.TV:
        mtype = "TV"
    elif media_item.type == MediaType.MOVIE:
        mtype = "MOV"
    else:
        mtype = "ANI"
    sql = "INSERT INTO SEARCH_TORRENTS(" \
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
          "RES_TYPE," \
          "RES_ORDER," \
          "SIZE," \
          "SEEDERS," \
          "PEERS," \
          "SITE," \
          "SITE_ORDER) VALUES (" \
          "'%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" % (
              str_sql(media_item.org_string),
              media_item.enclosure,
              str_sql(media_item.description),
              mtype,
              media_item.title,
              xstr(media_item.year),
              media_item.get_season_string(),
              media_item.get_episode_string(),
              media_item.get_season_episode_string(),
              media_item.vote_average,
              media_item.get_backdrop_path(),
              media_item.get_resource_type_string(),
              media_item.res_order,
              str_filesize(int(media_item.size)),
              media_item.seeders,
              media_item.peers,
              media_item.site,
              media_item.site_order
          )
    return update_by_sql(sql)


# 根据ID从数据库中查询检索结果的一条记录
def get_search_result_by_id(dl_id):
    sql = "SELECT ENCLOSURE,TITLE,YEAR,SEASON,EPISODE,VOTE,IMAGE,TYPE,TORRENT_NAME,DESCRIPTION,SIZE FROM SEARCH_TORRENTS WHERE ID=%s" % dl_id
    return select_by_sql(sql)


# 查询检索结果的所有记录
def get_search_results():
    sql = "SELECT ID,TITLE||' ('||YEAR||') '||ES_STRING,RES_TYPE,SIZE,SEEDERS,ENCLOSURE,SITE,YEAR,ES_STRING,IMAGE,TYPE,VOTE*1,TORRENT_NAME,DESCRIPTION FROM SEARCH_TORRENTS"
    return select_by_sql(sql)


# 查询RSS是否处理过，根据链接
def is_torrent_rssd_by_url(url):
    sql = "SELECT 1 FROM RSS_TORRENTS WHERE ENCLOSURE = '%s'" % url
    ret = select_by_sql(sql)
    if not ret:
        return False
    if len(ret) > 0:
        return True
    return False


# 查询RSS是否处理过，根据名称
def is_torrent_rssd(media_info):
    if not media_info:
        return True
    if media_info.type == MediaType.MOVIE:
        sql = "SELECT COUNT(1) FROM RSS_TORRENTS WHERE TITLE='%s' AND YEAR='%s'" % (media_info.title, media_info.year)
    else:
        sql = "SELECT COUNT(1) FROM RSS_TORRENTS WHERE TITLE='%s' AND YEAR='%s' AND SEASON='%s' AND EPISODE='%s'" % \
              (media_info.title, media_info.year, media_info.get_season_string(), media_info.get_episode_string())
    rets = select_by_sql(sql)
    if rets and rets[0][0] > 0:
        return True
    else:
        return False


# 删除所有搜索的记录
def delete_all_search_torrents():
    return update_by_sql("DELETE FROM SEARCH_TORRENTS")


# 将RSS的记录插入数据库
def insert_rss_torrents(media_info):
    sql = "INSERT INTO RSS_TORRENTS(TORRENT_NAME, ENCLOSURE, TYPE, TITLE, YEAR, SEASON, EPISODE) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s')" % (
        media_info.title, media_info.enclosure, media_info.type.value, media_info.title, media_info.year,
        media_info.get_season_string(), media_info.get_episode_string())
    return update_by_sql(sql)


# 将豆瓣的数据插入数据库
def insert_douban_media_state(media, state):
    if not media.year:
        sql = "DELETE FROM DOUBAN_MEDIAS WHERE NAME = '%s'" % media.get_name()
    else:
        sql = "DELETE FROM DOUBAN_MEDIAS WHERE NAME = '%s' AND YEAR = '%s'" % (media.get_name(), media.year)
    # 先删除
    update_by_sql(sql)
    sql = "INSERT INTO DOUBAN_MEDIAS(NAME, YEAR, TYPE, RATING, IMAGE, STATE) VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" % (
        media.get_name(), media.year, media.type.value, media.vote_average, media.poster_path, state)
    # 再插入
    return update_by_sql(sql)


# 标记豆瓣数据的状态
def update_douban_media_state(media, state):
    sql = "UPDATE DOUBAN_MEDIAS SET STATE = '%s' WHERE NAME = '%s' AND YEAR = '%s'" % (state, media.title, media.year)
    return update_by_sql(sql)


# 查询未检索的豆瓣数据
def get_douban_search_state(title, year):
    sql = "SELECT STATE FROM DOUBAN_MEDIAS WHERE NAME = '%s' AND YEAR = '%s'" % (title, year)
    return select_by_sql(sql)


# 查询识别转移记录
def is_transfer_history_exists(file_path, file_name, title, se):
    if not file_path:
        return False
    sql = "SELECT COUNT(1) FROM TRANSFER_HISTORY WHERE FILE_PATH='%s' AND FILE_NAME='%s' AND TITLE='%s' AND SE='%s'" % (
        str_sql(file_path), str_sql(file_name), str_sql(title), str_sql(se))
    ret = select_by_sql(sql)
    if ret and ret[0][0] > 0:
        return True
    else:
        return False


# 插入识别转移记录
def insert_transfer_history(in_from, rmt_mode, in_path, dest, media_info):
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
    sql = "INSERT INTO TRANSFER_HISTORY(SOURCE, MODE, TYPE, FILE_PATH, FILE_NAME, TITLE, CATEGORY, YEAR, SE, DEST, DATE) VALUES " \
          "('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')" % (
              in_from.value, rmt_mode.value, media_info.type.value, str_sql(file_path), str_sql(file_name),
              media_info.title,
              media_info.category, media_info.year, media_info.get_season_string(), dest, timestr)
    return update_by_sql(sql)


# 查询识别转移记录
def get_transfer_history(search, page, rownum):
    if page == 1:
        begin_pos = 0
    else:
        begin_pos = (page - 1) * rownum

    if search:
        count_sql = f"SELECT COUNT(1) FROM TRANSFER_HISTORY WHERE FILE_NAME LIKE '%{search}%' OR TITLE LIKE '%{search}%'"
        sql = f"SELECT SOURCE, MODE, TYPE, FILE_NAME, TITLE, CATEGORY, YEAR, SE, DEST, DATE, ID FROM TRANSFER_HISTORY WHERE FILE_NAME LIKE '%{search}%' OR TITLE LIKE '%{search}%' ORDER BY DATE DESC LIMIT {rownum} OFFSET {begin_pos}"
    else:
        count_sql = f"SELECT COUNT(1) FROM TRANSFER_HISTORY"
        sql = f"SELECT SOURCE, MODE, TYPE, FILE_NAME, TITLE, CATEGORY, YEAR, SE, DEST, DATE, ID FROM TRANSFER_HISTORY ORDER BY DATE DESC LIMIT {rownum} OFFSET {begin_pos}"
    return select_by_sql(count_sql), select_by_sql(sql)


# 根据logid查询PATH
def get_transfer_path_by_id(logid):
    sql = f"SELECT FILE_PATH, FILE_NAME, DEST, TITLE, CATEGORY, YEAR, SE, TYPE FROM TRANSFER_HISTORY WHERE ID={logid}"
    return select_by_sql(sql)


# 根据logid删除记录
def delete_transfer_log_by_id(logid):
    sql = f"DELETE FROM TRANSFER_HISTORY WHERE ID={logid}"
    return update_by_sql(sql)


# 查询未识别的记录列表
def get_transfer_unknown_paths():
    sql = f"SELECT ID, PATH, DEST FROM TRANSFER_UNKNOWN WHERE STATE='N'"
    return select_by_sql(sql)


# 更新未识别记录为识别
def update_transfer_unknown_state(path):
    if not path:
        return False
    path = os.path.normpath(path)
    sql = f"UPDATE TRANSFER_UNKNOWN SET STATE='Y' WHERE PATH='{str_sql(path)}'"
    return update_by_sql(sql)


# 删除未识别记录
def delete_transfer_unknown(tid):
    if not tid:
        return False
    sql = f"DELETE FROM TRANSFER_UNKNOWN WHERE ID='{tid}'"
    return update_by_sql(sql)


# 查询未识别记录
def get_unknown_path_by_id(tid):
    if not tid:
        return False
    sql = f"SELECT PATH,DEST FROM TRANSFER_UNKNOWN WHERE ID='{tid}'"
    return select_by_sql(sql)


# 查询未识别记录是否存在
def is_transfer_unknown_exists(path):
    if not path:
        return False
    path = os.path.normpath(path)
    sql = f"SELECT COUNT(1) FROM TRANSFER_UNKNOWN WHERE PATH='{str_sql(path)}'"
    ret = select_by_sql(sql)
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
        sql = f"INSERT INTO TRANSFER_UNKNOWN(PATH, DEST, STATE) VALUES('{str_sql(path)}', '{str_sql(dest)}', 'N')"
        return update_by_sql(sql)


# 查询是否为黑名单
def is_transfer_in_blacklist(path):
    if not path:
        return False
    path = os.path.normpath(path)
    sql = f"SELECT COUNT(1) FROM TRANSFER_BLACKLIST WHERE PATH='{str_sql(path)}'"
    ret = select_by_sql(sql)
    if ret and ret[0][0] > 0:
        return True
    else:
        return False


# 插入黑名单记录
def insert_transfer_blacklist(path):
    if not path:
        return False
    if is_transfer_in_blacklist(path):
        return False
    else:
        path = os.path.normpath(path)
        sql = f"INSERT INTO TRANSFER_BLACKLIST(PATH) VALUES('{str_sql(path)}')"
        return update_by_sql(sql)


# 查询所有站点信息
def get_config_site():
    return select_by_sql(
        "SELECT ID,NAME,PRI,RSSURL,SIGNURL,COOKIE,INCLUDE,EXCLUDE,SIZE,NOTE FROM CONFIG_SITE ORDER BY CAST(PRI AS DECIMAL) ASC")


# 查询1个站点信息
def get_site_by_id(tid):
    return select_by_sql(
        "SELECT ID,NAME,PRI,RSSURL,SIGNURL,COOKIE,INCLUDE,EXCLUDE,SIZE,NOTE FROM CONFIG_SITE WHERE ID='%s'" % tid)


# 插入站点信息
def insert_config_site(name, site_pri, rssurl, signurl, cookie, include, exclude, size, note):
    if not name:
        return
    sql = "INSERT INTO CONFIG_SITE(NAME,PRI,RSSURL,SIGNURL,COOKIE,INCLUDE,EXCLUDE,SIZE,NOTE) VALUES " \
          "('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s')" % (
              str_sql(name),
              str_sql(site_pri),
              str_sql(rssurl),
              str_sql(signurl),
              str_sql(cookie),
              str_sql(include),
              str_sql(exclude),
              str_sql(size),
              str_sql(note)
          )
    return update_by_sql(sql)


# 删除站点信息
def delete_config_site(tid):
    if not tid:
        return False
    return update_by_sql("DELETE FROM CONFIG_SITE WHERE ID='%s'" % tid)


# 更新站点信息
def update_config_site(tid, name, site_pri, rssurl, signurl, cookie, include, exclude, size, note):
    delete_config_site(tid)
    insert_config_site(name, site_pri, rssurl, signurl, cookie, include, exclude, size, note)


# 查询搜索过滤规则
def get_config_search_rule():
    return select_by_sql(
        "SELECT INCLUDE,EXCLUDE,NOTE,SIZE FROM CONFIG_SEARCH_RULE")


# 更新搜索过滤规则
def update_config_search_rule(include, exclude, note, size):
    update_by_sql("DELETE FROM CONFIG_SEARCH_RULE")
    return update_by_sql(
        "INSERT INTO CONFIG_SEARCH_RULE(INCLUDE,EXCLUDE,NOTE,SIZE) VALUES "
        "('%s', '%s', '%s', '%s')" % (str_sql(include),
                                      str_sql(exclude),
                                      str_sql(note),
                                      str_sql(size)))


# 查询RSS全局过滤规则
def get_config_rss_rule():
    return select_by_sql(
        "SELECT ID,NOTE FROM CONFIG_RSS_RULE")


# 更新RSS全局过滤规则
def update_config_rss_rule(note):
    update_by_sql("DELETE FROM CONFIG_RSS_RULE")
    return update_by_sql(
        "INSERT INTO CONFIG_RSS_RULE(NOTE) VALUES ('%s')" % str_sql(note))


# 查询订阅电影信息
def get_rss_movies(state=None):
    if not state:
        sql = "SELECT NAME,YEAR,TMDBID,IMAGE,DESC,STATE FROM RSS_MOVIES"
    else:
        sql = "SELECT NAME,YEAR,TMDBID,IMAGE,DESC,STATE FROM RSS_MOVIES WHERE STATE='%s'" % state
    return select_by_sql(sql)


# 查询订阅电视剧信息
def get_rss_tvs(state=None):
    if not state:
        sql = "SELECT NAME,YEAR,SEASON,TMDBID,IMAGE,DESC,TOTAL,LACK,STATE,((CAST(TOTAL AS FLOAT)-CAST(LACK AS FLOAT))/CAST(TOTAL AS FLOAT))*100 FROM RSS_TVS"
    else:
        sql = "SELECT NAME,YEAR,SEASON,TMDBID,IMAGE,DESC,TOTAL,LACK,STATE,((CAST(TOTAL AS FLOAT)-CAST(LACK AS FLOAT))/CAST(TOTAL AS FLOAT))*100 FROM RSS_TVS WHERE STATE='%s'" % state
    return select_by_sql(sql)


# 判断RSS电影是否存在
def is_exists_rss_movie(title, year):
    if not title:
        return False
    sql = "SELECT COUNT(1) FROM RSS_MOVIES WHERE NAME='%s' AND YEAR='%s'" % (title, year)
    ret = select_by_sql(sql)
    if ret and ret[0][0] > 0:
        return True
    else:
        return False


# 新增RSS电影
def insert_rss_movie(media_info):
    if not media_info:
        return False
    if not media_info.title or not media_info.year:
        return False
    if is_exists_rss_movie(media_info.title, media_info.year):
        return True
    sql = "INSERT INTO RSS_MOVIES(NAME,YEAR,TMDBID,IMAGE,DESC,STATE) VALUES('%s','%s','%s','%s','%s','%s')" % (
        str_sql(media_info.title),
        str_sql(media_info.year),
        str_sql(media_info.tmdb_id),
        str_sql(media_info.get_backdrop_path()),
        str_sql(media_info.overview),
        'D'
    )
    return update_by_sql(sql)


# 删除RSS电影
def delete_rss_movie(title, year):
    if not title:
        return False
    sql = "DELETE FROM RSS_MOVIES WHERE NAME='%s' AND YEAR='%s'" % (title, year)
    return update_by_sql(sql)


# 判断RSS电视剧是否存在
def is_exists_rss_tv(title, year, season):
    if not title:
        return False
    sql = "SELECT COUNT(1) FROM RSS_TVS WHERE NAME='%s' AND YEAR='%s' AND SEASON='%s'" % (title, year, season)
    ret = select_by_sql(sql)
    if ret and ret[0][0] > 0:
        return True
    else:
        return False


# 新增RSS电视剧
def insert_rss_tv(media_info, total, lack=0, state="D"):
    if not media_info:
        return False
    if not media_info.title or not media_info.year:
        return False
    if is_exists_rss_tv(media_info.title, media_info.year, media_info.get_season_string()):
        return True
    sql = "INSERT INTO RSS_TVS(NAME,YEAR,SEASON,TMDBID,IMAGE,DESC,TOTAL,LACK,STATE) VALUES('%s','%s','%s','%s','%s','%s',%s,%s,'%s')" % (
        str_sql(media_info.title),
        str_sql(media_info.year),
        media_info.get_season_string(),
        str_sql(media_info.tmdb_id),
        str_sql(media_info.get_backdrop_path()),
        str_sql(media_info.overview),
        total,
        lack,
        state
    )
    return update_by_sql(sql)


# 更新电视剧缺失的集数
def update_rss_tv_lack(title, year, season, lack):
    if not title:
        return False
    sql = "UPDATE RSS_TVS SET LACK='%s' WHERE NAME='%s' AND YEAR='%s' AND SEASON='%s'" % (lack, title, year, season)
    return update_by_sql(sql)


# 删除RSS电视剧
def delete_rss_tv(title, year, season):
    if not title:
        return False
    sql = "DELETE FROM RSS_TVS WHERE NAME='%s' AND YEAR='%s' AND SEASON='%s'" % (title, year, season)
    return update_by_sql(sql)


# 更新电影订阅状态
def update_rss_movie_state(title, year, state):
    if not title:
        return False
    sql = "UPDATE RSS_MOVIES SET STATE='%s' WHERE NAME='%s' AND YEAR='%s'" % (state, title, year)
    return update_by_sql(sql)


# 更新电视剧订阅状态
def update_rss_tv_state(title, year, season, state):
    if not title:
        return False
    sql = "UPDATE RSS_TVS SET STATE='%s' WHERE NAME='%s' AND YEAR='%s' AND SEASON='%s'" % (state, title, year, season)
    return update_by_sql(sql)


# 查询是否存在同步历史记录
def is_sync_in_history(path, dest):
    if not path:
        return False
    path = os.path.normpath(path)
    dest = os.path.normpath(dest)
    sql = f"SELECT COUNT(1) FROM SYNC_HISTORY WHERE PATH='{str_sql(path)}' AND DEST='{str_sql(dest)}'"
    ret = select_by_sql(sql)
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
        sql = f"INSERT INTO SYNC_HISTORY(PATH, SRC, DEST) VALUES('{str_sql(path)}', '{str_sql(src)}', '{str_sql(dest)}')"
        return update_by_sql(sql)
