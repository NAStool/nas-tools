import datetime
import random
from threading import Lock
from time import sleep

from lxml import etree
from requests.utils import dict_from_cookiejar

import log
from app.db import SqlHelper
from app.message import Message
from config import Config
from app.downloader.downloader import Downloader
from app.searcher import Searcher
from app.media.doubanv2api import DoubanApi
from app.media import Media, MetaInfo
from app.utils import RequestUtils
from app.utils.types import MediaType, SearchType
from web.backend.subscribe import add_rss_subscribe

lock = Lock()


class DouBan:
    req = None
    searcher = None
    media = None
    downloader = None
    doubanapi = None
    message = None
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
        self.message = Message()
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
        if not self.__interval \
                or not self.__days \
                or not self.__users \
                or not self.__types:
            log.warn("【DOUBAN】豆瓣未配置或配置不正确")
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
                        if not res:
                            log.warn(f"【DOUBAN】第 {page_number} 页无法访问")
                            break
                        html_text = res.text
                        if not html_text:
                            log.warn(f"【DOUBAN】第 {page_number} 页未获取到数据")
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
                                log.info("【DOUBAN】解析到媒体：%s" % doubanid)
                                douban_ids.append(doubanid)
                                sucess_urlnum += 1
                                user_type_succnum += 1
                                user_succnum += 1
                        log.debug(f"【DOUBAN】第 {page_number} 页解析完成，共获取到 {sucess_urlnum} 个媒体")
                    except Exception as err:
                        log.error(f"【DOUBAN】第 {page_number} 页解析出错：%s" % str(err))
                        break
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
            if not douban_info.get("title"):
                # 随机休眠
                sleep(round(random.uniform(1, 5), 1))
                continue
            # 组装媒体信息
            if douban_info.get("title") == "未知电影":
                douban_info = self.get_media_detail_from_web("https://movie.douban.com/subject/%s/" % doubanid)
                if not douban_info:
                    log.warn("【DOUBAN】%s 无权限访问，需要配置豆瓣Cookie" % doubanid)
                    # 随机休眠
                    sleep(round(random.uniform(1, 5), 1))
                    continue
            media_type = MediaType.TV if douban_info.get("episodes_count") else MediaType.MOVIE
            log.info("【DOUBAN】%s：%s %s".strip() % (media_type.value, douban_info.get("title"), douban_info.get("year")))
            meta_info = MetaInfo(title="%s %s" % (douban_info.get("title"), douban_info.get("year") or ""))
            meta_info.douban_id = doubanid
            meta_info.type = media_type
            meta_info.overview = douban_info.get("intro")
            meta_info.poster_path = douban_info.get("cover_url")
            rating = douban_info.get("rating", {}) or {}
            meta_info.vote_average = rating.get("value") or ""
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
            log.info("【DOUBAN】豆瓣配置：同步间隔未配置或配置不正确")
            return
        try:
            lock.acquire()
            log.info("【DOUBAN】开始同步豆瓣数据...")
            # 拉取豆瓣数据
            medias = self.get_all_douban_movies()
            # 开始检索
            if self.__auto_search:
                # 需要检索
                for media in medias:
                    if not media:
                        continue
                    # 查询数据库状态，已经加入RSS的不处理
                    search_state = SqlHelper.get_douban_search_state(media.get_name(), media.year)
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
                                SqlHelper.insert_douban_media_state(media, "DOWNLOADED")
                                continue
                            # 开始检索
                            search_result, no_exists, search_count, download_count = self.searcher.search_one_media(
                                media_info=media_info,
                                in_from=SearchType.DB,
                                no_exists=no_exists)
                            if search_result:
                                # 下载全了更新为已下载，没下载全的下次同步再次搜索
                                SqlHelper.insert_douban_media_state(media, "DOWNLOADED")
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
                                # 发送订阅消息
                                self.message.send_rss_success_message(in_from=SearchType.DB, media_info=media)
                                # 插入为已RSS状态
                                SqlHelper.insert_douban_media_state(media, "RSS")
                    else:
                        log.info("【DOUBAN】%s %s 已处理过" % (media.get_name(), media.year))
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
                            # 发送订阅消息
                            self.message.send_rss_success_message(in_from=SearchType.DB, media_info=media)
                            # 插入为已RSS状态
                            SqlHelper.insert_douban_media_state(media, "RSS")
            log.info("【DOUBAN】豆瓣数据同步完成")
        finally:
            lock.release()

    def search_douban_medias(self, keyword, mtype: MediaType = None, num=20, season=None, episode=None):
        """
        根据关键字搜索豆瓣，返回可能的标题和年份信息
        """
        if not keyword:
            return []
        result = self.doubanapi.search(keyword)
        if not result:
            return []
        ret_medias = []
        for item_obj in result.get("items"):
            if mtype and mtype.value != item_obj.get("type_name"):
                continue
            if item_obj.get("type_name") not in (MediaType.TV.value, MediaType.MOVIE.value):
                continue
            item = item_obj.get("target")
            meta_info = MetaInfo(title=item.get("title"))
            meta_info.title = item.get("title")
            if item_obj.get("type_name") == MediaType.MOVIE.value:
                meta_info.type = MediaType.MOVIE
            else:
                meta_info.type = MediaType.TV
            if season:
                if meta_info.type != MediaType.TV:
                    continue
                if season != 1 and meta_info.begin_season != season:
                    continue
            if episode and str(episode).isdigit():
                if meta_info.type != MediaType.TV:
                    continue
                meta_info.begin_episode = int(episode)
                meta_info.title = "%s 第%s集" % (meta_info.title, episode)
            meta_info.year = item.get("year")
            meta_info.tmdb_id = "DB:%s" % item.get("id")
            meta_info.douban_id = item.get("id")
            meta_info.overview = item.get("card_subtitle") or ""
            meta_info.poster_path = item.get("cover_url").split('?')[0]
            rating = item.get("rating", {}) or {}
            meta_info.vote_average = rating.get("value")
            if meta_info not in ret_medias:
                ret_medias.append(meta_info)

        return ret_medias[:num]

    def get_media_detail_from_web(self, url):
        """
        从豆瓣详情页抓紧媒体信息
        :param url: 豆瓣详情页URL
        :return: {title, year, intro, cover_url, rating{value}, episodes_count}
        """
        ret_media = {}
        res = self.req.get_res(url=url)
        if res and res.status_code == 200:
            html_text = res.text
            if not html_text:
                return None
            try:
                html = etree.HTML(html_text)
                ret_media['title'] = html.xpath("//span[@property='v:itemreviewed']/text()")[0]
                if not ret_media.get('title'):
                    return None
                ret_media['year'] = html.xpath("//div[@id='content']//span[@class='year']/text()")[0][1:-1]
                ret_media['intro'] = "".join(
                    [str(x).strip() for x in html.xpath("//span[@property='v:summary']/text()")])
                ret_media['cover_url'] = html.xpath("//div[@id='mainpic']/a/img/@src")[0]
                if ret_media['cover_url']:
                    ret_media['cover_url'] = ret_media.get('cover_url').replace("s_ratio_poster", "m_ratio_poster")
                ret_media['rating'] = {"value": float(html.xpath("//strong[@property='v:average']/text()")[0])}
                detail_info = html.xpath("//div[@id='info']/text()")
                if isinstance(detail_info, list):
                    detail_info = [str(x).strip() for x in detail_info if str(x).strip().isdigit()]
                    if detail_info and str(detail_info[0]).isdigit():
                        ret_media['episodes_count'] = int(detail_info[0])
            except Exception as err:
                print(err)
        return ret_media
