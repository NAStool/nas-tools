import os.path
import pickle

from app.utils import StringUtils, RequestUtils
from app.utils.exception_util import ExceptionUtils
from config import Config
from app.utils.commons import singleton


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
            ExceptionUtils.exception_traceback(err)

    def get_all_indexers(self):
        return self._indexers

    def get_indexer(self,
                    url,
                    cookie=None,
                    name=None,
                    rule=None,
                    public=None,
                    proxy=False,
                    parser=None,
                    ua=None,
                    render=False,
                    language=None,
                    pri=None):
        if not url:
            return None
        for indexer in self._indexers:
            if not indexer.get("domain"):
                continue
            if StringUtils.url_equal(indexer.get("domain"), url):
                return IndexerConf(datas=indexer,
                                   cookie=RequestUtils.cookie_parse(cookie),
                                   name=name,
                                   rule=rule,
                                   public=public,
                                   proxy=proxy,
                                   parser=parser,
                                   ua=ua,
                                   render=render,
                                   builtin=True,
                                   language=language,
                                   pri=pri)
        return None


class IndexerConf(object):

    def __init__(self,
                 datas=None,
                 cookie=None,
                 name=None,
                 rule=None,
                 public=None,
                 proxy=False,
                 parser=None,
                 ua=None,
                 render=False,
                 builtin=True,
                 language=None,
                 pri=None):
        if not datas:
            return
        self.datas = datas
        self.id = self.datas.get('id')
        self.name = self.datas.get('name') if not name else name
        self.domain = self.datas.get('domain')
        self.userinfo = self.datas.get('userinfo', {})
        self.search = self.datas.get('search', {})
        self.torrents = self.datas.get('torrents', {})
        self.category_mappings = self.datas.get('category_mappings', [])
        self.cookie = cookie
        self.rule = rule
        self.public = public
        self.proxy = proxy
        self.parser = parser
        self.ua = ua
        self.render = render
        self.builtin = builtin
        self.language = language
        self.pri = pri if pri else 0

    def get_userinfo(self):
        return self.userinfo

    def get_search(self):
        return self.search

    def get_torrents(self):
        return self.torrents

    def get_category_mapping(self):
        return self.category_mappings
