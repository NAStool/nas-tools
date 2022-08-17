import traceback
from threading import Lock

import re
from urllib import parse
import xml.dom.minidom
import log
from pt.filterrules import FilterRule
from pt.searcher import Searcher
from message.send import Message
from pt.downloader import Downloader
from pt.siteconf import RSS_EXTRA_SITES
from pt.sites import Sites
from pt.torrent import Torrent
from rmt.media import Media
from rmt.meta.metabase import MetaBase
from rmt.metainfo import MetaInfo
from utils.functions import tag_value, str_filesize
from utils.http_utils import RequestUtils
from utils.meta_helper import MetaHelper
from utils.sqls import get_rss_movies, get_rss_tvs, insert_rss_torrents, \
    is_torrent_rssd, delete_rss_movie, delete_rss_tv, update_rss_tv_lack, \
    update_rss_movie_state, update_rss_tv_state, update_rss_movie_tmdb, update_rss_tv_tmdb, get_rss_tv_episodes
from utils.types import MediaType, SearchType

lock = Lock()


class Rss:
    __sites = None
    filterrule = None
    message = None
    media = None
    downloader = None
    searcher = None
    metahelper = None

    def __init__(self):
        self.message = Message()
        self.media = Media()
        self.downloader = Downloader()
        self.searcher = Searcher()
        self.sites = Sites()
        self.filterrule = FilterRule()
        self.metahelper = MetaHelper()
        self.init_config()

    def init_config(self):
        self.__sites = self.sites.get_sites()

    def rssdownload(self):
        """
        RSS订阅检索下载入口，由定时服务调用
        """
        if not self.__sites:
            return
        try:
            lock.acquire()
            log.info("【RSS】开始RSS订阅...")
            # 读取电影订阅
            movie_keys = get_rss_movies(state='R')
            if not movie_keys:
                log.warn("【RSS】没有正在订阅的电影")
            else:
                log.info("【RSS】电影订阅清单：%s" % " ".join('%s' % key[0] for key in movie_keys))
            # 读取电视剧订阅
            tv_keys = get_rss_tvs(state='R')
            if not tv_keys:
                log.warn("【RSS】没有正在订阅的电视剧")
            else:
                log.info("【RSS】电视剧订阅清单：%s" % " ".join('%s' % key[0] for key in tv_keys))
            # 没有订阅退出
            if not movie_keys and not tv_keys:
                return
            # 获取有订阅的站点范围
            check_sites = []
            check_all = False
            for movie in movie_keys:
                rss_sites, _, _, _ = Torrent.get_rss_note_item(movie[4])
                if not rss_sites:
                    check_all = True
                    break
                else:
                    check_sites += rss_sites
            if not check_all:
                for tv in tv_keys:
                    rss_sites, _, _, _ = Torrent.get_rss_note_item(tv[5])
                    if not rss_sites:
                        check_all = True
                        break
                    else:
                        check_sites += rss_sites
            if check_all:
                check_sites = []

            # 代码站点配置优先级的序号
            order_seq = 100
            rss_download_torrents = []
            rss_no_exists = {}
            for site_info in self.__sites:
                if not site_info:
                    continue
                # 站点名称
                rss_job = site_info.get("name")
                # 没有订阅的站点中的不检索
                if check_sites and rss_job not in check_sites:
                    continue
                rssurl = site_info.get("rssurl")
                if not rssurl:
                    log.info("【RSS】%s 未配置rssurl，跳过..." % str(rss_job))
                    continue
                rss_cookie = site_info.get("cookie")
                # 是否解析种子详情
                site_parse = False if site_info.get("parse") == "N" else True
                # 使用的规则
                site_rule_group = site_info.get("rule")
                # 开始下载RSS
                log.info("【RSS】正在处理：%s" % rss_job)
                order_seq -= 1
                rss_result = self.parse_rssxml(rssurl)
                if len(rss_result) == 0:
                    log.warn("【RSS】%s 未下载到数据" % rss_job)
                    continue
                else:
                    log.info("【RSS】%s 获取数据：%s" % (rss_job, len(rss_result)))
                # 处理RSS结果
                res_num = 0
                for res in rss_result:
                    try:
                        # 种子名
                        torrent_name = res.get('title')
                        # 种子链接
                        enclosure = res.get('enclosure')
                        # 种子页面
                        page_url = res.get('link')
                        # 副标题
                        description = res.get('description')
                        # 种子大小
                        size = res.get('size')

                        log.info("【RSS】开始处理：%s" % torrent_name)

                        # 检查这个种子是不是下过了
                        if is_torrent_rssd(enclosure):
                            log.info("【RSS】%s 已成功订阅过" % torrent_name)
                            continue
                        # 识别种子名称，开始检索TMDB
                        media_info = self.media.get_media_info(title=torrent_name, subtitle=description)
                        if not media_info or not media_info.tmdb_info:
                            log.debug("【RSS】%s 未识别到媒体信息" % torrent_name)
                            continue
                        # 大小及种子页面
                        media_info.set_torrent_info(size=size,
                                                    page_url=page_url,
                                                    site=rss_job,
                                                    site_order=order_seq,
                                                    enclosure=enclosure)
                        # 检查种子是否匹配订阅，返回匹配到的订阅ID、是否洗版、总集数、上传因子、下载因子
                        match_rssid, over_edition, total_episodes, res_order, upload_volume_factor, download_volume_factor = self.__is_torrent_match_rss(
                            media_info=media_info,
                            movie_keys=movie_keys,
                            tv_keys=tv_keys,
                            site_rule=site_rule_group,
                            site_cookie=rss_cookie,
                            site_parse=site_parse)
                        if match_rssid is not None:
                            log.info("【RSS】%s %s%s 匹配成功" % (media_info.org_string,
                                                            media_info.get_title_string(),
                                                            media_info.get_season_episode_string()))
                        else:
                            log.info("【RSS】%s %s 不匹配订阅" % (media_info.org_string, media_info.get_title_string()))
                            continue

                        # 非模糊匹配命中
                        if match_rssid:
                            # 如果是电影
                            if media_info.type == MediaType.MOVIE:
                                # 非洗版时检查是否存在
                                if not over_edition:
                                    exist_flag, rss_no_exists, _ = self.downloader.check_exists_medias(
                                        meta_info=media_info,
                                        no_exists=rss_no_exists)
                                    if exist_flag:
                                        log.info("【RSS】电影 %s 已存在，删除订阅..." % media_info.get_title_string())
                                        delete_rss_movie(rssid=match_rssid)
                                        continue
                            # 如果是电视剧
                            else:
                                # 从登记薄中获取缺失剧集
                                episodes = get_rss_tv_episodes(match_rssid)
                                if episodes is None:
                                    rss_no_exists[media_info.get_title_string()] = [
                                        {"season": media_info.begin_season, "episodes": [],
                                         "total_episodes": total_episodes}]
                                elif episodes:
                                    rss_no_exists[media_info.get_title_string()] = [
                                        {"season": media_info.begin_season, "episodes": episodes,
                                         "total_episodes": total_episodes}]
                                else:
                                    log.info("【RSS】电视剧 %s%s 已全部订阅完成，删除订阅..." % (
                                        media_info.title, media_info.get_season_string()))
                                    delete_rss_tv(rssid=match_rssid)
                                    continue
                                # 非洗版时检查本地媒体库情况
                                if not over_edition:
                                    exist_flag, library_no_exists, _ = self.downloader.check_exists_medias(
                                        meta_info=media_info)
                                    # 当前剧集已存在，跳过
                                    if exist_flag:
                                        # 已全部存在
                                        if not library_no_exists or not library_no_exists.get(
                                                media_info.get_title_string()):
                                            log.info("【RSS】电视剧 %s %s 已存在，删除订阅..." % (
                                                media_info.get_title_string(), media_info.get_season_string()))
                                            delete_rss_tv(rssid=match_rssid)
                                        continue
                                    # 取交集做为缺失集
                                    rss_no_exists = self.__get_rss_no_exists(target=rss_no_exists,
                                                                             source=library_no_exists,
                                                                             title=media_info.get_title_string())
                        # 返回对象
                        media_info.set_torrent_info(res_order=res_order,
                                                    download_volume_factor=download_volume_factor,
                                                    upload_volume_factor=upload_volume_factor,
                                                    rssid=match_rssid,
                                                    description=description)
                        # 插入数据库
                        insert_rss_torrents(media_info)
                        # 加入下载列表
                        if media_info not in rss_download_torrents:
                            rss_download_torrents.append(media_info)
                            res_num = res_num + 1
                    except Exception as e:
                        log.error("【RSS】处理RSS发生错误：%s - %s" % (str(e), traceback.format_exc()))
                        continue
                log.info("【RSS】%s 处理结束，匹配到 %s 个有效资源" % (rss_job, res_num))
            log.info("【RSS】所有RSS处理结束，共 %s 个有效资源" % len(rss_download_torrents))
            # 去重择优后开始添加下载
            download_items, left_medias = self.downloader.check_and_add_pt(SearchType.RSS,
                                                                           rss_download_torrents,
                                                                           rss_no_exists)
            # 批量删除订阅
            if download_items:
                for item in download_items:
                    if item.type == MediaType.MOVIE:
                        # 删除电影订阅
                        if item.rssid:
                            log.info("【RSS】电影 %s 订阅完成，删除订阅..." % item.get_title_string())
                            delete_rss_movie(rssid=item.rssid)
                    else:
                        if not left_medias or not left_medias.get(item.get_title_string()):
                            # 删除电视剧订阅
                            if item.rssid:
                                log.info(
                                    "【RSS】电视剧 %s %s 订阅完成，删除订阅..." % (item.get_title_string(),
                                                                     item.get_season_string()))
                                delete_rss_tv(rssid=item.rssid)
                        else:
                            # 更新电视剧缺失剧集
                            left_media = left_medias.get(item.get_title_string())
                            if not left_media:
                                continue
                            for left_season in left_media:
                                if item.is_in_season(left_season.get("season")):
                                    if left_season.get("episodes"):
                                        log.info("【RSS】更新电视剧 %s %s 订阅缺失集数为 %s" % (
                                            item.get_title_string(), item.get_season_string(),
                                            len(left_season.get("episodes"))))
                                        update_rss_tv_lack(rssid=item.rssid, lack_episodes=left_season.get("episodes"))
                                        break
                log.info("【RSS】实际下载了 %s 个资源" % len(download_items))
            else:
                log.info("【RSS】未下载到任何资源")
        finally:
            lock.release()

    def rsssearch_all(self):
        """
        搜索R状态的所有订阅，由定时服务调用
        """
        self.rsssearch(state="R")

    def rsssearch(self, state="D"):
        """
        RSS订阅队列中状态的任务处理，先进行存量PT资源检索，缺失的才标志为RSS状态，由定时服务调用
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
            movies = get_rss_movies(rssid=rssid)
        else:
            movies = get_rss_movies(state=state)
        if movies:
            log.info("【RSS】共有 %s 个电影订阅需要检索" % len(movies))
        for movie in movies:
            rssid = movie[6]
            name = movie[0]
            year = movie[1] or ""
            tmdbid = movie[2]
            # 跳过模糊匹配的
            if not tmdbid:
                continue
            # 开始搜索
            update_rss_movie_state(rssid=rssid, state='S')
            # 搜索站点、洗版、过滤条件
            _, sites, over_edition, filter_map = Torrent.get_rss_note_item(movie[4])
            # 识别
            media_info = self.__get_media_info(tmdbid, name, year, MediaType.MOVIE)
            # 未识别到媒体信息
            if not media_info or not media_info.tmdb_info:
                update_rss_movie_state(rssid=rssid, state='R')
                continue
            # 非洗版的情况检查是否存在
            if not over_edition:
                # 检查是否存在
                exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info)
                # 已经存在
                if exist_flag:
                    log.info("【RSS】电影 %s 已存在，删除订阅..." % name)
                    delete_rss_movie(rssid=rssid)
                    continue
            else:
                # 洗版时按缺失来下载
                no_exists = None
            # 开始检索
            search_result, no_exists, search_count, download_count = self.searcher.search_one_media(
                media_info=media_info,
                in_from=SearchType.RSS,
                no_exists=no_exists,
                sites=sites,
                filters=filter_map)
            if search_result:
                log.info("【RSS】电影 %s 下载完成，删除订阅..." % name)
                delete_rss_movie(rssid=rssid)
            else:
                update_rss_movie_state(rssid=rssid, state='R')

    def rsssearch_tv(self, rssid=None, state="D"):
        """
        检索电视剧RSS
        :param rssid: 订阅ID，未输入时检索所有状态为D的，输入时检索该ID任何状态的
        :param state: 检索的状态，默认为队列中才检索
        """
        if rssid:
            tvs = get_rss_tvs(rssid=rssid)
        else:
            tvs = get_rss_tvs(state=state)
        if tvs:
            log.info("【RSS】共有 %s 个电视剧订阅需要检索" % len(tvs))
        for tv in tvs:
            rssid = tv[10]
            name = tv[0]
            year = tv[1] or ""
            season = tv[2]
            tmdbid = tv[3]
            total = int(tv[6])
            # 跳过模糊匹配的
            if not season or not tmdbid:
                continue
            # 开始搜索
            update_rss_tv_state(rssid=rssid, state='S')
            # 搜索站点、洗版、过滤条件
            _, sites, over_edition, filter_map = Torrent.get_rss_note_item(tv[5])
            # 开始识别
            media_info = self.__get_media_info(tmdbid, name, year, MediaType.TV)
            # 未识别到媒体信息
            if not media_info or not media_info.tmdb_info:
                update_rss_tv_state(rssid=rssid, state='R')
                continue
            # 季
            media_info.begin_season = int(season.replace("S", ""))

            # 从登记薄中获取缺失剧集
            episodes = get_rss_tv_episodes(rssid)
            if episodes is None:
                no_exists = {media_info.get_title_string(): [
                    {"season": media_info.begin_season, "episodes": [], "total_episodes": total}]}
            elif episodes:
                no_exists = {media_info.get_title_string(): [
                    {"season": media_info.begin_season, "episodes": episodes, "total_episodes": total}]}
            else:
                log.info("【RSS】电视剧 %s%s 已全部订阅完成，删除订阅..." % (name, season))
                delete_rss_tv(rssid=rssid)
                continue

            # 非洗版的情况检查是否存在
            if not over_edition:
                # 检查是否存在，电视剧返回不存在的集清单
                exist_flag, library_no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info)
                # 已经存在
                if exist_flag:
                    # 已全部存在
                    if not library_no_exists or not library_no_exists.get(
                            media_info.get_title_string()):
                        log.info("【RSS】电视剧 %s%s 已存在，删除订阅..." % (name, season))
                        delete_rss_tv(rssid=rssid)
                    continue
                # 取交集做为缺失集
                no_exists = self.__get_rss_no_exists(target=no_exists,
                                                     source=library_no_exists,
                                                     title=media_info.get_title_string())

            # 开始检索
            search_result, no_exists, search_count, download_count = self.searcher.search_one_media(
                media_info=media_info,
                in_from=SearchType.RSS,
                no_exists=no_exists,
                sites=sites,
                filters=filter_map)
            if not no_exists or not no_exists.get(media_info.get_title_string()):
                # 没有剩余或者剩余缺失季集中没有当前标题，说明下完了
                log.info("【RSS】电视剧 %s 下载完成，删除订阅..." % name)
                delete_rss_tv(rssid=rssid)
            else:
                # 更新状态
                update_rss_tv_state(rssid=rssid, state='R')
                no_exist_items = no_exists.get(media_info.get_title_string())
                for no_exist_item in no_exist_items:
                    if str(no_exist_item.get("season")) == media_info.get_season_seq():
                        if no_exist_item.get("episodes"):
                            log.info("【RSS】更新电视剧 %s %s 缺失集数为 %s" % (
                                media_info.get_title_string(), media_info.get_season_string(),
                                len(no_exist_item.get("episodes"))))
                            update_rss_tv_lack(rssid=rssid, lack_episodes=no_exist_item.get("episodes"))
                        break

    def refresh_rss_metainfo(self):
        """
        定时将豆瓣订阅转换为TMDB的订阅，并更新订阅的TMDB信息
        """
        # 更新电影
        movies = get_rss_movies(state='R')
        for movie in movies:
            rid = movie[6]
            name = movie[0]
            year = movie[1] or ""
            tmdbid = movie[2]
            if not tmdbid:
                continue
            media_info = self.__get_media_info(tmdbid=tmdbid,
                                               name=name,
                                               year=year,
                                               mtype=MediaType.MOVIE,
                                               cache=False)
            if media_info and media_info.tmdb_id and media_info.title != name:
                log.info(f"【RSS】检测到TMDB信息变化，更新电影订阅 {name} 为 {media_info.title}")
                # 更新订阅信息
                update_rss_movie_tmdb(rid=rid,
                                      tmdbid=media_info.tmdb_id,
                                      title=media_info.title,
                                      year=media_info.year,
                                      image=media_info.get_message_image())
                # 清除TMDB缓存
                self.metahelper.delete_meta_data_by_tmdbid(media_info.tmdb_id)

        # 更新电视剧
        tvs = get_rss_tvs(state='R')
        for tv in tvs:
            rid = tv[10]
            name = tv[0]
            year = tv[1] or ""
            season = tv[2]
            tmdbid = tv[3]
            total = int(tv[6])
            lack = int(tv[7])
            if not tmdbid:
                continue
            media_info = self.__get_media_info(tmdbid=tmdbid,
                                               name=name,
                                               year=year,
                                               mtype=MediaType.TV,
                                               cache=False)
            if media_info and media_info.tmdb_id:
                # 获取总集数
                total_episode = self.media.get_tmdb_season_episodes_num(sea=int(str(season).replace("S", "")),
                                                                        tv_info=media_info.tmdb_info)
                if total_episode and (name != media_info.title or total != total_episode):
                    # 新的缺失集数
                    lack_episode = total_episode - (total - lack)
                    log.info(f"【RSS】检测到TMDB信息变化，更新电视剧订阅 {name} 为 {media_info.title}，总集数为：{total_episode}")
                    # 更新订阅信息
                    update_rss_tv_tmdb(rid=rid,
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
        # 开始处理
        ret_array = []
        if not url:
            return []
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
                        title = tag_value(item, "title", default="")
                        if not title:
                            continue
                        # 描述
                        description = tag_value(item, "description", default="")
                        # 种子页面
                        link = tag_value(item, "link", default="")
                        # 种子链接
                        enclosure = tag_value(item, "enclosure", "url", default="")
                        if not enclosure:
                            # 种子链接
                            enclosure = tag_value(item, "link", default="")
                            # 大小
                            size = 0
                            size_map = {
                                'KiB': 1024,
                                'MiB': 1024 * 1024,
                                'GiB': 1024 * 1024 * 1024,
                                'TiB': 1024 * 1024 * 1024 * 1024
                            }
                            url_host = parse.urlparse(url).netloc
                            if RSS_EXTRA_SITES[url_host] == 'Unit3D':
                                size_temp = re.search(r'Size</strong>: (\d*\.\d*|\d*)(\s)(GiB|MiB|TiB|KiB)',
                                                      description)
                                if size_temp:
                                    size = int(float(size_temp.group(1)) * size_map[size_temp.group(3)])
                            elif RSS_EXTRA_SITES[url_host] == 'beyondhd':
                                size_temp = re.search(r'(\d*\.\d*|\d*) (GiB|MiB|TiB|KiB)', title)
                                if size_temp:
                                    size = int(float(size_temp.group(1)) * size_map[size_temp.group(2)])
                            else:
                                continue
                        else:
                            # 大小
                            size = tag_value(item, "enclosure", "length", default=0)
                            if size and str(size).isdigit():
                                size = int(size)
                            else:
                                size = 0
                        # 返回对象
                        tmp_dict = {'title': title, 'enclosure': enclosure, 'size': size, 'description': description,
                                    'link': link}
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

    @staticmethod
    def __is_torrent_match_rss(media_info: MetaBase,
                               movie_keys,
                               tv_keys,
                               site_rule,
                               site_cookie,
                               site_parse):
        """
        判断种子是否命中订阅
        :param media_info: 已识别的种子媒体信息
        :param movie_keys: 电影订阅清单
        :param tv_keys: 电视剧订阅清单
        :param site_rule: 站点过滤规则
        :param site_cookie: 站点的Cookie
        :param site_parse: 是否解析种子详情
        :return: 匹配到的订阅ID、是否洗版、总集数、匹配规则的资源顺序、上传因子、下载因子
        """
        # 默认值
        match_flag = False
        res_order = 0
        rssid = None
        over_edition = None
        upload_volume_factor = 1.0
        download_volume_factor = 1.0
        hit_and_run = False
        rulegroup = site_rule
        total_episodes = 0

        # 匹配电影
        if media_info.type == MediaType.MOVIE:
            for key_info in movie_keys:
                if not key_info:
                    continue
                name = key_info[0]
                year = key_info[1]
                tmdbid = key_info[2]
                rssid = key_info[6]
                # 订阅站点，是否洗板，过滤字典
                sites, _, over_edition, filter_map = Torrent.get_rss_note_item(key_info[4])
                # 订阅有指定过滤规则时优先使用订阅的
                if filter_map and filter_map.get("rule"):
                    rulegroup = filter_map.get("rule")
                # 过滤订阅站点
                if sites and media_info.site not in sites:
                    continue
                # 过滤字典
                if filter_map and not Torrent.check_torrent_filter(media_info, filter_map):
                    continue
                # 有tmdbid时使用TMDBID匹配
                if tmdbid:
                    if not tmdbid.startswith("DB:"):
                        if str(media_info.tmdb_id) != str(tmdbid):
                            continue
                    else:
                        if year and str(year) != str(media_info.year):
                            continue
                        if str(name) != str(media_info.title) \
                                and str(name) != str(media_info.original_title):
                            continue
                # 模糊匹配
                else:
                    # 模糊匹配时的默认值
                    rssid = 0
                    # 匹配年份
                    if year and str(year) != str(media_info.year):
                        continue
                    # 匹配关键字，可能是正则表达式
                    if not re.search(r"%s" % name,
                                     "%s %s %s %s" % (media_info.org_string, media_info.title, media_info.original_title, media_info.year),
                                     re.IGNORECASE):
                        continue
                # 媒体匹配成功
                match_flag = True
                break
        # 匹配电视剧
        else:
            # 匹配种子标题
            for key_info in tv_keys:
                if not key_info:
                    continue
                name = key_info[0]
                year = key_info[1]
                season = key_info[2]
                tmdbid = key_info[3]
                rssid = key_info[10]
                total_episodes = key_info[6]
                # 订阅站点
                sites, _, over_edition, filter_map = Torrent.get_rss_note_item(key_info[5])
                # 订阅有指定过滤规则时优先使用订阅的
                if filter_map and filter_map.get("rule"):
                    rulegroup = filter_map.get("rule")
                # 过滤订阅站点
                if sites and media_info.site not in sites:
                    continue
                # 过滤字典
                if filter_map and not Torrent.check_torrent_filter(media_info, filter_map):
                    continue
                # 有tmdbid时精确匹配
                if tmdbid:
                    if not tmdbid.startswith("DB:"):
                        if str(media_info.tmdb_id) != str(tmdbid):
                            continue
                    else:
                        # 匹配名称
                        if str(name) != str(media_info.title) \
                                and str(name) != str(media_info.original_title):
                            continue
                        # 匹配年份，年份可以为空
                        if year and str(year) != str(media_info.year):
                            continue
                    # 匹配季，季可以为空
                    if season and season != media_info.get_season_string():
                        continue
                # 模糊匹配
                else:
                    # 模糊匹配时的默认值
                    rssid = 0
                    # 匹配季
                    if season and season != "S00" and season != media_info.get_season_string():
                        continue
                    # 匹配年份
                    if year and str(year) != str(media_info.year):
                        continue
                    # 匹配关键字，可能是正则表达式
                    if not re.search(r"%s" % name,
                                     "%s %s %s %s" % (media_info.org_string, media_info.title, media_info.original_title, media_info.year),
                                     re.IGNORECASE):
                        continue
                # 媒体匹配成功
                match_flag = True
                break
        # 名称匹配成功，开始匹配规则
        if match_flag:
            if site_parse:
                # 检测Free
                attr_type = Torrent.check_torrent_attr(torrent_url=media_info.page_url, cookie=site_cookie)
                if "2XFREE" in attr_type:
                    download_volume_factor = 0.0
                    upload_volume_factor = 2.0
                elif "FREE" in attr_type:
                    download_volume_factor = 0.0
                    upload_volume_factor = 1.0
                if "HR" in attr_type:
                    hit_and_run = True
                # 设置属性
                media_info.set_torrent_info(upload_volume_factor=upload_volume_factor,
                                            download_volume_factor=download_volume_factor,
                                            hit_and_run=hit_and_run)
            match_flag, res_order, _ = FilterRule().check_rules(meta_info=media_info,
                                                                rolegroup=rulegroup)
            if not match_flag:
                log.info(
                    f"【RSS】{media_info.org_string} 大小：{str_filesize(media_info.size)} 促销：{media_info.get_volume_factor_string()} 不符合过滤规则")
        if match_flag:
            return rssid, over_edition, total_episodes, res_order, upload_volume_factor, download_volume_factor
        else:
            return None, None, total_episodes, res_order, upload_volume_factor, download_volume_factor
