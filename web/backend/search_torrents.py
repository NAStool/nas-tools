import log
from config import Config
from message.send import Message
from pt.downloader import Downloader
from pt.searcher import Searcher
from pt.torrent import Torrent
from rmt.media import Media
from rmt.meta.metabase import MetaBase
from rmt.metainfo import MetaInfo
from utils.sqls import insert_search_results, delete_all_search_torrents, insert_rss_tv, insert_rss_movie
from utils.types import SearchType, MediaType
from web.backend.subscribe import add_rss_subscribe

SEARCH_MEDIA_CACHE = []


def search_medias_for_web(content, ident_flag=True, filters=None):
    """
    WEB资源搜索
    :param content: 关键字文本，可以包括 类型、标题、季、集、年份等信息，使用 空格分隔，也支持种子的命名格式
    :param ident_flag: 是否进行媒体信息识别
    :param filters: 其它过滤条件
    :return: 错误码，错误原因，成功时直接插入数据库
    """
    mtype, key_word, season_num, episode_num, year, content = Torrent.get_keyword_from_string(content)
    if not key_word:
        log.info("【WEB】%s 检索关键字有误！" % content)
        return -1, "%s 未识别到搜索关键字！" % content

    # 识别媒体
    match_words = None
    if ident_flag:
        media_info = Media().get_media_info(mtype=mtype, title=content)
        if not media_info or not media_info.tmdb_info:
            return -1, "%s 查询不到媒体信息，请确认名称是否正确！" % content
        # 查找的季
        if not media_info.begin_season:
            search_season = None
        else:
            search_season = media_info.get_season_list()
        # 查找的集
        search_episode = media_info.get_episode_list()
        if search_episode and not search_season:
            search_season = [1]
        # 如果原标题是英文：用原标题去检索，用原标题及中文标题去匹配，以兼容国外网站
        key_word = media_info.original_title if media_info.original_language == "en" else media_info.title
        match_words = [media_info.title, key_word] if key_word != media_info.title else [media_info.title]
        filter_args = {"season": search_season,
                       "episode": search_episode,
                       "year": media_info.year,
                       "type": media_info.type}
    else:
        filter_args = {"season": season_num,
                       "episode": episode_num,
                       "year": year}

    # 整合高级查询条件
    if filters:
        filter_args.update(filters)

    # 开始检索
    log.info("【WEB】开始检索 %s ..." % content)
    media_list = Searcher().search_medias(key_word=key_word,
                                          filter_args=filter_args,
                                          match_type=1 if ident_flag else 2,
                                          match_words=match_words)
    delete_all_search_torrents()
    if len(media_list) == 0:
        log.info("【WEB】%s 未检索到任何资源" % content)
        return 0, "%s 未检索到任何资源" % content
    else:
        log.info("【WEB】共检索到 %s 个有效资源" % len(media_list))
        # 插入数据库
        media_list = sorted(media_list, key=lambda x: "%s%s%s" % (str(x.res_order).rjust(3, '0'),
                                                                  str(x.site_order).rjust(3, '0'),
                                                                  str(x.seeders).rjust(10, '0')), reverse=True)
        insert_search_results(media_list)
        return 0, ""


