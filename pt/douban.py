import datetime
import random
from threading import Lock
from time import sleep
import re
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

import log
from config import Config
from pt.downloader import Downloader
from pt.searcher import Searcher
from rmt.media import Media
from rmt.meta.metabase import MetaBase
from rmt.metainfo import MetaInfo
from utils.http_utils import RequestUtils
from utils.sqls import get_douban_search_state, insert_rss_tv, insert_rss_movie, insert_douban_media_state
from utils.types import MediaType, SearchType

lock = Lock()


class DouBan:
    req = None
    searcher = None
    media = None
    downloader = None
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
        self.init_config()

    def init_config(self):
        config = Config()
        app = config.get_config('app')
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
            # headers
            user_agent = app.get('user_agent')
            # Cookie
            cookie = douban.get('cookie')
            if not cookie:
                try:
                    if self.req:
                        res = self.req.get_res("https://www.douban.com/")
                        if res:
                            cookies = res.cookies
                            cookie = requests.utils.dict_from_cookiejar(cookies)
                except Exception as err:
                    log.warn(f"【DOUBAN】获取cookie失败:{format(err)}")
            self.req = RequestUtils(headers=user_agent, cookies=cookie)

    def get_all_douban_movies(self):
        """
        获取每一个用户的每一个类型的豆瓣标记
        :return: 检索到的媒体信息列表（不含TMDB信息）
        """
        movie_list = []
        start_number = 0
        # 每一个用户
        for user in self.__users:
            if not user:
                continue
            # 每一个类型
            user_succnum = 0
            for mtype in self.__types:
                if not mtype:
                    continue
                log.info(f"【DOUBAN】开始获取 {user} 的 {mtype} 数据...")
                err_url = []
                user_type_succnum = 0
                # 每一页
                while True:
                    page_number = int(start_number / 15 + 1)
                    # 每一页的文本
                    log.info(f"【DOUBAN】开始解析第 {page_number} 页数据...")
                    soup = self.get_html_soup(user_id=user, media_status=mtype, start_number=start_number)
                    # 获取全部url
                    url_dict = self.__get_url_list(soup, self.__days)
                    url_list = url_dict["url_list"]
                    url_num = len(url_list)
                    log.info(f"【DOUBAN】第 {page_number} 页有 {url_num} 个媒体")
                    monitoring_info = url_dict["monitoring_info"]
                    log.info(f"【DOUBAN】本页监控日期内的数据为：{monitoring_info[0]}")
                    log.info(f"【DOUBAN】是否继续访问下一页：{monitoring_info[1]}")
                    sucess_urlnum = 0
                    url_count = 0
                    for url in url_list:
                        if url_count == monitoring_info[0] and not monitoring_info[1]:
                            log.info("【DOUBAN】其他媒体不在监控时间内，结束导入")
                            break
                        else:
                            url_count += 1
                        # 随机休眠
                        time_number = round(random.uniform(1, 5), 1)
                        log.info(f"【DOUBAN】解析媒体 {url_count} 随机休眠：{time_number}s")
                        sleep(time_number)
                        # 每一个条目的内容
                        media_soup = self.get_html_soup(user_id=user, url=url, media_status=mtype)
                        if not media_soup:
                            log.warn(f"【DOUBAN】访问该页面出现问题，媒体链接：{url}")
                            err_url.append(url)
                        else:
                            movie_dict = self.__get_movie_dict(media_soup)
                            if movie_dict:
                                # 加入数组
                                if movie_dict not in movie_list:
                                    log.info(f"【DOUBAN】解析到媒体：%s" % movie_dict.get_name())
                                    movie_list.append(movie_dict)
                                    sucess_urlnum += 1
                                    user_type_succnum += 1
                                    user_succnum += 1
                    if monitoring_info[1] is False:
                        break
                    if url_num > 14:
                        start_number += 15
                    else:
                        break
                    log.info(f"【DOUBAN】第 {page_number} 页解析完成，共获取到 {sucess_urlnum} 个媒体")
                log.info(f"【DOUBAN】用户 {user} 的 {mtype} 解析完成，共获取到 {user_type_succnum} 个媒体")
            log.info(f"【DOUBAN】用户 {user} 解析完成，共获取到 {user_succnum} 个媒体")
        log.info(f"【DOUBAN】所有用户解析完成，共获取到 {len(movie_list)} 个媒体")

        return movie_list

    @staticmethod
    def __get_url_list(soup, monitoring_day=0):
        """
        解析个人wish/do/collect内容的每个url
        :return: { url_list: [url数组], monitoring_info: [符合日期的个数,是否继续]}
        """
        url_list = []
        continue_request = True
        monitoring_info = [0, continue_request]
        url_dict = {}
        try:
            info = soup.select('.nbg')
            for url in info:
                url_list.append(url.get('href'))
            if monitoring_day != 0:
                mark_date = soup.select('span.date')
                # 处理所有标记时间
                num = 0
                mark_date_dict = {}
                while num < len(mark_date):
                    mark_date_dict[num] = list(mark_date[num].strings)
                    mark_date_dict[num] = ''.join([i.split("\n", 1)[0] for i in mark_date_dict[num] if i.strip() != ''])
                    num += 1
                # 获取当天时间
                today = datetime.datetime.now()
                # 判断 标记时间
                # 符合监控日期内媒体个数计数
                count_num = 0
                for key in mark_date_dict:
                    mark_date_i = datetime.datetime.strptime(mark_date_dict.get(key), '%Y-%m-%d')
                    interval = today - mark_date_i
                    if interval.days < monitoring_day:
                        count_num += 1
                    else:
                        break
            else:
                # 如果没有监控日期，与媒体个数相同即可
                count_num = len(url_list)
            # 如果该页媒体为15，且监控没有限制或者都在监控日期内，则继续获取下一页内容
            if len(url_list) == 15 and count_num == len(url_list):
                continue_request = True
            else:
                continue_request = False

            monitoring_info[0] = count_num
            monitoring_info[1] = continue_request
            url_dict["url_list"] = url_list
            url_dict["monitoring_info"] = monitoring_info
            return url_dict
        except Exception as err:
            log.warn(f"【DOUBAN】解析失败：{err}")
            return url_dict

    def get_html_soup(self, user_id=None, url=None, media_status="wish", start_number=0):
        """
        获取链接的html文档
        :param user_id: 用户id(如果url选择第二种则为空）
        :param url: 链接地址
        :param media_status: 状态（wish/do/collect），同上
        :param start_number: url为空时，该参数必填
        :return: html的text格式
        """
        if not url:
            if not user_id:
                return None
            url = f"https://movie.douban.com/people/{user_id}/{media_status}?start={start_number}&sort=time&rating=all&filter=all&mode=grid"
        try:
            res = self.req.get_res(url=url)
            if res and res.status_code == 200:
                res_text = res.text
                if res_text.find('有异常请求从你的 IP 发出') != -1:
                    log.warn("【DOUBAN】被豆瓣识别到抓取行为了，请更换 IP 后才能使用")
                    return None
                return BeautifulSoup(res_text, 'html.parser')
            elif res and res.status_code == 404:
                log.warn(f"【DOUBAN】该页面不存在：{url}")
                return None
            else:
                log.error(f"【DOUBAN】网络连接失败：{url}")
                return None
        except Exception as err:
            log.error(f"【RUN】获取{url}页面失败：{format(err)}")
            return None

    def get_douban_hot_json(self, mtype='movie', nums=20):
        if mtype != "anime":
            data = {
                'type': mtype,
                'tag': '热门',
                'sort': 'recommend',
                'page_limit': nums,
                'page_start': 0
            }
        else:
            data = {
                'type': 'tv',
                'tag': '日本动画',
                'sort': 'recommend',
                'page_limit': nums,
                'page_start': 0
            }
        url = 'https://movie.douban.com/j/search_subjects?' + urlencode(data)
        try:
            res = self.req.get_res(url=url)
            if res and res.status_code == 200:
                return res.text
        except Exception as e:
            log.console(str(e))
            return None
        return None

    def get_douban_new_json(self, mtype='movie', nums=20):
        """
        获取豆瓣热门和最新电影
        :param mtype: 类型，movie或tv
        :param nums: 每页获取条数，默认20
        """
        if mtype == "movie":
            data = {
                'type': 'movie',
                'tag': '最新',
                'page_limit': nums,
                'page_start': 0
            }
        else:
            data = {
                'type': 'tv',
                'tag': '热门',
                'sort': 'time',
                'page_limit': nums,
                'page_start': 0
            }

        url = 'https://movie.douban.com/j/search_subjects?' + urlencode(data)
        try:
            res = self.req.get_res(url=url)
            if res and res.status_code == 200:
                return res.text
        except Exception as e:
            log.console(str(e))
            return None
        return None

    def __get_movie_dict(self, soup) -> MetaBase or None:
        """
        解析电影、电视剧详情页面，获取媒体信息
        :param soup: 页面soup对象
        :return: 媒体信息：标题、年份、季（不含TMDB信息）
        """
        try:
            info = soup.select('#info')
            infos = list(info[0].strings)
            infos = [i.strip() for i in infos if i.strip() != '']
            # 影视名称
            title = soup.select('#wrapper > div > h1')
            titles = list(title[0].strings)
            titles = [i.strip() for i in titles if i.strip() != '']
            douban_title = ''.join(titles)
            # 这里解析一下，拿到标题和年份（剧集这个年份不太对，不是首播年份）、还有标题中的季
            meta_info = MetaInfo(douban_title)
            # 分类 电影和电视剧
            if '集数:' in infos or '单集片长:' in infos or '首播:' in infos:
                meta_info.type = MediaType.TV
                # 获取首播年份
                firstair_year = self.__get_media_firstair_year(infos)
                if firstair_year:
                    meta_info.year = firstair_year
            else:
                meta_info.type = MediaType.MOVIE
            # 评分 评价数
            meta_info.vote_average = float(self.__get_media_rating_list(soup)[0])
            # 图片网址
            meta_info.poster_path = soup.select("#mainpic > a > img")[0].attrs['src']
        except Exception as e:
            log.error("【DOUBAN】解析豆瓣页面出错：%s" % str(e))
            return None
        return meta_info

    @staticmethod
    def __get_media_firstair_year(infos):
        """
        获取电视剧的首播年份
        """
        try:
            for info in infos:
                if info == "首播:":
                    year_str = infos[infos.index("首播:") + 1]
                    res = re.search(r'(\d{4})-\d{2}-\d{2}', year_str)
                    if res:
                        return res.group(1).strip()
        except Exception as e:
            log.warn("【DOUBAN】未解析到首播年份：%s" % str(e))
        return None

    @staticmethod
    def __get_media_rating_list(soup):
        """
        获取评分数据
        """
        rating_list = ['0', '0']
        try:
            rating_info = soup.select("#interest_sectl > div > div.rating_self.clearfix")
            rating_infos = list(rating_info[0].strings)
            rating_infos = [i.strip() for i in rating_infos if i.strip() != '']
            if len(rating_infos) > 2:
                rating_list = rating_infos
            else:
                rating_list[0] = 0.0
                rating_list[1] = 0
            return rating_list
        except Exception as err:
            log.warn(f"【DOUBAN】未解析到评价数据：{err}")
            return rating_list

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
                log.info("【DOUBAN】开始检索豆瓣中的影视资源...")
                for media in medias:
                    if not media:
                        continue
                    # 查询数据库状态，已经加入RSS的不处理
                    search_state = get_douban_search_state(media.get_name(), media.year)
                    if not search_state or search_state[0][0] == "NEW":
                        media_info = self.media.get_media_info(title="%s %s" % (media.get_name(), media.year),
                                                               mtype=media.type, strict=True)
                        if not media_info or not media_info.tmdb_info:
                            log.warn("【DOUBAN】%s 未查询到媒体信息" % media.get_name())
                            continue
                        # 合并季的信息
                        media_info.begin_season = media.begin_season
                        # 检查是否存在，电视剧返回不存在的集清单
                        exist_flag, no_exists, messages = self.downloader.check_exists_medias(meta_info=media_info)
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
                        if not search_result:
                            if self.__auto_rss:
                                if media_info.type != MediaType.MOVIE:
                                    if not no_exists:
                                        continue
                                    # 按季号降序排序
                                    no_exists_info = no_exists.get(media_info.get_title_string())
                                    if not no_exists_info:
                                        continue
                                    no_exists_info = sorted(no_exists_info, key=lambda x: x.get("season"), reverse=True)
                                    # 总集数、缺失集数
                                    total_count = lack_count = 0
                                    # 没有季的信息时，取最新季
                                    if not media_info.get_season_list():
                                        total_count = no_exists_info[0].get("total_episodes")
                                        if no_exists_info[0].get("episodes"):
                                            lack_count = len(no_exists_info[0].get("episodes"))
                                        else:
                                            lack_count = total_count
                                    # 取当前季的总集数
                                    else:
                                        for seasoninfo in no_exists_info:
                                            if seasoninfo.get("season") == media_info.begin_season:
                                                total_count = seasoninfo.get("total_episodes")
                                                if seasoninfo.get("episodes"):
                                                    lack_count = len(seasoninfo.get("episodes"))
                                                else:
                                                    lack_count = total_count
                                                break
                                    if not total_count:
                                        continue
                                    # 登记电视剧订阅
                                    log.info("【DOUBAN】 %s %s 更新到电视剧订阅中..." % (media_info.title, media_info.year))
                                    insert_rss_tv(media_info, total_count, lack_count, "R")
                                else:
                                    # 登记电影订阅
                                    log.info("【DOUBAN】 %s %s 更新到电影订阅中..." % (media_info.title, media_info.year))
                                    insert_rss_movie(media_info, 'R')
                                # 插入为已RSS状态
                                insert_douban_media_state(media, "RSS")
                            else:
                                log.info("【DOUBAN】 %s %s 等待下一次处理..." % (media_info.title, media_info.year))
                        else:
                            # 更新为已下载状态
                            insert_douban_media_state(media, "DOWNLOADED")
                    else:
                        log.info("【DOUBAN】 %s %s 已处理过，跳过..." % (media.get_name(), media.year))
            else:
                # 不需要检索
                if self.__auto_rss:
                    # 加入订阅
                    for media in medias:
                        # 查询媒体信息
                        media_info = self.media.get_media_info(
                            title="%s %s" % (media.get_name(), media.year),
                            mtype=media.type,
                            strict=True)
                        if not media_info or not media_info.tmdb_info:
                            continue
                        if media_info.type != MediaType.MOVIE:
                            seasons = media.get_season_list()
                            if len(seasons) == 1:
                                # 有季信息的取季的信息
                                season = seasons[0]
                                total_count = self.media.get_tmdb_season_episodes_num(sea=season,
                                                                                      tmdbid=media_info.tmdb_id)
                            else:
                                # 没有季信息的取最新季
                                total_seasoninfo = self.media.get_tmdb_seasons_info(tmdbid=media_info.tmdb_id)
                                if not total_seasoninfo:
                                    log.warn("【DOUBAN】%s 获取剧集信息失败，跳过..." % media_info.get_title_string())
                                    continue
                                # 按季号降序排序
                                total_seasoninfo = sorted(total_seasoninfo, key=lambda x: x.get("season_number"),
                                                          reverse=True)
                                # 没有季的信息时，取最新季
                                season = total_seasoninfo[0].get("season_number")
                                total_count = total_seasoninfo[0].get("episode_count")
                            if not total_count:
                                log.warn("【DOUBAN】%s 获取剧集数失败，跳过..." % media_info.get_title_string())
                                continue
                            media_info.begin_season = season
                            insert_rss_tv(media_info, total_count, total_count, 'R')
                        else:
                            media_info = self.media.get_media_info(title=media.get_name(), mtype=media.type,
                                                                   strict=True)
                            if not media_info or not media_info.tmdb_info:
                                continue
                            insert_rss_movie(media_info, 'R')
                    log.info("【DOUBAN】豆瓣数据加入订阅完成")
            log.info("【DOUBAN】豆瓣数据同步完成")
        finally:
            lock.release()
