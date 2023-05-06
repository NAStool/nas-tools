import re
from threading import Lock

import log
from app.downloader import Downloader
from app.filter import Filter
from app.timeframe import Timeframe
from app.helper import DbHelper, RssHelper
from app.media import Media
from app.media.meta import MetaInfo
from app.sites import Sites, SiteConf
from app.subscribe import Subscribe
from app.utils import ExceptionUtils, Torrent
from app.utils.commons import singleton
from app.utils.types import MediaType, SearchType

lock = Lock()


@singleton
class Rss:
    filter = None
    media = None
    sites = None
    siteconf = None
    downloader = None
    searcher = None
    dbhelper = None
    rsshelper = None
    subscribe = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.media = Media()
        self.downloader = Downloader()
        self.sites = Sites()
        self.siteconf = SiteConf()
        self.filter = Filter()
        self.dbhelper = DbHelper()
        self.rsshelper = RssHelper()
        self.subscribe = Subscribe()
        self.timeframe = Timeframe()

    def rssdownload(self):
        """
        RSS订阅搜索下载入口，由定时服务调用
        """
        rss_sites_info = self.sites.get_sites(rss=True)
        if not rss_sites_info:
            return

        with lock:
            log.info("【Rss】开始RSS订阅...")
            # 读取电影订阅
            rss_movies = self.subscribe.get_subscribe_movies(state='R')
            if not rss_movies:
                log.warn("【Rss】没有正在订阅的电影")
            else:
                log.info("【Rss】电影订阅清单：%s"
                         % " ".join('%s' % info.get("name") for _, info in rss_movies.items()))
            # 读取电视剧订阅
            rss_tvs = self.subscribe.get_subscribe_tvs(state='R')
            if not rss_tvs:
                log.warn("【Rss】没有正在订阅的电视剧")
            else:
                log.info("【Rss】电视剧订阅清单：%s"
                         % " ".join('%s' % info.get("name") for _, info in rss_tvs.items()))
            # 没有订阅退出
            if not rss_movies and not rss_tvs:
                return

            # 获取有订阅的站点范围
            check_sites = []
            check_all = False
            for rid, rinfo in rss_movies.items():
                rss_sites = rinfo.get("rss_sites")
                if not rss_sites:
                    check_all = True
                    break
                else:
                    check_sites += rss_sites
            if not check_all:
                for rid, rinfo in rss_tvs.items():
                    rss_sites = rinfo.get("rss_sites")
                    if not rss_sites:
                        check_all = True
                        break
                    else:
                        check_sites += rss_sites
            if check_all:
                check_sites = []
            else:
                check_sites = list(set(check_sites))
            # 匹配到的资源列表
            rss_download_torrents = []
            # 缺失的资源详情
            rss_no_exists = {}
            # 遍历站点资源
            for site_info in rss_sites_info:
                if not site_info:
                    continue
                # 站点名称
                site_name = site_info.get("name")
                # 没有订阅的站点中的不搜索
                if check_sites and site_name not in check_sites:
                    continue
                # 站点rss链接
                rss_url = site_info.get("rssurl")
                if not rss_url:
                    log.info(f"【Rss】{site_name} 未配置rssurl，跳过...")
                    continue
                # 站点信息
                site_id = site_info.get("id")
                site_cookie = site_info.get("cookie")
                site_ua = site_info.get("ua")
                # 是否解析种子详情
                site_parse = site_info.get("parse")
                # 是否使用代理
                site_proxy = site_info.get("proxy")
                # 使用的规则
                site_fliter_rule = site_info.get("rule")
                # 开始下载RSS
                log.info(f"【Rss】正在处理：{site_name}")
                if site_info.get("pri"):
                    site_order = 100 - int(site_info.get("pri"))
                else:
                    site_order = 0
                rss_acticles = self.rsshelper.parse_rssxml(url=rss_url)
                if rss_acticles is None:
                    # RSS链接过期
                    log.error(f"【Rss】站点 {site_name} RSS链接已过期，请重新获取！")
                    # 发送消息
                    self.message.send_site_message(title="【RSS链接过期提醒】",
                                                   text=f"站点：{site_name}\n"
                                                        f"链接：{rss_url}")
                    continue
                if not rss_acticles:
                    log.warn(f"【Rss】{site_name} 未下载到数据")
                    continue
                else:
                    log.info(f"【Rss】{site_name} 获取数据：{len(rss_acticles)}")
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
                        # 种子大小
                        size = article.get('size')
                        # 开始处理
                        log.info(f"【Rss】开始处理：{title}")
                        # 检查这个种子是不是下过了
                        if self.rsshelper.is_rssd_by_enclosure(enclosure):
                            log.info(f"【Rss】{title} 已成功订阅过")
                            continue
                        # 识别种子名称，开始搜索TMDB
                        media_info = MetaInfo(title=title)
                        cache_info = self.media.get_cache_info(media_info)
                        if cache_info.get("id"):
                            # 使用缓存信息
                            media_info.tmdb_id = cache_info.get("id")
                            media_info.type = cache_info.get("type")
                            media_info.title = cache_info.get("title")
                            media_info.year = cache_info.get("year")
                        else:
                            # 重新查询TMDB
                            media_info = self.media.get_media_info(title=title)
                            if not media_info:
                                log.warn(f"【Rss】{title} 无法识别出媒体信息！")
                                continue
                            elif not media_info.tmdb_info:
                                log.info(f"【Rss】{title} 识别为 {media_info.get_name()} 未匹配到TMDB媒体信息")
                        # 大小及种子页面
                        media_info.set_torrent_info(size=size,
                                                    page_url=page_url,
                                                    site=site_name,
                                                    site_order=site_order,
                                                    enclosure=enclosure)
                        # 检查种子是否匹配订阅，返回匹配到的订阅ID、是否洗版、总集数、上传因子、下载因子
                        match_flag, match_msg, match_info = self.check_torrent_rss(
                            media_info=media_info,
                            rss_movies=rss_movies,
                            rss_tvs=rss_tvs,
                            site_id=site_id,
                            site_filter_rule=site_fliter_rule,
                            site_cookie=site_cookie,
                            site_parse=site_parse,
                            site_ua=site_ua,
                            site_proxy=site_proxy)
                        for msg in match_msg:
                            log.info(f"【Rss】{msg}")

                        # 未匹配
                        if not match_flag:
                            continue

                        # 非模糊匹配命中，检查本地情况，检查删除订阅
                        if not match_info.get("fuzzy_match"):
                            # 匹配到订阅，如没有TMDB信息则重新查询
                            if not media_info.tmdb_info and media_info.tmdb_id:
                                media_info.set_tmdb_info(self.media.get_tmdb_info(mtype=media_info.type,
                                                                                  tmdbid=media_info.tmdb_id))
                            if not media_info.tmdb_info:
                                continue
                            # 非洗版时检查本地是否存在
                            if not match_info.get("over_edition"):
                                if media_info.type == MediaType.MOVIE:
                                    exist_flag, rss_no_exists, _ = self.downloader.check_exists_medias(
                                        meta_info=media_info,
                                        no_exists=rss_no_exists
                                    )
                                else:
                                    # 从登记薄中获取缺失剧集
                                    season = 1
                                    if match_info.get("season"):
                                        season = int(str(match_info.get("season")).replace("S", ""))
                                    # 设定的总集数
                                    total_ep = match_info.get("total")
                                    # 设定的开始集数
                                    current_ep = match_info.get("current_ep")
                                    # 表登记的缺失集数
                                    episodes = self.subscribe.get_subscribe_tv_episodes(match_info.get("id"))
                                    if episodes is None:
                                        episodes = []
                                        if current_ep:
                                            episodes = list(range(int(current_ep), int(total_ep) + 1))
                                        rss_no_exists[media_info.tmdb_id] = [
                                            {
                                                "season": season,
                                                "episodes": episodes,
                                                "total_episodes": total_ep
                                            }
                                        ]
                                    else:
                                        rss_no_exists[media_info.tmdb_id] = [
                                            {
                                                "season": season,
                                                "episodes": episodes,
                                                "total_episodes": total_ep
                                            }
                                        ]
                                    # 检查本地媒体库情况
                                    exist_flag, library_no_exists, _ = self.downloader.check_exists_medias(
                                        meta_info=media_info,
                                        total_ep={season: total_ep}
                                    )
                                    # 取交集做为缺失集
                                    rss_no_exists = Torrent.get_intersection_episodes(target=rss_no_exists,
                                                                                      source=library_no_exists,
                                                                                      title=media_info.tmdb_id)
                                    if rss_no_exists.get(media_info.tmdb_id):
                                        log.info("【Rss】%s 订阅缺失季集：%s" % (
                                            media_info.get_title_string(),
                                            rss_no_exists.get(media_info.tmdb_id)
                                        ))
                                # 本地已存在
                                if exist_flag:
                                    continue
                            # 洗版模式
                            else:
                                # 洗版时季集不完整的资源不要
                                if media_info.type != MediaType.MOVIE \
                                        and media_info.get_episode_list():
                                    log.info(
                                        f"【Rss】{media_info.get_title_string()}{media_info.get_season_string()} "
                                        f"正在洗版，过滤掉季集不完整的资源：{title}"
                                    )
                                    continue
                                if not self.subscribe.check_subscribe_over_edition(
                                        rtype=media_info.type,
                                        rssid=match_info.get("id"),
                                        res_order=match_info.get("res_order")):
                                    log.info(
                                        f"【Rss】{media_info.get_title_string()}{media_info.get_season_string()} "
                                        f"正在洗版，跳过低优先级或同优先级资源：{title}"
                                    )
                                    continue
                        # 模糊匹配
                        else:
                            # 不做处理，直接下载
                            pass

                        # 站点流控
                        if self.sites.check_ratelimit(site_id):
                            continue

                        # 设置种子信息
                        media_info.set_torrent_info(res_order=match_info.get("res_order"),
                                                    filter_rule=match_info.get("filter_rule"),
                                                    over_edition=match_info.get("over_edition"),
                                                    download_volume_factor=match_info.get("download_volume_factor"),
                                                    upload_volume_factor=match_info.get("upload_volume_factor"),
                                                    rssid=match_info.get("id"))
                        # 设置下载参数
                        media_info.set_download_info(download_setting=match_info.get("download_setting"),
                                                     save_path=match_info.get("save_path"))
                        
                        # 判断需要等待的种子
                        if self.timeframe.check_rss_filter(media_info,
                            match_info.get('filter_timeframe')):
                                continue                                  
                        else:
                            # 插入数据库历史记录
                            self.rsshelper.insert_rss_torrents(media_info)
                        # 加入下载列表
                            if media_info not in rss_download_torrents:
                                rss_download_torrents.append(media_info)
                                res_num = res_num + 1
                    except Exception as e:
                        ExceptionUtils.exception_traceback(e)
                        log.error("【Rss】处理RSS发生错误：%s" % str(e))
                        continue
                log.info("【Rss】%s 处理结束，匹配到 %s 个有效资源" % (site_name, res_num))
            log.info("【Rss】所有RSS处理结束，共 %s 个有效资源" % len(rss_download_torrents))
            # 开始择优下载
            self.download_rss_torrent(rss_download_torrents=rss_download_torrents,
                                      rss_no_exists=rss_no_exists)

    def check_torrent_rss(self,
                          media_info,
                          rss_movies,
                          rss_tvs,
                          site_id,
                          site_filter_rule,
                          site_cookie,
                          site_parse,
                          site_ua,
                          site_proxy):
        """
        判断种子是否命中订阅
        :param media_info: 已识别的种子媒体信息
        :param rss_movies: 电影订阅清单
        :param rss_tvs: 电视剧订阅清单
        :param site_id: 站点ID
        :param site_filter_rule: 站点过滤规则
        :param site_cookie: 站点的Cookie
        :param site_parse: 是否解析种子详情
        :param site_ua: 站点请求UA
        :param site_proxy: 是否使用代理
        :return: 匹配到的订阅ID、是否洗版、总集数、匹配规则的资源顺序、上传因子、下载因子，匹配的季（电视剧）
        """
        # 默认值
        # 匹配状态 0不在订阅范围内 -1不符合过滤条件 1匹配
        match_flag = False
        # 匹配的rss信息
        match_msg = []
        match_rss_info = {}
        # 上传因素
        upload_volume_factor = None
        # 下载因素
        download_volume_factor = None
        hit_and_run = False

        # 匹配电影
        if media_info.type == MediaType.MOVIE and rss_movies:
            for rid, rss_info in rss_movies.items():
                rss_sites = rss_info.get('rss_sites')
                # 过滤订阅站点
                if rss_sites and media_info.site not in rss_sites:
                    continue
                # tmdbid或名称年份匹配
                name = rss_info.get('name')
                year = rss_info.get('year')
                tmdbid = rss_info.get('tmdbid')
                fuzzy_match = rss_info.get('fuzzy_match')
                # 非模糊匹配
                if not fuzzy_match:
                    # 有tmdbid时使用tmdbid匹配
                    if tmdbid and not tmdbid.startswith("DB:"):
                        if str(media_info.tmdb_id) != str(tmdbid):
                            continue
                    else:
                        # 豆瓣年份与tmdb取向不同
                        if year and str(media_info.year) not in [str(year),
                                                                 str(int(year) + 1),
                                                                 str(int(year) - 1)]:
                            continue
                        if name != media_info.title:
                            continue
                # 模糊匹配
                else:
                    # 匹配年份
                    if year and str(year) != str(media_info.year):
                        continue
                    # 匹配关键字或正则表达式
                    search_title = f"{media_info.org_string} {media_info.title} {media_info.year}"
                    if not re.search(name, search_title, re.I) and name not in search_title:
                        continue
                # 媒体匹配成功
                match_flag = True
                match_rss_info = rss_info

                break
        # 匹配电视剧
        elif rss_tvs:
            # 匹配种子标题
            for rid, rss_info in rss_tvs.items():
                rss_sites = rss_info.get('rss_sites')
                # 过滤订阅站点
                if rss_sites and media_info.site not in rss_sites:
                    continue
                # 有tmdbid时精确匹配
                name = rss_info.get('name')
                year = rss_info.get('year')
                season = rss_info.get('season')
                tmdbid = rss_info.get('tmdbid')
                fuzzy_match = rss_info.get('fuzzy_match')
                # 非模糊匹配
                if not fuzzy_match:
                    if tmdbid and not tmdbid.startswith("DB:"):
                        if str(media_info.tmdb_id) != str(tmdbid):
                            continue
                    else:
                        # 匹配年份，年份可以为空
                        if year and str(year) != str(media_info.year):
                            continue
                        # 匹配名称
                        if name != media_info.title:
                            continue
                    # 匹配季，季可以为空
                    if season and season != media_info.get_season_string():
                        continue
                # 模糊匹配
                else:
                    # 匹配季，季可以为空
                    if season and season != "S00" and season != media_info.get_season_string():
                        continue
                    # 匹配年份
                    if year and str(year) != str(media_info.year):
                        continue
                    # 匹配关键字或正则表达式
                    search_title = f"{media_info.org_string} {media_info.title} {media_info.year}"
                    if not re.search(name, search_title, re.I) and name not in search_title:
                        continue
                # 媒体匹配成功
                match_flag = True
                match_rss_info = rss_info
                break

        # 名称匹配成功，开始过滤
        if match_flag:
            # 解析种子详情
            if site_parse:
                # 站点流控
                if self.sites.check_ratelimit(site_id):
                    match_msg.append("触发站点流控")
                    return False, match_msg, match_rss_info
                # 检测Free
                torrent_attr = self.siteconf.check_torrent_attr(torrent_url=media_info.page_url,
                                                                cookie=site_cookie,
                                                                ua=site_ua,
                                                                proxy=site_proxy)
                if torrent_attr.get('2xfree'):
                    download_volume_factor = 0.0
                    upload_volume_factor = 2.0
                elif torrent_attr.get('free'):
                    download_volume_factor = 0.0
                    upload_volume_factor = 1.0
                else:
                    upload_volume_factor = 1.0
                    download_volume_factor = 1.0
                if torrent_attr.get('hr'):
                    hit_and_run = True
                # 设置属性
                media_info.set_torrent_info(upload_volume_factor=upload_volume_factor,
                                            download_volume_factor=download_volume_factor,
                                            hit_and_run=hit_and_run)
            # 订阅无过滤规则应用站点设置
            filter_rule = match_rss_info.get('filter_rule') or site_filter_rule
            filter_dict = {
                "restype": match_rss_info.get('filter_restype'),
                "pix": match_rss_info.get('filter_pix'),
                "team": match_rss_info.get('filter_team'),
                "rule": filter_rule,
                "include": match_rss_info.get('filter_include'),
                "exclude": match_rss_info.get('filter_exclude'),
            }
            match_filter_flag, res_order, match_filter_msg = self.filter.check_torrent_filter(meta_info=media_info,
                                                                                              filter_args=filter_dict)
            if not match_filter_flag:
                match_msg.append(match_filter_msg)
                return False, match_msg, match_rss_info
            else:
                match_msg.append("%s 识别为 %s %s 匹配订阅成功" % (
                    media_info.org_string,
                    media_info.get_title_string(),
                    media_info.get_season_episode_string()))
                match_msg.append(f"种子描述：{media_info.subtitle}")
                match_rss_info.update({
                    "res_order": res_order,
                    "filter_rule": filter_rule,
                    "upload_volume_factor": upload_volume_factor,
                    "download_volume_factor": download_volume_factor})
                return True, match_msg, match_rss_info
        else:
            match_msg.append("%s 识别为 %s %s 不在订阅范围" % (
                media_info.org_string,
                media_info.get_title_string(),
                media_info.get_season_episode_string()))
            return False, match_msg, match_rss_info

    def download_rss_torrent(self, rss_download_torrents, rss_no_exists):
        """
        根据缺失情况以及匹配到的结果选择下载种子
        """

        if not rss_download_torrents:
            return

        finished_rss_torrents = []
        updated_rss_torrents = []

        def __finish_rss(download_item):
            """
            完成订阅
            """
            if not download_item:
                return
            if not download_item.rssid \
                    or download_item.rssid in finished_rss_torrents:
                return
            finished_rss_torrents.append(download_item.rssid)
            self.subscribe.finish_rss_subscribe(rssid=download_item.rssid,
                                                media=download_item)

        def __update_tv_rss(download_item, left_media):
            """
            更新订阅集数
            """
            if not download_item or not left_media:
                return
            if not download_item.rssid \
                    or download_item.rssid in updated_rss_torrents:
                return
            updated_rss_torrents.append(download_item.rssid)
            self.subscribe.update_subscribe_tv_lack(rssid=download_item.rssid,
                                                    media_info=download_item,
                                                    seasoninfo=left_media)

        def __update_over_edition(download_item):
            """
            更新洗版订阅
            """
            if not download_item:
                return
            if not download_item.rssid \
                    or download_item.rssid in updated_rss_torrents:
                return
            if download_item.get_episode_list():
                return
            updated_rss_torrents.append(download_item.rssid)
            self.subscribe.update_subscribe_over_edition(rtype=download_item.type,
                                                         rssid=download_item.rssid,
                                                         media=download_item)

        # 去重择优后开始添加下载
        download_items, left_medias = self.downloader.batch_download(SearchType.RSS,
                                                                     rss_download_torrents,
                                                                     rss_no_exists)
        # 批量删除订阅
        if download_items:
            for item in download_items:
                if not item.rssid:
                    continue
                if item.over_edition:
                    # 更新洗版订阅
                    __update_over_edition(item)
                elif not left_medias or not left_medias.get(item.tmdb_id):
                    # 删除电视剧订阅
                    __finish_rss(item)
                else:
                    # 更新电视剧缺失剧集
                    __update_tv_rss(item, left_medias.get(item.tmdb_id))
            log.info("【Rss】实际下载了 %s 个资源" % len(download_items))
        else:
            log.info("【Rss】未下载到任何资源")

    def delete_rss_history(self, rssid):
        """
        删除订阅历史
        """
        self.dbhelper.delete_rss_history(rssid=rssid)

    def get_rss_history(self, rtype=None, rid=None):
        """
        获取订阅历史
        """
        return self.dbhelper.get_rss_history(rtype=rtype, rid=rid)
