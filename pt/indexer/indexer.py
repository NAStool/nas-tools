import datetime
import xml.dom.minidom
from abc import ABCMeta, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures._base import as_completed

import log
from pt.filterrules import FilterRule
from pt.torrent import Torrent
from rmt.media import Media
from rmt.meta.metabase import MetaBase
from rmt.metainfo import MetaInfo
from utils.commons import ProcessHandler
from utils.functions import tag_value, str_filesize, handler_special_chars
from utils.http_utils import RequestUtils
from utils.types import MediaType


class IIndexer(metaclass=ABCMeta):
    media = None
    index_type = None
    api_key = None
    host = None
    filterrule = None
    __reverse_title_sites = ['keepfriends']
    __invalid_description_sites = ['tjupt']

    def __init__(self):
        self.media = Media()
        self.filterrule = FilterRule()
        self.init_config()

    @abstractmethod
    def init_config(self):
        """
        初始化配置
        """
        pass

    @abstractmethod
    def get_status(self):
        """
        检查连通性
        """
        pass

    @abstractmethod
    def get_indexers(self):
        """
        :return:  indexer 信息 [(indexerId, indexerName, url)]
        """
        pass

    def search_by_keyword(self, key_word, filter_args: dict, match_type=0, match_media: MetaBase = None):
        """
        根据关键字调用 Index API 检索
        :param key_word: 检索的关键字，不能为空
        :param filter_args: 过滤条件，对应属性为空则不过滤，{"season":季, "episode":集, "year":年, "type":类型, "site":站点,
                            "":, "restype":质量, "pix":分辨率, "sp_state":促销状态, "key":其它关键字}
                            sp_state: 为UL DL，* 代表不关心，
        :param match_type: 匹配模式：0-识别并模糊匹配；1-识别并精确匹配；2-不识别匹配
        :param match_media: 需要匹配的媒体信息
        :return: 命中的资源媒体信息列表
        """
        if not key_word:
            return []

        indexers = self.get_indexers()
        if not self.api_key or not indexers:
            log.error(f"【{self.index_type}】配置信息有误！")
            return []
        # 计算耗时
        start_time = datetime.datetime.now()
        if filter_args and filter_args.get("site"):
            log.info(f"【{self.index_type}】开始检索 %s，站点：%s ..." % (key_word, filter_args.get("site")))
            ProcessHandler().update(text="开始检索 %s，站点：%s ..." % (key_word, filter_args.get("site")))
        else:
            log.info(f"【{self.index_type}】开始并行检索 %s，线程数：%s ..." % (key_word, len(indexers)))
            ProcessHandler().update(text="开始并行检索 %s，线程数：%s ..." % (key_word, len(indexers)))
        executor = ThreadPoolExecutor(max_workers=len(indexers))
        all_task = []
        order_seq = 100
        for index in indexers:
            order_seq = order_seq - 1
            task = executor.submit(self.__search,
                                   order_seq,
                                   index,
                                   key_word,
                                   filter_args,
                                   match_type,
                                   match_media)
            all_task.append(task)
        ret_array = []
        finish_count = 0
        for future in as_completed(all_task):
            result = future.result()
            finish_count += 1
            ProcessHandler().update(value=round(100 * (finish_count / len(all_task))))
            if result:
                ret_array = ret_array + result
        # 计算耗时
        end_time = datetime.datetime.now()
        log.info(f"【{self.index_type}】所有站点检索完成，有效资源数：%s，总耗时 %s 秒"
                 % (len(ret_array), (end_time - start_time).seconds))
        ProcessHandler().update(text="所有站点检索完成，有效资源数：%s，总耗时 %s 秒"
                                     % (len(ret_array), (end_time - start_time).seconds),
                                value=100)
        return ret_array

    def __search(self, order_seq, indexer, key_word, filter_args: dict, match_type, match_media: MetaBase):
        """
        根据关键字多线程检索
        """
        if not indexer or not key_word:
            return None
        if filter_args is None:
            filter_args = {}
        ret_array = []
        indexer_name = indexer[1]
        indexer_url = indexer[2]

        if filter_args.get("site") and indexer_name not in filter_args.get("site"):
            return []
        # 计算耗时
        start_time = datetime.datetime.now()
        log.info(f"【{self.index_type}】开始检索Indexer：{indexer_name} ...")
        # 特殊符号处理
        search_word = handler_special_chars(text=key_word, replace_word=" ", allow_space=True)
        api_url = f"{indexer_url}?apikey={self.api_key}&t=search&q={search_word}"
        result_array = self.__parse_torznabxml(api_url)
        if len(result_array) == 0:
            log.warn(f"【{self.index_type}】{indexer_name} 未检索到数据")
            ProcessHandler().update(text=f"{indexer_name} 未检索到数据")
            return []
        else:
            log.warn(f"【{self.index_type}】{indexer_name} 返回数据：{len(result_array)}")
        # 从检索结果中匹配符合资源条件的记录
        index_sucess = 0
        index_rule_fail = 0
        index_match_fail = 0
        for item in result_array:
            # 这此站标题和副标题相反
            if indexer_name in self.__reverse_title_sites:
                torrent_name = item.get('description')
                description = item.get('title')
            else:
                torrent_name = item.get('title')
                description = item.get('description')
            # 这些站副标题无意义，需要去除
            if indexer_name in self.__invalid_description_sites:
                description = ""
            enclosure = item.get('enclosure')
            size = item.get('size')
            seeders = item.get('seeders')
            peers = item.get('peers')
            page_url = item.get('page_url')
            uploadvolumefactor = float(item.get('uploadvolumefactor'))
            downloadvolumefactor = float(item.get('downloadvolumefactor'))

            # 合匹配模式下，过滤掉做种数为0的
            if match_type == 1 and not seeders:
                log.info(f"【{self.index_type}】{torrent_name} 做种数为0")
                continue

            # 识别种子名称
            meta_info = MetaInfo(title=torrent_name, subtitle=description)
            if not meta_info.get_name():
                log.info(f"【{self.index_type}】{torrent_name} 无法识别到名称")
                index_match_fail += 1
                continue
            # 大小及促销
            meta_info.set_torrent_info(size=size,
                                       upload_volume_factor=uploadvolumefactor,
                                       download_volume_factor=downloadvolumefactor)

            if meta_info.type == MediaType.TV and filter_args.get("type") == MediaType.MOVIE:
                log.info(
                    f"【{self.index_type}】{torrent_name} 是 {meta_info.type.value}，不匹配类型：{filter_args.get('type').value}")
                continue

            # 检查订阅过滤规则匹配
            if filter_args.get("rule"):
                match_flag, res_order, _ = self.filterrule.check_rules(meta_info=meta_info,
                                                                       rolegroup=filter_args.get("rule"))
                if not match_flag:
                    log.info(f"【{self.index_type}】{torrent_name} 大小：{str_filesize(meta_info.size)} 促销：{meta_info.get_volume_factor_string()} 不符合订阅过滤规则")
                    index_rule_fail += 1
                    continue
            # 使用默认规则
            else:
                match_flag, res_order, _ = self.filterrule.check_rules(meta_info=meta_info)
                if match_type == 1 and not match_flag:
                    log.info(f"【{self.index_type}】{torrent_name} 大小：{str_filesize(meta_info.size)} 促销：{meta_info.get_volume_factor_string()} 不符合默认过滤规则")
                    index_rule_fail += 1
                    continue

            # 有高级过滤条件时，先过滤一遍
            if not Torrent.check_torrent_filter(meta_info=meta_info,
                                                filter_args=filter_args,
                                                uploadvolumefactor=uploadvolumefactor,
                                                downloadvolumefactor=downloadvolumefactor):
                log.info(f"【{self.index_type}】{torrent_name} 不符合高级过滤条件")
                index_rule_fail += 1
                continue

            # 识别媒体信息
            if match_type != 2:
                media_info = self.media.get_media_info(title=torrent_name, subtitle=description, chinese=False)
                if not media_info or not media_info.tmdb_info:
                    log.info(f"【{self.index_type}】{torrent_name} 以名称 {media_info.get_name()} 未匹配到媒体信息")
                    index_match_fail += 1
                    continue

                # 类型
                if filter_args.get("type"):
                    if filter_args.get("type") == MediaType.TV and media_info.type == MediaType.MOVIE \
                            or filter_args.get("type") == MediaType.MOVIE and media_info.type == MediaType.TV:
                        log.info(
                            f"【{self.index_type}】{torrent_name} 是 {media_info.type.value}，不是 {filter_args.get('type').value}")
                        index_rule_fail += 1
                        continue

                # 名称是否匹配
                if match_type == 1:
                    # 全匹配模式，TMDBID需要完全一样才匹配
                    if match_media and media_info.tmdb_id != match_media.tmdb_id:
                        log.info(f"【{self.index_type}】{media_info.org_string} 识别为 {media_info.type.value} {media_info.get_title_string()} 不匹配")
                        index_match_fail += 1
                        continue
                    # 统一标题和海报
                    media_info.title = match_media.title
                    media_info.fanart_image = match_media.get_fanart_image()
                else:
                    # 非全匹配模式，找出来的全要，不过滤名称
                    pass

            else:
                media_info = meta_info

            # 检查标题是否匹配季、集、年
            if not Torrent.is_torrent_match_sey(media_info, filter_args.get("season"), filter_args.get("episode"),
                                                filter_args.get("year")):
                log.info(
                    f"【{self.index_type}】{media_info.org_string} 识别为 {media_info.type.value} {media_info.get_title_string()} {media_info.get_season_episode_string()} 不匹配季/集/年份")
                index_match_fail += 1
                continue

            # 匹配到了
            log.info(f"【{self.index_type}】{torrent_name} 匹配成功")
            media_info.set_torrent_info(site=indexer_name,
                                        site_order=order_seq,
                                        enclosure=enclosure,
                                        res_order=res_order,
                                        size=size,
                                        seeders=seeders,
                                        peers=peers,
                                        description=description,
                                        page_url=page_url,
                                        upload_volume_factor=uploadvolumefactor,
                                        download_volume_factor=downloadvolumefactor)
            if media_info not in ret_array:
                index_sucess += 1
                ret_array.append(media_info)
        # 循环结束
        # 计算耗时
        end_time = datetime.datetime.now()
        log.info(
            f"【{self.index_type}】{indexer_name} 共检索到 {len(result_array)} 条数据，过滤 {index_rule_fail}，不匹配 {index_match_fail}，有效资源 {index_sucess}，耗时 {(end_time - start_time).seconds} 秒")
        ProcessHandler().update(
            text=f"{indexer_name} 共检索到 {len(result_array)} 条数据，过滤 {index_rule_fail}，不匹配 {index_match_fail}，有效资源 {index_sucess}，耗时 {(end_time - start_time).seconds} 秒")
        return ret_array

    @staticmethod
    def __parse_torznabxml(url):
        """
        从torznab xml中解析种子信息
        :param url: URL地址
        :return: 解析出来的种子信息列表
        """
        if not url:
            return []
        try:
            ret = RequestUtils(timeout=10).get_res(url)
        except Exception as e2:
            log.console(str(e2))
            return []
        if not ret:
            return []
        xmls = ret.text
        if not xmls:
            return []

        torrents = []
        try:
            # 解析XML
            dom_tree = xml.dom.minidom.parseString(xmls)
            root_node = dom_tree.documentElement
            items = root_node.getElementsByTagName("item")
            for item in items:
                try:
                    # indexer id
                    indexer_id = tag_value(item, "jackettindexer", "id",
                                           default=tag_value(item, "prowlarrindexer", "id", ""))
                    # indexer
                    indexer = tag_value(item, "jackettindexer", default=tag_value(item, "prowlarrindexer", default=""))

                    # 标题
                    title = tag_value(item, "title", default="")
                    if not title:
                        continue
                    # 种子链接
                    enclosure = tag_value(item, "enclosure", "url", default="")
                    if not enclosure:
                        continue
                    # 描述
                    description = tag_value(item, "description", default="")
                    # 种子大小
                    size = tag_value(item, "size", default=0)
                    # 种子页面
                    page_url = tag_value(item, "comments", default="")

                    # 做种数
                    seeders = 0
                    # 下载数
                    peers = 0
                    # 是否免费
                    freeleech = False
                    # 下载因子
                    downloadvolumefactor = 1.0
                    # 上传因子
                    uploadvolumefactor = 1.0

                    torznab_attrs = item.getElementsByTagName("torznab:attr")
                    for torznab_attr in torznab_attrs:
                        name = torznab_attr.getAttribute('name')
                        value = torznab_attr.getAttribute('value')
                        if name == "seeders":
                            seeders = value
                        if name == "peers":
                            peers = value
                        if name == "downloadvolumefactor":
                            downloadvolumefactor = value
                            if float(downloadvolumefactor) == 0:
                                freeleech = True
                        if name == "uploadvolumefactor":
                            uploadvolumefactor = value

                    tmp_dict = {'indexer_id': indexer_id, 'indexer': indexer,
                                'title': title, 'enclosure': enclosure, 'description': description, 'size': size,
                                'seeders': seeders, 'peers': peers,
                                'freeleech': freeleech,
                                'downloadvolumefactor': downloadvolumefactor,
                                'uploadvolumefactor': uploadvolumefactor,
                                "page_url": page_url}
                    torrents.append(tmp_dict)
                except Exception as e:
                    print(f"{e}")
                    continue
        except Exception as e2:
            print(f"{e2}")
            pass

        return torrents
