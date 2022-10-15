import datetime
import time

import log
from app.indexer.client.rarbg import Rarbg
from app.utils.types import SearchType, IndexerType
from config import Config
from app.indexer.indexer import IIndexer
from app.indexer.client.spider import TorrentSpider
from app.sites import Sites
from app.utils import StringUtils
from app.helper import ProgressHelper, IndexerHelper


class BuiltinIndexer(IIndexer):
    index_type = IndexerType.BUILTIN.value
    progress = None
    sites = None

    def init_config(self):
        self.sites = Sites()
        self.progress = ProgressHelper()

    def get_status(self):
        """
        检查连通性
        :return: True、False
        """
        return True

    def get_indexers(self, check=True, public=True, indexer_id=None):
        ret_indexers = []
        # 选中站点配置
        indexer_sites = Config().get_config("pt").get("indexer_sites") or []
        _indexer_domains = []
        # 私有站点
        for site in Sites().get_sites():
            if not site.get("rssurl") and not site.get("signurl"):
                continue
            if not site.get("cookie"):
                continue
            url = site.get("signurl") or site.get("rssurl")
            public_site = self.sites.get_public_sites(url=url)
            if public_site:
                if not public:
                    continue
                is_public = True
                proxy = public_site.get("proxy")
                language = public_site.get("language")
            else:
                is_public = False
                proxy = True if site.get("proxy") == "Y" else False
                language = None
            indexer = IndexerHelper().get_indexer(url=url,
                                                  cookie=site.get("cookie"),
                                                  name=site.get("name"),
                                                  rule=site.get("rule"),
                                                  public=is_public,
                                                  proxy=proxy,
                                                  ua=site.get("ua"),
                                                  language=language,
                                                  pri=site.get('pri'),
                                                  favicon=site.get('favicon'))
            if indexer:
                if indexer_id and indexer.id == indexer_id:
                    return indexer
                if check and indexer_sites and indexer.id not in indexer_sites:
                    continue
                if indexer.domain not in _indexer_domains:
                    _indexer_domains.append(indexer.domain)
                    indexer.name = site.get("name")
                    ret_indexers.append(indexer)
        # 公开站点
        if public:
            for site, attr in self.sites.get_public_sites():
                indexer = IndexerHelper().get_indexer(url=site,
                                                      public=True,
                                                      proxy=attr.get("proxy"),
                                                      render=attr.get("render"),
                                                      language=attr.get("language"),
                                                      parser=attr.get("parser"))
                if indexer:
                    if indexer_id and indexer.id == indexer_id:
                        return indexer
                    if check and indexer_sites and indexer.id not in indexer_sites:
                        continue
                    if indexer.domain not in _indexer_domains:
                        _indexer_domains.append(indexer.domain)
                        ret_indexers.append(indexer)
        return ret_indexers

    def search(self, order_seq,
               indexer,
               key_word,
               filter_args: dict,
               match_type,
               match_media,
               in_from: SearchType):
        """
        根据关键字多线程检索
        """
        if not indexer or not key_word:
            return None
        if filter_args is None:
            filter_args = {}
        # 不是配置的索引站点过滤掉
        indexer_sites = Config().get_config("pt").get("indexer_sites") or []
        if indexer_sites and indexer.id not in indexer_sites:
            return []
        # 不在设定搜索范围的站点过滤掉
        if filter_args.get("site") and indexer.name not in filter_args.get("site"):
            return []
        # 搜索条件没有过滤规则时，非WEB搜索模式下使用站点的过滤规则
        if in_from != SearchType.WEB and not filter_args.get("rule") and indexer.rule:
            filter_args.update({"rule": indexer.rule})
        # 计算耗时
        start_time = datetime.datetime.now()
        log.info(f"【{self.index_type}】开始检索Indexer：{indexer.name} ...")
        # 特殊符号处理
        search_word = StringUtils.handler_special_chars(text=key_word, replace_word=" ", allow_space=True)
        # 避免对英文站搜索中文
        if indexer.language == "en" and StringUtils.is_chinese(search_word):
            log.warn(f"【{self.index_type}】{indexer.name} 无法使用中文名搜索")
            return []
        if indexer.parser == "rarbg":
            imdb_id = match_media.imdb_id if match_media else None
            result_array = Rarbg(cookies=indexer.cookie).search(keyword=search_word, indexer=indexer, imdb_id=imdb_id)
        else:
            result_array = self.__spider_search(keyword=search_word, indexer=indexer)
        if len(result_array) == 0:
            log.warn(f"【{self.index_type}】{indexer.name} 未检索到数据")
            self.progress.update(ptype='search', text=f"{indexer.name} 未检索到数据")
            return []
        else:
            log.warn(f"【{self.index_type}】{indexer.name} 返回数据：{len(result_array)}")
            return self.filter_search_results(result_array=result_array,
                                              order_seq=order_seq,
                                              indexer=indexer,
                                              filter_args=filter_args,
                                              match_type=match_type,
                                              match_media=match_media,
                                              start_time=start_time)

    def list(self, index_id, page=0, keyword=None):
        """
        根据站点ID检索站点首页资源
        """
        if not index_id:
            return []
        indexer = self.get_indexers(indexer_id=index_id)
        if not indexer:
            return []
        return self.__spider_search(indexer, page=page, keyword=keyword, timeout=10)

    @staticmethod
    def __spider_search(indexer, page=None, keyword=None, timeout=20):
        """
        根据关键字搜索单个站点
        """
        spider = TorrentSpider()
        spider.setparam(indexer=indexer,
                        keyword=keyword,
                        page=page)
        spider.start()
        # 循环判断是否获取到数据
        sleep_count = 0
        while not spider.is_complete:
            sleep_count += 1
            time.sleep(1)
            if sleep_count > timeout:
                break
        # 返回数据
        result_array = spider.torrents_info_array.copy()
        spider.torrents_info_array.clear()
        return result_array
