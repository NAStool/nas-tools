from urllib.parse import quote

import log
from app.utils import RequestUtils, StringUtils
from config import Config


class TorrentLeech(object):
    _indexer = None
    _proxy = None
    _size = 100
    _searchurl = "%storrents/browse/list/query/%s"
    _browseurl = "%storrents/browse/list/page/2%s"
    _downloadurl = "%sdownload/%s/%s"
    _pageurl = "%storrent/%s"

    def __init__(self, indexer):
        self._indexer = indexer
        if indexer.proxy:
            self._proxy = Config().get_proxies()
        self.init_config()

    def init_config(self):
        self._size = Config().get_config('pt').get('site_search_result_num') or 100


    def search(self, keyword, page=0):
        if keyword:
            url = self._searchurl % (self._indexer.domain, quote(keyword))
        else:
            url = self._browseurl % (self._indexer.domain, int(page) + 1)
        res = RequestUtils(
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": f"{self._indexer.ua}"
            },
            cookies=self._indexer.cookie,
            proxies=self._proxy,
            timeout=30
        ).get_res(url)
        torrents = []
        if res and res.status_code == 200:
            results = res.json().get('torrentList') or []
            for result in results:
                torrent = {
                    'indexer': self._indexer.id,
                    'title': result.get('name'),
                    'enclosure': self._downloadurl % (self._indexer.domain, result.get('fid'), result.get('filename')),
                    'pubdate': StringUtils.timestamp_to_date(result.get('addedTimestamp')),
                    'size': result.get('size'),
                    'seeders': result.get('seeders'),
                    'peers': result.get('leechers'),
                    'grabs': result.get('completed'),
                    'downloadvolumefactor': result.get('download_multiplier'),
                    'uploadvolumefactor': 1,
                    'page_url': self._pageurl % (self._indexer.domain, result.get('fid')),
                    'imdbid': result.get('imdbID')
                }
                torrents.append(torrent)
        elif res is not None:
            log.warn(f"【INDEXER】{self._indexer.name} 搜索失败，错误码：{res.status_code}")
            return True, []
        else:
            log.warn(f"【INDEXER】{self._indexer.name} 搜索失败，无法连接 {self._indexer.domain}")
            return True, []

        return False, torrents
