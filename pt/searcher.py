import re
import log
from config import Config
from message.send import Message
from pt.downloader import Downloader
from pt.indexer.jackett import Jackett
from pt.indexer.prowlarr import Prowlarr
from pt.torrent import Torrent
from rmt.media import Media
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

    def search_medias(self, key_word, s_num, e_num, year, mtype, whole_word, match_words=None):
        """
        根据关键字调用索引器检查媒体
        :param key_word: 检索的关键字，不能为空
        :param s_num: 季号，为空则不过滤
        :param e_num: 集号，为空则不过滤
        :param year: 年份，为空则不过滤
        :param mtype: 类型：电影、电视剧、动漫
        :param whole_word: 是否完全匹配，为True时只有标题完全一致时才命中
        :param match_words: 匹配的关键字
        :return: 命中的资源媒体信息列表
        """
        if not key_word:
            return []
        if not self.indexer:
            return []
        return self.indexer.search_by_keyword(key_word, s_num, e_num, year, mtype, whole_word, match_words)

    def search_one_media(self, input_str, in_from=SearchType.OT, user_id=None):
        """
        只检索和下载一种资源，用于精确检索下载，由微信、Telegram或豆瓣调用
        :param input_str: 输入字符串，可以包括标题、年份、季、集的信息，使用空格隔开
        :param in_from: 搜索下载的请求来源
        :param user_id: 需要发送消息的，传入该参数，则只给对应用户发送交互消息
        :return: 请求的资源是否全部下载完整、请求的文本对应识别出来的媒体信息、请求的资源如果是剧集，则返回下载后仍然缺失的季集信息
        """
        if not input_str:
            log.info("【SEARCHER】检索关键字有误！")
            return False, None, None
        # 去掉查询中的电影或电视剧关键字
        if re.search(r'^电视剧|\s+电视剧|^动漫|\s+动漫', input_str):
            mtype = MediaType.TV
        else:
            mtype = None
        content = re.sub(r'^电影|^电视剧|^动漫|\s+电影|\s+电视剧|\s+动漫', '', input_str).strip()
        if not content:
            return False, None, None
        # 识别媒体信息
        log.info("【SEARCHER】正在识别 %s 的媒体信息..." % content)
        media_info = self.media.get_media_info(title=content, mtype=mtype, strict=True)
        if media_info and media_info.tmdb_info:
            log.info("类型：%s，标题：%s，年份：%s" % (media_info.type.value, media_info.title, media_info.year))
            if in_from in [SearchType.WX, SearchType.TG]:
                self.message.send_channel_msg(channel=in_from,
                                              title="类型：%s，标题：%s，年份：%s" % (
                                                  media_info.type.value, media_info.title, media_info.year),
                                              user_id=user_id)
            # 检查是否存在，电视剧返回不存在的集清单
            exist_flag, no_exists, messages = self.downloader.check_exists_medias(meta_info=media_info)
            if messages and in_from in [SearchType.WX, SearchType.TG]:
                self.message.send_channel_msg(channel=in_from, title="\n".join(messages))
            # 检查出错
            if exist_flag is None:
                return False, media_info, no_exists
            # 已经存在
            elif exist_flag:
                return True, media_info, no_exists
        else:
            if in_from in [SearchType.WX, SearchType.TG]:
                self.message.send_channel_msg(channel=in_from,
                                              title="%s 查询不到媒体信息" % content,
                                              user_id=user_id)
            log.info("【SEARCHER】%s 查询不到媒体信息" % content)
            return False, None, None

        # 开始真正搜索资源
        if in_from in [SearchType.WX, SearchType.TG]:
            self.message.send_channel_msg(channel=in_from,
                                          title="开始检索 %s ..." % media_info.title,
                                          user_id=user_id)
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
                self.message.send_channel_msg(channel=in_from,
                                              title="%s 未检索到任何资源" % media_info.title,
                                              user_id=user_id)
            return False, media_info, no_exists
        else:
            if in_from in [SearchType.WX, SearchType.TG]:
                # 保存微信搜索记录
                delete_all_search_torrents()
                # 插入数据库
                save_media_list = Torrent.get_torrents_group_item(media_list)
                insert_search_results(save_media_list)
                self.message.send_channel_msg(channel=in_from,
                                              title=media_info.get_title_vote_string(),
                                              text="%s 共检索到 %s 个有效资源" % (media_info.title, len(save_media_list)),
                                              image=media_info.get_message_image(),
                                              url='search',
                                              user_id=user_id)
            # 微信未开自动下载时返回
            if in_from in [SearchType.WX, SearchType.TG] and not self.__search_auto:
                return False, media_info, no_exists
            # 择优下载
            download_items, left_medias = self.downloader.check_and_add_pt(in_from, media_list, no_exists)
            # 统计下载情况，下全了返回True，没下全返回False
            if not download_items:
                log.info("【SEARCHER】%s 未下载到资源" % content)
                if in_from in [SearchType.WX, SearchType.TG]:
                    self.message.send_channel_msg(channel=in_from,
                                                  title="%s 未下载到资源" % content,
                                                  user_id=user_id)
                return False, media_info, left_medias
            else:
                log.info("【SEARCHER】实际下载了 %s 个资源" % len(download_items))
                # 还有剩下的缺失，说明没下完，返回False
                if left_medias:
                    return False, media_info, left_medias
            # 全部下完了
            return True, media_info, no_exists
