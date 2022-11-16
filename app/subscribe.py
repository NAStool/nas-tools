import json

from app.media.douban import DouBan
from app.helper import DbHelper
from app.media import MetaInfo, Media
from app.message import Message
from app.utils.types import MediaType


class Subscribe:
    dbhelper = None

    def __init__(self):
        self.dbhelper = DbHelper()

    def add_rss_subscribe(self, mtype, name, year,
                          season=None,
                          fuzzy_match=False,
                          doubanid=None,
                          tmdbid=None,
                          rss_sites=None,
                          search_sites=None,
                          over_edition=False,
                          filter_restype=None,
                          filter_pix=None,
                          filter_team=None,
                          filter_rule=None,
                          save_path=None,
                          download_setting=None,
                          total_ep=None,
                          current_ep=None,
                          state="D",
                          rssid=None):
        """
        添加电影、电视剧订阅
        :param mtype: 类型，电影、电视剧、动漫
        :param name: 标题
        :param year: 年份，如要是剧集需要是首播年份
        :param season: 第几季，数字
        :param fuzzy_match: 是否模糊匹配
        :param doubanid: 豆瓣ID，有此ID时从豆瓣查询信息
        :param tmdbid: TMDBID，有此ID时优先使用ID查询TMDB信息，没有则使用名称查询
        :param rss_sites: 订阅站点列表，为空则表示全部站点
        :param search_sites: 搜索站点列表，为空则表示全部站点
        :param over_edition: 是否选版
        :param filter_restype: 质量过滤
        :param filter_pix: 分辨率过滤
        :param filter_team: 制作组/字幕组过滤
        :param filter_rule: 关键字过滤
        :param save_path: 保存路径
        :param download_setting: 下载设置
        :param state: 添加订阅时的状态
        :param rssid: 修改订阅时传入
        :param total_ep: 总集数
        :param current_ep: 开始订阅集数
        :return: 错误码：0代表成功，错误信息
        """
        if not name:
            return -1, "标题或类型有误", None
        year = int(year) if str(year).isdigit() else ""
        rss_sites = rss_sites or []
        search_sites = search_sites or []
        over_edition = 1 if over_edition else 0
        filter_rule = int(filter_rule) if str(filter_rule).isdigit() else None
        total_ep = int(total_ep) if str(total_ep).isdigit() else None
        current_ep = int(current_ep) if str(current_ep).isdigit() else None
        download_setting = int(download_setting) if str(download_setting).isdigit() else -1
        fuzzy_match = 1 if fuzzy_match else 0
        # 检索媒体信息
        if not fuzzy_match:
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
                                                  strict=True if year else False,
                                                  cache=False)
                if media_info and media_info.tmdb_info:
                    tmdbid = media_info.tmdb_id
                elif doubanid:
                    # 先从豆瓣网页抓取（含TMDBID）
                    douban_info = DouBan().get_media_detail_from_web(doubanid)
                    if not douban_info:
                        douban_info = DouBan().get_douban_detail(doubanid=doubanid, mtype=mtype)
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
                    self.dbhelper.delete_rss_tv(rssid=rssid)
                if total_ep:
                    total = total_ep
                else:
                    total = media_info.total_episodes
                if current_ep:
                    lack = total - current_ep - 1
                else:
                    lack = total
                code = self.dbhelper.insert_rss_tv(media_info=media_info,
                                                   total=total,
                                                   lack=lack,
                                                   state=state,
                                                   rss_sites=rss_sites,
                                                   search_sites=search_sites,
                                                   over_edition=over_edition,
                                                   filter_restype=filter_restype,
                                                   filter_pix=filter_pix,
                                                   filter_team=filter_team,
                                                   filter_rule=filter_rule,
                                                   save_path=save_path,
                                                   download_setting=download_setting,
                                                   total_ep=total_ep,
                                                   current_ep=current_ep,
                                                   fuzzy_match=0)
            else:
                if rssid:
                    self.dbhelper.delete_rss_movie(rssid=rssid)
                code = self.dbhelper.insert_rss_movie(media_info=media_info,
                                                      state=state,
                                                      rss_sites=rss_sites,
                                                      search_sites=search_sites,
                                                      over_edition=over_edition,
                                                      filter_restype=filter_restype,
                                                      filter_pix=filter_pix,
                                                      filter_team=filter_team,
                                                      filter_rule=filter_rule,
                                                      save_path=save_path,
                                                      download_setting=download_setting,
                                                      fuzzy_match=0)
        else:
            # 模糊匹配
            media_info = MetaInfo(title=name, mtype=mtype)
            media_info.title = name
            media_info.type = mtype
            if season:
                media_info.begin_season = int(season)
            if mtype == MediaType.MOVIE:
                if rssid:
                    self.dbhelper.delete_rss_movie(rssid=rssid)
                code = self.dbhelper.insert_rss_movie(media_info=media_info,
                                                      state="R",
                                                      rss_sites=rss_sites,
                                                      search_sites=search_sites,
                                                      over_edition=over_edition,
                                                      filter_restype=filter_restype,
                                                      filter_pix=filter_pix,
                                                      filter_team=filter_team,
                                                      filter_rule=filter_rule,
                                                      save_path=save_path,
                                                      download_setting=download_setting,
                                                      fuzzy_match=1)
            else:
                if rssid:
                    self.dbhelper.delete_rss_tv(rssid=rssid)
                code = self.dbhelper.insert_rss_tv(media_info=media_info,
                                                   total=0,
                                                   lack=0,
                                                   state="R",
                                                   rss_sites=rss_sites,
                                                   search_sites=search_sites,
                                                   over_edition=over_edition,
                                                   filter_restype=filter_restype,
                                                   filter_pix=filter_pix,
                                                   filter_team=filter_team,
                                                   filter_rule=filter_rule,
                                                   save_path=save_path,
                                                   download_setting=download_setting,
                                                   fuzzy_match=1)

        if code == 0:
            return code, "添加订阅成功", media_info
        elif code == 9:
            return code, "订阅已存在", media_info
        else:
            return code, "添加订阅失败", media_info

    def finish_rss_subscribe(self, rtype, rssid, media):
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
            rss = self.dbhelper.get_rss_movies(rssid=rssid)
            if not rss:
                return
            # 登记订阅历史
            self.dbhelper.insert_rss_history(rssid=rssid,
                                             rtype=rtype,
                                             name=rss[0].NAME,
                                             year=rss[0].YEAR,
                                             tmdbid=rss[0].TMDBID,
                                             image=media.get_poster_image(),
                                             desc=media.overview)

            # 删除订阅
            self.dbhelper.delete_rss_movie(rssid=rssid)

        # 电视剧订阅
        else:
            # 查询电视剧RSS数据
            rss = self.dbhelper.get_rss_tvs(rssid=rssid)
            if not rss:
                return
            total = rss[0].TOTAL_EP
            # 登记订阅历史
            self.dbhelper.insert_rss_history(rssid=rssid,
                                             rtype=rtype,
                                             name=rss[0].NAME,
                                             year=rss[0].YEAR,
                                             season=rss[0].SEASON,
                                             tmdbid=rss[0].TMDBID,
                                             image=media.get_poster_image(),
                                             desc=media.overview,
                                             total=total if total else rss[0].TOTAL,
                                             start=rss[0].CURRENT_EP)
            # 删除订阅
            self.dbhelper.delete_rss_tv(rssid=rssid)

        # 发送订阅完成的消息
        if media:
            Message().send_rss_finished_message(media_info=media)

    def get_subscribe_movies(self, rid=None, state=None):
        """
        获取电影订阅
        """
        ret_dict = {}
        rss_movies = self.dbhelper.get_rss_movies(rssid=rid, state=state)
        for rss_movie in rss_movies:
            # 兼容旧配置
            desc = rss_movie.DESC
            tmdbid = rss_movie.TMDBID
            rss_sites = rss_movie.RSS_SITES
            rss_sites = json.loads(rss_sites) if rss_sites else []
            search_sites = rss_movie.SEARCH_SITES
            search_sites = json.loads(search_sites) if search_sites else []
            over_edition = True if rss_movie.OVER_EDITION == 1 else False
            filter_restype = rss_movie.FILTER_RESTYPE
            filter_pix = rss_movie.FILTER_PIX
            filter_team = rss_movie.FILTER_TEAM
            filter_rule = rss_movie.FILTER_RULE
            download_setting = rss_movie.DOWNLOAD_SETTING
            save_path = rss_movie.SAVE_PATH
            fuzzy_match = True if rss_movie.FUZZY_MATCH == 1 else False
            if desc and not download_setting:
                desc = self.__parse_rss_desc(desc)
                rss_sites = desc.get("rss_sites")
                search_sites = desc.get("search_sites")
                over_edition = True if desc.get("over_edition") == 'Y' else False
                filter_restype = desc.get("restype")
                filter_pix = desc.get("pix")
                filter_team = desc.get("team")
                filter_rule = desc.get("rule")
                download_setting = -1
                save_path = ""
                fuzzy_match = False if tmdbid else True
            ret_dict[str(rss_movie.ID)] = {
                "id": rss_movie.ID,
                "name": rss_movie.NAME,
                "year": rss_movie.YEAR,
                "tmdbid": rss_movie.TMDBID,
                "image": rss_movie.IMAGE,
                "rss_sites": rss_sites,
                "search_sites": search_sites,
                "over_edition": over_edition,
                "filter_restype": filter_restype,
                "filter_pix": filter_pix,
                "filter_team": filter_team,
                "filter_rule": filter_rule,
                "save_path": save_path,
                "download_setting": download_setting,
                "fuzzy_match": fuzzy_match,
                "state": rss_movie.STATE
            }
        return ret_dict

    def get_subscribe_tvs(self, rid=None, state=None):
        ret_dict = {}
        rss_tvs = self.dbhelper.get_rss_tvs(rssid=rid, state=state)
        for rss_tv in rss_tvs:
            # 兼容旧配置
            desc = rss_tv.DESC
            tmdbid = rss_tv.TMDBID
            rss_sites = json.loads(rss_tv.RSS_SITES) if rss_tv.RSS_SITES else []
            search_sites = json.loads(rss_tv.SEARCH_SITES) if rss_tv.SEARCH_SITES else []
            over_edition = True if rss_tv.OVER_EDITION == 1 else False
            filter_restype = rss_tv.FILTER_RESTYPE
            filter_pix = rss_tv.FILTER_PIX
            filter_team = rss_tv.FILTER_TEAM
            filter_rule = rss_tv.FILTER_RULE
            download_setting = rss_tv.DOWNLOAD_SETTING
            save_path = rss_tv.SAVE_PATH
            total_ep = rss_tv.TOTAL_EP
            current_ep = rss_tv.CURRENT_EP
            fuzzy_match = True if rss_tv.FUZZY_MATCH == 1 else False
            if desc and not download_setting:
                desc = self.__parse_rss_desc(desc)
                rss_sites = desc.get("rss_sites")
                search_sites = desc.get("search_sites")
                over_edition = True if desc.get("over_edition") == 'Y' else False
                filter_restype = desc.get("restype")
                filter_pix = desc.get("pix")
                filter_team = desc.get("team")
                filter_rule = desc.get("rule")
                save_path = ""
                download_setting = -1
                total_ep = desc.get("total")
                current_ep = desc.get("current")
                fuzzy_match = False if tmdbid else True
            ret_dict[str(rss_tv.ID)] = {
                "id": rss_tv.ID,
                "name": rss_tv.NAME,
                "year": rss_tv.YEAR,
                "season": rss_tv.SEASON,
                "tmdbid": rss_tv.TMDBID,
                "image": rss_tv.IMAGE,
                "rss_sites": rss_sites,
                "search_sites": search_sites,
                "over_edition": over_edition,
                "filter_restype": filter_restype,
                "filter_pix": filter_pix,
                "filter_team": filter_team,
                "filter_rule": filter_rule,
                "save_path": save_path,
                "download_setting": download_setting,
                "total": rss_tv.TOTAL,
                "lack": rss_tv.LACK,
                "total_ep": total_ep,
                "current_ep": current_ep,
                "fuzzy_match": fuzzy_match,
                "state": rss_tv.STATE
            }
        return ret_dict

    @staticmethod
    def __parse_rss_desc(desc):
        """
        解析订阅的DESC字段，从中获取订阅站点、搜索站点、是否洗版、订阅质量、订阅分辨率、订阅制作组/字幕组、过滤规则等信息
        DESC字段组成：RSS站点#搜索站点#是否洗版(Y/N)#过滤条件，站点用|分隔多个站点，过滤条件用@分隔多个条件
        :param desc: RSS订阅DESC字段的值
        :return: 订阅站点、搜索站点、是否洗版、过滤字典、总集数，当前集数
        """
        if not desc:
            return {}
        return json.loads(desc)
