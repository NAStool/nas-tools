import requests

import log
from config import Config
from pt.indexer.indexer import IIndexer


class Prowlarr(IIndexer):
    index_type = "PROWLARR"
    __host = None

    def init_config(self):
        config = Config()
        prowlarr = config.get_config('prowlarr')
        if prowlarr:
            self.api_key = prowlarr.get('api_key')
            self.__host = prowlarr.get('host')
            if not self.__host.startswith('http://') and not self.__host.startswith('https://'):
                self.__host = "http://" + self.__host
            if not self.__host.endswith('/'):
                self.__host = self.__host + "/"

    def get_status(self):
        """
        检查连通性
        :return: True、False
        """
        if not self.api_key or not self.__host:
            return False
        api_url = "%sapi/v1/search?apikey=%s&Query=%s" % (self.__host, self.api_key, "ASDFGHJKL")
        res = requests.get(api_url, timeout=10)
        if res and res.status_code == 200:
            return True
        return False

    def get_indexers(self):
        """
        获取配置的prowlarr indexer
        :return: indexer 信息 [(indexerId, indexerName, url)]
        """
        indexer_query_url = f"{self.__host}api/v1/indexerstats?apikey={self.api_key}"
        try:
            ret = requests.get(indexer_query_url, timeout=30)
        except Exception as e2:
            log.console(str(e2))
            return []

        if not ret:
            return []

        indexers = ret.json().get("indexers", [])

        return [(v["indexerId"], v["indexerName"], f'{self.__host}{v["indexerId"]}/api') for v in indexers]
