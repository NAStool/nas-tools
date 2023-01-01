import requests

from app.utils import ExceptionUtils
from app.utils.types import IndexerType
from config import Config
from app.indexer.client._base import _IIndexClient
from app.utils import RequestUtils
from app.helper import IndexerConf


class Jackett(_IIndexClient):
    schema = "jackett"
    _client_config = {}
    index_type = IndexerType.JACKETT.value
    _password = None

    def __init__(self, config=None):
        super().__init__()
        if config:
            self._client_config = config
        else:
            self._client_config = Config().get_config('jackett')
        self.init_config()

    def init_config(self):
        if self._client_config:
            self.api_key = self._client_config.get('api_key')
            self._password = self._client_config.get('password')
            self.host = self._client_config.get('host')
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

    @classmethod
    def match(cls, ctype):
        return True if ctype in [cls.schema, cls.index_type] else False

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
                                 "builtin": False})
                    for v in ret.json()]
        except Exception as e2:
            ExceptionUtils.exception_traceback(e2)
            return []

    def search(self, *kwargs):
        return super().search(*kwargs)
