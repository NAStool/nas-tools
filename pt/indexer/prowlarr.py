import re

import requests

import log
from config import Config, TORRENT_SEARCH_PARAMS
from pt.indexer.indexer import IIndexer
from pt.torrent import Torrent
from rmt.media import Media
from rmt.metainfo import MetaInfo
from utils.functions import str_filesize
from utils.sqls import get_config_search_rule
from utils.types import MediaType


class Prowlarr(IIndexer):
    media = None
    __api_key = None
    __host = None
    __res_type = None
    __space_chars = r"\.|-|/|:|："

    def __init__(self):
        self.media = Media()
        self.init_config()

    def init_config(self):
        config = Config()
        prowlarr = config.get_config('prowlarr')
        if prowlarr:
            self.__api_key = prowlarr.get('api_key')
            self.__host = prowlarr.get('host')
            if not self.__host.startswith('http://') and not self.__host.startswith('https://'):
                self.__host = "http://" + self.__host
            if not self.__host.endswith('/'):
                self.__host = self.__host + "/"
            res_type = get_config_search_rule()
            if res_type:
                if res_type[0][0] or res_type[0][1] or res_type[0][2] or res_type[0][3]:
                    include = str(res_type[0][0]).split("\n")
                    exclude = str(res_type[0][1]).split("\n")
                    note = str(res_type[0][2]).split("\n")
                    self.__res_type = {"include": include, "exclude": exclude, "note": note, "size": res_type[0][3]}
                else:
                    self.__res_type = None

    def get_status(self):
        """
        检查连通性
        :return: True、False
        """
        if not self.__api_key or not self.__host:
            return False
        api_url = "%sapi/v1/search?apikey=%s&Query=%s" % (self.__host, self.__api_key, "ASDFGHJKL")
        res = requests.get(api_url, timeout=10)
        if res and res.status_code == 200:
            return True
        return False

    def search_by_keyword(self, key_word, filter_args: dict, match_type=0, match_words=None):
        """
        根据关键字调用 prowlarr API 检索
        :param key_word: 检索的关键字，不能为空
        :param filter_args: 过滤条件，对应属性为空则不过滤，{"season":季, "episode":集, "year":年, "type":类型,
                            "site":站点, "":, "restype":质量, "pix":分辨率, "free":免费, "key":其它关键字}
        :param match_type: 匹配模式：0-识别并模糊匹配；1-识别并精确匹配；2-不识别匹配
        :param match_words: 匹配的关键字，为空时等于key_word
        :return: 命中的资源媒体信息列表
        """
        if not key_word:
            return []
        if filter_args is None:
            filter_args = {}
        if not match_words:
            match_words = [key_word]
        if not self.__api_key or not self.__host:
            log.error("【PROWLARR】Prowlarr配置信息有误！")
            return []
        ret_array = []
        # 需要处理掉特殊符号
        search_word = re.sub(r'\s+', ' ', re.sub(r"%s" % self.__space_chars, ' ', key_word)).strip()
        api_url = "%sapi/v1/search?apikey=%s&Query=%s" % (self.__host, self.__api_key, search_word)
        result_array = self.__parse_prowlarrjson(api_url)
        if len(result_array) == 0:
            log.warn("【PROWLARR】%s 未检索到任何资源" % search_word)
            return []
        else:
            log.warn("【PROWLARR】返回数据：%s" % len(result_array))
        # 从检索结果中匹配符合资源条件的记录
        index_sucess = 0
        for item in result_array:
            indexer_name = item.get('indexer')
            indexerId = 100 - item.get('indexerId')
            torrent_name = item.get('title')
            enclosure = item.get('enclosure')
            size = item.get('size')
            description = item.get('description')
            seeders = item.get('seeders')
            peers = item.get('peers')
            page_url = item.get('page_url')
            freeleech = item.get('freeleech')

            # 全匹配模式下，过滤掉做种数为0的
            if match_type == 1 and not seeders:
                log.info("【PROWLARR】%s 做种数为0，跳过..." % torrent_name)
                continue

            # 检查资源类型
            if match_type == 1:
                match_flag, res_order = Torrent.check_resouce_types(torrent_name, description, self.__res_type)
                if not match_flag:
                    log.info("【PROWLARR】%s 不符合过滤条件" % torrent_name)
                    continue
            else:
                res_order = Torrent.check_res_order(torrent_name, description, self.__res_type)

            # 识别种子名称
            meta_info = MetaInfo(torrent_name)
            if not meta_info.get_name():
                continue
            if meta_info.type not in [MediaType.MOVIE, MediaType.UNKNOWN] and filter_args.get("type") == MediaType.MOVIE:
                log.info("【PROWLARR】%s 是 %s，类型不匹配" % (torrent_name, meta_info.type.value))
                continue

            # 有高级过滤条件时，先过滤一遍
            if filter_args.get("restype"):
                restype_re = TORRENT_SEARCH_PARAMS["restype"].get(filter_args.get("restype"))
                if not meta_info.resource_type:
                    continue
                if restype_re and not re.search(r"%s" % restype_re, meta_info.resource_type, re.IGNORECASE):
                    log.info("【JACKETT】%s 不符合质量条件：%s" % (torrent_name, filter_args.get("restype")))
                    continue
            if filter_args.get("pix"):
                restype_re = TORRENT_SEARCH_PARAMS["pix"].get(filter_args.get("pix"))
                if not meta_info.resource_pix:
                    continue
                if restype_re and not re.search(r"%s" % restype_re, meta_info.resource_pix, re.IGNORECASE):
                    log.info("【JACKETT】%s 不符合分辨率条件：%s" % (torrent_name, filter_args.get("pix")))
                    continue
            if filter_args.get("free") and not freeleech:
                log.info("【JACKETT】%s 不符合免费条件" % torrent_name)
                continue
            if filter_args.get("key") and not re.search(r"%s" % filter_args.get("key"), torrent_name,
                                                        re.IGNORECASE):
                log.info("【JACKETT】%s 不符合关键字：%s" % (torrent_name, filter_args.get("key")))
                continue

            # 识别媒体信息
            if match_type != 2:
                media_info = self.media.get_media_info(title=torrent_name, subtitle=description)
                if not media_info or not media_info.tmdb_info:
                    log.info("【PROWLARR】%s 未查询到媒体信息" % torrent_name)
                    continue
                # 类型
                if filter_args.get("type") and media_info.type != filter_args.get("type"):
                    log.info("【PROWLARR】%s 是 %s，类型不匹配" % (torrent_name, media_info.type.value))
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
                        log.info("【PROWLARR】%s：%s 不匹配名称：%s" % (media_info.type.value, media_info.title, match_words))
                        continue
                else:
                    # 非全匹配模式，种子中或者名字中有关键字就行
                    match_flag = False
                    for match_word in match_words:
                        if str(match_word).upper() in str(media_info.get_title_string()).upper() \
                                or str(match_word).upper() in str(media_info.original_title).upper() \
                                or str(match_word).upper() in str(media_info.org_string).upper():
                            match_flag = True
                            break
                    if not match_flag:
                        log.info("【PROWLARR】%s：%s %s 不匹配名称：%s" % (
                            media_info.type.value, media_info.org_string, media_info.get_title_string(), match_words))
                        continue

                # 判断文件大小是否匹配，只针对电影
                if match_type == 1:
                    if not Torrent.is_torrent_match_size(media_info, self.__res_type, size):
                        log.info("【PROWLARR】%s：%s %s 不符合大小要求" % (
                            media_info.type.value, media_info.get_title_string(), str_filesize(size)))
                        continue
            else:
                media_info = meta_info

            # 检查标题是否匹配季、集、年
            if not Torrent.is_torrent_match_sey(media_info, filter_args.get("season"), filter_args.get("episode"), filter_args.get("year")):
                log.info("【PROWLARR】%s：%s %s 不匹配季/集/年份" % (
                    media_info.type.value, media_info.get_title_string(), media_info.get_season_episode_string()))
                continue

            # 匹配到了
            media_info.set_torrent_info(site=indexer_name,
                                        site_order=indexerId,
                                        enclosure=enclosure,
                                        res_order=res_order,
                                        size=size,
                                        seeders=seeders,
                                        peers=peers,
                                        description=description,
                                        page_url=page_url,
                                        freeleech=freeleech)
            if media_info not in ret_array:
                index_sucess = index_sucess + 1
                ret_array.append(media_info)
        # 循环结束
        log.info("【PROWLARR】共检索到 %s 条有效资源" % index_sucess)
        return ret_array

    @staticmethod
    def __parse_prowlarrjson(url):
        """
        解析Prowlarr返回的Json
        :param url: URL地址
        :return: 解析出来的种子信息列表
        """
        ret_array = []
        if not url:
            return ret_array
        try:
            ret = requests.get(url, timeout=30)
        except Exception as e2:
            log.console(str(e2))
            return []
        if ret:
            results = ret.json()
            for item in results:
                title = item.get("title")
                enclosure = item.get("downloadUrl")
                description = item.get("commentUrl")
                page_url = item.get("infoUrl")
                size = item.get("size")
                seeders = item.get("seeders")
                peers = item.get("leechers")
                indexer = item.get("indexer")
                indexerId = item.get("indexerId")
                indexerFlags = item.get("indexerFlags")
                if "freeleech" in indexerFlags:
                    freeleech = True
                else:
                    freeleech = False
                tmp_dict = {'title': title, 'enclosure': enclosure, 'description': description, 'size': size,
                            'seeders': seeders, 'peers': peers, 'indexer': indexer, 'indexerId': indexerId,
                            'page_url': page_url, "freeleech": freeleech}
                ret_array.append(tmp_dict)

        return ret_array
