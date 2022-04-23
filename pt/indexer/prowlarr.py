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

    def __init__(self):
        self.torrent = Torrent()
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

    # 根据关键字调用 prowlarr API 检索
    def search_by_keyword(self, key_word, s_num, e_num, year, mtype, whole_word=False):
        if not key_word:
            return []
        if not self.__api_key or not self.__host:
            log.error("【PROWLARR】Prowlarr配置信息有误！")
            return []
        ret_array = []
        # 需要处理掉特殊符号
        search_word = key_word.replace("：", " ")
        api_url = "%sapi/v1/search?apikey=%s&Query=%s" % (self.__host, self.__api_key, search_word)
        result_array = self.parse_prowlarrjson(api_url)
        if len(result_array) == 0:
            log.warn("【PROWLARR】%s 未检索到任何资源")
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

            # 检查资源类型
            match_flag, res_order = self.torrent.check_resouce_types(torrent_name, description, self.__res_type)
            if not match_flag:
                log.info("【PROWLARR】%s 不符合过滤条件" % torrent_name)
                continue

            # 识别种子名称
            meta_info = MetaInfo(torrent_name)
            if mtype and meta_info.type != MediaType.MOVIE and mtype == MediaType.MOVIE:
                log.info("【PROWLARR】%s 类型不匹配" % torrent_name)
                continue

            # 识别媒体信息
            media_info = self.media.get_media_info(title=torrent_name, subtitle=description)
            if not media_info or not media_info.tmdb_info:
                log.info("【PROWLARR】%s 未检索到媒体信息" % torrent_name)
                continue

            # 类型
            if mtype and media_info.type != mtype:
                log.info("【PROWLARR】%s 类型不匹配" % torrent_name)
                continue

            # 名称是否匹配
            if whole_word:
                # 全匹配模式，名字需要完全一样才下载
                if str(key_word).upper() == str(media_info.title).upper():
                    match_flag = True
                else:
                    match_flag = False
                    log.info("【PROWLARR】%s：%s 不匹配名称：%s" % (media_info.type.value, media_info.title, key_word))
            else:
                # 非全匹配模式，种子中或者名字中有关键字就行
                if str(key_word).upper() in str(media_info.get_title_string()).upper() \
                        or str(key_word).upper() in str(media_info.org_string).upper():
                    match_flag = True
                else:
                    match_flag = False
                    log.info("【PROWLARR】%s：%s %s 不匹配名称：%s" % (
                        media_info.type.value, media_info.org_string, media_info.get_title_string(), key_word))

            # 检查标题是否匹配剧集
            if match_flag:
                match_flag = self.torrent.is_torrent_match_sey(media_info, s_num, e_num, year)
                if not match_flag:
                    log.info("【PROWLARR】%s：%s %s 不匹配季/集/年份" % (
                        media_info.type.value, media_info.get_title_string(), media_info.get_season_episode_string()))

            # 判断文件大小是否匹配，只针对电影
            if match_flag:
                match_flag = self.torrent.is_torrent_match_size(media_info, self.__res_type, size)
                if not match_flag:
                    log.info("【PROWLARR】%s：%s %s 不符合大小要求" % (media_info.type.value, media_info.get_title_string(), str_filesize(size)))

            # 匹配到了
            if match_flag:
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
            else:
                continue
        log.info("【PROWLARR】共检索到 %s 条有效资源" % index_sucess)
        return ret_array

    # 解析PROWLARR的XML，返回标题及URL等
    @staticmethod
    def parse_prowlarrjson(url):
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
