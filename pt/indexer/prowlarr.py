import re

import requests
import log
from config import Config
from pt.torrent import Torrent
from rmt.media import Media
from rmt.metainfo import MetaInfo
from utils.functions import str_filesize
from utils.sqls import get_config_search_rule
from utils.types import MediaType


class Prowlarr:
    torrent = None
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

    def search_by_keyword(self, key_word, s_num, e_num, year, mtype, whole_word=False, match_words=None):
        """
        根据关键字调用 prowlarr API 检索
        :param key_word: 检索的关键字，不能为空
        :param s_num: 季号，为空则不过滤
        :param e_num: 集号，为空则不过滤
        :param year: 年份，为空则不过滤
        :param mtype: 类型：电影、电视剧、动漫
        :param whole_word: 是否完全匹配，为True时只有标题完全一致时才命中
        :param match_words: 匹配的关键字，为空时等于key_word
        :return: 命中的资源媒体信息列表
        """
        if not key_word:
            return []
        if not match_words:
            match_words = [key_word]
        if not self.__api_key or not self.__host:
            log.error("【PROWLARR】Prowlarr配置信息有误！")
            return []
        ret_array = []
        # 需要处理掉特殊符号
        search_word = re.sub(r'\s+', ' ', re.sub(r"%s" % self.__space_chars, ' ', key_word)).strip()
        api_url = "%sapi/v1/search?apikey=%s&Query=%s" % (self.__host, self.__api_key, search_word)
        result_array = self.parse_prowlarrjson(api_url)
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

            # 合匹配模式下，过滤掉做种数为0的
            if whole_word and not seeders:
                log.info("【PROWLARR】%s 做种数为0，跳过..." % torrent_name)
                continue

            # 检查资源类型
            if whole_word:
                match_flag, res_order = Torrent.check_resouce_types(torrent_name, description, self.__res_type)
                if not match_flag:
                    log.info("【PROWLARR】%s 不符合过滤条件" % torrent_name)
                    continue
            else:
                res_order = 0

            # 识别种子名称
            meta_info = MetaInfo(torrent_name)
            if mtype and meta_info.type not in [MediaType.MOVIE, MediaType.UNKNOWN] and mtype == MediaType.MOVIE:
                log.info("【PROWLARR】%s 是 %s，类型不匹配" % (torrent_name, meta_info.type.value))
                continue

            # 识别媒体信息
            media_info = self.media.get_media_info(title=torrent_name, subtitle=description)
            if not media_info or not media_info.tmdb_info:
                log.info("【PROWLARR】%s 未查询到媒体信息" % torrent_name)
                continue

            # 类型
            if mtype and media_info.type != mtype:
                log.info("【PROWLARR】%s 是 %s，类型不匹配" % (torrent_name, media_info.type.value))
                continue

            # 名称是否匹配
            if whole_word:
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

            # 检查标题是否匹配剧集
            if not Torrent.is_torrent_match_sey(media_info, s_num, e_num, year):
                log.info("【PROWLARR】%s：%s %s 不匹配季/集/年份" % (
                    media_info.type.value, media_info.get_title_string(), media_info.get_season_episode_string()))
                continue

            # 判断文件大小是否匹配，只针对电影
            if whole_word:
                if not Torrent.is_torrent_match_size(media_info, self.__res_type, size):
                    log.info("【PROWLARR】%s：%s %s 不符合大小要求" % (media_info.type.value, media_info.get_title_string(), str_filesize(size)))
                    continue

            # 匹配到了
            media_info.set_torrent_info(site=indexer_name,
                                        site_order=indexerId,
                                        enclosure=enclosure,
                                        res_order=res_order,
                                        size=size,
                                        seeders=seeders,
                                        peers=peers,
                                        description=description)
            if media_info not in ret_array:
                index_sucess = index_sucess + 1
                ret_array.append(media_info)
        # 循环结束
        log.info("【PROWLARR】共检索到 %s 条有效资源" % index_sucess)
        return ret_array

    @staticmethod
    def parse_prowlarrjson(url):
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
                description = item.get("infoUrl")
                size = item.get("size")
                seeders = item.get("seeders")
                peers = item.get("leechers")
                indexer = item.get("indexer")
                indexerId = item.get("indexerId")
                tmp_dict = {'title': title, 'enclosure': enclosure, 'description': description, 'size': size,
                            'seeders': seeders, 'peers': peers, 'indexer': indexer, 'indexerId': indexerId}
                ret_array.append(tmp_dict)

        return ret_array
