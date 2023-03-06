import copy
import datetime
import time

import log
from app.helper import IndexerHelper, IndexerConf, ProgressHelper, ChromeHelper, DbHelper
from app.indexer.client._base import _IIndexClient
from app.indexer.client._rarbg import Rarbg
from app.indexer.client._render_spider import RenderSpider
from app.indexer.client._spider import TorrentSpider
from app.indexer.client._tnode import TNodeSpider
from app.sites import Sites
from app.utils import StringUtils
from app.utils.types import SearchType, IndexerType
from config import Config


class BuiltinIndexer(_IIndexClient):
    # 索引器ID
    client_id = "builtin"
    # 索引器类型
    client_type = IndexerType.BUILTIN
    # 索引器名称
    client_name = IndexerType.BUILTIN.value

    # 私有属性
    _client_config = {}
    progress = None
    sites = None
    dbhelper = None

    def __init__(self, config=None):
        super().__init__()
        self._client_config = config or {}
        self.init_config()

    def init_config(self):
        self.sites = Sites()
        self.progress = ProgressHelper()
        self.dbhelper = DbHelper()

    @classmethod
    def match(cls, ctype):
        return True if ctype in [cls.client_id, cls.client_type, cls.client_name] else False

    def get_type(self):
        return self.client_type

    def get_status(self):
        """
        检查连通性
        :return: True、False
        """
        return True

    def get_indexers(self, check=True, indexer_id=None):
        ret_indexers = []
        # 选中站点配置
        indexer_sites = Config().get_config("pt").get("indexer_sites") or []
        _indexer_domains = []
        # 检查浏览器状态
        chrome_ok = ChromeHelper().get_status()
        # 私有站点
        for site in Sites().get_sites():
            url = site.get("signurl") or site.get("rssurl")
            cookie = site.get("cookie")
            if not url or not cookie:
                continue
            render = False if not chrome_ok else None
            indexer = IndexerHelper().get_indexer(url=url,
                                                  cookie=cookie,
                                                  ua=site.get("ua"),
                                                  name=site.get("name"),
                                                  rule=site.get("rule"),
                                                  pri=site.get('pri'),
                                                  public=False,
                                                  proxy=site.get("proxy"),
                                                  render=render)
            if indexer:
                if indexer_id and indexer.id == indexer_id:
                    return indexer
                if check and indexer_sites and indexer.id not in indexer_sites:
                    continue
                if indexer.domain not in _indexer_domains:
                    _indexer_domains.append(indexer.domain)
                    indexer.name = site.get("name")
                    ret_indexers.append(indexer)
        return ret_indexers

    def search(self, order_seq,
               indexer,
               key_word,
               filter_args: dict,
               match_media,
               in_from: SearchType):
        """
        根据关键字多线程检索
        """
        if not indexer or not key_word:
            return None
        # 不是配置的索引站点过滤掉
        indexer_sites = Config().get_config("pt").get("indexer_sites") or []
        if indexer_sites and indexer.id not in indexer_sites:
            return []
        # fix 共用同一个dict时会导致某个站点的更新全局全效
        if filter_args is None:
            _filter_args = {}
        else:
            _filter_args = copy.deepcopy(filter_args)
        # 不在设定搜索范围的站点过滤掉
        if _filter_args.get("site") and indexer.name not in _filter_args.get("site"):
            return []
        # 搜索条件没有过滤规则时，使用站点的过滤规则
        if not _filter_args.get("rule") and indexer.rule:
            _filter_args.update({"rule": indexer.rule})
        # 计算耗时
        start_time = datetime.datetime.now()
        log.info(f"【{self.client_name}】开始检索Indexer：{indexer.name} ...")
        # 特殊符号处理
        search_word = StringUtils.handler_special_chars(text=key_word,
                                                        replace_word=" ",
                                                        allow_space=True)
        # 避免对英文站搜索中文
        if indexer.language == "en" and StringUtils.is_chinese(search_word):
            log.warn(f"【{self.client_name}】{indexer.name} 无法使用中文名搜索")
            return []
        # 开始索引
        result_array = []
        try:
            if indexer.parser == "TNodeSpider":
                result_array = TNodeSpider(indexer=indexer).search(keyword=search_word)
            elif indexer.parser == "RenderSpider":
                result_array = RenderSpider().search(keyword=search_word,
                                                     indexer=indexer,
                                                     mtype=match_media.type if match_media else None)
            elif indexer.parser == "RarBg":
                result_array = Rarbg().search(keyword=search_word,
                                              indexer=indexer,
                                              imdb_id=match_media.imdb_id if match_media else None)
            else:
                result_array = self.__spider_search(keyword=search_word,
                                                    indexer=indexer,
                                                    mtype=match_media.type if match_media else None)
        except Exception as err:
            print(str(err))
        # 索引花费的时间
        seconds = (datetime.datetime.now() - start_time).seconds

        if len(result_array) == 0:
            log.warn(f"【{self.client_name}】{indexer.name} 未检索到数据")
            # 更新进度
            self.progress.update(ptype='search', text=f"{indexer.name} 未检索到数据")
            # 索引统计
            self.dbhelper.insert_indexer_statistics(indexer=indexer.name,
                                                    itype=self.client_id,
                                                    seconds=seconds,
                                                    result='N'
                                                    )
            return []
        else:
            log.warn(f"【{self.client_name}】{indexer.name} 返回数据：{len(result_array)}")
            # 更新进度
            self.progress.update(ptype='search', text=f"{indexer.name} 返回 {len(result_array)} 条数据")
            # 索引统计
            self.dbhelper.insert_indexer_statistics(indexer=indexer.name,
                                                    itype=self.client_id,
                                                    seconds=seconds,
                                                    result='Y'
                                                    )
            # 过滤
            return self.filter_search_results(result_array=result_array,
                                              order_seq=order_seq,
                                              indexer=indexer,
                                              filter_args=_filter_args,
                                              match_media=match_media,
                                              start_time=start_time)

    def list(self, index_id, page=0, keyword=None):
        """
        根据站点ID检索站点首页资源
        """
        if not index_id:
            return []
        indexer: IndexerConf = self.get_indexers(indexer_id=index_id)
        if not indexer:
            return []
        if indexer.parser == "RenderSpider":
            return RenderSpider().search(keyword=keyword,
                                         indexer=indexer,
                                         page=page)
        elif indexer.parser == "TNodeSpider":
            return TNodeSpider(indexer=indexer).search(keyword=keyword, page=page)
        return self.__spider_search(indexer=indexer,
                                    page=page,
                                    keyword=keyword)

    @staticmethod
    def __spider_search(indexer, keyword=None, page=None, mtype=None, timeout=30):
        """
        根据关键字搜索单个站点
        """
        spider = TorrentSpider()
        spider.setparam(indexer=indexer,
                        keyword=keyword,
                        page=page,
                        mtype=mtype)
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
