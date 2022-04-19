import re
import log
from config import Config
from message.send import Message
from pt.downloader import Downloader
from pt.indexer.jackett import Jackett
from pt.indexer.prowlarr import Prowlarr
from rmt.media import Media
from utils.functions import str_filesize
from utils.sqls import delete_all_search_torrents, insert_search_results
from utils.types import SearchType, MediaType, IndexerType


class Searcher:
    downloader = None
    media = None
    message = None
    indexer = None
    __search_indexer = None
    __search_auto = True

    def __init__(self):
        self.downloader = Downloader()
        self.media = Media()
        self.message = Message()
        self.init_config()

    def init_config(self):
        config = Config()
        self.__search_auto = config.get_config("pt").get('search_auto', True)
        search_indexer = config.get_config("pt").get('search_indexer')
        if search_indexer:
            if search_indexer.upper() == "PROWLARR":
                self.__search_indexer = IndexerType.PROWLARR
            else:
                self.__search_indexer = IndexerType.JACKETT
        else:
            self.__search_indexer = IndexerType.JACKETT
        if self.__search_indexer == IndexerType.PROWLARR:
            self.indexer = Prowlarr()
        else:
            self.indexer = Jackett()

    # 根据关键字检索
    def search_medias(self, key_word, s_num, e_num, year, mtype, whole_word):
        if not key_word:
            return []
        if not self.indexer:
            return
        return self.indexer.search_by_keyword(key_word, s_num, e_num, year, mtype, whole_word)

    # 检索一个媒体
    def search_one_media(self, input_str, in_from=SearchType.OT, user_id=None):
        if not input_str:
            log.info("【SEARCHER】检索关键字有误！")
            return False
        # 去掉查询中的电影或电视剧关键字
        if re.search(r'^电视剧|\s+电视剧', input_str):
            mtype = MediaType.TV
        else:
            mtype = None
        content = re.sub(r'^电影|^电视剧|\s+电影|\s+电视剧', '', input_str).strip()
        if not content:
            return
        # 识别媒体信息
        log.info("【SEARCHER】正在识别 %s 的媒体信息..." % content)
        media_info = self.media.get_media_info(title=content, mtype=mtype, strict=True)
        if media_info and media_info.tmdb_info:
            log.info("类型：%s，标题：%s，年份：%s" % (media_info.type.value, media_info.title, media_info.year))
            if in_from in [SearchType.WX, SearchType.TG]:
                self.message.sendmsg(title="类型：%s，标题：%s，年份：%s" % (media_info.type.value, media_info.title, media_info.year), user_id=user_id)
            # 检查是否存在，电视剧返回不存在的集清单
            exist_flag, no_exists = self.downloader.check_exists_medias(in_from=in_from,
                                                                        meta_info=media_info)
            if exist_flag is None:
                return False
            elif exist_flag:
                return True
        else:
            if in_from in [SearchType.WX, SearchType.TG]:
                self.message.sendmsg(title="%s 无法查询到任何电影或者电视剧信息，请确认名称是否正确" % content, user_id=user_id)
            log.info("【SEARCHER】%s 无法查询到任何电影或者电视剧信息，请确认名称是否正确" % content)
            return False

        # 开始真正搜索资源
        if in_from in [SearchType.WX, SearchType.TG]:
            self.message.sendmsg(title="开始检索 %s ..." % media_info.title, user_id=user_id)
        log.info("【SEARCHER】开始检索 %s ..." % media_info.title)
        # 查找的季
        if not media_info.begin_season:
            search_season = None
        else:
            search_season = media_info.get_season_list()
        # 查找的集
        search_episode = media_info.get_episode_list()
        if search_episode and not search_season:
            search_season = [1]
        media_list = self.search_medias(key_word=media_info.title,
                                        s_num=search_season,
                                        e_num=search_episode,
                                        year=media_info.year,
                                        mtype=media_info.type,
                                        whole_word=True)
        if len(media_list) == 0:
            log.info("%s 未检索到任何资源" % media_info.title)
            if in_from in [SearchType.WX, SearchType.TG]:
                self.message.sendmsg(title="%s 未检索到任何资源" % media_info.title, user_id=user_id)
            return False
        else:
            if in_from in [SearchType.WX, SearchType.TG]:
                # 保存微信搜索记录
                delete_all_search_torrents()
                # 插入数据库
                save_media_list = self.get_torrents_group_item(media_list)
                for save_media_item in save_media_list:
                    insert_search_results(save_media_item)
                self.message.sendmsg(title=media_info.get_title_vote_string(),
                                     text="%s 共检索到 %s 个有效资源" % (media_info.title, len(save_media_list)),
                                     image=media_info.get_message_image(),
                                     url='search',
                                     user_id=user_id)
            # 微信未开自动下载时返回
            if in_from in [SearchType.WX, SearchType.TG] and not self.__search_auto:
                return False
            # 择优下载
            download_num, left_medias = self.downloader.check_and_add_pt(in_from, media_list, no_exists)
            # 统计下载情况，下全了返回True，没下全返回False
            if download_num == 0:
                log.info("【SEARCHER】%s 搜索结果中没有符合下载条件的资源" % content)
                if in_from in [SearchType.WX, SearchType.TG]:
                    self.message.sendmsg(title="%s 搜索结果中没有符合下载条件的资源" % content, user_id=user_id)
                return False
            else:
                log.info("【SEARCHER】实际下载了 %s 个资源" % download_num)
                # 比较要下的都下完了没有，来决定返回什么状态
                if left_medias:
                    return False
            return True

    # 种子去重，每一个名称、站点、资源类型 选一个做种人最多的显示
    @staticmethod
    def get_torrents_group_item(media_list):
        if not media_list:
            return []

        # 排序函数
        def get_sort_str(x):
            season_len = str(len(x.get_season_list())).rjust(3, '0')
            episode_len = str(len(x.get_episode_list())).rjust(3, '0')
            # 排序：标题、季集、资源类型、站点、做种
            return "%s%s%s%s%s" % (str(x.title).ljust(100, ' '),
                                   "%s%s" % (season_len, episode_len),
                                   str(x.res_order).rjust(3, '0'),
                                   str(x.site_order).rjust(3, '0'),
                                   str(x.seeders).rjust(10, '0'))

        # 匹配的资源中排序分组
        media_list = sorted(media_list, key=lambda x: get_sort_str(x), reverse=True)
        # 控重
        can_download_list_item = []
        can_download_list = []
        # 按分组显示做种数最多的一个
        for t_item in media_list:
            if t_item.type == MediaType.TV:
                media_name = "%s%s%s%s%s" % (t_item.get_title_string(),
                                             t_item.site,
                                             t_item.get_resource_type_string(),
                                             t_item.get_season_episode_string(),
                                             str_filesize(t_item.size))
            else:
                media_name = "%s%s%s%s" % (
                    t_item.get_title_string(), t_item.site, t_item.get_resource_type_string(),
                    str_filesize(t_item.size))
            if media_name not in can_download_list:
                can_download_list.append(media_name)
                can_download_list_item.append(t_item)
        return can_download_list_item
