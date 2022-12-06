from app.utils.types import IndexerType
from config import Config
from app.indexer.indexer import IIndexer
from app.utils import RequestUtils
from app.helper import IndexerConf


class Prowlarr(IIndexer):
    index_type = IndexerType.PROWLARR.value

    def init_config(self, prowlarr = None):
        if not prowlarr:
            prowlarr = Config().get_config('prowlarr')
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
        测试连通性
        """
        # 载入测试  如返回{} 或 False 都会使not判断成立从而载入原始配置
        # 有可能在测试配置传递参数时填写错误, 所导致的异常可通过该思路回顾
        self.init_config(Config().get_test_config('prowlarr'))
        ret = False
        if self.api_key and self.host:
            ret = True if self.get_indexers() else False
        # 重置配置
        self.init_config()
        return ret

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
