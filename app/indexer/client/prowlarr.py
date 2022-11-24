from app.utils.types import IndexerType
from config import CONFIG
from app.indexer.indexer import IIndexer
from app.utils import RequestUtils
from app.helper import IndexerConf


class Prowlarr(IIndexer):
    index_type = IndexerType.PROWLARR.value

    def init_config(self):
        prowlarr = CONFIG.get_config('prowlarr')
        if prowlarr:
            self.api_key = prowlarr.get('api_key')
            self.host = prowlarr.get('host')
            if self.host:
                if not self.host.startswith('http'):
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
        return True if self.get_indexers() else False

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
        return [IndexerConf({"id": v["indexerId"],
                             "name": v["indexerName"],
                             "domain": f'{self.host}{v["indexerId"]}/api',
                             "buildin": False})
                for v in indexers]

    def search(self, *kwargs):
        return super().search(*kwargs)
