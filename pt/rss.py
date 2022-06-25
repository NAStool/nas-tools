import traceback
from threading import Lock

import re
from urllib import parse
import xml.dom.minidom
import log
from config import RSS_EXTRA_SITES
from pt.searcher import Searcher
from message.send import Message
from pt.downloader import Downloader
from pt.torrent import Torrent
from rmt.media import Media
from rmt.metainfo import MetaInfo
from utils.functions import tag_value
from utils.http_utils import RequestUtils
from utils.sqls import get_rss_movies, get_rss_tvs, insert_rss_torrents, \
    get_config_site, is_torrent_rssd, get_config_rss_rule, delete_rss_movie, delete_rss_tv, update_rss_tv_lack, \
    update_rss_movie_state, update_rss_tv_state, update_rss_movie_tmdbid, update_rss_tv_tmdbid
from utils.types import MediaType, SearchType

lock = Lock()


class Rss:
    __sites = None
    __rss_rule = None
    message = None
    media = None
    downloader = None
    searcher = None

    def __init__(self):
        self.message = Message()
        self.media = Media()
        self.downloader = Downloader()
        self.searcher = Searcher()
        self.init_config()

    def init_config(self):
        self.__sites = get_config_site()
        rss_rule = get_config_rss_rule()
        if rss_rule:
            if rss_rule[0][1]:
                self.__rss_rule = str(rss_rule[0][1]).split("\n")
            else:
                self.__rss_rule = None

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
                rss_sites = str(movie[4]).split('#')[0]
                if not rss_sites or rss_sites.find("|") == -1:
                    check_all = True
                    break
                else:
                    check_sites += rss_sites.split("|")
            if not check_all:
                for tv in tv_keys:
                    rss_sites = str(tv[5]).split('#')[0]
                    if not rss_sites or rss_sites.find("|") == -1:
                        check_all = True
                        break
                    else:
                        check_sites += rss_sites.split("|")
            if check_all:
                check_sites = []
            else:
                check_sites = [site for site in check_sites if site]
            # 代码站点配置优先级的序号
            order_seq = 100
            rss_download_torrents = []
            rss_no_exists = {}
            for site_info in self.__sites:
                if not site_info:
                    continue
                # 站点名称
                rss_job = site_info[1]
                # 没有订阅的站点中的不检索
                if check_sites and rss_job not in check_sites:
                    continue
                rssurl = site_info[3]
                if not rssurl:
                    log.info("【RSS】%s 未配置rssurl，跳过..." % str(rss_job))
                    continue
                rss_cookie = site_info[5]
                # 是否仅RSS促销
                rss_free = str(site_info[9]).split("|")[0] if str(site_info[9]).split("|")[0] in ["FREE", "2XFREE"] else None
                # 过滤条件
                if site_info[6] or site_info[7] or site_info[8]:
                    include = str(site_info[6]).split("\n")
                    exclude = str(site_info[7]).split("\n")
                    res_type = {"include": include, "exclude": exclude, "size": site_info[8], "note": self.__rss_rule}
                else:
                    res_type = None
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

                        log.debug("【RSS】开始处理：%s" % torrent_name)
                        # 识别种子名称，开始检索TMDB
                        media_info = self.media.get_media_info(title=torrent_name, subtitle=description)
                        if not media_info or not media_info.tmdb_info:
                            log.debug("【RSS】%s 未识别到媒体信息" % torrent_name)
                            continue
                        # 检查这个名字是不是下过了
                        if is_torrent_rssd(media_info):
                            log.info("【RSS】%s%s 已成功订阅过" % (
                                media_info.get_title_string(), media_info.get_season_episode_string()))
                            continue
                        # 检查种子名称或者标题是否匹配
                        if Torrent.is_torrent_match_rss(media_info, movie_keys, tv_keys, rss_job):
                            log.info("【RSS】%s: %s %s %s 匹配成功" % (media_info.type.value,
                                                                 media_info.get_title_string(),
                                                                 media_info.get_season_episode_string(),
                                                                 media_info.get_resource_type_string()))
                        else:
                            log.debug("【RSS】%s: %s %s %s 不匹配订阅" % (media_info.type.value,
                                                                   media_info.get_title_string(),
                                                                   media_info.get_season_episode_string(),
                                                                   media_info.get_resource_type_string()))
                            continue
                        # 确定标题中是否符合过滤规则，并返回关键字的顺序号
                        match_flag, res_order = Torrent.check_resouce_types(torrent_name, description, res_type)
                        if not match_flag:
                            log.info("【RSS】%s 不符合过滤规则" % torrent_name)
                            continue
                        # 判断文件大小是否匹配，只针对电影
                        if not Torrent.is_torrent_match_size(media_info, res_type, size):
                            continue
                        # 检查是否存在
                        exist_flag, rss_no_exists, messages = self.downloader.check_exists_medias(meta_info=media_info,
                                                                                                  no_exists=rss_no_exists)
                        if exist_flag:
                            # 如果是电影，已存在时删除订阅
                            if media_info.type == MediaType.MOVIE:
                                log.info("【RSS】删除电影订阅：%s" % media_info.get_title_string())
                                delete_rss_movie(media_info.title, media_info.year)
                            # 如果是电视剧
                            else:
                                # 不存在缺失季集时删除订阅
                                if not rss_no_exists or not rss_no_exists.get(media_info.get_title_string()):
                                    log.info("【RSS】删除电视剧订阅：%s %s" % (
                                        media_info.get_title_string(), media_info.get_season_string()))
                                    delete_rss_tv(media_info.title, media_info.year, media_info.get_season_string())
                            continue
                        # 判断种子是否免费
                        download_volume_factor = 1.0
                        upload_volume_factor = 1.0
                        if rss_free:
                            free_type = Torrent.check_torrent_free(torrent_url=page_url, cookie=rss_cookie)
                            if free_type == "2XFREE":
                                download_volume_factor = 0.0
                                upload_volume_factor = 2.0
                            elif free_type == "FREE":
                                download_volume_factor = 0.0
                                upload_volume_factor = 1.0
                            if rss_free != free_type:
                                log.info("【RSS】%s 不是 %s 种子" % (torrent_name, rss_free))
                                continue
                        # 返回对象
                        media_info.set_torrent_info(site_order=order_seq,
                                                    site=rss_job,
                                                    enclosure=enclosure,
                                                    res_order=res_order,
                                                    size=size,
                                                    description=description,
                                                    download_volume_factor=download_volume_factor,
                                                    upload_volume_factor=upload_volume_factor)
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
            download_items, left_medias = self.downloader.check_and_add_pt(SearchType.RSS, rss_download_torrents,
                                                                           rss_no_exists)
            # 批量删除订阅
            if download_items:
                for item in download_items:
                    if item.type == MediaType.MOVIE:
                        # 删除电影订阅
                        log.info("【RSS】删除电影订阅：%s" % item.get_title_string())
                        delete_rss_movie(item.title, item.year)
                    else:
                        if not left_medias or not left_medias.get(item.get_title_string()):
                            # 删除电视剧订阅
                            log.info("【RSS】删除电视剧订阅：%s %s" % (item.get_title_string(), item.get_season_string()))
                            delete_rss_tv(item.title, item.year, item.get_season_string())
                        else:
                            # 更新电视剧缺失剧集
                            left_media = left_medias.get(item.get_title_string())
                            if not left_media:
                                continue
                            for left_season in left_media:
                                if item.is_in_season(left_season.get("season")):
                                    if left_season.get("episodes"):
                                        log.info("【RSS】更新电视剧 %s %s 缺失集数为 %s" % (
                                            item.get_title_string(), item.get_season_string(),
                                            len(left_season.get("episodes"))))
                                        update_rss_tv_lack(item.title, item.year, item.get_season_string(),
                                                           len(left_season.get("episodes")))
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
            name = movie[0]
            year = movie[1] or ""
            tmdbid = movie[2]
            notes = str(movie[4]).split('#')
            if len(notes) > 1:
                sites = [site for site in notes[1].split('|') if site]
            else:
                sites = []
            # 跳过模糊匹配的
            if not tmdbid:
                continue
            update_rss_movie_state(name, year, 'S')
            # 开始识别
            if tmdbid and not tmdbid.startswith("DB:"):
                media_info = MetaInfo(title="%s %s".strip() % (name, year))
                tmdb_info = Media().get_tmdb_info(mtype=MediaType.MOVIE, title=name, year=year, tmdbid=tmdbid)
                media_info.set_tmdb_info(tmdb_info)
            else:
                media_info = Media().get_media_info(title="%s %s" % (name, year), mtype=MediaType.MOVIE, strict=True)
            # 未识别到媒体信息
            if not media_info or not media_info.tmdb_info:
                update_rss_movie_state(name, year, 'R')
                continue
            # 检查是否存在，电视剧返回不存在的集清单
            exist_flag, no_exists, messages = self.downloader.check_exists_medias(meta_info=media_info)
            # 已经存在
            if exist_flag:
                log.info("【RSS】电影 %s 已存在，删除订阅..." % name)
                delete_rss_movie(name, year)
                continue
            # 开始检索
            search_result, no_exists, search_count, download_count = self.searcher.search_one_media(
                media_info=media_info,
                in_from=SearchType.RSS,
                no_exists=no_exists,
                sites=sites)
            if search_result:
                log.info("【RSS】电影 %s 下载完成，删除订阅..." % name)
                delete_rss_movie(name, year)
            else:
                update_rss_movie_state(name, year, 'R')

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
            name = tv[0]
            year = tv[1] or ""
            season = tv[2]
            tmdbid = tv[3]
            notes = tv[5].split('#')
            if len(notes) > 1:
                sites = [site for site in notes[1].split('|') if site]
            else:
                sites = []
            lack = int(tv[7])
            # 跳过模糊匹配的
            if not season or not tmdbid:
                continue
            update_rss_tv_state(name, year, season, 'S')
            # 开始识别
            if tmdbid and not tmdbid.startswith("DB:"):
                media_info = MetaInfo(title="%s %s".strip() % (name, year))
                tmdb_info = Media().get_tmdb_info(mtype=MediaType.TV, title=name, year=year, tmdbid=tmdbid)
                media_info.set_tmdb_info(tmdb_info)
            else:
                media_info = Media().get_media_info(title="%s %s" % (name, year), mtype=MediaType.TV, strict=True)
            # 未识别到媒体信息
            if not media_info or not media_info.tmdb_info:
                update_rss_tv_state(name, year, season, 'R')
                continue
            # 检查是否存在，电视剧返回不存在的集清单
            exist_flag, no_exists, messages = self.downloader.check_exists_medias(meta_info=media_info)
            # 已经存在
            if exist_flag:
                log.info("【RSS】电视剧 %s 已存在，删除订阅..." % name)
                delete_rss_tv(name, year, season)
                continue
            # 开始检索
            media_info.begin_season = int(season.replace("S", ""))
            search_result, no_exists, search_count, download_count = self.searcher.search_one_media(
                media_info=media_info,
                in_from=SearchType.RSS,
                no_exists=no_exists,
                sites=sites)
            if not no_exists or not no_exists.get(media_info.get_title_string()):
                # 没有剩余或者剩余缺失季集中没有当前标题，说明下完了
                log.info("【RSS】电视剧 %s 下载完成，删除订阅..." % name)
                delete_rss_tv(name, year, season)
            else:
                # 更新状态
                update_rss_tv_state(name, year, season, 'R')
                no_exist_items = no_exists.get(media_info.get_title_string())
                for no_exist_item in no_exist_items:
                    if str(no_exist_item.get("season")) == media_info.get_season_seq():
                        if no_exist_item.get("episodes"):
                            log.info("【RSS】更新电视剧 %s %s 缺失集数为 %s" % (
                                media_info.get_title_string(), media_info.get_season_string(),
                                len(no_exist_item.get("episodes"))))
                            lack = len(no_exist_item.get("episodes"))
                        break
                update_rss_tv_lack(name, year, season, lack)

    @staticmethod
    def rssdouban_to_tmdb():
        """
        定时将豆瓣订阅转换为TMDB的订阅
        """
        # 更新电影
        movies = get_rss_movies(state='R')
        for movie in movies:
            rid = movie[6]
            name = movie[0]
            year = movie[1] or ""
            tmdbid = movie[2]
            if tmdbid and tmdbid.startswith("DB:"):
                media_info = Media().get_media_info(title="%s %s" % (name, year), mtype=MediaType.MOVIE, strict=True)
                if media_info and media_info.tmdb_id:
                    update_rss_movie_tmdbid(rid=rid, tmdbid=media_info.tmdb_id)
        # 更新电视剧
        tvs = get_rss_tvs(state='R')
        for tv in tvs:
            rid = tv[10]
            name = tv[0]
            year = tv[1] or ""
            tmdbid = tv[3]
            if tmdbid and tmdbid.startswith("DB:"):
                media_info = Media().get_media_info(title="%s %s" % (name, year), mtype=MediaType.TV, strict=True)
                if media_info and media_info.tmdb_id:
                    update_rss_tv_tmdbid(rid=rid, tmdbid=media_info.tmdb_id)

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
                                size_temp = re.search(r'Size</strong>: (\d*\.\d*|\d*)(\s)(GiB|MiB|TiB|KiB)', description)
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
                        tmp_dict = {'title': title, 'enclosure': enclosure, 'size': size, 'description': description, 'link': link}
                        ret_array.append(tmp_dict)
                    except Exception as e1:
                        log.console(str(e1))
                        continue
            except Exception as e2:
                log.console(str(e2))
                return ret_array
        return ret_array
