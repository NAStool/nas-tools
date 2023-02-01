import copy
import datetime
import re
from urllib.parse import quote

from jinja2 import Template
from pyquery import PyQuery

import feapder
import log
from app.utils import StringUtils, SystemUtils
from app.utils.exception_utils import ExceptionUtils
from app.utils.types import MediaType
from config import Config
from feapder.utils.tools import urlencode


class TorrentSpider(feapder.AirSpider):
    _webdriver_path = SystemUtils.get_webdriver_path()
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
            timeout=20,
            window_size=(1024, 800),
            executable_path=_webdriver_path,
            render_time=10,
            custom_argument=["--ignore-certificate-errors"],
        )
    )
    # 是否检索完成标志
    is_complete = False
    # 索引器ID
    indexerid = None
    # 索引器名称
    indexername = None
    # 站点域名
    domain = None
    # 站点Cookie
    cookie = None
    # 站点UA
    ua = None
    # 代理
    proxies = None
    # 是否渲染
    render = False
    # Referer
    referer = None
    # 检索关键字
    keyword = None
    # 媒体类型
    mtype = None
    # 检索路径、方式配置
    search = {}
    # 批量检索配置
    batch = {}
    # 浏览配置
    browse = {}
    # 站点分类配置
    category = {}
    # 站点种子列表配置
    list = {}
    # 站点种子字段配置
    fields = {}
    # 页码
    page = 0
    # 检索条数
    result_num = 100
    torrents_info = {}
    torrents_info_array = []

    def setparam(self, indexer,
                 keyword: [str, list] = None,
                 page=None,
                 referer=None,
                 mtype: MediaType = None):
        """
        设置查询参数
        :param indexer: 索引器
        :param keyword: 检索关键字，如果数组则为批量检索
        :param page: 页码
        :param referer: Referer
        :param mtype: 媒体类型
        """
        if not indexer:
            return
        self.keyword = keyword
        self.mtype = mtype
        self.indexerid = indexer.id
        self.indexername = indexer.name
        self.search = indexer.search
        self.batch = indexer.batch
        self.browse = indexer.browse
        self.category = indexer.category
        self.list = indexer.torrents.get('list', {})
        self.fields = indexer.torrents.get('fields')
        self.render = indexer.render
        self.domain = indexer.domain
        self.page = page
        if self.domain and not str(self.domain).endswith("/"):
            self.domain = self.domain + "/"
        if indexer.ua:
            self.ua = indexer.ua
        else:
            self.ua = Config().get_ua()
        if indexer.proxy:
            self.proxies = Config().get_proxies()
        if indexer.cookie:
            self.cookie = indexer.cookie
        if referer:
            self.referer = referer
        self.result_num = Config().get_config('pt').get('site_search_result_num') or 100
        self.torrents_info_array = []

    def start_requests(self):
        """
        开始请求
        """

        if not self.search or not self.domain:
            self.is_complete = True
            return

        # 种子搜索相对路径
        paths = self.search.get('paths', [])
        torrentspath = ""
        if len(paths) == 1:
            torrentspath = paths[0].get('path', '')
        else:
            for path in paths:
                if path.get("type") == "all" and not self.mtype:
                    torrentspath = path.get('path')
                    break
                elif path.get("type") == "movie" and self.mtype == MediaType.MOVIE:
                    torrentspath = path.get('path')
                    break
                elif path.get("type") == "tv" and self.mtype == MediaType.TV:
                    torrentspath = path.get('path')
                    break
                elif path.get("type") == "anime" and self.mtype == MediaType.ANIME:
                    torrentspath = path.get('path')
                    break

        # 关键字搜索
        if self.keyword:

            if isinstance(self.keyword, list):
                # 批量查询
                if self.batch:
                    delimiter = self.batch.get('delimiter') or ' '
                    space_replace = self.batch.get('space_replace') or ' '
                    search_word = delimiter.join([str(k).replace(' ', space_replace) for k in self.keyword])
                else:
                    search_word = " ".join(self.keyword)
                # 查询模式：或
                search_mode = "1"
            else:
                # 单个查询
                search_word = self.keyword
                # 查询模式与
                search_mode = "0"

            # 检索URL
            if self.search.get("params"):
                # 变量字典
                inputs_dict = {
                    "keyword": search_word
                }
                # 查询参数
                params = {
                    "search_mode": search_mode,
                    "page": self.page or 0
                }
                # 额外参数
                for key, value in self.search.get("params").items():
                    params.update({
                        "%s" % key: str(value).format(**inputs_dict)
                    })
                # 分类条件
                if self.category:
                    if self.mtype == MediaType.MOVIE:
                        cats = self.category.get("movie") or []
                    elif self.mtype:
                        cats = self.category.get("tv") or []
                    else:
                        cats = self.category.get("movie") or [] + self.category.get("tv") or []
                    for cat in cats:
                        if self.category.get("field"):
                            value = params.get(self.category.get("field"), "")
                            params.update({
                                "%s" % self.category.get("field"): value + self.category.get("delimiter", ' ') + cat.get("id")
                            })
                        else:
                            params.update({
                                "%s" % cat.get("id"): 1
                            })
                searchurl = self.domain + torrentspath + "?" + urlencode(params)
            else:
                # 变量字典
                inputs_dict = {
                    "keyword": quote(search_word),
                    "page": self.page or 0
                }
                # 无额外参数
                searchurl = self.domain + str(torrentspath).format(**inputs_dict)

        # 列表浏览
        else:
            # 变量字典
            inputs_dict = {
                "page": self.page or 0,
                "keyword": ""
            }
            # 有单独浏览路径
            if self.browse:
                torrentspath = self.browse.get("path")
                if self.browse.get("start"):
                    inputs_dict.update({
                        "page": self.browse.get("start")
                    })
            elif self.page:
                torrentspath = torrentspath + f"?page={self.page}"
            # 检索Url
            searchurl = self.domain + str(torrentspath).format(**inputs_dict)

        log.info(f"【Spider】开始请求：{searchurl}")
        yield feapder.Request(url=searchurl,
                              use_session=True,
                              render=self.render)

    def download_midware(self, request):
        request.headers = {
            "User-Agent": self.ua,
            "Cookie": self.cookie
        }
        if self.proxies:
            request.proxies = self.proxies
        return request

    def Gettitle_default(self, torrent):
        # title default
        if 'title' not in self.fields:
            return
        selector = self.fields.get('title', {})
        if 'selector' in selector:
            title = torrent(selector.get('selector', '')).clone()
            if "remove" in selector:
                removelist = selector.get('remove', '').split(', ')
                for v in removelist:
                    title.remove(v)
            if 'attribute' in selector:
                items = [item.attr(selector.get('attribute')) for item in title.items() if item]
            else:
                items = [item.text() for item in title.items() if item]
            if items:
                if "contents" in selector \
                        and len(items) > int(selector.get("contents")):
                    items = items[0].split("\n")[selector.get("contents")]
                elif "index" in selector \
                        and len(items) > int(selector.get("index")):
                    items = items[int(selector.get("index"))]
                else:
                    items = items[0]
                self.torrents_info['title'] = items if not isinstance(items, list) else items[0]
        elif 'text' in selector:
            render_dict = {}
            if "title_default" in self.fields:
                title_default_selector = self.fields.get('title_default', {})
                title_default_item = torrent(title_default_selector.get('selector', '')).clone()
                if "remove" in title_default_selector:
                    removelist = title_default_selector.get('remove', '').split(', ')
                    for v in removelist:
                        title_default_item.remove(v)
                if 'attribute' in title_default_selector:
                    render_dict.update(
                        {'title_default': title_default_item.attr(title_default_selector.get('attribute'))})
                else:
                    render_dict.update({'title_default': title_default_item.text()})
            if "title_optional" in self.fields:
                title_optional_selector = self.fields.get('title_optional', {})
                title_optional_item = torrent(title_optional_selector.get('selector', '')).clone()
                if "remove" in title_optional_selector:
                    removelist = title_optional_selector.get('remove', '').split(', ')
                    for v in removelist:
                        title_optional_item.remove(v)
                if 'attribute' in title_optional_selector:
                    render_dict.update(
                        {'title_optional': title_optional_item.attr(title_optional_selector.get('attribute'))})
                else:
                    render_dict.update({'title_optional': title_optional_item.text()})
            self.torrents_info['title'] = Template(selector.get('text')).render(fields=render_dict)
        if 'filters' in selector:
            self.torrents_info['title'] = self.__filter_text(self.torrents_info.get('title'),
                                                             selector.get('filters'))

    def Gettitle_optional(self, torrent):
        # title optional
        if 'description' not in self.fields:
            return
        selector = self.fields.get('description', {})
        if "selector" in selector \
                or "selectors" in selector:
            description = torrent(selector.get('selector', selector.get('selectors', ''))).clone()
            if description:
                if 'remove' in selector:
                    removelist = selector.get('remove', '').split(', ')
                    for v in removelist:
                        description.remove(v)
                if 'attribute' in selector:
                    items = [x.attr(selector.get('attribute')) for x in description.items()]
                else:
                    items = [item.text() for item in description.items() if item]
                if items:
                    if "contents" in selector \
                            and len(items) > int(selector.get("contents")):
                        items = items[0].split("\n")[selector.get("contents")]
                    elif "index" in selector \
                            and len(items) > int(selector.get("index")):
                        items = items[int(selector.get("index"))]
                    else:
                        items = items[0]
                    self.torrents_info['description'] = items if not isinstance(items, list) else items[0]
        elif "text" in selector:
            render_dict = {}
            if "tags" in self.fields:
                tags_selector = self.fields.get('tags', {})
                tags_item = torrent(tags_selector.get('selector', '')).clone()
                if "remove" in tags_selector:
                    removelist = tags_selector.get('remove', '').split(', ')
                    for v in removelist:
                        tags_item.remove(v)
                render_dict.update({'tags': tags_item.text()})
            if "subject" in self.fields:
                subject_selector = self.fields.get('subject', {})
                subject_item = torrent(subject_selector.get('selector', '')).clone()
                if "remove" in subject_selector:
                    removelist = subject_selector.get('remove', '').split(', ')
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
            self.torrents_info['description'] = Template(selector.get('text')).render(fields=render_dict)
        if 'filters' in selector:
            self.torrents_info['description'] = self.__filter_text(self.torrents_info.get('description'),
                                                                   selector.get('filters'))

    def Getdetails(self, torrent):
        # details
        if 'details' not in self.fields:
            return
        details = torrent(self.fields.get('details', {}).get('selector', ''))
        items = [item.attr(self.fields.get('details', {}).get('attribute')) for item in details.items()]
        if items:
            if not items[0].startswith("http"):
                if items[0].startswith("//"):
                    self.torrents_info['page_url'] = self.domain.split(":")[0] + ":" + items[0]
                elif items[0].startswith("/"):
                    self.torrents_info['page_url'] = self.domain + items[0][1:]
                else:
                    self.torrents_info['page_url'] = self.domain + items[0]
            else:
                self.torrents_info['page_url'] = items[0]
            if 'filters' in self.fields.get('details', {}):
                self.torrents_info['page_url'] = self.__filter_text(self.torrents_info.get('page_url'),
                                                                    self.fields.get('details',
                                                                                    {}).get('filters'))

    def Getdownload(self, torrent):
        # download link
        if 'download' not in self.fields:
            return
        if "detail" in self.fields.get('download', {}):
            selector = self.fields.get('download', {}).get("detail", {})
            if "xpath" in selector:
                self.torrents_info['enclosure'] = f'[{selector.get("xpath", "")}' \
                                                  f'|{self.cookie or ""}' \
                                                  f'|{self.ua or ""}' \
                                                  f'|{self.referer or ""}]'
            elif "hash" in selector:
                self.torrents_info['enclosure'] = f'#{selector.get("hash", "")}' \
                                                  f'|{self.cookie or ""}' \
                                                  f'|{self.ua or ""}' \
                                                  f'|{self.referer or ""}#'
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
        if "imdbid" not in self.fields:
            return
        selector = self.fields.get('imdbid', {})
        imdbid = torrent(selector.get('selector', ''))
        if 'attribute' in selector:
            items = [item.attr(selector.get('attribute')) for item in imdbid.items() if item]
        else:
            items = [item.text() for item in imdbid.items() if item]
        self.torrents_info['imdbid'] = items[0] if items else ''
        if 'filters' in selector:
            self.torrents_info['imdbid'] = self.__filter_text(self.torrents_info.get('imdbid'),
                                                              selector.get('filters'))

    def Getsize(self, torrent):
        # torrent size
        if 'size' not in self.fields:
            return
        selector = self.fields.get('size', {})
        size = torrent(selector.get('selector', selector.get("selectors", '')))
        items = [item.text() for item in size.items() if item]
        if "index" in selector \
                and len(items) > selector.get('index'):
            self.torrents_info['size'] = StringUtils.num_filesize(
                items[selector.get('index')].replace("\n", "").strip())
        elif len(items) > 0:
            self.torrents_info['size'] = StringUtils.num_filesize(
                items[0].replace("\n", "").strip())
        if 'filters' in selector:
            self.torrents_info['size'] = self.__filter_text(self.torrents_info.get('size'),
                                                            selector.get('filters'))
        if self.torrents_info.get('size'):
            self.torrents_info['size'] = StringUtils.num_filesize(self.torrents_info.get('size'))

    def Getleechers(self, torrent):
        # torrent leechers
        if 'leechers' not in self.fields:
            return
        selector = self.fields.get('leechers', {})
        leechers = torrent(selector.get('selector', ''))
        items = [item.text() for item in leechers.items() if item]
        self.torrents_info['peers'] = items[0] if items else 0
        if 'filters' in selector:
            self.torrents_info['peers'] = self.__filter_text(self.torrents_info.get('peers'),
                                                             selector.get('filters'))

    def Getseeders(self, torrent):
        # torrent leechers
        if 'seeders' not in self.fields:
            return
        selector = self.fields.get('seeders', {})
        seeders = torrent(selector.get('selector', ''))
        items = [item.text() for item in seeders.items() if item]
        self.torrents_info['seeders'] = items[0].split("/")[0] if items else 0
        if 'filters' in selector:
            self.torrents_info['seeders'] = self.__filter_text(self.torrents_info.get('seeders'),
                                                               selector.get('filters'))

    def Getgrabs(self, torrent):
        # torrent grabs
        if 'grabs' not in self.fields:
            return
        selector = self.fields.get('grabs', {})
        grabs = torrent(selector.get('selector', ''))
        items = [item.text() for item in grabs.items() if item]
        self.torrents_info['grabs'] = items[0] if items else ''
        if 'filters' in selector:
            self.torrents_info['grabs'] = self.__filter_text(self.torrents_info.get('grabs'),
                                                             selector.get('filters'))

    def Getpubdate(self, torrent):
        # torrent pubdate
        if 'date_added' not in self.fields:
            return
        selector = self.fields.get('date_added', {})
        pubdate = torrent(selector.get('selector', ''))
        if 'attribute' in selector:
            items = [item.attr(selector.get('attribute')) for item in pubdate.items() if item]
        else:
            items = [item.text() for item in pubdate.items() if item]
        self.torrents_info['pubdate'] = items[0] if items else ''
        if 'filters' in selector:
            self.torrents_info['pubdate'] = self.__filter_text(self.torrents_info.get('pubdate'),
                                                               selector.get('filters'))

    def Getelapsed_date(self, torrent):
        # torrent pubdate
        if 'date_elapsed' not in self.fields:
            return
        selector = self.fields.get('date_elapsed', {})
        date_elapsed = torrent(selector.get('selector', ''))
        if 'attribute' in selector:
            items = [item.attr(selector.get('attribute')) for item in date_elapsed.items() if item]
        else:
            items = [item.text() for item in date_elapsed.items() if item]
        self.torrents_info['date_elapsed'] = items[0] if items else ''
        if 'filters' in selector:
            self.torrents_info['date_elapsed'] = self.__filter_text(self.torrents_info.get('date_elapsed'),
                                                                    selector.get('filters'))

    def Getdownloadvolumefactor(self, torrent):
        # downloadvolumefactor
        selector = self.fields.get('downloadvolumefactor', {})
        if not selector:
            return
        if 'case' in selector:
            for downloadvolumefactorselector in list(selector.get('case',
                                                                  {}).keys()):
                downloadvolumefactor = torrent(downloadvolumefactorselector)
                if len(downloadvolumefactor) > 0:
                    self.torrents_info['downloadvolumefactor'] = selector.get('case',
                                                                              {}).get(
                        downloadvolumefactorselector)
                    break
        elif "selector" in selector:
            downloadvolume = torrent(selector.get('selector', ''))
            if downloadvolume:
                items = [item.text() for item in downloadvolume.items() if item]
                if items:
                    downloadvolumefactor = re.search(r'(\d+\.?\d*)', items[0])
                    if downloadvolumefactor:
                        self.torrents_info['downloadvolumefactor'] = int(downloadvolumefactor.group(1))

    def Getuploadvolumefactor(self, torrent):
        # uploadvolumefactor
        selector = self.fields.get('uploadvolumefactor', {})
        if not selector:
            return
        if 'case' in selector:
            for uploadvolumefactorselector in list(selector.get('case',
                                                                {}).keys()):
                uploadvolumefactor = torrent(uploadvolumefactorselector)
                if len(uploadvolumefactor) > 0:
                    self.torrents_info['uploadvolumefactor'] = selector.get('case',
                                                                            {}).get(uploadvolumefactorselector)
                    break
        elif "selector" in selector:
            uploadvolume = torrent(selector.get('selector', ''))
            if uploadvolume:
                items = [item.text() for item in uploadvolume.items() if item]
                if items:
                    uploadvolumefactor = re.search(r'(\d+\.?\d*)', items[0])
                    if uploadvolumefactor:
                        self.torrents_info['uploadvolumefactor'] = int(uploadvolumefactor.group(1))

    def Getinfo(self, torrent):
        """
        解析单条种子数据
        """
        self.torrents_info = {'indexer': self.indexerid}
        try:
            self.Gettitle_default(torrent)
            self.Gettitle_optional(torrent)
            self.Getdetails(torrent)
            self.Getdownload(torrent)
            self.Getgrabs(torrent)
            self.Getleechers(torrent)
            self.Getseeders(torrent)
            self.Getsize(torrent)
            self.Getimdbid(torrent)
            self.Getdownloadvolumefactor(torrent)
            self.Getuploadvolumefactor(torrent)
            self.Getpubdate(torrent)
            self.Getelapsed_date(torrent)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            log.error("【Spider】%s 检索出现错误：%s" % (self.indexername, str(err)))
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
                elif method_name == "strip":
                    text = text.strip()
                elif method_name == "appendleft":
                    text = f"{args}{text}"
            except Exception as err:
                ExceptionUtils.exception_traceback(err)
        return text.strip()

    def parse(self, request, response):
        """
        解析整个页面
        """
        try:
            # 获取站点文本
            html_text = response.extract()
            if not html_text:
                self.is_complete = True
                return
            # 解析站点文本对象
            html_doc = PyQuery(html_text)
            # 种子筛选器
            torrents_selector = self.list.get('selector', '')
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
                if len(self.torrents_info_array) >= int(self.result_num):
                    break

        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            log.warn("【Spider】错误：%s" % str(err))
        finally:
            self.is_complete = True
