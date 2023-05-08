import requests

import log
from app.utils import RequestUtils
from config import Config


class Rarbg:
    _appid = "nastool"
    _indexer_id = None
    _indexer_name = None
    _req = None
    _token = None
    _api_url = "http://torrentapi.org/pubapi_v2.php"

    def __init__(self, indexer):
        self._indexer_id = indexer.id
        self._indexer_name = indexer.name
        self.init_config()

    def init_config(self):
        session = requests.session()
        self._req = RequestUtils(proxies=Config().get_proxies(), session=session, timeout=10)
        self.__get_token()

    def __get_token(self):
        if self._token:
            return
        res = self._req.get_res(url=self._api_url, params={'app_id': self._appid, 'get_token': 'get_token'})
        if res and res.json():
            self._token = res.json().get('token')

    def search(self, keyword, imdb_id=None, page=1):
        if not keyword and not imdb_id:
            mode = "list"
        else:
            mode = "search"
        self.__get_token()
        if not self._token:
            log.warn(f"【INDEXER】{self._indexer_name} 未获取到token，无法搜索")
            return True, []
        params = {
            'app_id': self._appid,
            'mode': mode,
            'token': self._token,
            'format': 'json_extended',
            'limit': int(page) * 100
        }
        if imdb_id:
            params['search_imdb'] = imdb_id
        else:
            params['search_string'] = keyword
        res = self._req.get_res(url=self._api_url, params=params)
        torrents = []
        if res and res.status_code == 200:
            results = res.json().get('torrent_results') or []
            for result in results:
                if not result or not result.get('title'):
                    continue
                torrent = {'indexer': self._indexer_id,
                           'title': result.get('title'),
                           'enclosure': result.get('download'),
                           'size': result.get('size'),
                           'seeders': result.get('seeders'),
                           'peers': result.get('leechers'),
                           'freeleech': True,
                           'downloadvolumefactor': 0.0,
                           'uploadvolumefactor': 1.0,
                           'page_url': result.get('info_page'),
                           'imdbid': result.get('episode_info').get('imdb') if result.get('episode_info') else ''}
                torrents.append(torrent)
        elif res is not None:
            log.warn(f"【INDEXER】{self._indexer_name} 搜索失败，错误码：{res.status_code}")
            return True, []
        else:
            log.warn(f"【INDEXER】{self._indexer_name} 搜索失败，无法连接 torrentapi.org")
            return True, []
        return False, torrents
