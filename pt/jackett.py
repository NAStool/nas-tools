import re

import log
from config import get_config, JACKETT_MAX_INDEX_NUM
from functions import parse_rssxml
from message.send import Message
from pt.downloader import Downloader
from rmt.media import Media


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
    def search_medias_from_word(self, key_word, s_str, e_str):
        ret_array = []
        if not key_word:
            return []
        if not self.__api_key or not self.__indexers:
            log.error("【JACKETT】Jackett配置信息有误！")
            return []
        # 开始逐个检索将组合返回
        order_seq = 0
        for index in self.__indexers:
            if not index:
                continue
            log.info("【JACKETT】开始检索Indexer：%s ..." % index)
            order_seq = order_seq + 1
            api_url = "%sapi?apikey=%s&t=search&q=%s" % (index, self.__api_key, key_word)
            media_array = parse_rssxml(api_url)
            if len(media_array) == 0:
                log.warn("【JACKETT】未检索到资源！")
                continue
            # 从检索结果中匹配符合资源条件的记录
            index_num = 0
            for media_item in media_array:
                index_num = index_num + 1
                if index_num >= JACKETT_MAX_INDEX_NUM:
                    break
                title = media_item.get('title')
                enclosure = media_item.get('enclosure')
                # 检查剧集
                if s_str:
                    if title.find(s_str) == -1:
                        log.info("【JACKETT】%s 未匹配剧：%s" % (title, s_str))
                        continue
                if e_str:
                    if title.find(e_str) == -1:
                        log.info("【JACKETT】%s 未匹配集：%s" % (title, e_str))
                        continue

                match_flag, res_order, res_typestr = self.media.check_resouce_types(title, self.__res_type)
                if not match_flag:
                    log.debug("【JACKETT】%s 资源类型不匹配！" % title)
                    continue
                else:
                    # 自己检索一遍资源，看是否匹配
                    # 假定是电影
                    search_type = "电影"
                    # 判定是不是电视剧，如果是的话就是电视剧，否则就先按电影检索，电影检索不到时再按电视剧检索
                    if self.media.is_media_files_tv(title):
                        search_type = "电视剧"
                        media_info = self.media.get_media_info_on_name(title, search_type)
                    else:
                        # 按电影检索
                        media_info = self.media.get_media_info_on_name(title, search_type)
                        if not media_info or media_info['id'] == "0":
                            # 电影没有再按电视剧检索
                            search_type = "电视剧"
                            media_info = self.media.get_media_info_on_name(title, search_type)

                    if not media_info:
                        log.debug("【JACKETT】%s 检索媒体信息出错！" % title)
                        continue

                    media_id = media_info["id"]
                    if media_id == "0":
                        log.debug("【JACKETT】%s 未检索媒体信息！" % title)
                        continue
                    media_title = media_info["title"]
                    media_year = media_info["year"]
                    if media_info.get('vote_average'):
                        vote_average = media_info['vote_average']
                    else:
                        vote_average = ""
                    backdrop_path = self.media.get_backdrop_image(media_info.get('backdrop_path'), media_id)

                    if media_title == key_word:
                        # 匹配到了
                        res_info = {"site_order": order_seq,
                                    "type": search_type,
                                    "title": media_title,
                                    "year": media_year,
                                    "enclosure": enclosure,
                                    "torrent_name": title,
                                    "vote_average": vote_average,
                                    "res_order": res_order,
                                    "res_type": res_typestr,
                                    "backdrop_path": backdrop_path}
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
        season_re = re.search(r"第(\d+)季", content, re.IGNORECASE)
        episode_re = re.search(r"第(\d+)集", content, re.IGNORECASE)
        if season_re:
            season_str = 'S' + season_re.group(1).upper().rjust(2, '0')
        if episode_re:
            episode_str = 'E' + episode_re.group(1).upper().rjust(2, '0')
        key_word = re.sub(r'第\d+季|第\d+集', '', content, re.IGNORECASE)
        self.message.sendmsg("【JACKETT】开始检索 %s ..." % content)
        media_list = self.search_medias_from_word(key_word, season_str, episode_str)
        if len(media_list) == 0:
            log.warn("【JACKETT】%s 未检索到任何媒体资源！" % content)
            self.message.sendmsg("【JACKETT】%s 未检索到任何媒体资源！" % content, "")
        else:
            log.info("【JACKETT】共检索到 %s 个资源" % len(media_list))
            self.message.sendmsg(title="【JACKETT】%s 共检索到 %s 个资源，即将择优下载！" % (content, len(media_list)), text="")
            # 匹配的资源中排序选最好的一个下载
            # 所有site都检索完成，开始选种下载
            media_list = sorted(media_list, key=lambda x: x['title'] + str(x['site_order']) + str(x['res_order']))

            can_download_list = []
            can_download_list_item = []
            if media_list:
                # 按真实名称、站点序号、资源序号进行排序
                media_list = sorted(media_list, key=lambda x: x['title'] + str(x['site_order']) + str(x['res_order']))
                # 排序后重新加入数组，按真实名称控重，即只取每个名称的第一个
                for t_item in media_list:
                    media_name = "%s (%s)" % (t_item.get('title'), t_item.get('year'))
                    if media_name not in can_download_list:
                        can_download_list.append(media_name)
                        can_download_list_item.append(t_item)

            # 开始添加下载
            for can_item in can_download_list_item:
                # 添加PT任务
                log.info("【JACKETT】添加PT任务：%s，url= %s" % (can_item.get('title'), can_item.get('enclosure')))
                ret = self.downloader.add_pt_torrent(can_item.get('enclosure'))
                if ret:
                    tt = can_item.get('title')
                    va = can_item.get('vote_average')
                    yr = can_item.get('year')
                    bp = can_item.get('backdrop_path')
                    tp = can_item.get('type')
                    se = self.media.get_sestring_from_name(can_item.get('torrent_name'))
                    msg_title = tt
                    if yr:
                        msg_title = msg_title + " (%s)" % str(yr)
                    if se:
                        msg_text = "来自Jackett的%s %s %s 已开始下载" % (tp, msg_title, se)
                    else:
                        msg_text = "来自Jackett的%s %s 已开始下载" % (tp, msg_title)
                    if va and va != '0':
                        msg_title = msg_title + " 评分：%s" % str(va)
                    self.message.sendmsg(msg_title, msg_text, bp)
                else:
                    log.error("【JACKETT】添加下载任务失败：%s" % can_item.get('title'))
                    self.message.sendmsg("【JACKETT】添加PT任务失败：%s" % can_item.get('title'))
