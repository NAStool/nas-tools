import re
import xml.dom.minidom
from abc import ABCMeta, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures._base import as_completed

import log
from config import TORRENT_SEARCH_PARAMS
from pt.torrent import Torrent
from rmt.media import Media
from rmt.metainfo import MetaInfo
from utils.functions import str_filesize, tag_value
from utils.http_utils import RequestUtils
from utils.sqls import get_config_search_rule
from utils.types import MediaType


class IIndexer(metaclass=ABCMeta):
    media = None
    index_type = None
    api_key = None
    __res_type = None
    __space_chars = r"\.|-|/|:|："

    def __init__(self):
        self.media = Media()
        self.init_config()
        self.init_res_type()

    def init_res_type(self):
        res_type = get_config_search_rule()
        if res_type:
            if res_type[0][0] or res_type[0][1] or res_type[0][2] or res_type[0][3]:
                include = str(res_type[0][0]).split("\n")
                exclude = str(res_type[0][1]).split("\n")
                note = str(res_type[0][2]).split("\n")
                self.__res_type = {"include": include, "exclude": exclude, "note": note, "size": res_type[0][3]}
            else:
                self.__res_type = None

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

    def search_by_keyword(self, key_word, filter_args: dict, match_type=0, match_words=None):
        """
        根据关键字调用 Index API 检索
        :param key_word: 检索的关键字，不能为空
        :param filter_args: 过滤条件，对应属性为空则不过滤，{"season":季, "episode":集, "year":年, "type":类型, "site":站点,
                            "":, "restype":质量, "pix":分辨率, "sp_state":促销状态, "key":其它关键字}
                            sp_state: 为UL DL，* 代表不关心，
        :param match_type: 匹配模式：0-识别并模糊匹配；1-识别并精确匹配；2-不识别匹配
        :param match_words: 匹配的关键字，为空时等于key_word
        :return: 命中的资源媒体信息列表
        """
        if not key_word:
            return []
        if not match_words:
            match_words = [key_word]

        indexers = self.get_indexers()
        if not self.api_key or not indexers:
            log.error(f"【{self.index_type}】配置信息有误！")
            return []
        # 多线程检索
        if filter_args and filter_args.get("site"):
            log.info(f"【{self.index_type}】开始检索 %s，站点：%s ..." % (key_word, filter_args.get("site")))
        else:
            log.info(f"【{self.index_type}】开始并行检索 %s，线程数：%s ..." % (key_word, len(indexers)))
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
                                   match_words)
            all_task.append(task)
        ret_array = []
        for future in as_completed(all_task):
            result = future.result()
            if result:
                ret_array = ret_array + result
        log.info(f"【{self.index_type}】所有API检索完成，有效资源数：%s" % len(ret_array))
        return ret_array

    def __search(self, order_seq, indexer, key_word, filter_args: dict, match_type, match_words):
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
        log.info(f"【{self.index_type}】开始检索Indexer：{indexer_name} ...")
        # 特殊符号处理
        search_word = re.sub(r'\s+', ' ', re.sub(r"%s" % self.__space_chars, ' ', key_word)).strip()
        api_url = f"{indexer_url}?apikey={self.api_key}&t=search&q={search_word}"
        result_array = self.__parse_torznabxml(api_url)
        if len(result_array) == 0:
            log.warn(f"【{self.index_type}】{indexer_name} 未检索到资源")
            return []
        else:
            log.warn(f"【{self.index_type}】{indexer_name} 返回数据：{len(result_array)}")
        # 从检索结果中匹配符合资源条件的记录
        index_sucess = 0
        for item in result_array:
            # 获取属性
            torrent_name = item.get('title')
            enclosure = item.get('enclosure')
            size = item.get('size')
            description = item.get('description')
            seeders = item.get('seeders')
            peers = item.get('peers')
            page_url = item.get('page_url')
            uploadvolumefactor = float(item.get('uploadvolumefactor'))
            downloadvolumefactor = float(item.get('downloadvolumefactor'))

            # 合匹配模式下，过滤掉做种数为0的
            if match_type == 1 and not seeders:
                log.info(f"【{self.index_type}】{torrent_name} 做种数为0")
                continue

            # 检查资源类型
            if match_type == 1:
                match_flag, res_order = Torrent.check_resouce_types(torrent_name, description, self.__res_type)
                if not match_flag:
                    log.info(f"【{self.index_type}】{torrent_name} 不符合过滤规则")
                    continue
            else:
                res_order = Torrent.check_res_order(torrent_name, description, self.__res_type)

            # 识别种子名称
            meta_info = MetaInfo(title=torrent_name, subtitle=description)
            if not meta_info.get_name():
                continue

            if meta_info.type == MediaType.TV and filter_args.get("type") == MediaType.MOVIE:
                log.info(f"【{self.index_type}】{torrent_name} 是 {meta_info.type.value}，不匹配类型：{filter_args.get('type').value}")
                continue

            # 有高级过滤条件时，先过滤一遍
            if filter_args.get("restype"):
                restype_re = TORRENT_SEARCH_PARAMS["restype"].get(filter_args.get("restype"))
                if not meta_info.resource_type:
                    continue
                if restype_re and not re.search(r"%s" % restype_re, meta_info.resource_type, re.IGNORECASE):
                    log.info(f"【{self.index_type}】{torrent_name} 不符合质量条件：{filter_args.get('restype')}")
                    continue
            if filter_args.get("pix"):
                restype_re = TORRENT_SEARCH_PARAMS["pix"].get(filter_args.get("pix"))
                if not meta_info.resource_pix:
                    continue
                if restype_re and not re.search(r"%s" % restype_re, meta_info.resource_pix, re.IGNORECASE):
                    log.info(f"【{self.index_type}】{torrent_name} 不符合分辨率条件：{filter_args.get('pix')}")
                    continue
            if filter_args.get("sp_state"):
                sp_state = filter_args.get("sp_state")
                ul_factor, dl_factor = sp_state.split()

                if ul_factor not in ("*", str(uploadvolumefactor)):
                    log.info(f"【{self.index_type}】{torrent_name} 不符合促销条件：上传因子 {ul_factor}")
                    continue
                if dl_factor not in ("*", str(downloadvolumefactor)):
                    log.info(f"【{self.index_type}】{torrent_name} 不符合促销条件：下载因子 {dl_factor}")
                    continue
            if filter_args.get("key") and not re.search(r"%s" % filter_args.get("key"), torrent_name, re.IGNORECASE):
                log.info(f"【{self.index_type}】{torrent_name} 不符合关键字：{filter_args.get('key')}")
                continue

            # 识别媒体信息
            if match_type != 2:
                media_info = self.media.get_media_info(title=torrent_name, subtitle=description)
                if not media_info or not media_info.tmdb_info:
                    log.debug(f"【{self.index_type}】{torrent_name} 未识别到媒体信息")
                    continue

                # 类型
                if filter_args.get("type"):
                    if filter_args.get("type") == MediaType.TV and media_info.type == MediaType.MOVIE \
                            or filter_args.get("type") == MediaType.MOVIE and media_info.type == MediaType.TV:
                        log.info(f"【{self.index_type}】{torrent_name} 是 {media_info.type.value}，不匹配类型：{filter_args.get('type').value}")
                        continue

                # 名称是否匹配
                if match_type == 1:
                    # 全匹配模式，名字需要完全一样才下载
                    match_flag = False
                    for match_word in match_words:
                        if str(match_word).upper() == str(media_info.title).upper() \
                                or str(match_word).upper() == str(media_info.original_title).upper():
                            match_flag = True
                            break
                    if not match_flag:
                        log.info(f"【{self.index_type}】{media_info.type.value}：{media_info.title} 不匹配名称：{match_words}")
                        continue
                else:
                    # 非全匹配模式，找出来的全要，不过滤名称
                    pass

                # 判断文件大小是否匹配，只针对电影
                if match_type == 1:
                    if not Torrent.is_torrent_match_size(media_info, self.__res_type, size):
                        log.info(
                            f"【{self.index_type}】{media_info.type.value}：{media_info.get_title_string()} {str_filesize(size)} 不符合大小要求")
                        continue
            else:
                media_info = meta_info

            # 检查标题是否匹配季、集、年
            if not Torrent.is_torrent_match_sey(media_info, filter_args.get("season"), filter_args.get("episode"),
                                                filter_args.get("year")):
                log.info(
                    f"【{self.index_type}】{media_info.type.value}：{media_info.get_title_string()} {media_info.get_season_episode_string()} 不匹配季/集/年份")
                continue

            # 匹配到了
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
                index_sucess = index_sucess + 1
                ret_array.append(media_info)
        # 循环结束
        log.info(f"【{self.index_type}】{indexer_name} 共检索到 {index_sucess} 条有效资源")
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
            ret = RequestUtils().get_res(url)
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
