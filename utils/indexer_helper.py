import os.path
import pickle

from utils.functions import singleton
from urllib import parse

from utils.http_utils import RequestUtils
from utils.indexer_conf import IndexerConf


@singleton
class IndexerHelper:
    _indexers = []

    def __init__(self):
        self.init_config()

    def init_config(self):
        with open(os.path.join(os.getcwd(), "config", "sites.dat"), "rb") as f:
            self._indexers = pickle.load(f)

    def get_all_indexers(self):
        return self._indexers

    def get_indexer(self, url, cookie, name):
        if not url:
            return None
        url_host = parse.urlparse(url).netloc
        for indexer in self._indexers:
            if not indexer.get("domain"):
                continue
            if parse.urlparse(indexer.get("domain")).netloc == url_host:
                return IndexerConf(datas=indexer, cookie=RequestUtils.cookie_parse(cookie), name=name)
        return None
