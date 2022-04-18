import re
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures._base import as_completed
from xml.dom.minidom import parse
import xml.dom.minidom
import requests
import log
from config import Config
from message.send import Message
from pt.downloader import Downloader
from rmt.media import Media
from rmt.metainfo import MetaInfo
from utils.functions import str_filesize
from utils.sqls import delete_all_jackett_torrents, insert_jackett_results
from utils.types import SearchType, MediaType
from web.backend.emby import Emby


class Jackett:
    __api_key = None
    __indexers = []
    __res_type = []
    __wechat_auto = True
    media = None
    message = None
    downloader = None
    emby = None

    def __init__(self):
        self.media = Media()
        self.downloader = Downloader()
        self.message = Message()
        self.emby = Emby()
        self.media = Media()
        self.init_config()

    def init_config(self):
        config = Config()
        jackett = config.get_config('jackett')
        if jackett:
            self.__api_key = jackett.get('api_key')
            res_type = jackett.get('res_type')
            if isinstance(res_type, str):
                # 配单个字符串
                self.__res_type = [res_type]
            else:
                self.__res_type = res_type
            self.__indexers = jackett.get('indexers')
            if not isinstance(self.__indexers, list):
                self.__indexers = [self.__indexers]
            self.__wechat_auto = jackett.get('wechat_auto', True)

    # 检索一个Indexer
    def seach_indexer(self, order_seq, index, key_word, s_num, e_num, year, mtype, whole_word=False):
        if not index or not key_word:
            return None
        ret_array = []
        indexer_name = re.search(r'/indexers/([a-zA-Z0-9]+)/results/', index)
        if indexer_name:
            indexer_name = indexer_name.group(1)
        log.info("【JACKETT】开始检索Indexer：%s ..." % indexer_name)
        # 传给Jackett的需要处理掉特殊符号
        search_word = key_word.replace("：", "")
        api_url = "%sapi?apikey=%s&t=search&q=%s" % (index, self.__api_key, search_word)
        media_array = self.parse_jackettxml(api_url)
        if len(media_array) == 0:
            log.warn("【JACKETT】%s 未检索到资源" % indexer_name)
            return None
        # 从检索结果中匹配符合资源条件的记录
        index_sucess = 0
        for media_item in media_array:
            torrent_name = media_item.get('title')
            enclosure = media_item.get('enclosure')
            size = media_item.get('size')
            description = media_item.get('description')
            seeders = media_item.get('seeders')
            peers = media_item.get('peers')

            # 检查资源类型
            match_flag, res_order, res_typestr = self.downloader.check_resouce_types(torrent_name, self.__res_type)
            if not match_flag:
                log.debug("【JACKETT】%s 不符合过滤条件" % torrent_name)
                continue

            # 识别种子名称
            meta_info = MetaInfo(torrent_name)
            if mtype and meta_info.type == MediaType.TV and mtype != MediaType.TV:
                continue

            # 识别媒体信息
            media_info = self.media.get_media_info(title=torrent_name, subtitle=description)
            if not media_info or not media_info.tmdb_info:
                log.debug("【JACKETT】%s 未检索到媒体信息" % torrent_name)
                continue

            # 类型
            if mtype and media_info.type != mtype:
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
                if key_word in media_info.get_title_string() or key_word in media_info.org_string:
                    match_flag = True
                else:
                    match_flag = False
                    log.info("【JACKETT】%s：%s %s 不匹配名称：%s" % (
                        media_info.type.value, media_info.org_string, media_info.get_title_string(), key_word))

            # 检查标题是否匹配剧集
            if match_flag:
                match_flag = self.downloader.is_torrent_match_sey(media_info, s_num, e_num, year)

            # 判断文件大小是否匹配，只针对电影
            if match_flag:
                match_flag = self.downloader.is_torrent_match_size(media_info, self.__res_type, size)

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
    def search_medias_from_word(self, key_word, s_num, e_num, year, mtype, whole_word):
        if not key_word:
            return []
        if not self.__api_key or not self.__indexers:
            log.error("【JACKETT】Jackett配置信息有误！")
            return []
        # 多线程检索
        log.info("【JACKETT】开始并行检索 %s，线程数：%s" % (key_word, len(self.__indexers)))
        executor = ThreadPoolExecutor(max_workers=len(self.__indexers))
        all_task = []
        order_seq = 100
        for index in self.__indexers:
            order_seq = order_seq - 1
            task = executor.submit(self.seach_indexer, order_seq, index, key_word, s_num, e_num, year, mtype,
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
    # 名称完全匹配才会下载
    def search_one_media(self, input_str, in_from=SearchType.OT):
        if not input_str:
            log.info("【JACKETT】检索关键字有误！")
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
        log.info("【JACKETT】正在识别 %s 的媒体信息..." % content)
        media_info = self.media.get_media_info(title=content, mtype=mtype, strict=True)
        if media_info and media_info.tmdb_info:
            log.info("类型：%s，标题：%s，年份：%s" % (media_info.type.value, media_info.title, media_info.year))
            if in_from == SearchType.WX:
                self.message.sendmsg("类型：%s，标题：%s，年份：%s" % (media_info.type.value, media_info.title, media_info.year))
            # 检查是否存在，电视剧返回不存在的集清单
            exist_flag, no_exists = self.downloader.check_exists_medias(in_from=in_from,
                                                                        meta_info=media_info)
            if exist_flag is None:
                return False
            elif exist_flag:
                return True
        else:
            if in_from == SearchType.WX:
                self.message.sendmsg("%s 无法查询到任何电影或者电视剧信息，请确认名称是否正确" % content)
            log.info("【JACKETT】%s 无法查询到任何电影或者电视剧信息，请确认名称是否正确" % content)
            return False

        # 开始真正搜索资源
        if in_from == SearchType.WX:
            self.message.sendmsg("开始检索 %s ..." % media_info.title)
        log.info("【JACKETT】开始检索 %s ..." % media_info.title)
        # 查找的季
        if not media_info.begin_season:
            search_season = None
        else:
            search_season = media_info.get_season_list()
        # 查找的集
        search_episode = media_info.get_episode_list()
        if search_episode and not search_season:
            search_season = [1]
        media_list = self.search_medias_from_word(key_word=media_info.title,
                                                  s_num=search_season,
                                                  e_num=search_episode,
                                                  year=media_info.year,
                                                  mtype=media_info.type,
                                                  whole_word=True)
        if len(media_list) == 0:
            log.info("%s 未检索到任何资源" % media_info.title)
            if in_from == SearchType.WX:
                self.message.sendmsg("%s 未检索到任何资源" % media_info.title, "")
            return False
        else:
            if in_from == SearchType.WX:
                # 保存微信搜索记录
                delete_all_jackett_torrents()
                # 插入数据库
                save_media_list = self.get_torrents_group_item(media_list)
                for save_media_item in save_media_list:
                    insert_jackett_results(save_media_item)
                self.message.sendmsg(title=media_info.get_title_vote_string(),
                                     text="%s 共检索到 %s 个有效资源" % (media_info.title, len(save_media_list)),
                                     image=media_info.get_message_image(), url='search')
            # 微信未开自动下载时返回
            if in_from == SearchType.WX and not self.__wechat_auto:
                return False
            # 择优下载
            download_num, left_medias = self.downloader.check_and_add_pt(in_from, media_list, no_exists)
            # 统计下载情况，下全了返回True，没下全返回False
            if download_num == 0:
                log.info("【JACKETT】%s 搜索结果中没有符合下载条件的资源" % content)
                if in_from == SearchType.WX:
                    self.message.sendmsg("%s 搜索结果中没有符合下载条件的资源" % content, "")
                return False
            else:
                log.info("【JACKETT】实际下载了 %s 个资源" % download_num)
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

    # 解析Jackett的XML，返回标题及URL等
    @staticmethod
    def parse_jackettxml(url):
        ret_array = []
        if not url:
            return ret_array
        try:
            ret = requests.get(url, timeout=30)
        except Exception as e2:
            log.printf(str(e2))
            return []
        if ret:
            ret_xml = ret.text
            try:
                # 解析XML
                dom_tree = xml.dom.minidom.parseString(ret_xml)
                rootNode = dom_tree.documentElement
                items = rootNode.getElementsByTagName("item")
                for item in items:
                    try:
                        # 标题
                        title = ""
                        tagNames = item.getElementsByTagName("title")
                        if tagNames:
                            firstChild = tagNames[0].firstChild
                            if firstChild:
                                title = firstChild.data
                        if not title:
                            continue
                        # 种子链接
                        enclosure = ""
                        tagNames = item.getElementsByTagName("enclosure")
                        if tagNames:
                            enclosure = tagNames[0].getAttribute("url")
                        if not enclosure:
                            continue
                        # 描述
                        description = ""
                        tagNames = item.getElementsByTagName("description")
                        if tagNames:
                            firstChild = tagNames[0].firstChild
                            if firstChild:
                                description = firstChild.data
                        # 种子大小
                        size = 0
                        tagNames = item.getElementsByTagName("size")
                        if tagNames:
                            firstChild = tagNames[0].firstChild
                            if firstChild:
                                size = firstChild.data
                        # 做种数
                        seeders = 0
                        # 下载数
                        peers = 0
                        torznab_attrs = item.getElementsByTagName("torznab:attr")
                        for torznab_attr in torznab_attrs:
                            name = torznab_attr.getAttribute('name')
                            value = torznab_attr.getAttribute('value')
                            if name == "seeders":
                                seeders = value
                            if name == "peers":
                                peers = value

                        tmp_dict = {'title': title, 'enclosure': enclosure, 'description': description, 'size': size,
                                    'seeders': seeders, 'peers': peers}
                        ret_array.append(tmp_dict)
                    except Exception as e:
                        log.printf(str(e))
                        continue
            except Exception as e2:
                log.printf(str(e2))
                return ret_array
        return ret_array
