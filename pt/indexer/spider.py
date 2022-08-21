import traceback

import copy
import re
import feapder
from feapder.utils.tools import urlencode
from pyquery import PyQuery
from jinja2 import Template

import log
from utils.functions import num_filesize
from utils.indexer_conf import IndexerConf


class TorrentSpider(feapder.AirSpider):
    __custom_setting__ = dict(
        USE_SESSION=True,
        SPIDER_MAX_RETRY_TIMES=0,
        REQUEST_LOST_TIMEOUT=10,
        RETRY_FAILED_REQUESTS=False,
        LOG_LEVEL="ERROR",
        RANDOM_HEADERS=False
    )
    is_complete = False
    cookies = None
    keyword = None
    torrents_info_array = []
    indexer = None
    domain = None
    torrents_info = {}
    article_list = None
    fields = None

    def setparam(self, indexer: IndexerConf, keyword):
        if not indexer or not keyword:
            return
        self.keyword = keyword
        self.indexer = indexer
        self.domain = indexer.domain
        if self.domain and not str(self.domain).endswith("/"):
            self.domain = self.domain + "/"
        self.cookies = self.indexer.cookie
        self.torrents_info_array = []

    def start_requests(self):
        torrentspath = self.indexer.search.get('paths', [{}])[0].get('path', '')
        searchurl = self.indexer.domain + torrentspath + '?stypes=s&' + urlencode(
            {"search": self.keyword, "search_field": self.keyword})
        yield feapder.Request(searchurl, cookies=self.cookies)

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
                                                    {}).get('selector')).clone()
            selector = self.fields.get('title_default')
        else:
            title_default = torrent(self.fields.get('title',
                                                    {}).get('selector')).clone()
            selector = self.fields.get('title')

        if 'remove' in selector:
            removelist = selector.get('remove', '').split(', ')
            for v in removelist:
                title_default.remove(v)

        items = [item.text() for item in title_default.items() if item]
        self.torrents_info['title'] = items[0] if items else ''

    def Getdetails(self, torrent):
        # details
        details = torrent(self.fields.get('details', {}).get('selector'))
        items = [item.attr(self.fields.get('details', {}).get('attribute')) for item in details.items()]
        self.torrents_info['details'] = items[0] if items else ''
        self.torrents_info['page_url'] = self.indexer.domain + items[0] if items else ''

    def Getdownload(self, torrent):
        # download link
        download = torrent(self.fields.get('download', {}).get('selector'))
        items = [item.attr(self.fields.get('download', {}).get('attribute')) for item in download.items()]
        if items:
            if not items[0].startswith("http"):
                enclosure = self.domain + items[0][1:] if items[0].startswith("/") else self.domain + items[0]
            else:
                enclosure = items[0]
            self.torrents_info['enclosure'] = enclosure

    def Getimdbid(self, torrent):
        # imdbid
        if "imdbid" in self.fields:
            imdbid = torrent(self.fields.get('imdbid', {}).get('selector'))
            items = [item.attr(self.fields.get('imdbid', {}).get('attribute')) for item in imdbid.items() if item]
            self.torrents_info['imdbid'] = items[0] if items else ''

    def Getsize(self, torrent):
        # torrent size
        size = torrent(self.fields.get('size', {}).get('selector'))
        items = [item.text() for item in size.items() if item]
        if len(items) > 0:
            self.torrents_info['size'] = num_filesize(items[0].replace("\n", ""))

    def Getleechers(self, torrent):
        # torrent leechers
        leechers = torrent(self.fields.get('leechers', {}).get('selector'))
        items = [item.text() for item in leechers.items() if item]
        self.torrents_info['leechers'] = items[0] if items else 0
        self.torrents_info['peers'] = items[0] if items else 0

    def Getseeders(self, torrent):
        # torrent leechers
        seeders = torrent(self.fields.get('seeders', {}).get('selector'))
        items = [item.text() for item in seeders.items() if item]
        self.torrents_info['seeders'] = items[0].split("/")[0] if items else 0

    def Getgrabs(self, torrent):
        # torrent grabs
        grabs = torrent(self.fields.get('grabs', {}).get('selector'))
        items = [item.text() for item in grabs.items() if item]
        self.torrents_info['grabs'] = items[0] if items else ''

    def Gettitle_optional(self, torrent):
        # title optional
        description = self.fields.get('description') or {}
        description_item = None
        if "selector" in description:
            description_item = torrent(description.get('selector', '')).clone()
        elif "selectors" in description:
            description_item = torrent(description.get('selectors', '')).clone()
        if description_item:
            items = ""
            if 'attribute' in description:
                items = [x.attr(self.fields.get('description',
                                                {}).get('attribute')) for x in description_item.items()]

            if 'remove' in description:
                removelist = description.get('remove', '').split(', ')
                for v in removelist:
                    description_item.remove(v)

            if "contents" in description:
                items = [item.text() for item in description_item.items() if item]
                if items:
                    if len(items) > int(description.get("contents")):
                        items = items[0].split("\n")[description.get("contents")]
                    else:
                        items = items[0]

            if "index" in description:
                items = [item.text() for item in description_item.items() if item]
                if items:
                    if len(items) > int(description.get("index")):
                        items = items[int(description.get("index"))]
                    else:
                        items = items[0]

            self.torrents_info['description'] = items if not isinstance(items, list) else items[0]

        if "text" in self.fields.get('description'):
            render_dict = {}
            if "tags" in self.fields:
                render_dict.update({'tags': torrent(self.fields.get('tags', {}).get('selector', '')).text()})
            if "subject" in self.fields:
                render_dict.update({'subject': torrent(self.fields.get('subject', {}).get('selector', '')).text()})
            if "description_free_forever" in self.fields:
                render_dict.update({"description_free_forever": torrent(self.fields.get("description_free_forever",
                                                                                        {}).get("selector")).text()})
            if "description_normal" in self.fields:
                render_dict.update({"description_normal": torrent(self.fields.get("description_normal",
                                                                                  {}).get("selector")).text()})
            self.torrents_info['description'] = Template(self.fields.get('description',
                                                                         {}).get('text')).render(fields=render_dict)

    def Getdate_added(self, torrent):
        # date_added
        selector = torrent(self.fields.get('date_elapsed', {}).get('selector', ''))
        items = [item.attr(self.fields.get('date_elapsed', {}).get('attribute', '')) for item in selector.items()]
        self.torrents_info['date_added'] = items[0] if items else ''

    def Getdate_elapsed(self, torrent):
        # date_added
        selector = torrent(self.fields.get('date_elapsed', {}).get('selector', ''))
        items = [item.text() for item in selector.items()]
        self.torrents_info['date_elapsed'] = items[0] if items else ''

    def Getfree_deadline(self, torrent):
        # TODO free deadline
        selector = torrent(self.fields.get('free_deadline', {}).get('selector', ''))
        items = [item.attr(self.fields.get('free_deadline', {}).get('attribute')) for item in selector.items()]
        if len(items) > 0 and items is not None:
            if items[0] is not None:
                if "filters" in self.fields.get('free_deadline'):
                    itemdata = items[0]
                    for f_filter in self.fields.get('free_deadline', {}).get('filters') or []:
                        if f_filter.get('name') == "re_search" \
                                and isinstance(f_filter.get("args"), list) \
                                and len(f_filter.get("args")) > 1:
                            arg1 = f_filter.get('args', [])[0]
                            arg2 = f_filter.get('args', [])[1]
                            search = re.search(arg1, itemdata, arg2)
                            items = search[0] if search else ""
                        if f_filter.get('name') == "dateparse":
                            arg1 = f_filter.get('args')
                            items = arg1
                self.torrents_info['free_deadline'] = items

    def Getinfo(self, torrent):
        """
        解析单条种子数据
        """
        self.torrents_info = {'indexer': self.indexer.id}
        self.Gettitle_default(torrent)
        self.Gettitle_optional(torrent)
        self.Getgrabs(torrent)
        self.Getleechers(torrent)
        self.Getseeders(torrent)
        self.Getsize(torrent)
        self.Getimdbid(torrent)
        self.Getdownload(torrent)
        self.Getdetails(torrent)
        self.Getdownloadvolumefactor(torrent)
        self.Getuploadvolumefactor(torrent)
        self.Getdate_added(torrent)
        self.Getdate_elapsed(torrent)
        self.Getfree_deadline(torrent)
        return self.torrents_info

    def parse(self, request, response):
        """
        解析整个页面
        """
        try:
            # 获取网站信息
            self.article_list = response.extract()
            # 获取站点种子xml
            self.fields = self.indexer.torrents.get('fields')
            doc = PyQuery(self.article_list)
            # 种子筛选器
            torrents_selector = self.indexer.torrents.get('list', {}).get('selector')
            str_list = list(torrents_selector)
            # 兼容选择器中has()函数 部分情况下无双引号会报错
            has_index = torrents_selector.find('has')
            if has_index != -1:
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
            for torn in doc(torrents_selector):
                self.torrents_info_array.append(copy.deepcopy(self.Getinfo(PyQuery(torn))))

        except Exception as err:
            log.warn("【SPIDER】错误：%s - %s" % (str(err), traceback.format_exc()))
        finally:
            self.is_complete = True
