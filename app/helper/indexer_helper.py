import os.path
import pickle

from app.utils import StringUtils, ExceptionUtils
from app.utils.commons import singleton
from config import Config


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
                    render=None,
                    language=None,
                    pri=None,
                    chrome=True):
        if not url:
            return None
        for indexer in self._indexers:
            if not indexer.get("domain"):
                continue
            if StringUtils.url_equal(indexer.get("domain"), url):
                return IndexerConf(datas=indexer,
                                   cookie=cookie,
                                   name=name,
                                   rule=rule,
                                   public=public,
                                   proxy=proxy,
                                   parser=parser,
                                   ua=ua,
                                   render=render,
                                   builtin=True,
                                   language=language,
                                   pri=pri,
                                   chrome=chrome)
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
                 render=None,
                 builtin=True,
                 language=None,
                 pri=None,
                 chrome=True):
        if not datas:
            return
        self.datas = datas
        self.id = self.datas.get('id')
        self.name = self.datas.get('name') if not name else name
        self.domain = self.datas.get('domain')
        self.userinfo = self.datas.get('userinfo', {})
        self.search = self.datas.get('search', {})
        self.browse = self.datas.get('browse', {})
        self.torrents = self.datas.get('torrents', {})
        self.category_mappings = self.datas.get('category_mappings', [])
        self.cookie = cookie
        self.rule = rule
        self.public = public
        self.proxy = proxy
        if parser is not None:
            self.parser = parser
        else:
            self.parser = self.datas.get('parser')
        self.ua = ua
        if not chrome:
            self.render = False
        else:
            if render is not None:
                self.render = render
            else:
                self.render = True if self.datas.get("render") else False
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
