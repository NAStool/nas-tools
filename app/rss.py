import json
import traceback
import xml.dom.minidom
from threading import Lock

import log
from app.helper import DbHelper
from app.message import Message
from app.downloader.downloader import Downloader
from app.filter import Filter
from app.searcher import Searcher
from app.sites import Sites
from app.utils import DomUtils, RequestUtils, StringUtils
from app.helper import MetaHelper
from app.media import MetaInfo, Media
from app.utils.rsstitle_utils import RssTitleUtils
from app.utils.types import MediaType, SearchType
from app.subscribe import Subscribe

from config import TORRENT_SEARCH_PARAMS
lock = Lock()


class Rss:
    __sites = []
    filter = None
    message = None
    media = None
    downloader = None
    searcher = None
    metahelper = None
    dbhelper = None
    subscribe = None

    def __init__(self):
        self.message = Message()
        self.media = Media()
        self.downloader = Downloader()
        self.searcher = Searcher()
        self.sites = Sites()
        self.filter = Filter()
        self.metahelper = MetaHelper()
        self.dbhelper = DbHelper()
        self.subscribe = Subscribe()
        self.init_config()

    def init_config(self):
        self.__sites = self.sites.get_sites(rss=True)

    def rssdownload(self):
        """
        RSS订阅检索下载入口，由定时服务调用
        """
        if not self.__sites:
            return
        with lock:
            log_info("【Rss】开始RSS订阅...")
            # 读取电影订阅
            rss_movies = self.get_rss_movies(state='R')
            if not rss_movies:
                log_warn("【Rss】没有正在订阅的电影")
            else:
                log_info("【Rss】电影订阅清单：%s" % " ".join('%s' % rss_movies[id].get("name") for id in rss_movies))
            # 读取电视剧订阅
            rss_tvs = self.get_rss_tvs(state='R')
            if not rss_tvs:
                log_warn("【Rss】没有正在订阅的电视剧")
            else:
                log_info("【Rss】电视剧订阅清单：%s" % " ".join('%s' % rss_tvs[id].get("name") for id in rss_tvs))
            # 没有订阅退出
            if not rss_movies and not rss_tvs:
                return
            # 获取有订阅的站点范围
            check_sites = []
            check_all = False
            for id in rss_movies:
                rss_sites = rss_movies[id].get("rss_sites")
                if not rss_sites:
                    check_all = True
                    break
                else:
                    check_sites += rss_sites
            if not check_all:
                for id in rss_tvs:
                    rss_sites = rss_tvs[id].get("rss_sites")
                    if not rss_sites:
                        check_all = True
                        break
                    else:
                        check_sites += rss_sites
            if check_all:
                check_sites = []
            else:
                check_sites = list(set(check_sites))

            # 代码站点配置优先级的序号
            rss_download_torrents = []
            rss_no_exists = {}
            for site_info in self.__sites:
                if not site_info:
                    continue
                site_id = site_info.get("id")
                # 没有订阅的站点中的不检索
                if check_sites and site_id not in check_sites:
                    continue
                # 站点名称
                site_name = site_info.get("name")
                # 站点rss链接
                rss_url = site_info.get("rssurl")
                if not rss_url:
                    log_info(f"【Rss】{site_name} 未配置rssurl，跳过...")
                    continue
                site_cookie = site_info.get("cookie")
                site_ua = site_info.get("ua")
                # 是否解析种子详情
                site_parse = False if site_info.get("parse") == "N" else True
                # 使用的规则
                site_fliter_rule = site_info.get("rule")
                # 开始下载RSS
                log_info(f"【Rss】正在处理：{site_name}")
                if site_info.get("pri"):
                    site_order = 100 - int(site_info.get("pri"))
                else:
                    site_order = 0
                rss_acticles = self.parse_rssxml(rss_url)
                if not rss_acticles:
                    log_warn(f"【Rss】{site_name} 未下载到数据")
                    continue
                else:
                    log_info(f"【Rss】{site_name} 获取数据：{len(rss_acticles)}")
                # 处理RSS结果
                res_num = 0
                for article in rss_acticles:
                    try:
                        # 种子名
                        title = article.get('title')
                        # 种子链接
                        enclosure = article.get('enclosure')
                        # 种子页面
                        page_url = article.get('link')
                        # 副标题
                        description = article.get('description')
                        # 种子大小
                        size = article.get('size')
                        # 开始处理
                        log_info(f"【Rss】开始处理：{title}")
                        # 检查这个种子是不是下过了
                        if self.dbhelper.is_torrent_rssd(enclosure):
                            log_info(f"【Rss】{title} 已成功订阅过")
                            continue
                        # 识别种子名称，开始检索TMDB
                        media_info = self.media.get_media_info(title=title, subtitle=description)
                        if not media_info:
                            log_warn(f"【Rss】{title} 识别媒体信息出错！")
                            continue
                        elif not media_info.tmdb_info:
                            log_info(f"【Rss】{title} 识别为 {media_info.get_name()} 未匹配到媒体信息")
                            continue
                        # 大小及种子页面
                        media_info.set_torrent_info(size=size,
                                                    page_url=page_url,
                                                    site=site_id,
                                                    site_order=site_order,
                                                    enclosure=enclosure)
                        # 检查种子是否匹配订阅，返回匹配到的订阅ID、是否洗版、总集数、上传因子、下载因子
                        match_info = self.filter.torrent_match_rss(
                            media_info=media_info,
                            rss_movies=rss_movies,
                            rss_tvs=rss_tvs,
                            site_filter_rule=site_fliter_rule,
                            site_cookie=site_cookie,
                            site_parse=site_parse,
                            site_ua=site_ua)
                        # 未匹配
                        if not match_info:
                            continue
                        # 非模糊匹配命中
                        if not match_info.get("fuzzy_match"):
                            # 如果是电影
                            if media_info.type == MediaType.MOVIE:
                                # 非洗版时检查是否存在
                                if not match_info.get("over_edition"):
                                    exist_flag, rss_no_exists, _ = self.downloader.check_exists_medias(
                                        meta_info=media_info,
                                        no_exists=rss_no_exists)
                                    if exist_flag:
                                        log_info(f"【Rss】电影 {media_info.get_title_string()} 已存在，删除订阅...")
                                        # 完成订阅
                                        self.subscribe.finish_rss_subscribe(rtype="MOV",
                                                                            rssid=match_info.get("id"),
                                                                            media=media_info)
                                        continue
                            # 如果是电视剧
                            else:
                                # 从登记薄中获取缺失剧集
                                season = 1
                                if match_info.get("season"):
                                    season = int(str(match_info.get("season")).replace("S", ""))
                                total_ep = match_info.get("total")
                                current_ep = match_info.get("current_ep")
                                episodes = self.dbhelper.get_rss_tv_episodes(match_info.get("id"))
                                if episodes is None:
                                    episodes = []
                                    if current_ep:
                                        episodes = list(range(current_ep, total_ep + 1))
                                    rss_no_exists[media_info.tmdb_id] = [
                                        {"season": season,
                                         "episodes": episodes,
                                         "total_episodes": total_ep}]
                                elif episodes:
                                    rss_no_exists[media_info.tmdb_id] = [
                                        {"season": season,
                                         "episodes": episodes,
                                         "total_episodes": total_ep}]
                                else:
                                    log_info("【Rss】电视剧 %s%s 已全部订阅完成，删除订阅..." % (
                                        media_info.title, media_info.get_season_string()))
                                    # 完成订阅
                                    self.subscribe.finish_rss_subscribe(rtype="TV",
                                                                        rssid=match_info.get("id"),
                                                                        media=media_info)
                                    continue
                                # 非洗版时检查本地媒体库情况
                                if not match_info.get("over_edition"):
                                    exist_flag, library_no_exists, _ = self.downloader.check_exists_medias(
                                        meta_info=media_info,
                                        total_ep={season: total_ep})
                                    # 当前剧集已存在，跳过
                                    if exist_flag:
                                        # 已全部存在
                                        if not library_no_exists or not library_no_exists.get(
                                                media_info.tmdb_id):
                                            log_info("【Rss】电视剧 %s 订阅剧集已全部存在，删除订阅..." % (
                                                media_info.get_title_string()))
                                            # 完成订阅
                                            self.subscribe.finish_rss_subscribe(rtype="TV",
                                                                                rssid=match_info.get("id"),
                                                                                media=media_info)
                                        continue
                                    # 取交集做为缺失集
                                    rss_no_exists = self.__get_rss_no_exists(target=rss_no_exists,
                                                                             source=library_no_exists,
                                                                             title=media_info.tmdb_id)
                                    if rss_no_exists.get(media_info.tmdb_id):
                                        log_info("【Rss】%s 订阅缺失季集：%s" % (
                                            media_info.get_title_string(),
                                            rss_no_exists.get(media_info.tmdb_id)))
                        # 返回对象
                        media_info.set_torrent_info(res_order=match_info.get("res_order"),
                                                    download_volume_factor=match_info.get("download_volume_factor"),
                                                    upload_volume_factor=match_info.get("upload_volume_factor"),
                                                    rssid=match_info.get("id"),
                                                    description=description)
                        media_info.save_path = match_info.get("save_path")
                        media_info.download_setting = match_info.get("download_setting")
                        # 插入数据库
                        self.dbhelper.insert_rss_torrents(media_info)
                        # 加入下载列表
                        if media_info not in rss_download_torrents:
                            rss_download_torrents.append(media_info)
                            res_num = res_num + 1
                    except Exception as e:
                        log_error("【Rss】处理RSS发生错误：%s - %s" % (str(e), traceback.format_exc()))
                        continue
                log_info("【Rss】%s 处理结束，匹配到 %s 个有效资源" % (site_name, res_num))
            log_info("【Rss】所有RSS处理结束，共 %s 个有效资源" % len(rss_download_torrents))

            # 去重择优后开始添加下载
            if rss_download_torrents:
                download_items, left_medias = self.downloader.batch_download(SearchType.RSS,
                                                                             rss_download_torrents,
                                                                             rss_no_exists)
                # 批量删除订阅
                if download_items:
                    for item in download_items:
                        if item.type == MediaType.MOVIE:
                            # 删除电影订阅
                            if item.rssid:
                                log_info("【Rss】电影 %s 订阅完成，删除订阅..." % item.get_title_string())
                                self.subscribe.finish_rss_subscribe(rtype="MOV", rssid=item.rssid, media=item)
                        else:
                            if not left_medias or not left_medias.get(item.tmdb_id):
                                # 删除电视剧订阅
                                if item.rssid:
                                    log_info(
                                        "【Rss】电视剧 %s %s 订阅完成，删除订阅..." % (item.get_title_string(),
                                                                         item.get_season_string()))
                                    # 完成订阅
                                    self.subscribe.finish_rss_subscribe(rtype="TV", rssid=item.rssid, media=item)
                            else:
                                # 更新电视剧缺失剧集
                                left_media = left_medias.get(item.tmdb_id)
                                if not left_media:
                                    continue
                                for left_season in left_media:
                                    if item.is_in_season(left_season.get("season")):
                                        if left_season.get("episodes"):
                                            log_info("【Rss】更新电视剧 %s %s 订阅缺失集数为 %s" % (
                                                item.get_title_string(), item.get_season_string(),
                                                len(left_season.get("episodes"))))
                                            self.dbhelper.update_rss_tv_lack(rssid=item.rssid,
                                                                             lack_episodes=left_season.get("episodes"))
                                            break
                    log_info("【Rss】实际下载了 %s 个资源" % len(download_items))
                else:
                    log_info("【Rss】未下载到任何资源")

    def rsssearch_all(self):
        """
        搜索R状态的所有订阅，由定时服务调用
        """
        self.rsssearch(state="R")

    def rsssearch(self, state="D"):
        """
        RSS订阅队列中状态的任务处理，先进行存量资源检索，缺失的才标志为RSS状态，由定时服务调用
        """
        try:
            lock.acquire()
            # 处理电影
            self.rsssearch_movie(state=state)
            # 处理电视剧
            self.rsssearch_tv(state=state)
        finally:
            lock.release()

    def rsssearch_movie(self, rssid=None, state='D'):
        """
        检索电影RSS
        :param rssid: 订阅ID，未输入时检索所有状态为D的，输入时检索该ID任何状态的
        :param state: 检索的状态，默认为队列中才检索
        """
        if rssid:
            rss_movies = self.get_rss_movies(rid=rssid)
        else:
            rss_movies = self.get_rss_movies(state=state)
        if rss_movies:
            log_info("【Rss】共有 %s 个电影订阅需要检索" % len(rss_movies))
        for id in rss_movies:
            rss_info = rss_movies[id]
            # 跳过模糊匹配的
            if rss_info.get("fuzzy_match"):
                continue
            rssid = rss_info.get("id")
            name = rss_info.get("name")
            year = rss_info.get("year") or ""
            tmdbid = rss_info.get("tmdbid")
            # 开始搜索
            self.dbhelper.update_rss_movie_state(rssid=rssid, state='S')
            # 识别
            media_info = self.__get_media_info(tmdbid, name, year, MediaType.MOVIE)
            # 未识别到媒体信息
            if not media_info or not media_info.tmdb_info:
                self.dbhelper.update_rss_movie_state(rssid=rssid, state='R')
                continue
            # 非洗版的情况检查是否存在
            if not rss_info.get("over_edition"):
                # 检查是否存在
                exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info)
                # 已经存在
                if exist_flag:
                    log_info("【Rss】电影 %s 已存在，删除订阅..." % name)
                    self.subscribe.finish_rss_subscribe(rtype="MOV", rssid=rssid, media=media_info)
                    continue
            else:
                # 洗版时按缺失来下载
                no_exists = {}
            # 开始检索
            filter_dict = {
                "restype": rss_info.get('filter_restype'),
                "pix": rss_info.get('filter_pix'),
                "team": rss_info.get('filter_team'),
                "rule": rss_info.get('filter_rule')
            }
            search_result, no_exists, search_count, download_count = self.searcher.search_one_media(
                media_info=media_info,
                in_from=SearchType.RSS,
                no_exists=no_exists,
                sites=rss_info.get("search_sites"),
                filters=filter_dict)
            if search_result:
                log_info("【Rss】电影 %s 下载完成，删除订阅..." % name)
                self.subscribe.finish_rss_subscribe(rtype="MOV", rssid=rssid, media=media_info)
            else:
                self.dbhelper.update_rss_movie_state(rssid=rssid, state='R')

    def rsssearch_tv(self, rssid=None, state="D"):
        """
        检索电视剧RSS
        :param rssid: 订阅ID，未输入时检索所有状态为D的，输入时检索该ID任何状态的
        :param state: 检索的状态，默认为队列中才检索
        """
        if rssid:
            rss_tvs = self.get_rss_tvs(rid=rssid)
        else:
            rss_tvs = self.get_rss_tvs(state=state)
        if rss_tvs:
            log_info("【Rss】共有 %s 个电视剧订阅需要检索" % len(rss_tvs))
        rss_no_exists = {}
        for id in rss_tvs:
            rss_info = rss_tvs[id]
            # 跳过模糊匹配的
            if rss_info.get("fuzzy_match"):
                continue
            rssid = rss_info.get("id")
            name = rss_info.get("name")
            year = rss_info.get("year") or ""
            tmdbid = rss_info.get("tmdbid")
            # 开始搜索
            self.dbhelper.update_rss_tv_state(rssid=rssid, state='S')
            # 识别
            media_info = self.__get_media_info(tmdbid, name, year, MediaType.TV)
            # 未识别到媒体信息
            if not media_info or not media_info.tmdb_info:
                self.dbhelper.update_rss_tv_state(rssid=rssid, state='R')
                continue
            # 从登记薄中获取缺失剧集
            season = 1
            if rss_info.get("season"):
                season = int(str(rss_info.get("season")).replace("S", ""))
            total_ep = rss_info.get("total")
            current_ep = rss_info.get("current_ep")
            episodes = self.dbhelper.get_rss_tv_episodes(rss_info.get("id"))
            if episodes is None:
                episodes = []
                if current_ep:
                    episodes = list(range(current_ep, total_ep + 1))
                rss_no_exists[media_info.tmdb_id] = [
                    {"season": season,
                     "episodes": episodes,
                     "total_episodes": total_ep}]
            elif episodes:
                rss_no_exists[media_info.tmdb_id] = [
                    {"season": season,
                     "episodes": episodes,
                     "total_episodes": total_ep}]
            else:
                log_info("【Rss】电视剧 %s%s 已全部订阅完成，删除订阅..." % (
                    media_info.title, media_info.get_season_string()))
                # 完成订阅
                self.subscribe.finish_rss_subscribe(rtype="TV",
                                                    rssid=rss_info.get("id"),
                                                    media=media_info)
                continue
            # 非洗版时检查本地媒体库情况
            if not rss_info.get("over_edition"):
                exist_flag, library_no_exists, _ = self.downloader.check_exists_medias(
                    meta_info=media_info,
                    total_ep={season: total_ep})
                # 当前剧集已存在，跳过
                if exist_flag:
                    # 已全部存在
                    if not library_no_exists or not library_no_exists.get(
                            media_info.tmdb_id):
                        log_info("【Rss】电视剧 %s 订阅剧集已全部存在，删除订阅..." % (
                            media_info.get_title_string()))
                        # 完成订阅
                        self.subscribe.finish_rss_subscribe(rtype="TV",
                                                            rssid=rss_info.get("id"),
                                                            media=media_info)
                    continue
                # 取交集做为缺失集
                rss_no_exists = self.__get_rss_no_exists(target=rss_no_exists,
                                                         source=library_no_exists,
                                                         title=media_info.tmdb_id)
                if rss_no_exists.get(media_info.tmdb_id):
                    log_info("【Rss】%s 订阅缺失季集：%s" % (
                        media_info.get_title_string(),
                        rss_no_exists.get(media_info.tmdb_id)))

            # 开始检索
            filter_dict = {
                "restype": rss_info.get('filter_restype'),
                "pix": rss_info.get('filter_pix'),
                "team": rss_info.get('filter_team'),
                "rule": rss_info.get('filter_rule')
            }
            search_result, no_exists, search_count, download_count = self.searcher.search_one_media(
                media_info=media_info,
                in_from=SearchType.RSS,
                no_exists=rss_no_exists,
                sites=rss_info.get("search_sites"),
                filters=filter_dict)
            if not no_exists or not no_exists.get(media_info.tmdb_id):
                # 没有剩余或者剩余缺失季集中没有当前标题，说明下完了
                log_info("【Rss】电视剧 %s 下载完成，删除订阅..." % name)
                # 完成订阅
                self.subscribe.finish_rss_subscribe(rtype="TV", rssid=rssid, media=media_info)
            else:
                # 更新状态
                self.dbhelper.update_rss_tv_state(rssid=rssid, state='R')
                no_exist_items = no_exists.get(media_info.tmdb_id)
                for no_exist_item in no_exist_items:
                    if str(no_exist_item.get("season")) == media_info.get_season_seq():
                        if no_exist_item.get("episodes"):
                            log_info("【Rss】更新电视剧 %s %s 缺失集数为 %s" % (
                                media_info.get_title_string(), media_info.get_season_string(),
                                len(no_exist_item.get("episodes"))))
                            self.dbhelper.update_rss_tv_lack(rssid=rssid, lack_episodes=no_exist_item.get("episodes"))
                        break

    def refresh_rss_metainfo(self):
        """
        定时将豆瓣订阅转换为TMDB的订阅，并更新订阅的TMDB信息
        """
        # 更新电影
        rss_movies = self.get_rss_movies(state='R')
        for id in rss_movies:
            rss_info = rss_movies[id]
            # 跳过模糊匹配的
            if rss_info.get("fuzzy_match"):
                continue
            rssid = rss_info.get("id")
            name = rss_info.get("name")
            year = rss_info.get("year") or ""
            tmdbid = rss_info.get("tmdbid")
            # 更新TMDB信息
            media_info = self.__get_media_info(tmdbid=tmdbid,
                                               name=name,
                                               year=year,
                                               mtype=MediaType.MOVIE,
                                               cache=False)
            if media_info and media_info.tmdb_id and media_info.title != name:
                log_info(f"【Rss】检测到TMDB信息变化，更新电影订阅 {name} 为 {media_info.title}")
                # 更新订阅信息
                self.dbhelper.update_rss_movie_tmdb(rid=rssid,
                                                    tmdbid=media_info.tmdb_id,
                                                    title=media_info.title,
                                                    year=media_info.year,
                                                    image=media_info.get_message_image())
                # 清除TMDB缓存
                self.metahelper.delete_meta_data_by_tmdbid(media_info.tmdb_id)

        # 更新电视剧
        rss_tvs = self.get_rss_tvs(state='R')
        for id in rss_tvs:
            rss_info = rss_tvs[id]
            # 跳过模糊匹配的
            if rss_info.get("fuzzy_match"):
                continue
            rssid = rss_info.get("id")
            name = rss_info.get("name")
            year = rss_info.get("year") or ""
            tmdbid = rss_info.get("tmdbid")
            season = rss_info.get("season") or 1
            total = rss_info.get("total")
            total_ep = rss_info.get("total_ep")
            lack = rss_info.get("lack")
            # 更新TMDB信息
            media_info = self.__get_media_info(tmdbid=tmdbid,
                                               name=name,
                                               year=year,
                                               mtype=MediaType.TV,
                                               cache=False)
            if media_info and media_info.tmdb_id:
                # 获取总集数
                if not total_ep:
                    total_episode = self.media.get_tmdb_season_episodes_num(sea=int(str(season).replace("S", "")),
                                                                        tv_info=media_info.tmdb_info)
                else:
                    total_episode = total_ep
                # 设置总集数的，不更新集数
                if total_episode and (name != media_info.title or total != total_episode):
                    # 新的缺失集数
                    lack_episode = total_episode - (total - lack)
                    log_info(f"【Rss】检测到TMDB信息变化，更新电视剧订阅 {name} 为 {media_info.title}，总集数为：{total_episode}")
                    # 更新订阅信息
                    self.dbhelper.update_rss_tv_tmdb(rid=rssid,
                                                     tmdbid=media_info.tmdb_id,
                                                     title=media_info.title,
                                                     year=media_info.year,
                                                     total=total_episode,
                                                     lack=lack_episode,
                                                     image=media_info.get_message_image())
                    # 清除TMDB缓存
                    self.metahelper.delete_meta_data_by_tmdbid(media_info.tmdb_id)

    @staticmethod
    def __get_media_info(tmdbid, name, year, mtype, cache=True):
        """
        综合返回媒体信息
        """
        if tmdbid and not tmdbid.startswith("DB:"):
            media_info = MetaInfo(title="%s %s".strip() % (name, year))
            tmdb_info = Media().get_tmdb_info(mtype=mtype, title=name, year=year, tmdbid=tmdbid)
            media_info.set_tmdb_info(tmdb_info)
        else:
            media_info = Media().get_media_info(title="%s %s" % (name, year), mtype=mtype, strict=True, cache=cache)
        return media_info

    @staticmethod
    def parse_rssxml(url):
        """
        解析RSS订阅URL，获取RSS中的种子信息
        :param url: RSS地址
        :return: 种子信息列表
        """
        _special_title_sites = {
            'pt.keepfrds.com': RssTitleUtils.keepfriends_title
        }

        # 开始处理
        ret_array = []
        if not url:
            return []
        _, netloc = StringUtils.get_url_netloc(url)
        try:
            ret = RequestUtils().get_res(url)
            if not ret:
                return []
            ret.encoding = ret.apparent_encoding
        except Exception as e2:
            log.console(str(e2))
            return []
        if ret:
            ret_xml = ret.text
            try:
                # 解析XML
                dom_tree = xml.dom.minidom.parseString(ret_xml)
                rootNode = dom_tree.documentElement
                items = rootNode.getElementsByTagName("item")
                for item in items:
                    try:
                        # 标题
                        title = DomUtils.tag_value(item, "title", default="")
                        if not title:
                            continue
                        # 标题特殊处理
                        if netloc and netloc in _special_title_sites:
                            title = _special_title_sites.get(netloc)(title)
                        # 描述
                        description = DomUtils.tag_value(item, "description", default="")
                        # 种子页面
                        link = DomUtils.tag_value(item, "link", default="")
                        # 种子链接
                        enclosure = DomUtils.tag_value(item, "enclosure", "url", default="")
                        if not enclosure and not link:
                            continue
                        # 部分RSS只有link没有enclosure
                        if not enclosure and link:
                            enclosure = link
                            link = None
                        # 大小
                        size = DomUtils.tag_value(item, "enclosure", "length", default=0)
                        if size and str(size).isdigit():
                            size = int(size)
                        else:
                            size = 0
                        # 发布日期
                        pubdate = DomUtils.tag_value(item, "pubDate", default="")
                        if pubdate:
                            # 转换为时间
                            pubdate = StringUtils.get_time_stamp(pubdate)
                        # 返回对象
                        tmp_dict = {'title': title,
                                    'enclosure': enclosure,
                                    'size': size,
                                    'description': description,
                                    'link': link,
                                    'pubdate': pubdate}
                        ret_array.append(tmp_dict)
                    except Exception as e1:
                        log.console(str(e1))
                        continue
            except Exception as e2:
                log.console(str(e2))
                return ret_array
        return ret_array

    @staticmethod
    def __get_rss_no_exists(target, source, title):
        """
        对两个字典值进行判重，有相同项目的取集的交集
        """
        if not source or not title:
            return target
        if not source.get(title):
            return target
        if not target.get(title):
            target[title] = source.get(title)
            return target
        index = -1
        for target_info in target.get(title):
            index += 1
            source_info = None
            for info in source.get(title):
                if info.get("season") == target_info.get("season"):
                    source_info = info
                    break
            if not source_info:
                continue
            if not source_info.get("episodes"):
                continue
            if not target_info.get("episodes"):
                target_episodes = source_info.get("episodes")
                target[title][index]["episodes"] = target_episodes
                continue
            target_episodes = list(set(target_info.get("episodes")).intersection(set(source_info.get("episodes"))))
            target[title][index]["episodes"] = target_episodes
        return target

    def get_rss_movies(self, rid=None, state=None):
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
            over_edition = rss_movie.OVER_EDITION
            filter_restype = rss_movie.FILTER_RESTYPE
            filter_pix = rss_movie.FILTER_PIX
            filter_team = rss_movie.FILTER_TEAM
            filter_rule = rss_movie.FILTER_RULE
            download_setting = rss_movie.DOWNLOAD_SETTING
            save_path = rss_movie.SAVE_PATH
            fuzzy_match = rss_movie.FUZZY_MATCH
            if desc and not download_setting:
                desc = self.__parse_desc(desc)
                rss_sites = desc.get("rss_sites")
                search_sites = desc.get("search_sites")
                over_edition = desc.get("over_edition")
                filter_restype = desc.get("restype")
                filter_pix = desc.get("pix")
                filter_team = desc.get("team")
                filter_rule = desc.get("rule")
                download_setting = -1
                save_path = ""
                fuzzy_match = 0 if tmdbid else 1
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

    def get_rss_tvs(self, rid=None, state=None):
        ret_dict = {}
        rss_tvs = self.dbhelper.get_rss_tvs(rssid=rid, state=state)
        for rss_tv in rss_tvs:
            # 兼容旧配置
            desc = rss_tv.DESC
            tmdbid = rss_tv.TMDBID
            rss_sites = rss_tv.RSS_SITES
            rss_sites = json.loads(rss_sites) if rss_sites else []
            search_sites = rss_tv.SEARCH_SITES
            search_sites = json.loads(search_sites) if search_sites else []
            over_edition = rss_tv.OVER_EDITION
            filter_restype = rss_tv.FILTER_RESTYPE
            filter_pix = rss_tv.FILTER_PIX
            filter_team = rss_tv.FILTER_TEAM
            filter_rule = rss_tv.FILTER_RULE
            download_setting = rss_tv.DOWNLOAD_SETTING
            save_path = rss_tv.SAVE_PATH
            total_ep = rss_tv.TOTAL_EP
            current_ep = rss_tv.CURRENT_EP
            fuzzy_match = rss_tv.FUZZY_MATCH
            if desc and not download_setting:
                desc = self.__parse_desc(desc)
                rss_sites = desc.get("rss_sites")
                search_sites = desc.get("search_sites")
                over_edition = desc.get("over_edition")
                filter_restype = desc.get("restype")
                filter_pix = desc.get("pix")
                filter_team = desc.get("team")
                filter_rule = desc.get("rule")
                save_path = ""
                download_setting = -1
                total_ep = desc.get("total")
                current_ep = desc.get("current")
                fuzzy_match = 0 if tmdbid else 1
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

    def __parse_desc(self, desc):
        """
        解析订阅的DESC字段，从中获取订阅站点、搜索站点、是否洗版、订阅质量、订阅分辨率、订阅制作组/字幕组、过滤规则等信息
        DESC字段组成：RSS站点#搜索站点#是否洗版(Y/N)#过滤条件，站点用|分隔多个站点，过滤条件用@分隔多个条件
        :param desc: RSS订阅DESC字段的值
        :return: 订阅站点、搜索站点、是否洗版、过滤字典、总集数，当前集数
        """
        if not desc:
            return {}
        rss_sites = []
        search_sites = []
        over_edition = False
        restype = None
        pix = None
        team = None
        rule = None
        total = None
        current = None
        notes = str(desc).split('#')
        # 订阅站点
        if len(notes) > 0:
            if notes[0]:
                rss_sites = [site for site in notes[0].split('|') if site and len(site) < 20]
                if rss_sites:
                    rss_sites_dict = {site["name"]: site["id"] for site in self.__sites}
                    rss_sites = [rss_sites_dict[site] for site in rss_sites if rss_sites_dict.get("site")]
        # 搜索站点
        if len(notes) > 1:
            if notes[1]:
                search_sites = [site for site in notes[1].split('|') if site]
                if search_sites:
                    search_sites_dict = {str(site.id): site.name for site in self.searcher.indexer.get_indexers()}
                    search_sites = [search_sites_dict[site] for site in search_sites if search_sites_dict.get("site")]
        # 洗版
        if len(notes) > 2:
            if notes[2] == 'Y':
                over_edition = 1
            else:
                over_edition = 0
        # 过滤条件
        if len(notes) > 3:
            if notes[3]:
                filters = notes[3].split('@')
                if len(filters) > 0:
                    restype = filters[0]
                    if restype:
                        restype_dict = TORRENT_SEARCH_PARAMS.get("restype")
                        restype_dict = {restype_dict[id]["name"]: int(id) for id in restype_dict}
                        restype = restype_dict[restype] if restype_dict.get(restype) else 0
                    else:
                        restype = 0
                if len(filters) > 1:
                    pix = filters[1]
                    if pix:
                        pix_dict = TORRENT_SEARCH_PARAMS.get("pix")
                        pix_dict = {pix_dict[id]["name"]: int(id) for id in pix_dict}
                        pix = pix_dict[pix] if pix_dict.get(pix) else 0
                    else:
                        pix = 0
                if len(filters) > 2:
                    rule = filters[2]
                    rule = int(rule) if rule else 0
                if len(filters) > 3:
                    team = filters[3] or ""
        # 总集数及当前集数
        if len(notes) > 4:
            if notes[4]:
                ep_info = notes[4].split('@')
                if len(ep_info) > 0:
                    total = ep_info[0]
                    total = int(total) if total else 0
                if len(ep_info) > 1:
                    current = ep_info[1]
                    current = int(current) if current else 0
        return {
            "rss_sites": rss_sites,
            "search_sites": search_sites,
            "over_edition": over_edition,
            "restype": restype,
            "pix": pix,
            "team": team,
            "rule": rule,
            "total": total,
            "current": current
        }


def log_info(text):
    log.info(text, module="rss")


def log_warn(text):
    log.warn(text, module="rss")


def log_error(text):
    log.error(text, module="rss")
