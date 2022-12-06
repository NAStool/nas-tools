import requests

from app.utils.types import IndexerType
from config import Config
from app.indexer.indexer import IIndexer
from app.utils import RequestUtils
from app.helper import IndexerConf


class Jackett(IIndexer):
    index_type = IndexerType.JACKETT.value
    _password = None

    def init_config(self, jackett = None):
        if not jackett:
            jackett = Config().get_config('jackett')
        if jackett:
            self.api_key = jackett.get('api_key')
            self._password = jackett.get('password')
            self.host = jackett.get('host')
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
        self.init_config(Config().get_test_config('jackett'))
        ret = False
        if self.api_key and self.host:
            ret = True if self.get_indexers() else False
        # 重置配置
        self.init_config()
        return ret

    def get_indexers(self):
        """
        获取配置的jackett indexer
        :return: indexer 信息 [(indexerId, indexerName, url)]
        """
        # 获取Cookie
        cookie = None
        session = requests.session()
        res = RequestUtils(session=session).post_res(url=f"{self.host}UI/Dashboard",
                                                     params={"password": self._password})
        if res and session.cookies:
            cookie = session.cookies.get_dict()
        indexer_query_url = f"{self.host}api/v2.0/indexers?configured=true"
        try:
            ret = RequestUtils(cookies=cookie).get_res(indexer_query_url)
            if not ret or not ret.json():
                return []
            return [IndexerConf({"id": v["id"],
                                 "name": v["name"],
                                 "domain": f'{self.host}api/v2.0/indexers/{v["id"]}/results/torznab/',
                                 "public": True if v['type'] == 'public' else False,
                                 "buildin": False})
                    for v in ret.json()]
        except Exception as e2:
            print(str(e2))
            return []

    def search(self, *kwargs):
        return super().search(*kwargs)
