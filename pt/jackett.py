import re

import log
from config import get_config, JACKETT_MAX_INDEX_NUM
from utils.functions import parse_jackettxml, str_filesize
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

    # 根据关键字调用 Jackett API 检索
    def search_medias_from_word(self, key_word, s_str, e_str, year_str):
        ret_array = []
        if not key_word:
            return []
        if not self.__api_key or not self.__indexers:
            log.error("【JACKETT】Jackett配置信息有误！")
            return []
        if year_str:
            search_word = "%s %s" % (key_word, year_str)
        else:
            search_word = key_word
        # 开始逐个检索将组合返回
        order_seq = 100
        # 已检索的信息不重复检索
        media_names = {}
        for index in self.__indexers:
            if not index:
                continue
            log.info("【JACKETT】开始检索Indexer：%s ..." % index)
            order_seq = order_seq - 1
            api_url = "%sapi?apikey=%s&t=search&q=%s" % (index, self.__api_key, search_word)
            media_array = parse_jackettxml(api_url)
            if len(media_array) == 0:
                log.warn("【JACKETT】%s 未检索到资源！" % index)
                continue
            # 从检索结果中匹配符合资源条件的记录
            index_num = 0
            for media_item in media_array:
                title = media_item.get('title')
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

                # 检索媒体信息
                media_name = self.media.get_pt_media_name(title)
                media_year = self.media.get_media_file_year(title)
                media_key = "%s%s" % (media_name, media_year)
                if not media_names.get(media_key):
                    index_num = index_num + 1
                    # 每个源最多查10个，避免查TMDB时间太长，已经查过的不计数
                    if index_num >= JACKETT_MAX_INDEX_NUM:
                        break
                    media_info = self.media.get_media_info_on_name(title, media_name, media_year)
                    media_names[media_key] = media_info
                else:
                    media_info = media_names.get(media_key)

                if not media_info:
                    log.debug("【JACKETT】%s 未检索媒体信息！" % title)
                    continue
                search_type = media_info["search_type"]
                media_id = media_info["id"]
                media_title = media_info["title"]
                media_year = media_info["year"]
                vote_average = media_info['vote_average']
                backdrop_path = self.media.get_backdrop_image(media_info['backdrop_path'], media_id)
                # 是否匹配
                if key_word in media_title:
                    match_flag = True
                else:
                    # 检查标题是否匹配剧集
                    match_flag = self.__is_jackett_match_title(title, key_word, s_str, e_str, year_str)

                # 匹配到了
                if match_flag:
                    season = self.media.get_media_file_season(title)
                    episode = self.media.get_media_file_seq(title)
                    res_info = {"site_order": order_seq,
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
                                "episode": episode}
                    if res_info not in ret_array:
                        ret_array.append(res_info)
                else:
                    log.info("【JACKETT】%s 不匹配关键字，跳过..." % title)
                    continue
            log.info("【JACKETT】%s 共检索到 %s 条记录" % (index, len(ret_array)))
        return ret_array

    # 排序只检索1个下载
    def search_one_media(self, content):
        # 稍微切一下剧集吧
        season_str = ""
        episode_str = ""
        year_str = ""
        season_re = re.search(r"第[\s.]*(\d+)[\s.]*季", content, re.IGNORECASE)
        episode_re = re.search(r"第[\s.]*(\d+)[\s.]*集", content, re.IGNORECASE)
        year_re = re.search(r"[\s.(]+(\d{4})[\s.)]*", content)
        if season_re:
            season_str = 'S' + season_re.group(1).upper().rjust(2, '0')
        if episode_re:
            episode_str = 'E' + episode_re.group(1).upper().rjust(2, '0')
        if year_re:
            year_str = year_re.group(1)
        key_word = re.sub(r'第[\s.]*\d+[\s.]*季|第[\s.]*\d+[\s.]*集|[\s.(]+(\d{4})[\s.)]*', '', content,
                          re.IGNORECASE).strip()
        self.message.sendmsg("【JACKETT】开始检索 %s ..." % content)
        media_list = self.search_medias_from_word(key_word, season_str, episode_str, year_str)
        if len(media_list) == 0:
            log.warn("【JACKETT】%s 未检索到任何媒体资源！" % content)
            self.message.sendmsg("【JACKETT】%s 未检索到任何媒体资源！" % content, "")
        else:
            log.info("【JACKETT】共检索到 %s 个资源" % len(media_list))
            self.message.sendmsg(title="【JACKETT】%s 共检索到 %s 个资源，即将择优下载！" % (content, len(media_list)), text="")
            # 匹配的资源中排序选最好的一个下载
            # 所有site都检索完成，开始选种下载
            # 按站点顺序、资源匹配顺序、做种人数排序，逆序
            media_list = sorted(media_list, key=lambda x: x['title'] + str(x['site_order']).rjust(3, '0') + str(x['res_order']).rjust(3, '0') + str(x['seeders']).rjust(10, '0') + str(x['peers']).rjust(10, '0'), reverse=True)
            log.info("【JACKETT】检索到的种子信息排序后如下：")
            for media_item in media_list:
                log.info(">标题：%s，序号：%s，资源类型：%s，大小：%s，做种：%s，下载：%s，季：%s，集：%s，种子：%s" % (media_item['title'],
                                                                                     media_item['site_order'],
                                                                                     media_item['res_type'],
                                                                                     media_item['size'],
                                                                                     media_item['seeders'],
                                                                                     media_item['peers'],
                                                                                     media_item['season'],
                                                                                     media_item['episode'],
                                                                                     media_item['torrent_name']))
            # 控重
            can_download_list = []
            # 存储信息
            can_download_list_item = []
            if media_list:
                # 按真实名称、站点序号、资源序号进行排序
                media_list = sorted(media_list, key=lambda x: x['title'] + str(x['site_order']) + str(x['res_order']))
                # 排序后重新加入数组，按真实名称控重，即只取每个名称的第一个
                for t_item in media_list:
                    # 控重的主链是名称、季、集
                    if t_item['type'] == MediaType.TV:
                        media_name = "%s%s%s%s" % (t_item.get('title'), t_item.get('year'), t_item.get('season'), t_item.get('episode'))
                    else:
                        media_name = "%s%s" % (t_item.get('title'), t_item.get('year'))
                    if media_name not in can_download_list:
                        can_download_list.append(media_name)
                        can_download_list_item.append(t_item)

            # 开始添加下载
            for can_item in can_download_list_item:
                # 添加PT任务
                log.info("【JACKETT】添加PT任务：%s，url= %s" % (can_item.get('title'), can_item.get('enclosure')))
                ret = self.downloader.add_pt_torrent(can_item.get('enclosure'))
                if ret:
                    self.__send_jackett_message(can_item)
                else:
                    log.error("【JACKETT】添加下载任务失败：%s" % can_item.get('title'))
                    self.message.sendmsg("【JACKETT】添加PT任务失败：%s" % can_item.get('title'))

    @staticmethod
    def __is_jackett_match_title(title, word, s_str, e_str, year_str):
        if word:
            if title.find(word) == -1:
                log.info("【JACKETT】%s 未匹配关键字：%s" % (title, word))
                return False
        if s_str:
            if title.find(s_str) == -1:
                log.info("【JACKETT】%s 未匹配剧：%s" % (title, s_str))
                return False
        if e_str:
            if title.find(e_str) == -1:
                log.info("【JACKETT】%s 未匹配集：%s" % (title, e_str))
                return False
        if year_str:
            if title.find(year_str) == -1:
                log.info("【JACKETT】%s 未匹配年份：%s" % (title, year_str))
                return False
        return True

    def __send_jackett_message(self, can_item):
        tt = can_item.get('title')
        va = can_item.get('vote_average')
        yr = can_item.get('year')
        bp = can_item.get('backdrop_path')
        tp = can_item.get('type')
        if tp in MediaType:
            tp = tp.value
        se = self.media.get_sestring_from_name(can_item.get('torrent_name'))
        msg_title = tt
        if yr:
            msg_title = "%s (%s)" % (tt, str(yr))
        if se:
            msg_text = "来自Jackett的%s %s %s 已开始下载" % (tp, msg_title, se)
        else:
            msg_text = "来自Jackett的%s %s 已开始下载" % (tp, msg_title)
        if va and va != '0':
            msg_title = msg_title + " 评分：%s" % str(va)
        self.message.sendmsg(msg_title, msg_text, bp)
