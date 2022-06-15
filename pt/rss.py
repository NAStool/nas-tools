import traceback
from threading import Lock

import requests
import xml.dom.minidom
import log
from config import Config
from pt.searcher import Searcher
from pt.torrent import Torrent
from message.send import Message
from pt.downloader import Downloader
from rmt.media import Media
from rmt.metainfo import MetaInfo
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
    torrent = None
    searcher = None

    def __init__(self):
        self.message = Message()
        self.media = Media()
        self.downloader = Downloader()
        self.searcher = Searcher()
        self.init_config()

    def init_config(self):
        config = Config()
        pt = config.get_config('pt')
        if pt:
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
            # 读取关键字配置
            movie_keys = get_rss_movies(state='R')
            if not movie_keys:
                log.warn("【RSS】未订阅电影")
            else:
                log.info("【RSS】电影订阅清单：%s" % " ".join('%s' % key[0] for key in movie_keys))

            tv_keys = get_rss_tvs(state='R')
            if not tv_keys:
                log.warn("【RSS】未订阅电视剧")
            else:
                log.info("【RSS】电视剧订阅清单：%s" % " ".join('%s' % key[0] for key in tv_keys))

            if not movie_keys and not tv_keys:
                return

            # 代码站点配置优先级的序号
            order_seq = 100
            rss_download_torrents = []
            rss_no_exists = {}
            for site_info in self.__sites:
                if not site_info:
                    continue
                order_seq -= 1
                # 读取子配置
                rss_job = site_info[1]
                rssurl = site_info[3]
                if not rssurl:
                    log.info("【RSS】%s 未配置rssurl，跳过..." % str(rss_job))
                    continue
                if site_info[6] or site_info[7] or site_info[8]:
                    include = str(site_info[6]).split("\n")
                    exclude = str(site_info[7]).split("\n")
                    res_type = {"include": include, "exclude": exclude, "size": site_info[8], "note": self.__rss_rule}
                else:
                    res_type = None

                # 开始下载RSS
                log.info("【RSS】正在处理：%s" % rss_job)
                rss_result = self.parse_rssxml(rssurl)
                if len(rss_result) == 0:
                    log.warn("【RSS】%s 未下载到数据" % rss_job)
                    continue
                else:
                    log.info("【RSS】%s 获取数据：%s" % (rss_job, len(rss_result)))

                res_num = 0
                for res in rss_result:
                    try:
                        # 种子名
                        torrent_name = res.get('title')
                        # 种子链接
                        enclosure = res.get('enclosure')
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
                        if Torrent.is_torrent_match_rss(media_info, movie_keys, tv_keys):
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
                        # 返回对象
                        media_info.set_torrent_info(site_order=order_seq,
                                                    site=rss_job,
                                                    enclosure=enclosure,
                                                    res_order=res_order,
                                                    size=size,
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

    def rsssearch(self):
        """
        RSS订阅队列中状态的任务处理，先进行存量PT资源检索，缺失的才标志为RSS状态，由定时服务调用
        """
        try:
            lock.acquire()
            # 处理电影
            self.rsssearch_movie()
            # 处理电视剧
            self.rsssearch_tv()
        finally:
            lock.release()

    def rsssearch_movie(self, rssid=None):
        """
        检索电影RSS
        :param rssid: 订阅ID，未输入时检索所有状态为D的，输入时检索该ID任何状态的
        """
        if rssid:
            movies = get_rss_movies(rssid=rssid)
        else:
            movies = get_rss_movies(state='D')
        if movies:
            log.info("【RSS】共有 %s 个电影订阅需要检索" % len(movies))
        for movie in movies:
            name = movie[0]
            year = movie[1]
            tmdbid = movie[2]
            # 跳过模糊匹配的
            if not tmdbid:
                continue
            update_rss_movie_state(name, year, 'S')
            # 开始识别
            if tmdbid and not tmdbid.startswith("DB:"):
                media_info = MetaInfo(title="%s %s" % (name, year))
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
            # 开始检索
            search_result, no_exists, search_count, download_count = self.searcher.search_one_media(
                media_info=media_info,
                in_from=SearchType.RSS,
                no_exists=no_exists)
            if search_result:
                log.info("【RSS】电影 %s 下载完成，删除订阅..." % name)
                delete_rss_movie(name, year)
            else:
                update_rss_movie_state(name, year, 'R')

    def rsssearch_tv(self, rssid=None):
        """
        检索电视剧RSS
        :param rssid: 订阅ID，未输入时检索所有状态为D的，输入时检索该ID任何状态的
        """
        if rssid:
            tvs = get_rss_tvs(rssid=rssid)
        else:
            tvs = get_rss_tvs(state='D')
        if tvs:
            log.info("【RSS】共有 %s 个电视剧订阅需要检索" % len(tvs))
        for tv in tvs:
            name = tv[0]
            year = tv[1]
            season = tv[2]
            tmdbid = tv[3]
            lack = int(tv[7])
            # 跳过模糊匹配的
            if not season or not tmdbid:
                continue
            update_rss_tv_state(name, year, season, 'S')
            # 开始识别
            if tmdbid and not tmdbid.startswith("DB:"):
                media_info = MetaInfo(title="%s %s" % (name, year))
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
            # 开始检索
            media_info.begin_season = int(season.replace("S", ""))
            search_result, no_exists, search_count, download_count = self.searcher.search_one_media(
                media_info=media_info,
                in_from=SearchType.RSS,
                no_exists=no_exists)
            if not no_exists or not no_exists.get(media_info.get_title_string()):
                # 没有剩余或者剩余缺失季集中没有当前标题，说明下完了
                log.info("【RSS】电视剧 %s 下载完成，删除订阅..." % name)
                delete_rss_tv(name, year, season)
            else:
                # 更新状态
                update_rss_tv_state(name, year, season, 'R')
                no_exist_items = no_exists.get(media_info.get_title_string())
                for no_exist_item in no_exist_items:
                    if no_exist_item.get("season") == media_info.begin_season:
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
            year = movie[1]
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
            year = tv[1]
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
        ret_array = []
        if not url:
            return []
        try:
            ret = requests.get(url, timeout=30)
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
                        title = ""
                        tagNames = item.getElementsByTagName("title")
                        if tagNames:
                            firstChild = tagNames[0].firstChild
                            if firstChild:
                                title = firstChild.data
                        if not title:
                            continue
                        # 种子链接
                        enclosure = ""
                        # 大小
                        size = 0
                        tagNames = item.getElementsByTagName("enclosure")
                        if tagNames:
                            enclosure = tagNames[0].getAttribute("url")
                            size = tagNames[0].getAttribute("length")
                        if not enclosure:
                            continue
                        if size and size.isdigit():
                            size = int(size)
                        else:
                            size = 0
                        # 描述
                        description = ""
                        tagNames = item.getElementsByTagName("description")
                        if tagNames:
                            firstChild = tagNames[0].firstChild
                            if firstChild:
                                description = firstChild.data
                        tmp_dict = {'title': title, 'enclosure': enclosure, 'size': size, 'description': description}
                        ret_array.append(tmp_dict)
                    except Exception as e1:
                        log.console(str(e1))
                        continue
            except Exception as e2:
                log.console(str(e2))
                return ret_array
        return ret_array
