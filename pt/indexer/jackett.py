import re
from xml.dom.minidom import parse
import xml.dom.minidom
import requests
import log
from config import Config
from pt.torrent import Torrent
from rmt.media import Media
from rmt.metainfo import MetaInfo
from utils.functions import str_filesize
from utils.sqls import get_config_search_rule
from utils.types import MediaType
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures._base import as_completed


class Jackett:
    torrent = None
    media = None
    __api_key = None
    __indexers = []
    __res_type = None

    def __init__(self):
        self.torrent = Torrent()
        self.media = Media()
        self.init_config()

    def init_config(self):
        config = Config()
        jackett = config.get_config('jackett')
        if jackett:
            self.__api_key = jackett.get('api_key')
            self.__indexers = jackett.get('indexers')
            if not isinstance(self.__indexers, list):
                self.__indexers = [self.__indexers]
            res_type = get_config_search_rule()
            if res_type:
                if res_type[0][0] or res_type[0][1] or res_type[0][2] or res_type[0][3]:
                    include = str(res_type[0][0]).split("\n")
                    exclude = str(res_type[0][1]).split("\n")
                    note = str(res_type[0][2]).split("\n")
                    self.__res_type = {"include": include, "exclude": exclude, "note": note, "size": res_type[0][3]}
                else:
                    self.__res_type = None

    # 根据关键字调用 Jackett API 检索
    def search_by_keyword(self, key_word, s_num, e_num, year, mtype, whole_word):
        if not key_word:
            return []
        if not self.__api_key or not self.__indexers:
            log.error("【JACKETT】Jackett配置信息有误！")
            return []
        # 多线程检索
        log.info("【JACKETT】开始并行检索 %s，线程数：%s" % (key_word, len(self.__indexers)))
        executor = ThreadPoolExecutor(max_workers=len(self.__indexers))
        all_task = []
        order_seq = 100
        for index in self.__indexers:
            order_seq = order_seq - 1
            task = executor.submit(self.search, order_seq, index, key_word, s_num, e_num, year, mtype,
                                   whole_word)
            all_task.append(task)
        ret_array = []
        for future in as_completed(all_task):
            result = future.result()
            if result:
                ret_array = ret_array + result
        log.info("【JACKETT】所有API检索完成，有效资源数：%s" % len(ret_array))
        return ret_array

    # 检索一个Indexer
    def search(self, order_seq, index, key_word, s_num, e_num, year, mtype, whole_word=False):
        if not index or not key_word:
            return None
        ret_array = []
        indexer_name = re.search(r'/indexers/([a-zA-Z0-9]+)/results/', index)
        if indexer_name:
            indexer_name = indexer_name.group(1)
        log.info("【JACKETT】开始检索Indexer：%s ..." % indexer_name)
        # 传给Jackett的需要处理掉特殊符号
        search_word = key_word.replace("：", " ")
        api_url = "%sapi?apikey=%s&t=search&q=%s" % (index, self.__api_key, search_word)
        result_array = self.parse_jackettxml(api_url)
        if len(result_array) == 0:
            log.warn("【JACKETT】%s 未检索到资源" % indexer_name)
            return []
        else:
            log.warn("【JACKETT】返回数据：%s" % len(result_array))
        # 从检索结果中匹配符合资源条件的记录
        index_sucess = 0
        for item in result_array:
            torrent_name = item.get('title')
            enclosure = item.get('enclosure')
            size = item.get('size')
            description = item.get('description')
            seeders = item.get('seeders')
            peers = item.get('peers')

            # 检查资源类型
            match_flag, res_order = self.torrent.check_resouce_types(torrent_name, description, self.__res_type)
            if not match_flag:
                log.info("【JACKETT】%s 不符合过滤条件" % torrent_name)
                continue

            # 识别种子名称
            meta_info = MetaInfo(torrent_name)
            if mtype and meta_info.type != MediaType.MOVIE and mtype == MediaType.MOVIE:
                log.info("【JACKETT】%s 类型不匹配" % torrent_name)
                continue

            # 识别媒体信息
            media_info = self.media.get_media_info(title=torrent_name, subtitle=description)
            if not media_info or not media_info.tmdb_info:
                log.info("【JACKETT】%s 未检索到媒体信息" % torrent_name)
                continue

            # 类型
            if mtype and media_info.type != mtype:
                log.info("【JACKETT】%s 类型不匹配" % torrent_name)
                continue

            # 名称是否匹配
            if whole_word:
                # 全匹配模式，名字需要完全一样才下载
                if str(key_word).upper() == str(media_info.title).upper():
                    match_flag = True
                else:
                    match_flag = False
                    log.info("【JACKETT】%s：%s 不匹配名称：%s" % (media_info.type.value, media_info.title, key_word))
            else:
                # 非全匹配模式，种子中或者名字中有关键字就行
                if str(key_word).upper() in str(media_info.get_title_string()).upper() \
                        or str(key_word).upper() in str(media_info.org_string).upper():
                    match_flag = True
                else:
                    match_flag = False
                    log.info("【JACKETT】%s：%s %s 不匹配名称：%s" % (
                        media_info.type.value, media_info.org_string, media_info.get_title_string(), key_word))

            # 检查标题是否匹配剧集
            if match_flag:
                match_flag = self.torrent.is_torrent_match_sey(media_info, s_num, e_num, year)
                if not match_flag:
                    log.info("【JACKETT】%s：%s %s 不匹配季/集/年份" % (
                        media_info.type.value, media_info.get_title_string(), media_info.get_season_episode_string()))

            # 判断文件大小是否匹配，只针对电影
            if match_flag:
                match_flag = self.torrent.is_torrent_match_size(media_info, self.__res_type, size)
                if not match_flag:
                    log.info("【JACKETT】%s：%s %s 不符合大小要求" % (media_info.type.value, media_info.get_title_string(), str_filesize(size)))

            # 匹配到了
            if match_flag:
                media_info.set_torrent_info(site=indexer_name,
                                            site_order=order_seq,
                                            enclosure=enclosure,
                                            res_order=res_order,
                                            size=size,
                                            seeders=seeders,
                                            peers=peers,
                                            description=description)
                if media_info not in ret_array:
                    index_sucess = index_sucess + 1
                    ret_array.append(media_info)
            else:
                continue
        log.info("【JACKETT】%s 共检索到 %s 条有效资源" % (indexer_name, index_sucess))
        return ret_array

    # 解析Jackett的XML，返回标题及URL等
    @staticmethod
    def parse_jackettxml(url):
        ret_array = []
        if not url:
            return ret_array
        try:
            ret = requests.get(url, timeout=30)
        except Exception as e2:
            log.console(str(e2))
            return []
        if ret:
            ret_xml = ret.text
            try:
                # 解析XML
                dom_tree = xml.dom.minidom.parseString(ret_xml)
                rootNode = dom_tree.documentElement
                items = rootNode.getElementsByTagName("item")
                for item in items:
                    try:
                        # 标题
                        title = ""
                        tagNames = item.getElementsByTagName("title")
                        if tagNames:
                            firstChild = tagNames[0].firstChild
                            if firstChild:
                                title = firstChild.data
                        if not title:
                            continue
                        # 种子链接
                        enclosure = ""
                        tagNames = item.getElementsByTagName("enclosure")
                        if tagNames:
                            enclosure = tagNames[0].getAttribute("url")
                        if not enclosure:
                            continue
                        # 描述
                        description = ""
                        tagNames = item.getElementsByTagName("description")
                        if tagNames:
                            firstChild = tagNames[0].firstChild
                            if firstChild:
                                description = firstChild.data
                        # 种子大小
                        size = 0
                        tagNames = item.getElementsByTagName("size")
                        if tagNames:
                            firstChild = tagNames[0].firstChild
                            if firstChild:
                                size = firstChild.data
                        # 做种数
                        seeders = 0
                        # 下载数
                        peers = 0
                        torznab_attrs = item.getElementsByTagName("torznab:attr")
                        for torznab_attr in torznab_attrs:
                            name = torznab_attr.getAttribute('name')
                            value = torznab_attr.getAttribute('value')
                            if name == "seeders":
                                seeders = value
                            if name == "peers":
                                peers = value

                        tmp_dict = {'title': title, 'enclosure': enclosure, 'description': description, 'size': size,
                                    'seeders': seeders, 'peers': peers}
                        ret_array.append(tmp_dict)
                    except Exception as e:
                        log.console(str(e))
                        continue
            except Exception as e2:
                log.console(str(e2))
                return ret_array
        return ret_array
