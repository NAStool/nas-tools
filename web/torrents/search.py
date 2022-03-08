import log
from pt.jackett import Jackett
from utils.db.db_helper import update_by_sql
from utils.functions import get_keyword_from_string


def search_medias_for_web(content):
    # 拆分关键字
    key_word, season_num, episode_num, year = get_keyword_from_string(content)
    log.info("【WEB】开始检索 %s ..." % content)
    media_list = Jackett().search_medias_from_word(key_word, season_num, episode_num, year)
    update_by_sql("DELETE FROM JACKETT_TORRENTS")
    if len(media_list) == 0:
        log.info("【WEB】%s 未检索到任何媒体资源！")
        sql = "INSERT INTO JACKETT_TORRENTS(TITLE) VALUES('未检索到资源')"
        update_by_sql(sql)
    else:
        log.info("【WEB】共检索到 %s 个有效资源" % len(media_list))
        # 插入数据库
        for media_item in media_list:
            sql = "INSERT INTO JACKETT_TORRENTS(" \
                  "TORRENT_NAME," \
                  "ENCLOSURE," \
                  "DESCRIPTION," \
                  "TYPE," \
                  "TITLE," \
                  "YEAR," \
                  "SEASON," \
                  "EPISODE," \
                  "VOTE," \
                  "IMAGE," \
                  "RES_TYPE," \
                  "RES_ORDER," \
                  "SIZE," \
                  "SEEDERS," \
                  "PEERS," \
                  "SITE," \
                  "SITE_ORDER) VALUES (" \
                  "'%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" % (
                      media_item.get('torrent_name'),
                      media_item.get('enclosure'),
                      media_item.get('description'),
                      media_item.get('type').value,
                      media_item.get('title'),
                      media_item.get('year') if media_item.get('year') else "",
                      media_item.get('season') if media_item.get('season') else "",
                      media_item.get('episode') if media_item.get('episode') else "",
                      media_item.get('vote_average') if media_item.get('vote_average') else "",
                      media_item.get('backdrop_path') if media_item.get('backdrop_path') else "",
                      media_item.get('res_type'),
                      media_item.get('res_order'),
                      media_item.get('size'),
                      media_item.get('seeders'),
                      media_item.get('peers'),
                      media_item.get('index'),
                      media_item.get('site_order')
                  )
            update_by_sql(sql)

