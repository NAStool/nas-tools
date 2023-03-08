import requests

import log
from app.utils import RequestUtils
from config import Config


class TorrentLeech:
    _indexerid = None
    _domain = None
    _name = None
    _req = None
    _proxy = None
    _cookie = None
    _ua = None

    # 只查询movie,tv,anime
    _api_url = "%storrents/browse/list/categories/8,9,11,37,43,14,12,13,47,15,29,26,32,27,34,35/"

    _search_url = "%s/query/%s"
    _list_url = "%s/page/%s"

    _download_url = "download/%s/%s"
    _page_url = "torrent/%s"

    def __init__(self, indexer):
        if indexer:
            self._indexerid = indexer.id
            self._name = indexer.name
            self._domain = indexer.domain
            self._api_url = self._api_url % indexer.domain
            self._download_url = indexer.domain + self._download_url
            self._page_url = indexer.domain + self._page_url
            if indexer.proxy:
                self._proxy = Config().get_proxies()
            self._cookie = indexer.cookie
            self._ua = indexer.ua
        self.init_config()

    def init_config(self):
        session = requests.session()
        self._req = RequestUtils(
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": f"{self._ua}"
            },
            cookies=self._cookie,
            proxies=self._proxy,
            timeout=10,
            session=session
        )

    def search(self, keyword, page=None, mtype=None):

        if keyword:
            req_url = self._search_url % (self._api_url, keyword)
        else:
            req_url = self._list_url % (self._api_url, int(page) + 1)

        res = self._req.get_res(url=req_url)
        torrents = []
        if res and res.status_code == 200:
            results = res.json().get('torrentList') or []
            for result in results:
                if not result or not result.get('name'):
                    continue

                f_id = result.get('fid')
                free_leech = "FREELEECH" in (result.get('tags') or [])

                torrent = {
                    'indexer': self._indexerid,
                    'title': result.get('name'),
                    'enclosure': self._download_url % (f_id, result.get('filename')),
                    'size': result.get('size'),
                    'seeders': result.get('seeders'),
                    'peers': result.get('leechers'),
                    'freeleech': free_leech,
                    'downloadvolumefactor': 0.0 if free_leech else 1.0,
                    'uploadvolumefactor': 1.0,
                    'page_url': self._page_url % f_id,
                    'imdbid': result.get('imdbID')
                }
                torrents.append(torrent)
        elif res is not None:
            log.warn(f"【INDEXER】{self._name} 搜索失败，错误码：{res.status_code}")
            return True, []
        else:
            log.warn(f"【INDEXER】{self._name} 搜索失败，无法连接 {req_url}")
            return True, []
        return False, torrents
