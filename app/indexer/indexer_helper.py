import os.path
import pickle

from app.utils.string_utils import StringUtils
from config import Config
from app.utils.commons import singleton
from app.utils.http_utils import RequestUtils
from app.indexer.indexer_conf import IndexerConf


@singleton
class IndexerHelper:
    _indexers = []

    def __init__(self):
        self.init_config()

    def init_config(self):
        try:
            with open(os.path.join(Config().get_inner_config_path(),
                                   "sites.dat"),
                      "rb") as f:
                self._indexers = pickle.load(f)
        except Exception as err:
            print(err)

    def get_all_indexers(self):
        return self._indexers

    def get_indexer(self, url, cookie=None, name=None):
        if not url:
            return None
        for indexer in self._indexers:
            if not indexer.get("domain"):
                continue
            if StringUtils.url_equal(indexer.get("domain"), url):
                return IndexerConf(datas=indexer, cookie=RequestUtils.cookie_parse(cookie), name=name)
        return None
