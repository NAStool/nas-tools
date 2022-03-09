import re
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures._base import as_completed
import log
from config import get_config, JACKETT_MAX_INDEX_NUM
from utils.functions import parse_jackettxml, get_keyword_from_string
from message.send import Message
from pt.downloader import Downloader
from rmt.media import Media
from utils.types import MediaType


class Jackett:
    __api_key = None
    __indexers = []
    __res_type = []
    media = None
    message = None
    downloader = None

    def __init__(self):
        self.media = Media()
        self.downloader = Downloader()
        self.message = Message()

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
    def seach_indexer(self, order_seq, index, search_word, key_word, s_num, e_num, year):
        if not index:
            return None
        ret_array = []
        indexer_name = re.search(r'/indexers/([a-zA-Z0-9]+)/results/', index)
        if indexer_name:
            indexer_name = indexer_name.group(1)
        log.info("【JACKETT】开始检索Indexer：%s ..." % index)
        api_url = "%sapi?apikey=%s&t=search&q=%s" % (index, self.__api_key, search_word)
        media_array = parse_jackettxml(api_url)
        if len(media_array) == 0:
            log.warn("【JACKETT】%s 未检索到资源！" % index)
            return None
        # 从检索结果中匹配符合资源条件的记录
        index_num = 0
        index_sucess = 0
        for media_item in media_array:
            title = media_item.get('title')
            # 去掉第1个以[]开关的种子名称，有些站会把类型加到种子名称上，会误导识别
            # 非贪婪只匹配一个
            title = re.sub(r'^\[.+?]', "", title, count=1)
            enclosure = media_item.get('enclosure')
            size = media_item.get('size')
            description = media_item.get('description')
            seeders = media_item.get('seeders')
            peers = media_item.get('peers')

            # 检查资源类型
            match_flag, res_order, res_typestr = self.media.check_resouce_types(title, self.__res_type)
            if not match_flag:
                log.debug("【JACKETT】%s 资源类型不匹配！" % title)
                continue

            # 识别种子名称
            media_info = self.media.get_media_info(title)
            if not media_info or not media_info.tmdb_info:
                log.debug("【JACKETT】%s 未检索媒体信息！" % title)
                continue

            search_type = media_info.type
            media_title = media_info.title
            media_year = media_info.year
            vote_average = media_info.vote_average
            backdrop_path = media_info.backdrop_path
            # 名称是否匹配
            if key_word in media_title or key_word in "%s %s" % (media_info.en_name, media_info.cn_name):
                match_flag = True
            else:
                match_flag = False
                log.info("【JACKETT】%s 未匹配名称：%s" % (title, key_word))

            # 检查标题是否匹配剧集
            if match_flag:
                match_flag = self.__is_jackett_match_sey(media_info, s_num, e_num, year)

            # 匹配到了
            if match_flag:
                season = media_info.get_season_string()
                episode = media_info.get_episode_string()
                es_string = media_info.get_season_episode_string()
                res_info = {"site_order": order_seq,
                            "site_name": indexer_name,
                            "type": search_type,
                            "title": media_title,
                            "year": media_year,
                            "enclosure": enclosure,
                            "torrent_name": title,
                            "vote_average": vote_average,
                            "res_order": res_order,
                            "res_type": res_typestr,
                            "backdrop_path": backdrop_path,
                            "size": size,
                            "description": description,
                            "seeders": seeders,
                            "peers": peers,
                            "season": season,
                            "episode": episode,
                            "es_string": es_string,
                            "index": index}
                if res_info not in ret_array:
                    index_sucess = index_sucess + 1
                    ret_array.append(res_info)
                # 控制匹配数量，避免查TMDB时间太长
                index_num = index_num + 1
                if index_num >= JACKETT_MAX_INDEX_NUM:
                    break
            else:
                log.info("【JACKETT】%s 不匹配，跳过..." % title)
                continue
        log.info("【JACKETT】%s 共检索到 %s 条有效资源" % (index, index_sucess))
        return ret_array

    # 根据关键字调用 Jackett API 检索
    def search_medias_from_word(self, key_word, s_num, e_num, year):
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
        log.info("【JACKETT】开始并行检索，线程数：%s" % len(self.__indexers))
        executor = ThreadPoolExecutor(max_workers=len(self.__indexers))
        all_task = []
        order_seq = 100
        for index in self.__indexers:
            order_seq = order_seq - 1
            task = executor.submit(self.seach_indexer, order_seq, index, search_word, key_word, s_num, e_num, year)
            all_task.append(task)
        ret_array = []
        for future in as_completed(all_task):
            result = future.result()
            if result:
                ret_array = ret_array + result
        log.info("【JACKETT】所有API检索完成，有效资源数：%s" % len(ret_array))
        return ret_array

    # 按关键字，检索排序去重后择优下载
    def search_one_media(self, content):
        key_word, season_num, episode_num, year = get_keyword_from_string(content)
        self.message.sendmsg("【JACKETT】开始检索 %s ..." % content)
        media_list = self.search_medias_from_word(key_word, season_num, episode_num, year)
        if len(media_list) == 0:
            self.message.sendmsg("【JACKETT】%s 未检索到任何媒体资源！" % content, "")
        else:
            self.message.sendmsg(title="【JACKETT】%s 共检索到 %s 个有效资源，即将择优下载！" % (content, len(media_list)), text="")
            # 去重择优后开始添加下载
            for can_item in self.__get_download_list(media_list):
                # 添加PT任务
                log.info("【JACKETT】添加PT任务：%s，url= %s" % (can_item.get('title'), can_item.get('enclosure')))
                ret = self.downloader.add_pt_torrent(can_item.get('enclosure'))
                if ret:
                    self.message.send_download_message("Jackett", can_item, can_item.get('es_string'))
                else:
                    log.error("【JACKETT】添加下载任务失败：%s" % can_item.get('title'))
                    self.message.sendmsg("【JACKETT】添加PT任务失败：%s" % can_item.get('title'))

    # 种子名称关键字匹配
    @staticmethod
    def __is_jackett_match_sey(media_info, s_num, e_num, year_str):
        if s_num:
            if not media_info.is_in_seasion(s_num):
                log.info("【JACKETT】%s 未匹配季：%s" % (media_info.org_string, s_num))
                return False
        if e_num:
            if not media_info.is_in_episode(e_num):
                log.info("【JACKETT】%s 未匹配集：%s" % (media_info.org_string, e_num))
                return False
        if year_str:
            if str(media_info.year) != year_str:
                log.info("【JACKETT】%s 未匹配年份：%s" % (media_info.org_string, year_str))
                return False
        return True

    # 排序、去重 选种
    @staticmethod
    def __get_download_list(media_list):
        if not media_list:
            return []

        # 排序函数
        def get_sort_str(x):
            return "%s%s%s%s" % (str(x['title']).ljust(100, ' '),
                                 str(x['res_order']).rjust(3, '0'),
                                 str(x['seeders']).rjust(10, '0'),
                                 str(x['site_order']).rjust(3, '0'))

        # 匹配的资源中排序分组选最好的一个下载
        # 按站点顺序、资源匹配顺序、做种人数下载数逆序排序
        media_list = sorted(media_list, key=lambda x: get_sort_str(x), reverse=True)
        log.info("【JACKETT】检索到的种子信息排序后如下：")
        for media_item in media_list:
            log.info(">标题：%s，"
                     "序号：%s，"
                     "资源类型：%s，"
                     "大小：%s，"
                     "做种：%s，"
                     "下载：%s，"
                     "季：%s，"
                     "集：%s，"
                     "种子：%s" % (media_item['title'],
                                media_item['site_order'],
                                media_item['res_type'],
                                media_item['size'],
                                media_item['seeders'],
                                media_item['peers'],
                                media_item['season'],
                                media_item['episode'],
                                media_item['torrent_name']))
        # 控重
        can_download_list_item = []
        can_download_list = []
        # 排序后重新加入数组，按真实名称控重，即只取每个名称的第一个
        for t_item in media_list:
            # 控重的主链是名称、节份、季、集
            if t_item['type'] == MediaType.TV:
                media_name = "%s%s%s%s" % (t_item.get('title'),
                                           t_item.get('year'),
                                           t_item.get('season'),
                                           t_item.get('episode'))
            else:
                media_name = "%s%s" % (t_item.get('title'), t_item.get('year'))
            if media_name not in can_download_list:
                can_download_list.append(media_name)
                can_download_list_item.append(t_item)

        return can_download_list_item
