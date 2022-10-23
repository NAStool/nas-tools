import datetime
import random
from threading import Lock
from time import sleep

from lxml import etree

import log
from app.media.douban import DouBan
from app.downloader import Downloader
from app.helper import DbHelper
from app.media import Media, MetaInfo
from app.message import Message
from app.searcher import Searcher
from app.utils.types import SearchType, MediaType
from config import Config
from app.subscribe import Subscribe

lock = Lock()


class DoubanSync:
    douban = None
    searcher = None
    media = None
    downloader = None
    dbhelper = None
    subscribe = None
    __interval = None
    __auto_search = None
    __auto_rss = None
    __users = None
    __days = None
    __types = None

    def __init__(self):
        self.douban = DouBan()
        self.searcher = Searcher()
        self.downloader = Downloader()
        self.media = Media()
        self.message = Message()
        self.dbhelper = DbHelper()
        self.subscribe = Subscribe()
        self.init_config()

    def init_config(self):
        config = Config()
        douban = config.get_config('douban')
        if douban:
            # 同步间隔
            self.__interval = int(douban.get('interval')) if str(douban.get('interval')).isdigit() else None
            self.__auto_search = douban.get('auto_search')
            self.__auto_rss = douban.get('auto_rss')
            # 用户列表
            users = douban.get('users')
            if users:
                if not isinstance(users, list):
                    users = [users]
                self.__users = users
            # 时间范围
            self.__days = int(douban.get('days')) if str(douban.get('days')).isdigit() else None
            # 类型
            types = douban.get('types')
            if types:
                self.__types = types.split(',')

    def sync(self):
        """
        同步豆瓣数据
        """
        if not self.__interval:
            log.info("【Douban】豆瓣配置：同步间隔未配置或配置不正确")
            return
        try:
            lock.acquire()
            log.info("【Douban】开始同步豆瓣数据...")
            # 拉取豆瓣数据
            medias = self.__get_all_douban_movies()
            # 开始检索
            if self.__auto_search:
                # 需要检索
                for media in medias:
                    if not media:
                        continue
                    # 查询数据库状态，已经加入RSS的不处理
                    search_state = self.dbhelper.get_douban_search_state(media.get_name(), media.year)
                    if not search_state or search_state[0][0] == "NEW":
                        if media.begin_season:
                            subtitle = "第%s季" % media.begin_season
                        else:
                            subtitle = None
                        media_info = self.media.get_media_info(title="%s %s" % (media.get_name(), media.year or ""),
                                                               subtitle=subtitle,
                                                               mtype=media.type)
                        # 不需要自动加订阅，则直接搜索
                        if not media_info or not media_info.tmdb_info:
                            log.warn("【Douban】%s 未查询到媒体信息" % media.get_name())
                            continue
                        # 检查是否存在，电视剧返回不存在的集清单
                        exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info)
                        # 已经存在
                        if exist_flag:
                            # 更新为已下载状态
                            log.info("【Douban】%s 已存在" % media.get_name())
                            self.dbhelper.insert_douban_media_state(media, "DOWNLOADED")
                            continue
                        if not self.__auto_rss:
                            # 合并季
                            media_info.begin_season = media.begin_season
                            # 开始检索
                            search_result, no_exists, search_count, download_count = self.searcher.search_one_media(
                                media_info=media_info,
                                in_from=SearchType.DB,
                                no_exists=no_exists)
                            if search_result:
                                # 下载全了更新为已下载，没下载全的下次同步再次搜索
                                self.dbhelper.insert_douban_media_state(media, "DOWNLOADED")
                        else:
                            # 需要加订阅，则由订阅去检索
                            log.info("【Douban】%s %s 更新到%s订阅中..." % (media.get_name(), media.year, media.type.value))
                            code, msg, _ = self.subscribe.add_rss_subscribe(mtype=media.type,
                                                                            name=media.get_name(),
                                                                            year=media.year,
                                                                            season=media.begin_season,
                                                                            doubanid=media.douban_id)
                            if code != 0:
                                log.error("【Douban】%s 添加订阅失败：%s" % (media.get_name(), msg))
                            else:
                                # 发送订阅消息
                                self.message.send_rss_success_message(in_from=SearchType.DB, media_info=media)
                                # 插入为已RSS状态
                                self.dbhelper.insert_douban_media_state(media, "RSS")
                    else:
                        log.info("【Douban】%s %s 已处理过" % (media.get_name(), media.year))
            else:
                # 不需要检索
                if self.__auto_rss:
                    # 加入订阅，使状态为R
                    for media in medias:
                        log.info("【Douban】%s %s 更新到%s订阅中..." % (media.get_name(), media.year, media.type.value))
                        code, msg, _ = self.subscribe.add_rss_subscribe(mtype=media.type,
                                                                        name=media.get_name(),
                                                                        year=media.year,
                                                                        season=media.begin_season,
                                                                        doubanid=media.douban_id,
                                                                        state="R")
                        if code != 0:
                            log.error("【Douban】%s 添加订阅失败：%s" % (media.get_name(), msg))
                        else:
                            # 发送订阅消息
                            self.message.send_rss_success_message(in_from=SearchType.DB, media_info=media)
                            # 插入为已RSS状态
                            self.dbhelper.insert_douban_media_state(media, "RSS")
            log.info("【Douban】豆瓣数据同步完成")
        finally:
            lock.release()

    def __get_all_douban_movies(self):
        """
        获取每一个用户的每一个类型的豆瓣标记
        :return: 检索到的媒体信息列表（不含TMDB信息）
        """
        if not self.__interval \
                or not self.__days \
                or not self.__users \
                or not self.__types:
            log.warn("【Douban】豆瓣未配置或配置不正确")
            return []
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
                log.info(f"【Douban】开始获取 {user} 的 {mtype} 数据...")
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
                    log.debug(f"【Douban】开始解析第 {page_number} 页数据...")
                    try:
                        # 解析豆瓣页面
                        url = f"https://movie.douban.com/people/{user}/{mtype}?start={start_number}&sort=time&rating=all&filter=all&mode=grid"
                        html_text = self.douban.get_douban_page_html(url=url)
                        if not html_text:
                            log.warn(f"【Douban】第 {page_number} 页未获取到数据")
                            break
                        html = etree.HTML(html_text)
                        # ID列表
                        items = html.xpath(
                            "//div[@class='info']//a[contains(@href,'https://movie.douban.com/subject/')]/@href")
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
                                log.info("【Douban】解析到媒体：%s" % doubanid)
                                douban_ids.append(doubanid)
                                sucess_urlnum += 1
                                user_type_succnum += 1
                                user_succnum += 1
                        log.debug(f"【Douban】第 {page_number} 页解析完成，共获取到 {sucess_urlnum} 个媒体")
                    except Exception as err:
                        log.error(f"【Douban】第 {page_number} 页解析出错：%s" % str(err))
                        break
                    # 继续下一页
                    if continue_next_page:
                        start_number += perpage_number
                        # 随机休眠
                        sleep(round(random.uniform(1, 5), 1))
                    else:
                        break
                # 当前类型解析结束
                log.debug(f"【Douban】用户 {user} 的 {mtype} 解析完成，共获取到 {user_type_succnum} 个媒体")
            log.info(f"【Douban】用户 {user} 解析完成，共获取到 {user_succnum} 个媒体")
        log.info(f"【Douban】所有用户解析完成，共获取到 {len(douban_ids)} 个媒体")
        # 查询豆瓣详情
        for doubanid in douban_ids:
            douban_info = self.douban.get_douban_detail(doubanid)
            # 组装媒体信息
            if not douban_info:
                log.warn("【Douban】%s 未正确获取豆瓣详细信息，尝试使用网页获取" % doubanid)
                douban_info = self.douban.get_media_detail_from_web("https://movie.douban.com/subject/%s/" % doubanid)
                if not douban_info:
                    log.warn("【Douban】%s 无权限访问，需要配置豆瓣Cookie" % doubanid)
                    # 随机休眠
                    sleep(round(random.uniform(1, 5), 1))
                    continue
            media_type = MediaType.TV if douban_info.get("episodes_count") else MediaType.MOVIE
            log.info("【Douban】%s：%s %s".strip() % (media_type.value, douban_info.get("title"), douban_info.get("year")))
            meta_info = MetaInfo(title="%s %s" % (douban_info.get("title"), douban_info.get("year") or ""))
            meta_info.douban_id = doubanid
            meta_info.type = media_type
            meta_info.overview = douban_info.get("intro")
            meta_info.poster_path = douban_info.get("cover_url")
            rating = douban_info.get("rating", {}) or {}
            meta_info.vote_average = rating.get("value") or ""
            meta_info.imdb_id = douban_info.get("imdbid")
            if meta_info not in media_list:
                media_list.append(meta_info)
            # 随机休眠
            sleep(round(random.uniform(1, 5), 1))
        return media_list
