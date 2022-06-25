import re

import log
from message.send import Message
from pt.torrent import Torrent
from rmt.doubanv2api.doubanapi import DoubanApi
from rmt.media import Media
from rmt.metainfo import MetaInfo
from utils.sqls import insert_rss_tv, insert_rss_movie
from utils.types import MediaType, SearchType


def add_rss_substribe_from_string(rss_string, in_from=SearchType.OT, user_id=None):
    """
    解析字符串，提取信息后添加订阅
    :param rss_string: 输入字符串，以”订阅“两字开头
    :param in_from: 搜索下载的请求来源
    :param user_id: 需要发送消息的，传入该参数，则只给对应用户发送交互消息
    :return: 状态 True/False
    """
    message = Message()
    title_str = re.sub(r"订阅[:：\s]*", "", rss_string)
    if not title_str:
        log.info("【WEB】%s 内容有误" % rss_string)
        if in_from in [SearchType.WX, SearchType.TG]:
            message.send_channel_msg(channel=in_from,
                                     title="订阅内容有误",
                                     user_id=user_id)
        return False
    mtype, key_word, season_num, episode_num, year, title_str = Torrent.get_keyword_from_string(title_str)
    if not key_word:
        log.info("【WEB】%s 名称有误" % rss_string)
        if in_from in [SearchType.WX, SearchType.TG]:
            message.send_channel_msg(channel=in_from,
                                     title="订阅名称有误",
                                     user_id=user_id)
        return False
    code, msg, media_info = add_rss_subscribe(mtype, key_word, year, season_num)
    if code == 0:
        log.info("【WEB】%s %s 已添加订阅" % (media_info.type.value, media_info.get_title_string()))
        if in_from in [SearchType.WX, SearchType.TG]:
            if media_info.type == MediaType.MOVIE:
                msg_title = f"{media_info.get_title_string()} 已添加订阅"
            else:
                msg_title = f"{media_info.get_title_string()} {media_info.get_season_string()} 已添加订阅"
            msg_str = f"类型：{media_info.type.value}"
            if media_info.vote_average:
                msg_str = f"{msg_str}，{media_info.get_vote_string()}"

            message.send_channel_msg(channel=in_from,
                                     title=msg_title,
                                     text=msg_str,
                                     image=media_info.get_message_image(),
                                     url='movie_rss' if media_info.type == MediaType.MOVIE else 'tv_rss',
                                     user_id=user_id)
        return True
    else:
        if in_from in [SearchType.WX, SearchType.TG]:
            log.info("【WEB】%s 添加订阅失败：%s" % (key_word, msg))
            message.send_channel_msg(channel=in_from,
                                     title="%s 添加订阅失败：%s" % (key_word, msg),
                                     user_id=user_id)
        return False


def add_rss_subscribe(mtype, name, year, season=None, match=False, doubanid=None, tmdbid=None, sites=None, search_sites=None, state="D"):
    """
    添加电影、电视剧订阅
    :param mtype: 类型，电影、电视剧、动漫
    :param name: 标题
    :param year: 年份，如要是剧集需要是首播年份
    :param season: 第几季，数字
    :param match: 是否模糊匹配
    :param doubanid: 豆瓣ID，有此ID时从豆瓣查询信息
    :param tmdbid: TMDBID，有此ID时优先使用ID查询TMDB信息，没有则使用名称查询
    :param sites: 站点列表，为空则表示全部站点
    :param search_sites: 搜索站点列表，为空则表示全部站点
    :param state: 添加订阅时的状态
    :return: 错误码：0代表成功，错误信息
    """
    if not name:
        return -1, "标题或类型有误", None
    if not year:
        year = ""
    # 检索媒体信息
    if not match:
        # 精确匹配
        media = Media()
        # 根据TMDBID查询，从推荐加订阅的情况
        if tmdbid:
            media_info = MetaInfo(title="%s %s".strip() % (name, year), mtype=mtype)
            media_info.set_tmdb_info(media.get_tmdb_info(mtype=mtype, tmdbid=tmdbid))
            if not media_info or not media_info.tmdb_info or not tmdbid:
                return 1, "无法查询到媒体信息", None
        else:
            # 根据名称和年份查询
            media_info = media.get_media_info(title="%s %s" % (name, year),
                                              mtype=mtype,
                                              strict=True if year else False)
            if media_info and media_info.tmdb_info:
                tmdbid = media_info.tmdb_id
            elif doubanid:
                # 查询豆瓣，从推荐加订阅的情况
                if mtype == MediaType.MOVIE:
                    douban_info = DoubanApi().movie_detail(doubanid)
                else:
                    douban_info = DoubanApi().tv_detail(doubanid)
                if not douban_info or douban_info.get("localized_message"):
                    return 1, "无法查询到豆瓣媒体信息", None
                media_info = MetaInfo(title="%s %s".strip() % (douban_info.get('title'), year), mtype=mtype)
                media_info.title = media_info.get_name()
                media_info.year = douban_info.get("year")
                media_info.type = mtype
                media_info.backdrop_path = douban_info.get("cover_url")
                media_info.tmdb_id = "DB:%s" % doubanid
                media_info.overview = douban_info.get("intro")
                media_info.total_episodes = douban_info.get("episodes_count")
                # 合并季
                if season:
                    media_info.begin_season = int(season)
            else:
                return 1, "无法查询到媒体信息", None
        # 添加订阅
        if media_info.type != MediaType.MOVIE:
            if tmdbid:
                if season:
                    season = int(season)
                    total_episode = media.get_tmdb_season_episodes_num(sea=season, tmdbid=tmdbid)
                else:
                    # 查询季及集信息
                    total_seasoninfo = media.get_tmdb_seasons_list(tmdbid=tmdbid)
                    if not total_seasoninfo:
                        return 2, "获取剧集信息失败", media_info
                    # 按季号降序排序
                    total_seasoninfo = sorted(total_seasoninfo, key=lambda x: x.get("season_number"),
                                              reverse=True)
                    # 取最新季
                    season = total_seasoninfo[0].get("season_number")
                    total_episode = total_seasoninfo[0].get("episode_count")
                if not total_episode:
                    return 3, "%s 获取剧集数失败，请确认该季是否存在" % media_info.get_title_string(), media_info
                media_info.begin_season = season
                media_info.total_episodes = total_episode
            insert_rss_tv(media_info=media_info,
                          total=media_info.total_episodes,
                          lack=media_info.total_episodes,
                          sites=sites,
                          search_sites=search_sites,
                          state=state)
        else:
            insert_rss_movie(media_info=media_info,
                             sites=sites,
                             search_sites=search_sites,
                             state=state)
    else:
        # 模糊匹配
        media_info = MetaInfo(title=name, mtype=mtype)
        media_info.title = name
        media_info.type = mtype
        if season:
            media_info.begin_season = int(season)
        if mtype == MediaType.MOVIE:
            insert_rss_movie(media_info=media_info, state="R", sites=sites, search_sites=search_sites)
        else:
            insert_rss_tv(media_info=media_info, total=0, lack=0, state="R", sites=sites, search_sites=search_sites)

    return 0, "添加订阅成功", media_info
