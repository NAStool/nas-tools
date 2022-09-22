import copy
import datetime
import re
import traceback
from urllib.parse import quote

from requests.utils import dict_from_cookiejar

import feapder
from app.utils import RequestUtils, StringUtils, SystemUtils
from app.utils.types import OsType
from config import Config, DEFAULT_UA
from feapder.utils.tools import urlencode
from jinja2 import Template
from pyquery import PyQuery

import log


class TorrentSpider(feapder.AirSpider):
    __custom_setting__ = dict(
        USE_SESSION=True,
        SPIDER_THREAD_COUNT=1,
        SPIDER_MAX_RETRY_TIMES=0,
        REQUEST_LOST_TIMEOUT=10,
        RETRY_FAILED_REQUESTS=False,
        LOG_LEVEL="ERROR",
        RANDOM_HEADERS=False,
        WEBDRIVER=dict(
            pool_size=1,
            load_images=False,
            proxy=None,
            headless=True,
            driver_type="CHROME",
            timeout=15,
            window_size=(1024, 800),
            executable_path="/usr/lib/chromium/chromedriver" if SystemUtils.get_system() == OsType.LINUX else None,
            render_time=5,
            custom_argument=["--ignore-certificate-errors"],
        )
    )
    is_complete = False
    indexerid = None
    cookies = None
    headers = None
    proxies = None
    render = False
    keyword = None
    indexer = None
    search = None
    domain = None
    torrents = None
    article_list = None
    fields = None
    torrents_info = {}
    torrents_info_array = []

    def setparam(self, indexer, keyword):
        if not indexer or not keyword:
            return
        self.keyword = keyword
        self.indexerid = indexer.id
        self.search = indexer.search
        self.torrents = indexer.torrents
        self.render = indexer.render
        self.domain = indexer.domain
        if self.domain and not str(self.domain).endswith("/"):
            self.domain = self.domain + "/"
        if indexer.ua:
            self.headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                            "User-Agent": f"{indexer.ua}"}
        else:
            self.headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                            "User-Agent": f"{Config().get_config('app').get('user_agent') or DEFAULT_UA}"}
        if indexer.proxy and Config().get_proxies():
            self.proxies = Config().get_proxies()
            self.__custom_setting__['WEBDRIVER']['proxy'] = self.proxies.get("http") or None
        else:
            self.proxies = None
            self.__custom_setting__['WEBDRIVER']['proxy'] = None
        if indexer.cookie:
            self.cookies = indexer.cookie
        else:
            try:
                res = RequestUtils(headers=self.headers, proxies=self.proxies, timeout=10).get_res(self.domain)
                if res:
                    self.cookies = dict_from_cookiejar(res.cookies)
            except Exception as err:
                log.warn(f"【SPIDER】获取 {self.domain} cookie失败：{format(err)}")
        self.torrents_info_array = []

    def start_requests(self):
        if self.search:
            torrentspath = self.search.get('paths', [{}])[0].get('path', '')
            if torrentspath.find("{keyword}") != -1:
                searchurl = self.domain + torrentspath.replace("{keyword}", quote(self.keyword))
            else:
                searchurl = self.domain + torrentspath + '?stypes=s&' + urlencode(
                    {"search": self.keyword, "search_field": self.keyword, "keyword": self.keyword})
            yield feapder.Request(searchurl,
                                  cookies=self.cookies,
                                  render=self.render,
                                  headers=self.headers)
        else:
            self.is_complete = True

    def Getdownloadvolumefactor(self, torrent):
        # downloadvolumefactor
        for downloadvolumefactorselector in list(self.fields.get('downloadvolumefactor',
                                                                 {}).get('case',
                                                                         {}).keys()):
            downloadvolumefactor = PyQuery(torrent)(downloadvolumefactorselector)
            if len(downloadvolumefactor) > 0:
                self.torrents_info['downloadvolumefactor'] = self.fields.get('downloadvolumefactor',
                                                                             {}).get('case',
                                                                                     {}).get(
                    downloadvolumefactorselector)
                break

    def Getuploadvolumefactor(self, torrent):
        # uploadvolumefactor
        for uploadvolumefactorselector in list(self.fields.get('uploadvolumefactor',
                                                               {}).get('case',
                                                                       {}).keys()):
            uploadvolumefactor = PyQuery(torrent)(uploadvolumefactorselector)
            if len(uploadvolumefactor) > 0:
                self.torrents_info['uploadvolumefactor'] = self.fields.get('uploadvolumefactor',
                                                                           {}).get('case',
                                                                                   {}).get(uploadvolumefactorselector)
                break

    def Gettitle_default(self, torrent):
        # title default
        if "title_default" in self.fields:
            title_default = torrent(self.fields.get('title_default',
                                                    {}).get('selector',
                                                            '')).clone()
            selector = self.fields.get('title_default', {})
        else:
            title_default = torrent(self.fields.get('title',
                                                    {}).get('selector',
                                                            '')).clone()
            selector = self.fields.get('title', {})

        if 'remove' in selector:
            removelist = selector.get('remove', '').split(', ')
            for v in removelist:
                title_default.remove(v)

        items = [item.text() for item in title_default.items() if item]
        self.torrents_info['title'] = items[0] if items else ''

    def Getdetails(self, torrent):
        # details
        details = torrent(self.fields.get('details', {}).get('selector', ''))
        items = [item.attr(self.fields.get('details', {}).get('attribute')) for item in details.items()]
        if items:
            if not items[0].startswith("http"):
                self.torrents_info['page_url'] = self.domain + items[0][1:] if items[0].startswith(
                    "/") else self.domain + items[0]
            else:
                self.torrents_info['page_url'] = items[0]

    def Getdownload(self, torrent):
        # download link
        if "detail" in self.fields.get('download', {}):
            self.torrents_info['enclosure'] = "[%s]" % self.fields.get('download',
                                                                       {}).get("detail",
                                                                               {}).get("xpath", "")
        else:
            download = torrent(self.fields.get('download', {}).get('selector', ''))
            items = [item.attr(self.fields.get('download', {}).get('attribute')) for item in download.items()]
            if items:
                if not items[0].startswith("http") and not items[0].startswith("magnet"):
                    self.torrents_info['enclosure'] = self.domain + items[0][1:] if items[0].startswith(
                        "/") else self.domain + items[0]
                else:
                    self.torrents_info['enclosure'] = items[0]

    def Getimdbid(self, torrent):
        # imdbid
        if "imdbid" in self.fields:
            imdbid = torrent(self.fields.get('imdbid', {}).get('selector', ''))
            items = [item.attr(self.fields.get('imdbid', {}).get('attribute')) for item in imdbid.items() if item]
            self.torrents_info['imdbid'] = items[0] if items else ''
            filters = self.fields.get('imdbid', {}).get('filters', {})
            if filters:
                self.torrents_info['imdbid'] = self.__filter_text(self.torrents_info['imdbid'], filters)

    def Getsize(self, torrent):
        # torrent size
        size_item = torrent(self.fields.get('size',
                                            {}).get('selector', self.fields.get('size',
                                                                                {}).get("selectors",
                                                                                        '')))
        items = [item.text() for item in size_item.items() if item]
        if "index" in self.fields.get('size', {}) \
                and len(items) > self.fields.get('size', {}).get('index'):
            self.torrents_info['size'] = StringUtils.num_filesize(
                items[self.fields.get('size', {}).get('index')].replace("\n", ""))
        elif len(items) > 0:
            self.torrents_info['size'] = StringUtils.num_filesize(items[0].replace("\n", ""))

    def Getleechers(self, torrent):
        # torrent leechers
        leechers = torrent(self.fields.get('leechers', {}).get('selector', ''))
        items = [item.text() for item in leechers.items() if item]
        self.torrents_info['peers'] = items[0] if items else 0
        filters = self.fields.get('peers', {}).get('filters', {})
        if filters:
            self.torrents_info['peers'] = self.__filter_text(self.torrents_info['peers'], filters)

    def Getseeders(self, torrent):
        # torrent leechers
        seeders = torrent(self.fields.get('seeders', {}).get('selector', ''))
        items = [item.text() for item in seeders.items() if item]
        self.torrents_info['seeders'] = items[0].split("/")[0] if items else 0
        filters = self.fields.get('seeders', {}).get('filters', {})
        if filters:
            self.torrents_info['seeders'] = self.__filter_text(self.torrents_info['seeders'], filters)

    def Getgrabs(self, torrent):
        # torrent grabs
        grabs = torrent(self.fields.get('grabs', {}).get('selector', ''))
        items = [item.text() for item in grabs.items() if item]
        self.torrents_info['grabs'] = items[0] if items else ''
        filters = self.fields.get('grabs', {}).get('filters', {})
        if filters:
            self.torrents_info['grabs'] = self.__filter_text(self.torrents_info['grabs'], filters)

    def Gettitle_optional(self, torrent):
        # title optional
        if "selector" in self.fields.get('description', {}) \
                or "selectors" in self.fields.get('description', {}):
            description_item = torrent(self.fields.get('description',
                                                       {}).get('selector',
                                                               self.fields.get('description',
                                                                               {}).get('selectors',
                                                                                       ''))).clone()
            if description_item:
                if 'attribute' in self.fields.get('description', {}):
                    items = [x.attr(self.fields.get('description',
                                                    {}).get('attribute')) for x in description_item.items()]

                else:
                    if 'remove' in self.fields.get('description', {}):
                        removelist = self.fields.get('description', {}).get('remove', '').split(', ')
                        for v in removelist:
                            description_item.remove(v)
                    items = [item.text() for item in description_item.items() if item]

                if items:
                    if "contents" in self.fields.get('description', {}) \
                            and len(items) > int(self.fields.get('description', {}).get("contents")):
                        items = items[0].split("\n")[self.fields.get('description', {}).get("contents")]
                    elif "index" in self.fields.get('description', {}) \
                            and len(items) > int(self.fields.get('description', {}).get("index")):
                        items = items[int(self.fields.get('description', {}).get("index"))]
                    else:
                        items = items[0]

                    self.torrents_info['description'] = items if not isinstance(items, list) else items[0]

        elif "text" in self.fields.get('description', {}):
            render_dict = {}
            if "tags" in self.fields:
                tags_item = torrent(self.fields.get('tags',
                                                    {}).get('selector',
                                                            '')).clone()
                if "remove" in self.fields.get("tags", {}):
                    removelist = self.fields.get("tags",
                                                 {}).get('remove',
                                                         '').split(', ')
                    for v in removelist:
                        tags_item.remove(v)
                render_dict.update({'tags': tags_item.text()})
            if "subject" in self.fields:
                subject_item = torrent(self.fields.get('subject',
                                                       {}).get('selector',
                                                               '')).clone()
                if "remove" in self.fields.get("subject", {}):
                    removelist = self.fields.get("subject",
                                                 {}).get('remove',
                                                         '').split(', ')
                    for v in removelist:
                        subject_item.remove(v)
                render_dict.update({'subject': subject_item.text()})
            if "description_free_forever" in self.fields:
                render_dict.update({"description_free_forever": torrent(self.fields.get("description_free_forever",
                                                                                        {}).get("selector",
                                                                                                '')).text()})
            if "description_normal" in self.fields:
                render_dict.update({"description_normal": torrent(self.fields.get("description_normal",
                                                                                  {}).get("selector",
                                                                                          '')).text()})
            self.torrents_info['description'] = Template(self.fields.get('description',
                                                                         {}).get('text')).render(fields=render_dict)

    def Getinfo(self, torrent):
        """
        解析单条种子数据
        """
        self.torrents_info = {'indexer': self.indexerid}
        self.Gettitle_default(torrent)
        self.Gettitle_optional(torrent)
        self.Getgrabs(torrent)
        self.Getleechers(torrent)
        self.Getseeders(torrent)
        self.Getsize(torrent)
        self.Getimdbid(torrent)
        self.Getdetails(torrent)
        self.Getdownload(torrent)
        self.Getdownloadvolumefactor(torrent)
        self.Getuploadvolumefactor(torrent)
        return self.torrents_info

    @staticmethod
    def __filter_text(text, filters):
        """
        对文件进行处理
        """
        if not text or not filters or not isinstance(filters, list):
            return text
        if not isinstance(text, str):
            text = str(text)
        for filter_item in filters:
            try:
                method_name = filter_item.get("name")
                args = filter_item.get("args")
                if method_name == "re_search" and isinstance(args, list):
                    text = re.search(r"%s" % args[0], text).group(args[-1])
                elif method_name == "split" and isinstance(args, list):
                    text = text.split(r"%s" % args[0])[args[-1]]
                elif method_name == "replace" and isinstance(args, list):
                    text = text.replace(r"%s" % args[0], r"%s" % args[-1])
                elif method_name == "dateparse" and isinstance(args, str):
                    text = datetime.datetime.strptime(text, r"%s" % args)
            except Exception as err:
                print(str(err))
        return text.strip()

    def parse(self, request, response):
        """
        解析整个页面
        """
        try:
            # 获取网站文本
            self.article_list = response.extract()
            # 获取站点种子xml
            self.fields = self.torrents.get('fields')
            html_doc = PyQuery(self.article_list)
            # 种子筛选器
            torrents_selector = self.torrents.get('list', {}).get('selector', '')
            str_list = list(torrents_selector)
            # 兼容选择器中has()函数 部分情况下无双引号会报错
            has_index = torrents_selector.find('has')
            if has_index != -1 and torrents_selector.find('"') == -1:
                flag = 0
                str_list.insert(has_index + 4, '"')
                for i in range(len(str_list)):
                    if i > has_index + 2:
                        n = str_list[i]
                        if n == '(':
                            flag = flag + 1
                        if n == ')':
                            flag = flag - 1
                        if flag == 0:
                            str_list.insert(i, '"')
                torrents_selector = "".join(str_list)
            # 遍历种子html列表
            for torn in html_doc(torrents_selector):
                self.torrents_info_array.append(copy.deepcopy(self.Getinfo(PyQuery(torn))))
                if len(self.torrents_info_array) >= 100:
                    break

        except Exception as err:
            log.warn("【SPIDER】错误：%s - %s" % (str(err), traceback.format_exc()))
        finally:
            self.is_complete = True
