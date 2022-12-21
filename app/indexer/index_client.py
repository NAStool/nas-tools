import datetime
import xml.dom.minidom
from abc import ABCMeta, abstractmethod

import log
from app.filter import Filter
from app.utils import DomUtils, RequestUtils, StringUtils
from app.helper import ProgressHelper
from app.media import MetaInfo, Media
from app.utils.exception_utils import ExceptionUtils
from app.utils.types import MediaType, SearchType


class IIndexClient(metaclass=ABCMeta):
    media = None
    index_type = None
    api_key = None
    host = None
    filter = None
    progress = None
    _reverse_title_sites = ['keepfriends']
    _invalid_description_sites = ['tjupt']

    def __init__(self):
        self.media = Media()
        self.filter = Filter()
        self.progress = ProgressHelper()
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

    @abstractmethod
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
        if filter_args is None:
            filter_args = {}
        # 不在设定搜索范围的站点过滤掉
        if filter_args.get("site") and indexer.name not in filter_args.get("site"):
            return []
        # 计算耗时
        start_time = datetime.datetime.now()
        log.info(f"【{self.index_type}】开始检索Indexer：{indexer.name} ...")
        # 特殊符号处理
        search_word = StringUtils.handler_special_chars(text=key_word, replace_word=" ", allow_space=True)
        api_url = f"{indexer.domain}?apikey={self.api_key}&t=search&q={search_word}"
        result_array = self.__parse_torznabxml(api_url)
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
                                              match_media=match_media,
                                              start_time=start_time)

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
            ExceptionUtils.exception_traceback(e2)
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
                    indexer_id = DomUtils.tag_value(item, "jackettindexer", "id",
                                                    default=DomUtils.tag_value(item, "prowlarrindexer", "id", ""))
                    # indexer
                    indexer = DomUtils.tag_value(item, "jackettindexer",
                                                 default=DomUtils.tag_value(item, "prowlarrindexer", default=""))

                    # 标题
                    title = DomUtils.tag_value(item, "title", default="")
                    if not title:
                        continue
                    # 种子链接
                    enclosure = DomUtils.tag_value(item, "enclosure", "url", default="")
                    if not enclosure:
                        continue
                    # 描述
                    description = DomUtils.tag_value(item, "description", default="")
                    # 种子大小
                    size = DomUtils.tag_value(item, "size", default=0)
                    # 种子页面
                    page_url = DomUtils.tag_value(item, "comments", default="")

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
                    # imdbid
                    imdbid = ""

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
                        if name == "imdbid":
                            imdbid = value

                    tmp_dict = {'indexer_id': indexer_id,
                                'indexer': indexer,
                                'title': title,
                                'enclosure': enclosure,
                                'description': description,
                                'size': size,
                                'seeders': seeders,
                                'peers': peers,
                                'freeleech': freeleech,
                                'downloadvolumefactor': downloadvolumefactor,
                                'uploadvolumefactor': uploadvolumefactor,
                                'page_url': page_url,
                                'imdbid': imdbid}
                    torrents.append(tmp_dict)
                except Exception as e:
                    ExceptionUtils.exception_traceback(e)
                    continue
        except Exception as e2:
            ExceptionUtils.exception_traceback(e2)
            pass

        return torrents

    def filter_search_results(self, result_array: list,
                              order_seq,
                              indexer,
                              filter_args: dict,
                              match_media,
                              start_time):
        """
        从检索结果中匹配符合资源条件的记录
        """
        ret_array = []
        index_sucess = 0
        index_rule_fail = 0
        index_match_fail = 0
        index_error = 0
        for item in result_array:
            # 这此站标题和副标题相反
            if indexer.id in self._reverse_title_sites:
                torrent_name = item.get('description')
                description = item.get('title')
            else:
                torrent_name = item.get('title')
                description = item.get('description')
            # 这些站副标题无意义，需要去除
            if indexer.id in self._invalid_description_sites:
                description = ""
            if not torrent_name:
                index_error += 1
                continue
            enclosure = item.get('enclosure')
            size = item.get('size')
            seeders = item.get('seeders')
            peers = item.get('peers')
            page_url = item.get('page_url')
            uploadvolumefactor = round(float(item.get('uploadvolumefactor')), 1) if item.get(
                'uploadvolumefactor') is not None else 1.0
            downloadvolumefactor = round(float(item.get('downloadvolumefactor')), 1) if item.get(
                'downloadvolumefactor') is not None else 1.0
            imdbid = item.get("imdbid")
            # 全匹配模式下，非公开站点，过滤掉做种数为0的
            if filter_args.get("seeders") and not indexer.public and str(seeders) == "0":
                log.info(f"【{self.index_type}】{torrent_name} 做种数为0")
                index_rule_fail += 1
                continue
            # 识别种子名称
            meta_info = MetaInfo(title=torrent_name, subtitle=description)
            if not meta_info.get_name():
                log.info(f"【{self.index_type}】{torrent_name} 无法识别到名称")
                index_match_fail += 1
                continue
            # 大小及促销等
            meta_info.set_torrent_info(size=size,
                                       imdbid=imdbid,
                                       upload_volume_factor=uploadvolumefactor,
                                       download_volume_factor=downloadvolumefactor)

            # 先过滤掉可以明确的类型
            if meta_info.type == MediaType.TV and filter_args.get("type") == MediaType.MOVIE:
                log.info(
                    f"【{self.index_type}】{torrent_name} 是 {meta_info.type.value}，不匹配类型：{filter_args.get('type').value}")
                index_rule_fail += 1
                continue
            # 检查订阅过滤规则匹配
            match_flag, res_order, match_msg = self.filter.check_torrent_filter(meta_info=meta_info,
                                                                                filter_args=filter_args,
                                                                                uploadvolumefactor=uploadvolumefactor,
                                                                                downloadvolumefactor=downloadvolumefactor)
            if not match_flag:
                log.info(f"【{self.index_type}】{match_msg}")
                index_rule_fail += 1
                continue
            # 识别媒体信息
            if not match_media:
                # 不过滤
                media_info = meta_info
            else:
                # 0-识别并模糊匹配；1-识别并精确匹配
                if meta_info.imdb_id \
                        and match_media.imdb_id \
                        and str(meta_info.imdb_id) == str(match_media.imdb_id):
                    # IMDBID匹配，合并媒体数据
                    media_info = self.media.merge_media_info(meta_info, match_media)
                else:
                    # 查询缓存
                    cache_info = self.media.get_cache_info(meta_info)
                    if match_media and str(cache_info.get("id")) == str(match_media.tmdb_id):
                        # 缓存匹配，合并媒体数据
                        media_info = self.media.merge_media_info(meta_info, match_media)
                    else:
                        # 重新识别
                        media_info = self.media.get_media_info(title=torrent_name, subtitle=description, chinese=False)
                        if not media_info:
                            log.warn(f"【{self.index_type}】{torrent_name} 识别媒体信息出错！")
                            index_error += 1
                            continue
                        elif not media_info.tmdb_info:
                            log.info(f"【{self.index_type}】{torrent_name} 识别为 {media_info.get_name()} 未匹配到媒体信息")
                            index_match_fail += 1
                            continue
                        # TMDBID是否匹配
                        if str(media_info.tmdb_id) != str(match_media.tmdb_id):
                            log.info(
                                f"【{self.index_type}】{torrent_name} 识别为 {media_info.type.value} {media_info.get_title_string()} 不匹配")
                            index_match_fail += 1
                            continue
                        # 合并媒体数据
                        media_info = self.media.merge_media_info(media_info, match_media)
                # 过滤类型
                if filter_args.get("type"):
                    if filter_args.get("type") == MediaType.TV and media_info.type == MediaType.MOVIE \
                            or filter_args.get("type") == MediaType.MOVIE and media_info.type == MediaType.TV:
                        log.info(
                            f"【{self.index_type}】{torrent_name} 是 {media_info.type.value}，不是 {filter_args.get('type').value}")
                        index_rule_fail += 1
                        continue
            # 检查标题是否匹配季、集、年
            if not self.filter.is_torrent_match_sey(media_info,
                                                    filter_args.get("season"),
                                                    filter_args.get("episode"),
                                                    filter_args.get("year")):
                log.info(
                    f"【{self.index_type}】{torrent_name} 识别为 {media_info.type.value} {media_info.get_title_string()} {media_info.get_season_episode_string()} 不匹配季/集/年份")
                index_match_fail += 1
                continue

            # 匹配到了
            log.info(
                f"【{self.index_type}】{torrent_name} {description} 识别为 {media_info.get_title_string()} {media_info.get_season_episode_string()} 匹配成功")
            media_info.set_torrent_info(site=indexer.name,
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
            else:
                index_rule_fail += 1
        # 循环结束
        # 计算耗时
        end_time = datetime.datetime.now()
        log.info(
            f"【{self.index_type}】{indexer.name} 共检索到 {len(result_array)} 条数据，过滤 {index_rule_fail}，不匹配 {index_match_fail}，错误 {index_error}，有效 {index_sucess}，耗时 {(end_time - start_time).seconds} 秒")
        self.progress.update(ptype='search',
                             text=f"{indexer.name} 共检索到 {len(result_array)} 条数据，过滤 {index_rule_fail}，不匹配 {index_match_fail}，错误 {index_error}，有效 {index_sucess}，耗时 {(end_time - start_time).seconds} 秒")
        return ret_array
