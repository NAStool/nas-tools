from utils.db_helper import update_by_sql, select_by_sql
from utils.functions import str_filesize
from utils.types import MediaType


# 将Jackett返回信息插入数据库
def insert_jackett_results(media_item):
    sql = "INSERT INTO JACKETT_TORRENTS(" \
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
              media_item.org_string,
              media_item.enclosure,
              media_item.description,
              "TV" if media_item.type == MediaType.TV else "MOV",
              media_item.title,
              media_item.year if media_item.year else "",
              media_item.get_season_string(),
              media_item.get_episode_string(),
              media_item.get_season_episode_string(),
              media_item.vote_average,
              media_item.backdrop_path,
              media_item.res_type if media_item.res_type else media_item.resource_type,
              media_item.res_order,
              str_filesize(int(media_item.size)),
              media_item.seeders,
              media_item.peers,
              media_item.site,
              media_item.site_order
          )
    return update_by_sql(sql)


# 根据ID从数据库中查询Jackett检索结果的一条记录
def get_jackett_result_by_id(dl_id):
    sql = "SELECT ENCLOSURE,TITLE,YEAR,SEASON,EPISODE,VOTE,IMAGE,TYPE FROM JACKETT_TORRENTS WHERE ID=%s" % dl_id
    return select_by_sql(sql)


# 查询Jackett检索结果的所有记录
def get_jackett_results():
    sql = "SELECT ID,TITLE||' ('||YEAR||') '||ES_STRING,RES_TYPE,SIZE,SEEDERS,ENCLOSURE,SITE,YEAR,ES_STRING,IMAGE,TYPE,VOTE*1 FROM JACKETT_TORRENTS ORDER BY TITLE, SEEDERS DESC"
    return select_by_sql(sql)


# 查询电影关键字
def get_movie_keys():
    sql = "SELECT NAME FROM RSS_MOVIEKEYS"
    return select_by_sql(sql)


# 查询电视剧关键字
def get_tv_keys():
    sql = "SELECT NAME FROM RSS_TVKEYS"
    return select_by_sql(sql)


# 删除全部电影关键字
def delete_all_movie_keys():
    sql = "DELETE FROM RSS_MOVIEKEYS"
    return update_by_sql(sql)


# 删除全部电视剧关键字
def delete_all_tv_keys():
    sql = "DELETE FROM RSS_TVKEYS"
    return update_by_sql(sql)


# 插入电影关键字
def insert_movie_key(key):
    sql = "SELECT 1 FROM RSS_MOVIEKEYS WHERE NAME = '%s'" % key
    ret = select_by_sql(sql)
    if not ret or len(ret) == 0:
        sql = "INSERT INTO RSS_MOVIEKEYS(NAME) VALUES ('%s')" % key
        return update_by_sql(sql)
    else:
        return False


# 插入电视剧关键字
def insert_tv_key(key):
    sql = "SELECT 1 FROM RSS_TVKEYS WHERE NAME = '%s'" % key
    ret = select_by_sql(sql)
    if not ret or len(ret) == 0:
        sql = "INSERT INTO RSS_TVKEYS(NAME) VALUES ('%s')" % key
        return update_by_sql(sql)
    else:
        return False


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
def is_torrent_rssd_by_name(media_title, media_year, media_seaion, media_episode):
    if not media_title:
        return True
    sql = "SELECT 1 FROM RSS_TORRENTS WHERE TITLE = '%s'" % media_title
    if media_year:
        sql = "%s AND YEAR='%s'" % (sql, media_year)
    if media_seaion:
        sql = "%s AND SEASON='%s'" % (sql, media_seaion)
    if media_episode:
        sql = "%s AND EPISODE='%s'" % (sql, media_episode)
    ret = select_by_sql(sql)
    if not ret:
        return False
    if len(ret) > 0:
        return True
    return False


# 将RSS的记录插入数据库
def insert_rss_torrents(media_info):
    sql = "INSERT INTO RSS_TORRENTS(TORRENT_NAME, ENCLOSURE, TYPE, TITLE, YEAR, SEASON, EPISODE) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s')" % (
        media_info.title, media_info.enclosure, media_info.type, media_info.title, media_info.year, media_info.get_season_string(), media_info.get_episode_string())
    return update_by_sql(sql)


# 将豆瓣的数据插入数据库
def insert_douban_medias(medias):
    for media in medias:
        if not media.year:
            sql = "SELECT 1 FROM DOUBAN_MEDIAS WHERE NAME = '%s'" % media.get_name()
        else:
            sql = "SELECT 1 FROM DOUBAN_MEDIAS WHERE NAME = '%s' AND YEAR = '%s'" % (media.get_name(), media.year)
        ret = select_by_sql(sql)
        if not ret or len(ret) == 0:
            sql = "INSERT INTO DOUBAN_MEDIAS(NAME, YEAR, TYPE, RATING, IMAGE, STATE) VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" % (media.get_name(), media.year, media.type.value, media.douban_rating, media.douban_poster, 'NEW')
            if not update_by_sql(sql):
                return False
    return True


# 标记豆瓣数据的状态
def update_douban_media_state(title, year, state):
    sql = "UPDATE DOUBAN_MEDIAS SET STATE = '%s' WHERE NAME = '%s' AND YEAR = '%s'" % (state, title, year)
    return update_by_sql(sql)


# 查询未检索的豆瓣数据
def get_douban_search_medias():
    sql = "SELECT NAME, YEAR, TYPE FROM DOUBAN_MEDIAS WHERE STATE = 'NEW'"
    return select_by_sql(sql)
