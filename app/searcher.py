import log
from app.db import SqlHelper
from config import Config
from app.message import Message
from app.downloader import Downloader
from app.indexer import BuiltinIndexer, Jackett, Prowlarr
from app.media import Media
from app.utils import ProgressController
from app.utils.types import SearchType, MediaType


class Searcher:
    downloader = None
    media = None
    message = None
    indexer = None
    progress = None
    __search_auto = True

    def __init__(self):
        self.downloader = Downloader()
        self.media = Media()
        self.message = Message()
        self.progress = ProgressController()
        self.init_config()

    def init_config(self):
        config = Config()
        self.__search_auto = config.get_config("pt").get('search_auto', True)
        if config.get_config("pt").get('search_indexer') == "prowlarr":
            self.indexer = Prowlarr()
        elif config.get_config("pt").get('search_indexer') == "jackett":
            self.indexer = Jackett()
        else:
            self.indexer = BuiltinIndexer()

    def search_medias(self,
                      key_word,
                      filter_args: dict,
                      match_type,
                      match_media=None,
                      in_from: SearchType = None):
        """
        根据关键字调用索引器检查媒体
        :param key_word: 检索的关键字，不能为空
        :param filter_args: 过滤条件
        :param match_type: 匹配模式：0-识别并模糊匹配；1-识别并精确匹配；2-不识别匹配
        :param match_media: 区配的媒体信息
        :param in_from: 搜索渠道
        :return: 命中的资源媒体信息列表
        """
        if not key_word:
            return []
        if not self.indexer:
            return []
        return self.indexer.search_by_keyword(key_word=key_word,
                                              filter_args=filter_args,
                                              match_type=match_type,
                                              match_media=match_media,
                                              in_from=in_from)

    def search_one_media(self, media_info,
                         in_from: SearchType,
                         no_exists: dict,
                         sites: list = None,
                         filters: dict = None):
        """
        只检索和下载一个资源，用于精确检索下载，由微信、Telegram或豆瓣调用
        :param media_info: 已识别的媒体信息
        :param in_from: 搜索渠道
        :param no_exists: 缺失的剧集清单
        :param sites: 检索哪些站点
        :param filters: 过滤条件，为空则不过滤
        :return: 请求的资源是否全部下载完整
                 请求的资源如果是剧集则返回下载后仍然缺失的季集信息
                 搜索到的结果数量
                 下载到的结果数量，如为None则表示未开启自动下载
        """
        if not media_info:
            return False, {}, 0, 0
        # 进度计数重置
        self.progress.reset('search')
        # 查找的季
        if media_info.begin_season is None:
            search_season = None
        else:
            search_season = media_info.get_season_list()
        # 查找的集
        search_episode = media_info.get_episode_list()
        if search_episode and not search_season:
            search_season = [1]
        # 过滤条件
        filter_args = {"season": search_season,
                       "episode": search_episode,
                       "year": media_info.year,
                       "type": media_info.type,
                       "site": sites,
                       "seeders": True}
        if filters:
            filter_args.update(filters)
        # 中文名
        if media_info.cn_name:
            search_cn_name = media_info.cn_name
        else:
            search_cn_name = media_info.title
        # 英文名
        search_en_name = None
        if media_info.en_name:
            search_en_name = media_info.en_name
        else:
            if media_info.original_language == "en":
                search_en_name = media_info.original_title
            else:
                en_info = Media().get_tmdb_info(mtype=media_info.type, tmdbid=media_info.tmdb_id, language="en-US")
                if en_info:
                    search_en_name = en_info.get("title") if media_info.type == MediaType.MOVIE else en_info.get("name")
        # 两次搜索名称
        second_search_name = None
        if Config().get_config("laboratory").get("search_en_title"):
            if search_en_name:
                first_search_name = search_en_name
                second_search_name = search_cn_name
            else:
                first_search_name = search_cn_name
        else:
            first_search_name = search_cn_name
            if search_en_name:
                second_search_name = search_en_name
        # 开始搜索
        log.info("【SEARCHER】开始检索 %s ..." % first_search_name)
        media_list = self.search_medias(key_word=first_search_name,
                                        filter_args=filter_args,
                                        match_type=1,
                                        match_media=media_info,
                                        in_from=in_from)
        # 使用名称重新搜索
        if len(media_list) == 0 \
                and second_search_name \
                and second_search_name != first_search_name:
            log.info("【SEARCHER】%s 未检索到资源,尝试通过 %s 重新检索 ..." % (first_search_name, second_search_name))
            media_list = self.search_medias(key_word=second_search_name,
                                            filter_args=filter_args,
                                            match_type=1,
                                            match_media=media_info,
                                            in_from=in_from)

        if len(media_list) == 0:
            log.info("【SEARCHER】%s 未搜索到任何资源" % second_search_name)
            return False, no_exists, 0, 0
        else:
            if in_from in [SearchType.WX, SearchType.TG]:
                # 保存搜索记录
                SqlHelper.delete_all_search_torrents()
                # 搜索结果排序
                media_list = sorted(media_list, key=lambda x: "%s%s%s%s" % (str(x.title).ljust(100, ' '),
                                                                            str(x.res_order).rjust(3, '0'),
                                                                            str(x.site_order).rjust(3, '0'),
                                                                            str(x.seeders).rjust(10, '0')),
                                    reverse=True)
                # 插入数据库
                SqlHelper.insert_search_results(media_list)
                # 微信未开自动下载时返回
                if not self.__search_auto:
                    return False, no_exists, len(media_list), None
            # 择优下载
            download_items, left_medias = self.downloader.check_and_add_pt(in_from, media_list, no_exists)
            # 统计下载情况，下全了返回True，没下全返回False
            if not download_items:
                log.info("【SEARCHER】%s 未下载到资源" % media_info.title)
                return False, left_medias, len(media_list), 0
            else:
                log.info("【SEARCHER】实际下载了 %s 个资源" % len(download_items))
                # 还有剩下的缺失，说明没下完，返回False
                if left_medias:
                    return False, left_medias, len(media_list), len(download_items)
                # 全部下完了
                else:
                    return True, no_exists, len(media_list), len(download_items)
