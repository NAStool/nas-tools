import re

import log
from message.send import Message
from pt.torrent import Torrent
from rmt.media import Media
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


def add_rss_subscribe(mtype, name, year, season):
    """
    添加电影、电视剧订阅
    :param mtype: 类型，电影、电视剧、动漫
    :param name: 标题
    :param year: 年份，如要是剧集需要是首播年份
    :param season: 第几季，数字
    :return: 错误码：0代表成功，错误信息
    """
    if not name:
        return -1, "标题或类型有误", None
    # 检索媒体信息
    media = Media()
    media_info = media.get_media_info(title="%s %s" % (name, year), mtype=mtype, strict=True if year else False)
    if not media_info or not media_info.tmdb_info:
        return 1, "无法查询到媒体信息", None
    if media_info.type != MediaType.MOVIE:
        if not season:
            # 查询季及集信息
            total_seasoninfo = media.get_tmdb_seasons_info(tmdbid=media_info.tmdb_id)
            if not total_seasoninfo:
                return 2, "获取剧集信息失败", media_info
            # 按季号降序排序
            total_seasoninfo = sorted(total_seasoninfo, key=lambda x: x.get("season_number"),
                                      reverse=True)
            # 没有季的信息时，取最新季
            season = total_seasoninfo[0].get("season_number")
            total_count = total_seasoninfo[0].get("episode_count")
        else:
            season = int(season)
            total_count = media.get_tmdb_season_episodes_num(sea=season, tmdbid=media_info.tmdb_id)
        if not total_count:
            return 3, "%s 获取剧集数失败，请确认该季是否存在" % media_info.get_title_string(), media_info
        media_info.begin_season = season
        insert_rss_tv(media_info, total_count, total_count)
    else:
        insert_rss_movie(media_info)

    return 0, "添加订阅成功", media_info
