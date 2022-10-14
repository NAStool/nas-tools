import random
from threading import Lock
from time import sleep

from lxml import etree
from requests.utils import dict_from_cookiejar
from app.utils.string_utils import StringUtils

import log
from config import Config
from app.media.doubanv2api import DoubanApi
from app.media import MetaInfo
from app.utils import RequestUtils
from app.utils.types import MediaType

lock = Lock()


class DouBan:
    req = None
    doubanapi = None
    message = None

    def __init__(self):
        self.doubanapi = DoubanApi()
        self.init_config()

    def init_config(self):
        config = Config()
        douban = config.get_config('douban')
        if douban:
            # Cookie
            cookie = douban.get('cookie')
            if not cookie:
                try:
                    if self.req:
                        res = self.req.get_res("https://www.douban.com/")
                        if res:
                            cookie = dict_from_cookiejar(res.cookies)
                except Exception as err:
                    log.warn(f"【Douban】获取cookie失败：{format(err)}")
            self.req = RequestUtils(cookies=cookie)

    def get_douban_detail(self, doubanid):
        """
        根据豆瓣ID返回豆瓣详情，带休眠
        """
        log.info("【Douban】正在通过API查询豆瓣详情：%s" % doubanid)
        douban_info = self.doubanapi.movie_detail(doubanid)
        if not douban_info:
            douban_info = self.doubanapi.tv_detail(doubanid)
        if not douban_info:
            log.warn("【Douban】%s 未找到豆瓣详细信息" % doubanid)
            sleep(round(random.uniform(1, 5), 1))
            return None
        if douban_info.get("localized_message"):
            log.warn("【Douban】查询豆瓣详情返回：%s" % douban_info.get("localized_message"))
            # 随机休眠
            sleep(round(random.uniform(1, 5), 1))
            return None
        if not douban_info.get("title"):
            # 随机休眠
            sleep(round(random.uniform(1, 5), 1))
            return None
        if douban_info.get("title") == "未知电影" or douban_info.get("title") == "未知电视剧":
            return None
        return douban_info

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
        log.info("【Douban】正在通过网页抓取豆瓣详情：%s" % url)
        ret_media = {}
        res = self.req.get_res(url=url)
        if res and res.status_code == 200:
            html_text = res.text
            if not html_text:
                return None
            try:
                html = etree.HTML(html_text)
                # 标题
                title = html.xpath("//span[@property='v:itemreviewed']/text()")[0]
                if not title:
                    return None
                if " " in title and StringUtils.is_chinese(title.split(" ")[0]):
                    title = title.split(" ")[0]
                ret_media['title'] = title
                # 年份
                ret_media['year'] = html.xpath("//div[@id='content']//span[@class='year']/text()")[0][1:-1]
                # 简介
                ret_media['intro'] = "".join(
                    [str(x).strip() for x in html.xpath("//span[@property='v:summary']/text()")])
                # 封面图
                ret_media['cover_url'] = html.xpath("//div[@id='mainpic']/a/img/@src")[0]
                if ret_media['cover_url']:
                    ret_media['cover_url'] = ret_media.get('cover_url').replace("s_ratio_poster", "m_ratio_poster")
                # 评分
                ret_media['rating'] = {"value": float(html.xpath("//strong[@property='v:average']/text()")[0])}
                detail_info = html.xpath("//div[@id='info']/text()")
                if isinstance(detail_info, list):
                    # 集数
                    episodes_info = [str(x).strip() for x in detail_info if str(x).strip().isdigit()]
                    if episodes_info and str(episodes_info[0]).isdigit():
                        ret_media['episodes_count'] = int(episodes_info[0])
                    # IMDBID
                    for info in detail_info:
                        if str(info).strip().startswith('tt'):
                            ret_media['imdbid'] = str(info).strip()
                            break
            except Exception as err:
                print(err)
        return ret_media

    def get_douban_page_html(self, url):
        """
        获取豆瓣页面HTML
        """
        res = self.req.get_res(url=url)
        if not res:
            return None
        html_text = res.text
        if not html_text:
            return None
        return html_text
