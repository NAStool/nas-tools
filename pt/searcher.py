import log
from config import Config
from message.send import Message
from pt.downloader import Downloader
from pt.indexer.jackett import Jackett
from pt.indexer.prowlarr import Prowlarr
from rmt.media import Media
from rmt.meta.metabase import MetaBase
from utils.commons import ProcessHandler
from utils.sqls import delete_all_search_torrents, insert_search_results
from utils.types import SearchType, MediaType


class Searcher:
    downloader = None
    media = None
    message = None
    indexer = None
    __search_auto = True

    def __init__(self):
        self.downloader = Downloader()
        self.media = Media()
        self.message = Message()
        self.init_config()

    def init_config(self):
        config = Config()
        self.__search_auto = config.get_config("pt").get('search_auto', True)
        if config.get_config("pt").get('search_indexer') == "prowlarr":
            self.indexer = Prowlarr()
        else:
            self.indexer = Jackett()

    def search_medias(self, key_word, filter_args: dict, match_type, match_media: MetaBase = None):
        """
        根据关键字调用索引器检查媒体
        :param key_word: 检索的关键字，不能为空
        :param filter_args: 过滤条件
        :param match_type: 匹配模式：0-识别并模糊匹配；1-识别并精确匹配；2-不识别匹配
        :param match_media: 区配的媒体信息
        :return: 命中的资源媒体信息列表
        """
        if not key_word:
            return []
        if not self.indexer:
            return []
        return self.indexer.search_by_keyword(key_word=key_word,
                                              filter_args=filter_args,
                                              match_type=match_type,
                                              match_media=match_media)

    def search_one_media(self, media_info: MetaBase,
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
        ProcessHandler().reset()
        # 查找的季
        if media_info.begin_season is None:
            search_season = None
        else:
            search_season = media_info.get_season_list()
        # 查找的集
        search_episode = media_info.get_episode_list()
        if search_episode and not search_season:
            search_season = [1]
        # 检索标题
        search_title = media_info.title
        if Config().get_config("laboratory").get("search_en_title"):
            # 如果原标题是英文：用原标题去检索，否则使用英文+原标题搜索去匹配，优化小语种资源
            if media_info.original_language != "en":
                en_info = Media().get_tmdb_info(mtype=media_info.type, tmdbid=media_info.tmdb_id, language="en-US")
                if en_info:
                    search_title = en_info.get("title") if media_info.type == MediaType.MOVIE else en_info.get("name")
            else:
                search_title = media_info.original_title

        # 过滤条件
        filter_args = {"season": search_season,
                       "episode": search_episode,
                       "year": media_info.year,
                       "type": media_info.type,
                       "site": sites}
        if filters:
            filter_args.update(filters)
        # 开始搜索
        log.info("【SEARCHER】开始检索 %s ..." % search_title)
        media_list = self.search_medias(key_word=search_title,
                                        filter_args=filter_args,
                                        match_type=1,
                                        match_media=media_info)
        # 使用名称重新搜索
        if len(media_list) == 0 and media_info.get_name() and search_title != media_info.get_name():
            log.info("【SEARCHER】%s 未检索到资源,尝试通过 %s 重新检索 ..." % (search_title, media_info.get_name()))
            media_list = self.search_medias(key_word=media_info.get_name(),
                                            filter_args=filter_args,
                                            match_type=1,
                                            match_media=media_info)

        if len(media_list) == 0:
            log.info("【SEARCHER】%s 未搜索到任何资源" % search_title)
            return False, no_exists, 0, 0
        else:
            if in_from in [SearchType.WX, SearchType.TG]:
                # 保存搜索记录
                delete_all_search_torrents()
                # 搜索结果排序
                media_list = sorted(media_list, key=lambda x: "%s%s%s%s" % (str(x.title).ljust(100, ' '),
                                                                            str(x.res_order).rjust(3, '0'),
                                                                            str(x.site_order).rjust(3, '0'),
                                                                            str(x.seeders).rjust(10, '0')),
                                    reverse=True)
                # 插入数据库
                insert_search_results(media_list)
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
