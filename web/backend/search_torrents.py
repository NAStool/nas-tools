import re
import cn2an
import log
from pt.searcher import Searcher
from utils.sqls import insert_search_results, delete_all_search_torrents


def search_medias_for_web(content):
    # 拆分关键字
    key_word, season_num, episode_num, year = get_keyword_from_string(content)
    if not key_word:
        log.info("【WEB】检索关键字有误！" % content)
        return
    log.info("【WEB】开始检索 %s ..." % content)
    searcher = Searcher()
    media_list = searcher.search_medias(key_word=key_word,
                                        s_num=season_num,
                                        e_num=episode_num,
                                        year=year,
                                        mtype=None,
                                        whole_word=False)
    delete_all_search_torrents()
    if len(media_list) == 0:
        log.info("【WEB】%s 未检索到任何媒体资源" % content)
        return
    else:
        log.info("【WEB】共检索到 %s 个有效资源" % len(media_list))
        # 分组择优
        media_list = searcher.get_torrents_group_item(media_list)
        log.info("【WEB】分组择优后剩余 %s 个有效资源" % len(media_list))
        # 插入数据库
        for media_item in media_list:
            insert_search_results(media_item)


# 从检索关键字中拆分中年份、季、集、类型
# 名称 年份 第X季 第X集 电影/电视剧，用空格分隔
def get_keyword_from_string(content):
    if not content:
        return {}
    # 稍微切一下剧集吧
    season_num = None
    episode_num = None
    year = None
    season_re = re.search(r"第\s*([0-9一二三四五六七八九十]+)\s*季", content, re.IGNORECASE)
    if season_re:
        season_num = int(cn2an.cn2an(season_re.group(1), mode='smart'))
    episode_re = re.search(r"第\s*([0-9一二三四五六七八九十]+)\s*集", content, re.IGNORECASE)
    if episode_re:
        episode_num = int(cn2an.cn2an(episode_re.group(1), mode='smart'))
        if episode_num and not season_num:
            season_num = "1"
    year_re = re.search(r"[\s(]+(\d{4})[\s)]*", content)
    if year_re:
        year = year_re.group(1)
    key_word = re.sub(r'第\s*[0-9一二三四五六七八九十]+\s*季|第\s*[0-9一二三四五六七八九十]+\s*集|[\s(]+(\d{4})[\s)]*', '',
                      content,
                      flags=re.IGNORECASE).strip()
    if key_word:
        key_word = re.sub(r'\s+', ' ', key_word)
    if not key_word:
        key_word = year

    return key_word, season_num, episode_num, year
