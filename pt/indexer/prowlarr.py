from config import Config
from pt.indexer.indexer import IIndexer
from utils.http_utils import RequestUtils


class Prowlarr(IIndexer):
    index_type = "PROWLARR"

    def init_config(self):
        config = Config()
        prowlarr = config.get_config('prowlarr')
        if prowlarr:
            self.api_key = prowlarr.get('api_key')
            self.host = prowlarr.get('host')
            if not self.host.startswith('http://') and not self.host.startswith('https://'):
                self.host = "http://" + self.host
            if not self.host.endswith('/'):
                self.host = self.host + "/"

    def get_status(self):
        """
        检查连通性
        :return: True、False
        """
        if not self.api_key or not self.host:
            return False
        api_url = "%sapi/v1/search?apikey=%s&Query=%s" % (self.host, self.api_key, "ASDFGHJKL")
        res = RequestUtils().get_res(api_url)
        if res and res.status_code == 200:
            return True
        return False

    def get_indexers(self):
        """
        获取配置的prowlarr indexer
        :return: indexer 信息 [(indexerId, indexerName, url)]
        """
        indexer_query_url = f"{self.host}api/v1/indexerstats?apikey={self.api_key}"
        try:
            ret = RequestUtils().get_res(indexer_query_url)
        except Exception as e2:
            print(str(e2))
            return []
        if not ret:
            return []
        indexers = ret.json().get("indexers", [])
        return [(v["indexerId"], v["indexerName"], f'{self.host}{v["indexerId"]}/api') for v in indexers]
