import requests

from config import Config
from pt.indexer.indexer import IIndexer
from utils.http_utils import RequestUtils


class Jackett(IIndexer):
    index_type = "JACKETT"
    _password = None
    
    def init_config(self):
        config = Config()
        jackett = config.get_config('jackett')
        if jackett:
            self.api_key = jackett.get('api_key')
            self._password = jackett.get('password')
            self.host = jackett.get('host')
            if self.host:
                if not self.host.startswith('http://') and not self.host.startswith('https://'):
                    self.host = "http://" + self.host
                if not self.host.endswith('/'):
                    self.host = self.host + "/"

    def get_status(self):
        """
        检查连通性
        :return: True、False
        """
        return True if self.get_indexers() else False

    def get_indexers(self):
        """
        获取配置的jackett indexer
        :return: indexer 信息 [(indexerId, indexerName, url)]
        """
        # 获取Cookie
        cookie = None
        session = requests.session()
        res = RequestUtils(session=session).post_res(url=f"{self.host}UI/Dashboard", params={"password": self._password})
        if res and session.cookies:
            cookie = session.cookies.get_dict()
        indexer_query_url = f"{self.host}api/v2.0/indexers?configured=true"
        try:
            ret = RequestUtils(cookies=cookie).get_res(indexer_query_url)
            if not ret or not ret.json():
                return []
            return [(v["id"], v["name"], f'{self.host}api/v2.0/indexers/{v["id"]}/results/torznab/') for v in ret.json()]
        except Exception as e2:
            print(str(e2))
            return []
