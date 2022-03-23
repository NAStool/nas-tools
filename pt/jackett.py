import re
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures._base import as_completed
import log
from config import get_config
from utils.functions import parse_jackettxml, get_keyword_from_string, get_tmdb_seasons_info, \
    get_tmdb_season_episodes_num
from message.send import Message
from pt.downloader import Downloader
from rmt.media import Media
from utils.types import SearchType, MediaType
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
            torrent_name = self.downloader.prepare_torrent_name(torrent_name)
            enclosure = media_item.get('enclosure')
            size = media_item.get('size')
            description = media_item.get('description')
            seeders = media_item.get('seeders')
            peers = media_item.get('peers')

            # 检查资源类型
            match_flag, res_order, res_typestr = self.media.check_resouce_types(torrent_name, self.__res_type)
            if not match_flag:
                log.debug("【JACKETT】%s 资源类型不匹配" % torrent_name)
                continue

            # 识别种子名称
            media_info = self.media.get_media_info(torrent_name, description)
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
                    log.info("【JACKETT】%s：%s 不匹配名称：%s" % (media_info.type.value, media_info.title, key_word))
            else:
                # 非全匹配模式，种子中或者名字中有关键字就行
                if key_word in media_info.title or key_word in "%s %s" % (media_info.en_name, media_info.cn_name):
                    match_flag = True
                else:
                    match_flag = False
                    log.info("【JACKETT】%s：%s %s %s 不匹配名称：%s" % (media_info.type.value, media_info.en_name, media_info.cn_name, media_info.title, key_word))

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
    def search_one_media(self, content, in_from=SearchType.OT):
        key_word, search_season, search_episode, search_year = get_keyword_from_string(content)
        if not key_word:
            log.info("【JACKETT】检索关键字有误！")
            return False

        # 先识别关键字是什么电视或者电视剧，如果是电视据看下有多少季，每季有多少集
        log.info("【JACKETT】正在识别 %s 的媒体信息..." % content)
        meta_info = self.media.get_media_info(content)
        total_tv_no_exists = []
        if meta_info.tmdb_info:
            if meta_info.type == MediaType.TV:
                # 检索电视剧的信息
                tv_info = self.media.get_tmdb_tv_info(meta_info.tmdb_id)
                if tv_info:
                    # 共有多少季，每季有多少季
                    total_seasons = get_tmdb_seasons_info(tv_info.get("seasons"))
                else:
                    if in_from == SearchType.WX:
                        self.message.sendmsg("%s 无法查询到媒体详细信息" % meta_info.title)
                    log.info("【JACKETT】%s 无法查询到媒体详细信息" % meta_info.title)
                    return False
                if not search_season:
                    # 没有输入季
                    if in_from == SearchType.WX:
                        self.message.sendmsg("电视剧 %s 共有 %s 季" % (meta_info.title, len(total_seasons)))
                    log.info("【JACKETT】电视剧 %s 共有 %s 季" % (meta_info.title, len(total_seasons)))
                else:
                    # 有输入季
                    episode_num = get_tmdb_season_episodes_num(tv_info.get("seasons"), search_season)
                    total_seasons = [{"season_number": search_season, "episode_count": episode_num}]
                    if in_from == SearchType.WX:
                        self.message.sendmsg("电视剧 %s 第%s季 共有 %s 集" % (meta_info.title, search_season, episode_num))
                    log.info("【JACKETT】电视剧 %s 第%s季 共有 %s 集" % (meta_info.title, search_season, episode_num))
                # 查询缺少多少集
                need_search = False
                for season in total_seasons:
                    season_number = season.get("season_number")
                    episode_count = season.get("episode_count")
                    if not season_number or not episode_count:
                        continue
                    no_exists_tv_episodes = self.emby.get_emby_no_exists_episodes(meta_info.title, meta_info.year, season_number, episode_count)
                    if no_exists_tv_episodes:
                        # 存在缺失
                        need_search = True
                        exists_tvs_str = "、".join(["%s" % tv for tv in no_exists_tv_episodes])
                        if search_episode:
                            # 有集数
                            if search_episode not in no_exists_tv_episodes:
                                # 这一集存在
                                if in_from == SearchType.WX:
                                    self.message.sendmsg(title="%s 在Emby媒体库中已经存在，本次下载取消！" % content, text="")
                                log.info("【JACKETT】%s 在Emby媒体库中已经存在，本次下载取消！" % content)
                                return True
                            else:
                                total_tv_no_exists = [{"season": season_number, "episodes": [search_episode]}]
                        else:
                            if len(no_exists_tv_episodes) == episode_count:
                                if in_from == SearchType.WX:
                                    self.message.sendmsg(title="第%s季 缺失%s集" % (season_number, episode_count))
                                log.info("【JACKETT】第%s季 缺失%s集" % (season_number, episode_count))
                            else:
                                if in_from == SearchType.WX:
                                    self.message.sendmsg(title="第%s季 缺失集：%s" % (season_number, exists_tvs_str))
                                log.info("【JACKETT】第%s季 缺失集：%s" % (season_number, exists_tvs_str))
                            total_tv_no_exists.append({"season": season_number, "episodes": no_exists_tv_episodes})
                    else:
                        if in_from == SearchType.WX:
                            self.message.sendmsg("第%s季 共%s集 已全部存在" % (season_number, episode_count))
                        log.info("【JACKETT】第%s季 共%s集 已全部存在" % (season_number, episode_count))

                if not need_search:
                    # 全部存在，不用栓索
                    return True
            else:
                # 检查电影
                exists_movies = self.emby.get_emby_movies(meta_info.title, meta_info.year)
                if exists_movies:
                    movies_str = "\n * ".join(["%s (%s)" % (m.get('title'), m.get('year')) for m in exists_movies])
                    if in_from == SearchType.WX:
                        # 微信已存在时不处理
                        self.message.sendmsg(title="%s 在Emby媒体库中已经存在以下电影：\n * %s" % (content, movies_str))
                        return True
                    else:
                        log.info("【JACKETT】%s 在Emby媒体库中已经存在以下电影：\n * %s" % (content, movies_str))
                        if in_from == SearchType.DB:
                            # 豆瓣已存在时不处理
                            return True
        else:
            if in_from == SearchType.WX:
                self.message.sendmsg("%s 无法查询到任何电影或者电视剧信息，请确认名称是否正确" % content)
            log.info("【JACKETT】%s 无法查询到任何电影或者电视剧信息，请确认名称是否正确" % content)
            return False

        # 开始真正搜索资源
        if in_from == SearchType.WX:
            self.message.sendmsg("开始检索 %s ..." % content)
        log.info("【JACKETT】开始检索 %s ..." % content)
        media_list = self.search_medias_from_word(key_word=key_word, s_num=search_season, e_num=search_episode, year=search_year, whole_word=True)
        if len(media_list) == 0:
            if in_from == SearchType.WX:
                self.message.sendmsg("%s 未检索到任何媒体资源！" % content, "")
            return False
        else:
            if in_from == SearchType.WX:
                self.message.sendmsg(title="%s 共检索到 %s 个有效资源，即将择优下载..." % (content, len(media_list)), text="")
            # 去重择优后开始添加下载
            download_medias = self.downloader.check_and_add_pt(in_from, media_list, total_tv_no_exists)
            # 统计下载情况，下全了返回True，没下全返回False
            if len(download_medias) == 0:
                log.info("【JACKETT】%s 搜索结果在媒体库中均已存在，本次下载取消" % content)
                if in_from == SearchType.WX:
                    self.message.sendmsg("%s 搜索结果在媒体库中均已存在，本次下载取消" % content, "")
                return False
            else:
                log.info("【JACKETT】实际下载了 %s 个资源" % len(download_medias))
                if total_tv_no_exists:
                    # 下载已存在的电视剧，比较要下的都下完了没有，来决定返回什么状态
                    for tv_item in total_tv_no_exists:
                        complete_flag = False
                        for media in download_medias:
                            # 如果下了一个多季集合，且包括了当前季，则认为下全了
                            if len(media.get_season_list()) > 1 and media.is_in_seasion(tv_item.get("season")):
                                complete_flag = True
                                break
                            # 如果下了一个单季，没有集的信息，则认为所有的集都下全了
                            if len(media.get_season_list()) == 1 and media.is_in_seasion(tv_item.get("season") and not media.get_episode_list()):
                                complete_flag = True
                                break
                            # 如果下了一个单季，有集的信息，且所含了所有缺失的集，则认为下全了
                            if len(media.get_season_list()) == 1 and set(media.get_episode_list()).issuperset(tv_item.get("episodes")):
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
            if not media_info.is_in_seasion(s_num):
                log.info("【JACKETT】%s(%s)%s%s 不匹配季：%s" % (media_info.title, media_info.year, media_info.get_season_string(), media_info.get_episode_string(), s_num))
                return False
        if e_num:
            if not media_info.is_in_episode(e_num):
                log.info("【JACKETT】%s(%s)%s%s 不匹配集：%s" % (media_info.title, media_info.year, media_info.get_season_string(), media_info.get_episode_string(), e_num))
                return False
        if year_str:
            if str(media_info.year) != year_str:
                log.info("【JACKETT】%s(%s)%s%s 不匹配年份：%s" % (media_info.title, media_info.year, media_info.get_season_string(), media_info.get_episode_string(), year_str))
                return False
        return True
