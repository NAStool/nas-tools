import os.path

import yaml

from config import Config
from utils.functions import get_dir_files, singleton
from urllib import parse

from utils.http_utils import RequestUtils
from utils.indexer_conf import IndexerConf


@singleton
class IndexerHelper:
    _indexers = []
    _site_path = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        # 站点配置文件在config文件夹sites目录下
        self._site_path = os.path.join(os.path.dirname(Config().get_config_path()), "sites")
        cfg_files = get_dir_files(in_path=self._site_path, exts=[".yml"])
        for cfg_file in cfg_files:
            with open(cfg_file, mode='r', encoding='utf-8') as f:
                self._indexers.append(yaml.safe_load(f))

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
