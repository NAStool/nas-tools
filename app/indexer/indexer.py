import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import log
from app.conf import ModuleConf
from app.helper import ProgressHelper, SubmoduleHelper
from app.indexer.client import BuiltinIndexer
from app.utils import ExceptionUtils, StringUtils
from app.utils.commons import singleton
from app.utils.types import SearchType, IndexerType
from config import Config


@singleton
class Indexer(object):
    _indexer_schemas = []
    _client = None
    _client_type = None
    progress = None

    def __init__(self):
        self._indexer_schemas = SubmoduleHelper.import_submodules(
            'app.indexer.client',
            filter_func=lambda _, obj: hasattr(obj, 'schema')
        )
        log.debug(f"【Indexer】: 已经加载的索引器：{self._indexer_schemas}")
        self.init_config()

    def init_config(self):
        self.progress = ProgressHelper()
        self._client_type = ModuleConf.INDEXER_DICT.get(
            Config().get_config("pt").get('search_indexer') or 'builtin'
        )
        self._client = self.__get_client(self._client_type)

    def __build_class(self, ctype, conf):
        for indexer_schema in self._indexer_schemas:
            try:
                if indexer_schema.match(ctype):
                    return indexer_schema(conf)
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
        return None

    def get_indexers(self):
        """
        获取当前索引器的索引站点
        """
        if not self._client:
            return []
        return self._client.get_indexers()

    def get_indexer_dict(self):
        """
        获取索引器字典
        """
        return [
            {
                "id": index.id,
                "name": index.name
            } for index in self.get_indexers()
        ]

    def get_indexer_hash_dict(self):
        """
        获取索引器Hash字典
        """
        IndexerDict = {}
        for item in self.get_indexers() or []:
            IndexerDict[StringUtils.md5_hash(item.name)] = {
                "id": item.id,
                "name": item.name,
                "public": item.public,
                "builtin": item.builtin
            }
        return IndexerDict

    def get_indexer_names(self):
        """
        获取当前索引器的索引站点名称
        """
        return [indexer.name for indexer in self.get_indexers()]

    @staticmethod
    def get_builtin_indexers(check=True, public=True, indexer_id=None):
        """
        获取内置索引器的索引站点
        """
        return BuiltinIndexer().get_indexers(check=check, public=public, indexer_id=indexer_id)

    @staticmethod
    def list_builtin_resources(index_id, page=0, keyword=None):
        """
        获取内置索引器的资源列表
        :param index_id: 内置站点ID
        :param page: 页码
        :param keyword: 搜索关键字
        """
        return BuiltinIndexer().list(index_id=index_id, page=page, keyword=keyword)

    def __get_client(self, ctype: IndexerType, conf=None):
        return self.__build_class(ctype=ctype.value, conf=conf)

    def get_client(self):
        """
        获取当前索引器
        """
        return self._client

    def get_client_type(self):
        """
        获取当前索引器类型
        """
        return self._client_type

    def search_by_keyword(self,
                          key_word: [str, list],
                          filter_args: dict,
                          match_media=None,
                          in_from: SearchType = None):
        """
        根据关键字调用 Index API 检索
        :param key_word: 检索的关键字，不能为空
        :param filter_args: 过滤条件，对应属性为空则不过滤，{"season":季, "episode":集, "year":年, "type":类型, "site":站点,
                            "":, "restype":质量, "pix":分辨率, "sp_state":促销状态, "key":其它关键字}
                            sp_state: 为UL DL，* 代表不关心，
        :param match_media: 需要匹配的媒体信息
        :param in_from: 搜索渠道
        :return: 命中的资源媒体信息列表
        """
        if not key_word:
            return []

        indexers = self.get_indexers()
        if not indexers:
            log.error(f"【{self._client_type.value}】没有有效的索引器配置！")
            return []
        # 计算耗时
        start_time = datetime.datetime.now()
        if filter_args and filter_args.get("site"):
            log.info(f"【{self._client_type.value}】开始检索 %s，站点：%s ..." % (key_word, filter_args.get("site")))
            self.progress.update(ptype='search', text="开始检索 %s，站点：%s ..." % (key_word, filter_args.get("site")))
        else:
            log.info(f"【{self._client_type.value}】开始并行检索 %s，线程数：%s ..." % (key_word, len(indexers)))
            self.progress.update(ptype='search', text="开始并行检索 %s，线程数：%s ..." % (key_word, len(indexers)))
        # 多线程
        executor = ThreadPoolExecutor(max_workers=len(indexers))
        all_task = []
        for index in indexers:
            order_seq = 100 - int(index.pri)
            task = executor.submit(self._client.search,
                                   order_seq,
                                   index,
                                   key_word,
                                   filter_args,
                                   match_media,
                                   in_from)
            all_task.append(task)
        ret_array = []
        finish_count = 0
        for future in as_completed(all_task):
            result = future.result()
            finish_count += 1
            self.progress.update(ptype='search', value=round(100 * (finish_count / len(all_task))))
            if result:
                ret_array = ret_array + result
        # 计算耗时
        end_time = datetime.datetime.now()
        log.info(f"【{self._client_type.value}】所有站点检索完成，有效资源数：%s，总耗时 %s 秒"
                 % (len(ret_array), (end_time - start_time).seconds))
        self.progress.update(ptype='search', text="所有站点检索完成，有效资源数：%s，总耗时 %s 秒"
                                                  % (len(ret_array), (end_time - start_time).seconds),
                             value=100)
        return ret_array
