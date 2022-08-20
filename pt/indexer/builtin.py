import datetime
import time

import log
from pt.indexer.indexer import IIndexer
from pt.indexer.spider import TorrentSpider
from pt.sites import Sites
from rmt.meta.metabase import MetaBase
from utils.commons import ProcessHandler
from utils.functions import handler_special_chars
from utils.indexer_helper import IndexerHelper


class BuiltinIndexer(IIndexer):

    index_type = "INDEXER"

    def init_config(self):
        pass

    def get_status(self):
        """
        检查连通性
        :return: True、False
        """
        return True

    def get_indexers(self):
        ret_indexers = []
        for site in Sites().get_sites():
            if not site.get("cookie"):
                continue
            if not site.get("rssurl") and not site.get("signurl"):
                continue
            indexer = IndexerHelper().get_indexer(site.get("rssurl") or site.get("signurl"),
                                                  site.get("cookie"),
                                                  site.get("name"))
            if indexer:
                indexer.name = site.get("name")
                ret_indexers.append(indexer)
        return ret_indexers

    def search(self, order_seq,
               indexer,
               key_word,
               filter_args: dict,
               match_type,
               match_media: MetaBase):
        """
        根据关键字多线程检索
        """
        if not indexer or not key_word:
            return None
        if filter_args is None:
            filter_args = {}

        if filter_args.get("site") and indexer.name not in filter_args.get("site"):
            return []
        # 计算耗时
        start_time = datetime.datetime.now()
        log.info(f"【{self.index_type}】开始检索Indexer：{indexer.name} ...")
        # 特殊符号处理
        search_word = handler_special_chars(text=key_word, replace_word=" ", allow_space=True)
        result_array = self.__spider_search(keyword=search_word, indexer=indexer)
        if len(result_array) == 0:
            log.warn(f"【{self.index_type}】{indexer.name} 未检索到数据")
            ProcessHandler().update(text=f"{indexer.name} 未检索到数据")
            return []
        else:
            log.warn(f"【{self.index_type}】{indexer.name} 返回数据：{len(result_array)}")
            return self.filter_search_results(result_array=result_array,
                                              order_seq=order_seq,
                                              indexer_name=indexer.name,
                                              filter_args=filter_args,
                                              match_type=match_type,
                                              match_media=match_media,
                                              start_time=start_time)

    @staticmethod
    def __spider_search(keyword, indexer):
        spider = TorrentSpider()
        spider.setparam(indexer=indexer, keyword=keyword)
        spider.start()
        # 循环判断是否获取到数据
        sleep_count = 0
        while not spider.is_complete:
            sleep_count += 1
            time.sleep(1)
            if sleep_count > 20:
                break
        # 返回数据
        result_array = spider.torrents_info_array.copy()
        spider.torrents_info_array.clear()
        return result_array
