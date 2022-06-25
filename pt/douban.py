import datetime
import random
from threading import Lock
from time import sleep

from lxml import etree
from requests.utils import dict_from_cookiejar

import log
from config import Config
from pt.downloader import Downloader
from pt.searcher import Searcher
from rmt.doubanv2api.doubanapi import DoubanApi
from rmt.media import Media
from rmt.metainfo import MetaInfo
from utils.http_utils import RequestUtils
from utils.sqls import get_douban_search_state, insert_douban_media_state
from utils.types import MediaType, SearchType
from web.backend.subscribe import add_rss_subscribe

lock = Lock()


class DouBan:
    req = None
    searcher = None
    media = None
    downloader = None
    doubanapi = None
    __users = []
    __days = 0
    __interval = None
    __auto_search = True
    __auto_rss = True
    __types = []

    def __init__(self):
        self.searcher = Searcher()
        self.downloader = Downloader()
        self.media = Media()
        self.doubanapi = DoubanApi()
        self.init_config()

    def init_config(self):
        config = Config()
        douban = config.get_config('douban')
        if douban:
            # 同步间隔
            self.__interval = int(douban.get('interval'))
            self.__auto_search = douban.get('auto_search')
            self.__auto_rss = douban.get('auto_rss')
            # 用户列表
            users = douban.get('users')
            if users:
                if not isinstance(users, list):
                    users = [users]
                self.__users = users
            # 时间范围
            self.__days = int(douban.get('days'))
            # 类型
            types = douban.get('types')
            if types:
                self.__types = types.split(',')
            # Cookie
            cookie = douban.get('cookie')
            if not cookie:
                try:
                    if self.req:
                        res = self.req.get_res("https://www.douban.com/")
                        if res:
                            cookie = dict_from_cookiejar(res.cookies)
                except Exception as err:
                    log.warn(f"【DOUBAN】获取cookie失败：{format(err)}")
            self.req = RequestUtils(cookies=cookie)

    def get_all_douban_movies(self):
        """
        获取每一个用户的每一个类型的豆瓣标记
        :return: 检索到的媒体信息列表（不含TMDB信息）
        """
        # 返回媒体列表
        media_list = []
        # 豆瓣ID列表
        douban_ids = []
        # 开始序号
        start_number = 0
        # 每页条数
        perpage_number = 15
        # 每一个用户
        for user in self.__users:
            if not user:
                continue
            # 每一个类型成功数量
            user_succnum = 0
            for mtype in self.__types:
                if not mtype:
                    continue
                log.info(f"【DOUBAN】开始获取 {user} 的 {mtype} 数据...")
                # 类型成功数量
                user_type_succnum = 0
                # 每一页
                while True:
                    # 页数
                    page_number = int(start_number / perpage_number + 1)
                    # 当前页成功数量
                    sucess_urlnum = 0
                    # 是否继续下一页
                    continue_next_page = True
                    log.debug(f"【DOUBAN】开始解析第 {page_number} 页数据...")
                    try:
                        # 解析豆瓣页面
                        url = f"https://movie.douban.com/people/{user}/{mtype}?start={start_number}&sort=time&rating=all&filter=all&mode=grid"
                        res = self.req.get_res(url=url)
                        html_text = res.text
                        if not html_text:
                            log.warn(f"【DOUBAN】第 {page_number} 页未获取到数据")
                            break
                        html = etree.HTML(html_text)
                        # ID列表
                        items = html.xpath("//div[@class='info']//a[contains(@href,'https://movie.douban.com/subject/')]/@href")
                        if not items:
                            break
                        # 时间列表
                        dates = html.xpath("//div[@class='info']//span[@class='date']/text()")
                        if not dates:
                            break
                        # 计算当前页有效个数
                        items_count = 0
                        for date in dates:
                            mark_date = datetime.datetime.strptime(date, '%Y-%m-%d')
                            if (datetime.datetime.now() - mark_date).days < int(self.__days):
                                items_count += 1
                            else:
                                break
                        # 当前页有效个数不足15个时
                        if items_count < 15:
                            continue_next_page = False
                        # 解析豆瓣ID
                        for item in items:
                            items_count -= 1
                            if items_count < 0:
                                break
                            doubanid = item.split("/")[-2]
                            if str(doubanid).isdigit():
                                log.info("【DOUBAN】解析到媒体：%s" % doubanid)
                                douban_ids.append(doubanid)
                                sucess_urlnum += 1
                                user_type_succnum += 1
                                user_succnum += 1
                        log.debug(f"【DOUBAN】第 {page_number} 页解析完成，共获取到 {sucess_urlnum} 个媒体")
                    except Exception as err:
                        log.error(f"【DOUBAN】第 {page_number} 页解析出错：%s" % str(err))
                    # 继续下一页
                    if continue_next_page:
                        start_number += perpage_number
                        # 随机休眠
                        sleep(round(random.uniform(1, 5), 1))
                    else:
                        break
                # 当前类型解析结束
                log.debug(f"【DOUBAN】用户 {user} 的 {mtype} 解析完成，共获取到 {user_type_succnum} 个媒体")
            log.info(f"【DOUBAN】用户 {user} 解析完成，共获取到 {user_succnum} 个媒体")
        log.info(f"【DOUBAN】所有用户解析完成，共获取到 {len(douban_ids)} 个媒体")
        # 查询豆瓣详情
        for doubanid in douban_ids:
            log.info("【DOUBAN】正在查询豆瓣详情：%s" % doubanid)
            douban_info = self.doubanapi.movie_detail(doubanid)
            if not douban_info:
                douban_info = self.doubanapi.tv_detail(doubanid)
            if not douban_info:
                log.warn("【DOUBAN】%s 未找到豆瓣详细信息" % doubanid)
                # 随机休眠
                sleep(round(random.uniform(1, 5), 1))
                continue
            if douban_info.get("localized_message"):
                log.warn("【DOUBAN】查询豆瓣详情返回：%s" % douban_info.get("localized_message"))
                # 随机休眠
                sleep(round(random.uniform(1, 5), 1))
                continue
            media_type = MediaType.TV if douban_info.get("episodes_count") else MediaType.MOVIE
            # 组装媒体信息
            title = douban_info.get("title")
            year = douban_info.get("year")
            if title == "未知电影" and not year:
                log.warn("【DOUBAN】%s 无权限访问，需要配置豆瓣Cookie" % doubanid)
                continue
            log.info("【DOUBAN】%s：%s %s".strip() % (media_type.value, title, year))
            meta_info = MetaInfo(title="%s %s" % (title, year or ""))
            meta_info.douban_id = doubanid
            meta_info.type = media_type
            meta_info.overview = douban_info.get("intro")
            meta_info.poster_path = douban_info.get("cover_url")
            meta_info.vote_average = douban_info.get("rating", {}).get("value") or ""
            if meta_info not in media_list:
                media_list.append(meta_info)
            # 随机休眠
            sleep(round(random.uniform(1, 5), 1))
        return media_list

    def sync(self):
        """
        同步豆瓣数据
        """
        if not self.__interval:
            return
        try:
            lock.acquire()
            log.info("【DOUBAN】开始同步豆瓣数据...")
            # 拉取豆瓣数据
            medias = self.get_all_douban_movies()
            # 开始检索
            if self.__auto_search:
                # 需要检索
                if len(medias) == 0:
                    return
                for media in medias:
                    if not media:
                        continue
                    # 查询数据库状态，已经加入RSS的不处理
                    search_state = get_douban_search_state(media.get_name(), media.year)
                    if not search_state or search_state[0][0] == "NEW":
                        if not self.__auto_rss:
                            # 不需要自动加订阅，则直接搜索
                            if media.begin_season:
                                subtitle = "第%s季" % media.begin_season
                            else:
                                subtitle = None
                            media_info = self.media.get_media_info(title="%s %s" % (media.get_name(), media.year or ""),
                                                                   subtitle=subtitle,
                                                                   mtype=media.type)
                            if not media_info or not media_info.tmdb_info:
                                log.warn("【DOUBAN】%s 未查询到媒体信息" % media.get_name())
                                continue
                            # 合并季
                            media_info.begin_season = media.begin_season
                            # 检查是否存在，电视剧返回不存在的集清单
                            exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info)
                            # 已经存在
                            if exist_flag:
                                # 更新为已下载状态
                                log.info("【DOUBAN】%s 已存在" % media.get_name())
                                insert_douban_media_state(media, "DOWNLOADED")
                                continue
                            # 开始检索
                            search_result, no_exists, search_count, download_count = self.searcher.search_one_media(
                                media_info=media_info,
                                in_from=SearchType.DB,
                                no_exists=no_exists)
                            if search_result:
                                # 下载全了更新为已下载，没下载全的下次同步再次搜索
                                insert_douban_media_state(media, "DOWNLOADED")
                        else:
                            # 需要加订阅，则由订阅去检索
                            log.info("【DOUBAN】%s %s 更新到%s订阅中..." % (media.get_name(), media.year, media.type.value))
                            code, msg, _ = add_rss_subscribe(mtype=media.type,
                                                             name=media.get_name(),
                                                             year=media.year,
                                                             season=media.begin_season,
                                                             doubanid=media.douban_id)
                            if code != 0:
                                log.error("【DOUBAN】%s 添加订阅失败：%s" % (media.get_name(), msg))
                            else:
                                # 插入为已RSS状态
                                insert_douban_media_state(media, "RSS")
                    else:
                        log.debug("【DOUBAN】%s %s 已处理过" % (media.get_name(), media.year))
            else:
                # 不需要检索
                if self.__auto_rss:
                    # 加入订阅，使状态为R
                    for media in medias:
                        log.info("【DOUBAN】%s %s 更新到%s订阅中..." % (media.get_name(), media.year, media.type.value))
                        code, msg, _ = add_rss_subscribe(mtype=media.type,
                                                         name=media.get_name(),
                                                         year=media.year,
                                                         season=media.begin_season,
                                                         doubanid=media.douban_id,
                                                         state="R")
                        if code != 0:
                            log.error("【DOUBAN】%s 添加订阅失败：%s" % (media.get_name(), msg))
                        else:
                            # 插入为已RSS状态
                            insert_douban_media_state(media, "RSS")
            log.info("【DOUBAN】豆瓣数据同步完成")
        finally:
            lock.release()
