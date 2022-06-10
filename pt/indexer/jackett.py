import re

import requests

from config import Config
from pt.indexer.indexer import IIndexer


class Jackett(IIndexer):
    index_type = "JACKETT"
    __indexers = []

    def init_config(self):
        config = Config()
        jackett = config.get_config('jackett')
        if jackett:
            self.api_key = jackett.get('api_key')
            self.__indexers = jackett.get('indexers')
            if self.__indexers and not isinstance(self.__indexers, list):
                self.__indexers = [self.__indexers]

    def get_status(self):
        """
        检查连通性
        :return: True、False
        """
        if not self.api_key or not self.__indexers:
            return False
        api_url = "%sapi?apikey=%s&t=search&q=%s" % (self.__indexers[0], self.api_key, "ASDFGHJKL")
        res = requests.get(api_url, timeout=10)
        if res and res.status_code == 200:
            if res.text.find("Invalid API Key") == -1:
                return True
        return False

    def get_indexers(self):
        """
        获取配置的jackett indexer
        :return: indexer 信息 [(indexerId, indexerName, url)]
        """

        indexers = []
        indexer_id = 0
        for item in self.__indexers:
            indexer_name = re.search(r'/indexers/([a-zA-Z0-9]+)/results/', item)
            if indexer_name:
                indexer_name = indexer_name.group(1)
                indexer_id += 1
                indexers.append((indexer_id, indexer_name, item))

        return indexers
