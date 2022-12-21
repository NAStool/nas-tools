from functools import lru_cache
from urllib.parse import quote

from pyquery import PyQuery

import log
from app.helper import ChromeHelper, CHROME_LOCK
from config import Config


class SubHelper:
    _cookie = ""
    _ua = None
    _url_imdbid = "https://www.opensubtitles.org/zh/search/imdbid-%s/sublanguageid-chi"
    _url_keyword = "https://www.opensubtitles.org/zh/search/moviename-%s/sublanguageid-chi"

    def __init__(self):
        self._ua = Config().get_ua()

    def search_subtitles(self, query):
        if query.get("imdbid"):
            return self.__search_subtitles_by_imdbid(query.get("imdbid"))
        else:
            return self.__search_subtitles_by_keyword("%s %s" % (query.get("name"), query.get("year")))

    def __search_subtitles_by_imdbid(self, imdbid):
        """
        按TMDBID搜索OpenSubtitles
        """
        return self.__parse_opensubtitles_results(url=self._url_imdbid % str(imdbid).replace("tt", ""))

    def __search_subtitles_by_keyword(self, keyword):
        """
        按关键字搜索OpenSubtitles
        """
        return self.__parse_opensubtitles_results(url=self._url_keyword % quote(keyword))

    @classmethod
    @lru_cache(maxsize=128)
    def __parse_opensubtitles_results(cls, url):
        """
        搜索并解析结果
        """
        chrome = ChromeHelper()
        if not chrome.get_status():
            log.error("【Subtitle】未找到浏览器内核，当前环境无法检索opensubtitles字幕！")
            return []
        with CHROME_LOCK:
            # 访问页面
            chrome.visit(url)
            # 源码
            html_text = chrome.get_html()
            if not html_text:
                log.error("【Subtitle】无法连接opensubtitles.org！")
                return []
            # Cookie
            cls._cookie = chrome.get_cookies()
        # 解析列表
        ret_subtitles = []
        html_doc = PyQuery(html_text)
        global_season = ''
        for tr in html_doc('#search_results > tbody > tr:not([style])'):
            tr_doc = PyQuery(tr)
            # 季
            season = tr_doc('span[id^="season-"] > a > b').text()
            if season:
                global_season = season
                continue
            # 集
            episode = tr_doc('span[itemprop="episodeNumber"]').text()
            # 标题
            title = tr_doc('strong > a.bnone').text()
            # 描述 下载链接
            if not global_season:
                description = tr_doc('td:nth-child(1)').text()
                if description and len(description.split("\n")) > 1:
                    description = description.split("\n")[1]
                link = tr_doc('td:nth-child(5) > a').attr("href")
            else:
                description = tr_doc('span[itemprop="name"]').text()
                link = tr_doc('a[href^="/download/"]').attr("href")
            if link:
                link = "https://www.opensubtitles.org%s" % link
            else:
                continue
            ret_subtitles.append({
                "season": global_season,
                "episode": episode,
                "title": title,
                "description": description,
                "link": link
            })
        return ret_subtitles

    def get_cookie(self):
        """
        返回Cookie
        """
        return self._cookie

    def get_ua(self):
        """
        返回User-Agent
        """
        return self._ua