def search_media_by_message(input_str, in_from: SearchType, user_id=None):
    """
    输入字符串，解析要求并进行资源检索
    :param input_str: 输入字符串，可以包括标题、年份、季、集的信息，使用空格隔开
    :param in_from: 搜索下载的请求来源
    :param user_id: 需要发送消息的，传入该参数，则只给对应用户发送交互消息
    :return: 请求的资源是否全部下载完整、请求的文本对应识别出来的媒体信息、请求的资源如果是剧集，则返回下载后仍然缺失的季集信息
    """
    if not input_str:
        log.info("【SEARCHER】检索关键字有误！")
        return
    # 如果是数字，表示选择项
    if input_str.isdigit():
        # 获取之前保存的可选项
        choose = int(input_str) - 1
        if choose < 0 or choose >= len(SEARCH_MEDIA_CACHE):
            Message().send_channel_msg(channel=in_from,
                                       title="输入有误！",
                                       user_id=user_id)
            log.warn("【WEB】错误的输入值：%s" % input_str)
            return
        media_info = SEARCH_MEDIA_CACHE[choose]
        __search_media(in_from, media_info, user_id)
    # 接收到文本，开始查询可能的媒体信息供选择
    else:
        # 去掉查询中的电影或电视剧关键字
        mtype, _, _, _, _, content = Torrent.get_keyword_from_string(input_str)
        # 识别媒体信息，列出匹配到的所有媒体
        log.info("【WEB】正在识别 %s 的媒体信息..." % content)
        media_info = MetaInfo(title=content, mtype=mtype)
        if not media_info.get_name():
            Message().send_channel_msg(channel=in_from,
                                       title="无法识别搜索内容！",
                                       user_id=user_id)
            return
        tmdb_infos = Media().get_tmdb_infos(title=media_info.get_name(), year=media_info.year, mtype=mtype)
        if not tmdb_infos:
            # 查询不到媒体信息
            Message().send_channel_msg(channel=in_from,
                                       title="%s 查询不到媒体信息！" % media_info.get_name(),
                                       user_id=user_id)
            return

        # 保存识别信息到临时结果中
        SEARCH_MEDIA_CACHE.clear()
        for tmdb_info in tmdb_infos:
            meta_info = MetaInfo(title=content)
            meta_info.set_tmdb_info(tmdb_info)
            SEARCH_MEDIA_CACHE.append(meta_info)

        if 1 == len(SEARCH_MEDIA_CACHE):
            # 只有一条数据，直接开始搜索
            media_info = SEARCH_MEDIA_CACHE[0]
            Message().send_channel_msg(channel=in_from,
                                       title=media_info.get_title_vote_string(),
                                       text=media_info.get_overview_string(),
                                       image=media_info.get_message_image(),
                                       user_id=user_id)
            __search_media(in_from, media_info, user_id)
        else:
            # 发送消息通知选择
            Message().send_channel_list_msg(channel=in_from,
                                            title="共找到%s条相关信息，请回复对应序号开始搜索" % len(SEARCH_MEDIA_CACHE),
                                            medias=SEARCH_MEDIA_CACHE,
                                            user_id=user_id)


def __search_media(in_from, media_info: MetaBase, user_id):
    # 检查是否存在，电视剧返回不存在的集清单
    exist_flag, no_exists, messages = Downloader().check_exists_medias(meta_info=media_info)
    # 已经存在
    if exist_flag:
        Message().send_channel_msg(channel=in_from,
                                   title="\n".join(messages),
                                   user_id=user_id)
        return
    # 开始检索
    Message().send_channel_msg(channel=in_from,
                               title="开始检索 %s ..." % media_info.title,
                               user_id=user_id)
    search_result, no_exists, search_count, download_count = Searcher().search_one_media(media_info=media_info,
                                                                                         in_from=in_from,
                                                                                         no_exists=no_exists)
    # 没有搜索到数据
    if not search_count:
        Message().send_channel_msg(channel=in_from,
                                   title="%s 未搜索到任何资源" % media_info.title,
                                   user_id=user_id)
        # 自动添加订阅
        if Config().get_config('pt').get('search_no_result_rss'):
            # 添加订阅
            if add_rss_subscribe(mtype=media_info.type,
                                 name=media_info.title,
                                 year=media_info.year,
                                 season=media_info.begin_season,
                                 tmdbid=media_info.tmdb_id,
                                 state='R'):
                # 发送通知
                if media_info.type == MediaType.MOVIE:
                    msg_title = f"{media_info.get_title_string()} 已添加订阅"
                else:
                    msg_title = f"{media_info.get_title_string()} {media_info.get_season_string()} 已添加订阅"
                msg_str = f"类型：{media_info.type.value}"
                if media_info.vote_average:
                    msg_str = f"{msg_str}，{media_info.get_vote_string()}"
                Message().send_channel_msg(channel=in_from,
                                           title=msg_title,
                                           text=msg_str,
                                           image=media_info.get_message_image(),
                                           url='movie_rss' if media_info.type == MediaType.MOVIE else 'tv_rss',
                                           user_id=user_id)
    # 搜索到了但是没开自动下载
    elif download_count is None:
        Message().send_channel_msg(channel=in_from,
                                   title="%s 共搜索到%s个资源，点击选择下载" % (media_info.get_title_string(), search_count),
                                   image=media_info.get_message_image(),
                                   url="search",
                                   user_id=user_id)
    elif download_count == 0:
        Message().send_channel_msg(channel=in_from,
                                   title="%s 共搜索到%s个结果，但没有下载到任何资源" % (media_info.title, search_count),
                                   user_id=user_id)
