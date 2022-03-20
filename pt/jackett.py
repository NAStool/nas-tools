import re
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures._base import as_completed
import log
from config import get_config
from utils.functions import parse_jackettxml, get_keyword_from_string
from message.send import Message
from pt.downloader import Downloader
from rmt.media import Media
from utils.types import SearchType
from web.backend.emby import Emby


class Jackett:
    __api_key = None
    __indexers = []
    __res_type = []
    media = None
    message = None
    downloader = None
    emby = None

    def __init__(self):
        self.media = Media()
        self.downloader = Downloader()
        self.message = Message()
        self.emby = Emby()

        config = get_config()
        if config.get('jackett'):
            self.__api_key = config['jackett'].get('api_key')
            self.__res_type = config['jackett'].get('res_type')
            if not isinstance(self.__res_type, list):
                self.__res_type = [self.__res_type]
            self.__indexers = config['jackett'].get('indexers')
            if not isinstance(self.__indexers, list):
                self.__indexers = [self.__indexers]
            self.media = Media()

    # 检索一个Indexer
    def seach_indexer(self, order_seq, index, search_word, key_word, s_num, e_num, year, whole_word=False):
        if not index:
            return None
        ret_array = []
        indexer_name = re.search(r'/indexers/([a-zA-Z0-9]+)/results/', index)
        if indexer_name:
            indexer_name = indexer_name.group(1)
        log.info("【JACKETT】开始检索Indexer：%s ..." % indexer_name)
        api_url = "%sapi?apikey=%s&t=search&q=%s" % (index, self.__api_key, search_word)
        media_array = parse_jackettxml(api_url)
        if len(media_array) == 0:
            log.warn("【JACKETT】%s 未检索到资源！" % indexer_name)
            return None
        # 从检索结果中匹配符合资源条件的记录
        index_sucess = 0
        for media_item in media_array:
            torrent_name = media_item.get('title')
            # 去掉第1个以[]开关的种子名称，有些站会把类型加到种子名称上，会误导识别
            # 非贪婪只匹配一个
            torrent_name = re.sub(r'^\[.+?]', "", torrent_name, count=1)
            enclosure = media_item.get('enclosure')
            size = media_item.get('size')
            description = media_item.get('description')
            seeders = media_item.get('seeders')
            peers = media_item.get('peers')

            # 检查资源类型
            match_flag, res_order, res_typestr = self.media.check_resouce_types(torrent_name, self.__res_type)
            if not match_flag:
                log.debug("【JACKETT】%s 资源类型不匹配！" % torrent_name)
                continue

            # 识别种子名称
            media_info = self.media.get_media_info(torrent_name)
            if not media_info or not media_info.tmdb_info:
                log.debug("【JACKETT】%s 未检索媒体信息！" % torrent_name)
                continue

            # 名称是否匹配
            if whole_word:
                # 全匹配模式，名字需要完全一样才下载
                if key_word == media_info.title:
                    match_flag = True
                else:
                    match_flag = False
                    log.info("【JACKETT】%s 未匹配名称：%s" % (torrent_name, key_word))
            else:
                # 非全匹配模式，种子中或者名字中有关键字就行
                if key_word in media_info.title or key_word in "%s %s" % (media_info.en_name, media_info.cn_name):
                    match_flag = True
                else:
                    match_flag = False
                    log.info("【JACKETT】%s 未匹配名称：%s" % (torrent_name, key_word))

            # 检查标题是否匹配剧集
            if match_flag:
                match_flag = self.__is_jackett_match_sey(media_info, s_num, e_num, year)

            # 匹配到了
            if match_flag:
                media_info.set_torrent_info(site=indexer_name,
                                            site_order=order_seq,
                                            enclosure=enclosure,
                                            res_type=res_typestr,
                                            res_order=res_order,
                                            size=size,
                                            seeders=seeders,
                                            peers=peers,
                                            description=description)
                if media_info not in ret_array:
                    index_sucess = index_sucess + 1
                    ret_array.append(media_info)
            else:
                log.info("【JACKETT】%s 不匹配，跳过..." % torrent_name)
                continue
        log.info("【JACKETT】%s 共检索到 %s 条有效资源" % (indexer_name, index_sucess))
        return ret_array

    # 根据关键字调用 Jackett API 检索
    def search_medias_from_word(self, key_word, s_num, e_num, year, whole_word):
        if not key_word:
            return []
        if not self.__api_key or not self.__indexers:
            log.error("【JACKETT】Jackett配置信息有误！")
            return []
        if year:
            search_word = "%s %s" % (key_word, year)
        else:
            search_word = key_word
        # 多线程检索
        log.info("【JACKETT】开始并行检索 %s，线程数：%s" % (key_word, len(self.__indexers)))
        executor = ThreadPoolExecutor(max_workers=len(self.__indexers))
        all_task = []
        order_seq = 100
        for index in self.__indexers:
            order_seq = order_seq - 1
            task = executor.submit(self.seach_indexer, order_seq, index, search_word, key_word, s_num, e_num, year,
                                   whole_word)
            all_task.append(task)
        ret_array = []
        for future in as_completed(all_task):
            result = future.result()
            if result:
                ret_array = ret_array + result
        log.info("【JACKETT】所有API检索完成，有效资源数：%s" % len(ret_array))
        return ret_array

    # 按关键字，检索排序去重后择优下载：content是搜索内容，total_num是电视剧的总集数
    def search_one_media(self, content, in_from=SearchType.OT, tv_total_episode_num=None):
        key_word, season_num, episode_num, year = get_keyword_from_string(content)
        if not key_word:
            log.info("【JACKETT】检索关键字有误！" % content)
            return False
        if in_from == SearchType.WX:
            self.message.sendmsg("开始检索 %s ..." % content)
        log.info("【JACKETT】开始检索 %s ..." % content)

        # 先检查一波Emby中是不是有了
        no_exists_tv_episodes = []
        # 检查电影
        exists_movies = self.emby.get_emby_movies(key_word, year)
        if exists_movies:
            movies_str = "\n * ".join(["%s (%s)" % (m.get('title'), m.get('year')) for m in exists_movies])
            if in_from == SearchType.WX:
                # 微信已存在时不处理
                self.message.sendmsg(title="%s 在Emby媒体库中已经存在以下电影：\n * %s\n本次下载取消，如没有您想要的请尝试输入不同年份检索" % (content, movies_str), text="")
                return True
            else:
                log.info("【JACKETT】%s 在Emby媒体库中已经存在以下电影：\n * %s" % (content, movies_str))
                if in_from == SearchType.DB:
                    # 豆瓣已存在时不处理
                    return True
        # 检查电视剧
        exists_tvs = self.emby.get_emby_tv_episodes(key_word, year, season_num)
        if exists_tvs:
            exists_tvs_str = ",".join(["%s" % tv for tv in exists_tvs])
            if season_num:
                key_str = "%s第%s季" % (key_word, season_num)
            else:
                # 已经存在的电视剧，没有输入第几季时，默认只处理第1季
                season_num = 1
                key_str = "%s第1季" % key_word
            if in_from == SearchType.WX:
                # 微信已存在
                if episode_num:
                    # 有集数
                    if episode_num in exists_tvs:
                        # 这一集存在
                        self.message.sendmsg(title="%s 在Emby媒体库中已经存在，本次下载取消！" % content, text="")
                        return True
                else:
                    self.message.sendmsg(title="%s 在Emby媒体库中已经存在，剧集：%s，将继续检索缺失剧集..." % (key_str, exists_tvs_str), text="")
            else:
                if in_from == SearchType.DB:
                    # 豆瓣
                    if tv_total_episode_num and len(exists_tvs) >= tv_total_episode_num:
                        log.info("【JACKETT】%s 在Emby媒体库中已经存在，且剧季数完整，本次下载取消！" % key_str)
                        return True
                    # 查询缺失多少集
                    if tv_total_episode_num:
                        no_exists_tv_episodes = self.emby.get_emby_no_exists_episodes(key_word, year, season_num, tv_total_episode_num)
                        no_exists_tv_episodes_str = ",".join(["%s" % tv for tv in no_exists_tv_episodes])
                        if no_exists_tv_episodes:
                            log.info("【JACKETT】%s 缺失以下剧集：%s" % (key_str, no_exists_tv_episodes_str))
                        else:
                            log.info("【JACKETT】%s 在Emby媒体库中没有查询到有剧集缺失，本次下载取消..." % key_str)
                            return True
                    else:
                        log.info("【JACKETT】%s 在Emby媒体库中已经存在，剧集：%s，将继续检索缺失剧集..." % (key_str, exists_tvs_str))
                else:
                    log.info("【JACKETT】%s 在Emby媒体库中已存在，剧集：%s，将继续检索缺失剧集..." % (key_str, exists_tvs_str))
        # 开始真正搜索资源
        media_list = self.search_medias_from_word(key_word=key_word, s_num=season_num, e_num=episode_num, year=year, whole_word=True)
        if len(media_list) == 0:
            if in_from == SearchType.WX:
                self.message.sendmsg("%s 未检索到任何媒体资源！" % content, "")
            return False
        else:
            if in_from == SearchType.WX:
                self.message.sendmsg(title="%s 共检索到 %s 个有效资源，即将择优下载！" % (content, len(media_list)), text="")
            # 去重择优后开始添加下载
            download_medias = self.downloader.check_and_add_pt(in_from, media_list)
            # 统计下载情况，下全了返回True，没下全返回False
            if len(download_medias) == 0:
                log.info("【JACKETT】%s 搜索结果在媒体库中均已存在，本次下载取消！" % content)
                if in_from == SearchType.WX:
                    self.message.sendmsg("%s 搜索结果在媒体库中均已存在，本次下载取消！" % content, "")
                return False
            else:
                log.info("【JACKETT】实际下载了 %s 个资源！" % len(download_medias))
                if no_exists_tv_episodes:
                    # 下载已存在的电视剧，比较要下的都下完了没有，来决定返回什么状态
                    for tv_episode in no_exists_tv_episodes:
                        complete_flag = False
                        for media in download_medias:
                            # 如果下了一个多季集合，且包括了当前季，则认为下全了
                            if len(media.get_season_list()) > 1 and media.is_in_seasion(season_num):
                                complete_flag = True
                                break
                            # 如果下了一个单季，集为空或者包括了当前集则认为下到了
                            if len(media.get_season_list()) == 1 and (media.is_in_episode(tv_episode) or not media.begin_episode):
                                complete_flag = True
                                break
                        # 有一集没匹配就是没下全
                        if not complete_flag:
                            return False
                    return True

            return True

    # 种子名称关键字匹配
    @staticmethod
    def __is_jackett_match_sey(media_info, s_num, e_num, year_str):
        if s_num:
            # 只要单季不下集合，下集合会导致下很多
            if not media_info.is_in_seasion(s_num) or len(media_info.get_season_list()) > 1:
                log.info("【JACKETT】%s 未匹配季：%s" % (media_info.org_string, s_num))
                return False
        if e_num:
            if not media_info.is_in_episode(e_num):
                log.info("【JACKETT】%s 未匹配集：%s" % (media_info.org_string, e_num))
                return False
        if year_str:
            # 有的电视剧年份会是最新的年份（比如豆瓣过来的），所以年份的问题也比对下标题
            if str(media_info.year) != year_str and year_str not in media_info.org_string:
                log.info("【JACKETT】%s 未匹配年份：%s" % (media_info.org_string, year_str))
                return False
        return True


if __name__ == "__main__":
    Jackett().search_one_media("西部世界")
