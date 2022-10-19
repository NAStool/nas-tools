from app.media.douban import DouBan
from app.helper import SqlHelper
from app.media.doubanv2api import DoubanApi
from app.media import MetaInfo, Media
from app.message import Message
from app.utils import Torrent
from app.utils.types import MediaType


class Subscribe:

    @staticmethod
    def add_rss_subscribe(mtype, name, year,
                          season=None,
                          match=False,
                          doubanid=None,
                          tmdbid=None,
                          sites=None,
                          search_sites=None,
                          over_edition=False,
                          rss_restype=None,
                          rss_pix=None,
                          rss_team=None,
                          rss_rule=None,
                          state="D",
                          rssid=None,
                          total_ep=None,
                          current_ep=None):
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
        :param over_edition: 是否选版
        :param rss_restype: 质量过滤
        :param rss_pix: 分辨率过滤
        :param rss_team: 制作组/字幕组过滤
        :param rss_rule: 关键字过滤
        :param state: 添加订阅时的状态
        :param rssid: 修改订阅时传入
        :param total_ep: 总集数
        :param current_ep: 开始订阅集数
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
            if season:
                title = "%s %s 第%s季".strip() % (name, year, season)
            else:
                title = "%s %s".strip() % (name, year)
            if tmdbid:
                # 根据TMDBID查询
                media_info = MetaInfo(title=title, mtype=mtype)
                media_info.set_tmdb_info(media.get_tmdb_info(mtype=mtype, tmdbid=tmdbid))
                if not media_info or not media_info.tmdb_info or not tmdbid:
                    return 1, "无法查询到媒体信息", None
            else:
                # 根据名称和年份查询
                media_info = media.get_media_info(title=title,
                                                  mtype=mtype,
                                                  strict=True if year else False)
                if media_info and media_info.tmdb_info:
                    tmdbid = media_info.tmdb_id
                elif doubanid:
                    # 先从豆瓣网页抓取（含TMDBID）
                    douban_info = DouBan().get_media_detail_from_web("https://movie.douban.com/subject/%s/" % doubanid)
                    if not douban_info:
                        if mtype == MediaType.MOVIE:
                            douban_info = DoubanApi().movie_detail(doubanid)
                        else:
                            douban_info = DoubanApi().tv_detail(doubanid)
                    if not douban_info or douban_info.get("localized_message"):
                        return 1, "无法查询到豆瓣媒体信息", None
                    media_info = MetaInfo(title="%s %s".strip() % (douban_info.get('title'), year), mtype=mtype)
                    # 以IMDBID查询TMDB
                    if douban_info.get("imdbid"):
                        tmdbid = Media().get_tmdbid_by_imdbid(douban_info.get("imdbid"))
                        if tmdbid:
                            media_info.set_tmdb_info(Media().get_tmdb_info(mtype=mtype, tmdbid=tmdbid))
                    # 无法识别TMDB时以豆瓣信息订阅
                    if not media_info.tmdb_info:
                        media_info.title = douban_info.get('title')
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
                    if season or media_info.begin_season is not None:
                        season = int(season) if season else media_info.begin_season
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
                if rssid:
                    SqlHelper.delete_rss_tv(rssid=rssid)
                SqlHelper.insert_rss_tv(media_info=media_info,
                                        total=media_info.total_episodes,
                                        lack=media_info.total_episodes,
                                        sites=sites,
                                        search_sites=search_sites,
                                        over_edition=over_edition,
                                        rss_restype=rss_restype,
                                        rss_pix=rss_pix,
                                        rss_team=rss_team,
                                        rss_rule=rss_rule,
                                        state=state,
                                        match=match,
                                        total_ep=total_ep,
                                        current_ep=current_ep)
            else:
                if rssid:
                    SqlHelper.delete_rss_movie(rssid=rssid)
                SqlHelper.insert_rss_movie(media_info=media_info,
                                           sites=sites,
                                           search_sites=search_sites,
                                           over_edition=over_edition,
                                           rss_restype=rss_restype,
                                           rss_pix=rss_pix,
                                           rss_team=rss_team,
                                           rss_rule=rss_rule,
                                           state=state)
        else:
            # 模糊匹配
            media_info = MetaInfo(title=name, mtype=mtype)
            media_info.title = name
            media_info.type = mtype
            if season:
                media_info.begin_season = int(season)
            if mtype == MediaType.MOVIE:
                if rssid:
                    SqlHelper.delete_rss_movie(rssid=rssid)
                SqlHelper.insert_rss_movie(media_info=media_info,
                                           state="R",
                                           sites=sites,
                                           search_sites=search_sites,
                                           over_edition=over_edition,
                                           rss_restype=rss_restype,
                                           rss_pix=rss_pix,
                                           rss_team=rss_team,
                                           rss_rule=rss_rule)
            else:
                if rssid:
                    SqlHelper.delete_rss_tv(rssid=rssid)
                SqlHelper.insert_rss_tv(media_info=media_info,
                                        total=0,
                                        lack=0,
                                        state="R",
                                        sites=sites,
                                        search_sites=search_sites,
                                        over_edition=over_edition,
                                        rss_restype=rss_restype,
                                        rss_pix=rss_pix,
                                        rss_team=rss_team,
                                        rss_rule=rss_rule,
                                        match=match,
                                        total_ep=total_ep,
                                        current_ep=current_ep)

        return 0, "添加订阅成功", media_info

    @staticmethod
    def finish_rss_subscribe(rtype, rssid, media):
        """
        完成订阅
        :param rtype: 订阅类型
        :param rssid: 订阅ID
        :param media: 识别的媒体信息，发送消息使用
        """
        if not rtype or not rssid or not media:
            return
        # 电影订阅
        if rtype == "MOV":
            # 查询电影RSS数据
            rss = SqlHelper.get_rss_movies(rssid=rssid)
            if not rss:
                return
            # 登记订阅历史
            SqlHelper.insert_rss_history(rssid=rssid,
                                         rtype=rtype,
                                         name=rss[0][0],
                                         year=rss[0][1],
                                         tmdbid=rss[0][2],
                                         image=media.get_poster_image(),
                                         desc=media.overview)

            # 删除订阅
            SqlHelper.delete_rss_movie(rssid=rssid)

        # 电视剧订阅
        else:
            # 查询电视剧RSS数据
            rss = SqlHelper.get_rss_tvs(rssid=rssid)
            if not rss:
                return
            # 解析RSS属性
            rss_info = Torrent.get_rss_note_item(rss[0][5])
            total_ep = rss_info.get("episode_info", {}).get("total")
            start_ep = rss_info.get("episode_info", {}).get("current")
            # 登记订阅历史
            SqlHelper.insert_rss_history(rssid=rssid,
                                         rtype=rtype,
                                         name=rss[0][0],
                                         year=rss[0][1],
                                         season=rss[0][2],
                                         tmdbid=rss[0][3],
                                         image=media.get_poster_image(),
                                         desc=media.overview,
                                         total=total_ep if total_ep else rss[0][6],
                                         start=start_ep)
            # 删除订阅
            SqlHelper.delete_rss_tv(rssid=rssid)

        # 发送订阅完成的消息
        if media:
            Message().send_rss_finished_message(media_info=media)
