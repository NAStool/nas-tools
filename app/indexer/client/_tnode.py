import re

import log
from app.utils import RequestUtils, StringUtils
from config import Config


class TNodeSpider(object):
    _indexerid = None
    _domain = None
    _name = ""
    _proxy = None
    _cookie = None
    _ua = None
    _token = None
    _size = 100
    _searchurl = "%sapi/torrent/advancedSearch"
    _downloadurl = "%sapi/torrent/download/%s"
    _pageurl = "%storrent/info/%s"

    def __init__(self, indexer):
        if indexer:
            self._indexerid = indexer.id
            self._domain = indexer.domain
            self._searchurl = self._searchurl % self._domain
            self._name = indexer.name
            if indexer.proxy:
                self._proxy = Config().get_proxies()
            self._cookie = indexer.cookie
            self._ua = indexer.ua
        self.init_config()

    def init_config(self):
        self._size = Config().get_config('pt').get('site_search_result_num') or 100
        self.__get_token()

    def __get_token(self):
        if not self._domain:
            return
        res = RequestUtils(headers=self._ua,
                           cookies=self._cookie,
                           proxies=self._proxy,
                           timeout=15).get_res(url=self._domain)
        if res and res.status_code == 200:
            csrf_token = re.search(r'<meta name="x-csrf-token" content="(.+?)">', res.text)
            if csrf_token:
                self._token = csrf_token.group(1)

    def search(self, keyword, page=1):
        if not self._token:
            log.warn(f"【INDEXER】{self._name} 未获取到token，无法搜索")
            return []
        params = {
            "page": int(page) + 1,
            "size": self._size,
            "type": "title",
            "keyword": keyword or "",
            "sorter": "id",
            "order": "desc",
            "tags": [],
            "category": [501, 502, 503, 504],
            "medium": [],
            "videoCoding": [],
            "audioCoding": [],
            "resolution": [],
            "group": []
        }
        res = RequestUtils(
            headers={
                'X-CSRF-TOKEN': self._token,
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": f"{self._ua}"
            },
            cookies=self._cookie,
            proxies=self._proxy,
            timeout=30
        ).post_res(url=self._searchurl, json=params)
        torrents = []
        if res and res.status_code == 200:
            results = res.json().get('data', {}).get("torrents") or []
            for result in results:
                torrent = {
                    'indexer': self._indexerid,
                    'title': result.get('title'),
                    'description': result.get('subtitle'),
                    'enclosure': self._downloadurl % (self._domain, result.get('id')),
                    'pubdate': StringUtils.timestamp_to_date(result.get('upload_time')),
                    'size': result.get('size'),
                    'seeders': result.get('seeding'),
                    'peers': result.get('leeching'),
                    'grabs': result.get('complete'),
                    'downloadvolumefactor': result.get('downloadRate'),
                    'uploadvolumefactor': result.get('uploadRate'),
                    'page_url': self._pageurl % (self._domain, result.get('id')),
                    'imdbid': result.get('imdb')
                }
                torrents.append(torrent)
        elif res is not None:
            log.warn(f"【INDEXER】{self._name} 搜索失败，错误码：{res.status_code}")
            return []
        else:
            log.warn(f"【INDEXER】{self._name} 搜索失败，无法连接 {self._domain}")
            return []
        return torrents
