import log
from pt.jackett import Jackett
from utils.functions import get_keyword_from_string
from utils.sqls import insert_jackett_results, delete_all_jackett_torrents


def search_medias_for_web(content):
    # 拆分关键字
    key_word, season_num, episode_num, year = get_keyword_from_string(content)
    if not key_word:
        log.info("【WEB】检索关键字有误！" % content)
        return
    log.info("【WEB】开始检索 %s ..." % content)
    jackett = Jackett()
    media_list = jackett.search_medias_from_word(key_word=key_word,
                                                 s_num=season_num,
                                                 e_num=episode_num,
                                                 year=year,
                                                 whole_word=False)
    delete_all_jackett_torrents()
    if len(media_list) == 0:
        log.info("【WEB】%s 未检索到任何媒体资源" % content)
        return
    else:
        log.info("【WEB】共检索到 %s 个有效资源" % len(media_list))
        # 分组择优
        media_list = jackett.get_torrents_group_item(media_list)
        log.info("【WEB】分组择优后剩余 %s 个有效资源" % len(media_list))
        # 插入数据库
        for media_item in media_list:
            insert_jackett_results(media_item)
