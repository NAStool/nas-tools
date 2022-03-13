import log
from pt.jackett import Jackett
from utils.db_helper import update_by_sql
from utils.functions import get_keyword_from_string
from utils.sqls import insert_jackett_results
from utils.types import MediaType


def search_medias_for_web(content):
    # 拆分关键字
    key_word, season_num, episode_num, year = get_keyword_from_string(content)
    if not key_word:
        log.info("【WEB】检索关键字有误！" % content)
        return
    log.info("【WEB】开始检索 %s ..." % content)
    media_list = Jackett().search_medias_from_word(key_word, season_num, episode_num, year, False)
    update_by_sql("DELETE FROM JACKETT_TORRENTS")
    if len(media_list) == 0:
        log.info("【WEB】%s 未检索到任何媒体资源！" % content)
        return
    else:
        log.info("【WEB】共检索到 %s 个有效资源" % len(media_list))
        # 分组择优
        media_list = __get_download_list(media_list)
        log.info("【WEB】分组择优后剩余 %s 个有效资源" % len(media_list))
        # 插入数据库
        for media_item in media_list:
            insert_jackett_results(media_item)


# 种子去重，每一个名称、站点、资源类型 选一个做种人最多的显示
def __get_download_list(media_list):
    if not media_list:
        return []

    # 排序函数
    def get_sort_str(x):
        return "%s%s%s%s" % (str(x['title']).ljust(100, ' '),
                             str(x['site_name']).ljust(20, ' '),
                             str(x['res_type']).ljust(20, ' '),
                             str(x['seeders']).rjust(10, '0'))

    # 匹配的资源中排序分组
    media_list = sorted(media_list, key=lambda x: get_sort_str(x), reverse=True)
    # 控重
    can_download_list_item = []
    can_download_list = []
    # 排序后重新加入数组，按真实名称控重，即只取每个名称的第一个
    for t_item in media_list:
        # 控重的主链是名称、节份、季、集
        if t_item['type'] == MediaType.TV:
            media_name = "%s%s%s%s%s%s" % (t_item.get('title'),
                                           t_item.get('year'),
                                           t_item.get('site_name'),
                                           t_item.get('res_type'),
                                           t_item.get('season'),
                                           t_item.get('episode'))
        else:
            media_name = "%s%s%s%s" % (
                t_item.get('title'), t_item.get('year'), t_item.get('site_name'), t_item.get('res_type'))
        if media_name not in can_download_list:
            can_download_list.append(media_name)
            can_download_list_item.append(t_item)
    return can_download_list_item
