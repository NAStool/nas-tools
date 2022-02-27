import os
import re
import requests
import log
from xml.dom.minidom import parse
import xml.dom.minidom

from config import get_config, RMT_MOVIETYPE, RMT_MEDIAEXT
from functions import is_chinese
from message.send import Message
from rmt.media import Media
from rmt.qbittorrent import Qbittorrent
from rmt.transmission import Transmission


class RSSDownloader:
    __rss_cache_list = []
    __rss_cache_name = []
    __running_flag = False

    __movie_subtypedir = True
    __tv_subtypedir = True
    __pt_client = None
    __rss_jobs = None
    __movie_path = None
    __tv_path = None
    __rss_chinese = None
    __save_path = None

    message = None
    media = None
    qbittorrent = None
    transmission = None

    def __init__(self):
        self.message = Message()
        self.media = Media()

        config = get_config()
        if config.get('pt'):
            self.__rss_jobs = config['pt'].get('sites')
            self.__rss_chinese = config['pt'].get('rss_chinese')
            self.__pt_client = config['pt'].get('pt_client')
            if self.__pt_client == "qbittorrent":
                if config.get('qbittorrent'):
                    self.qbittorrent = Qbittorrent()
                    self.__save_path = config['qbittorrent'].get('save_path')
            elif self.__pt_client == "transmission":
                if config.get('transmission'):
                    self.transmission = Transmission()
                    self.__save_path = config['transmission'].get('save_path')
        if config.get('media'):
            self.__movie_path = config['media'].get('movie_path')
            self.__tv_path = config['media'].get('tv_path')
            self.__movie_subtypedir = config['media'].get('movie_subtypedir', True)
            self.__tv_subtypedir = config['media'].get('tv_subtypedir', True)

    def run_schedule(self):
        try:
            if self.__running_flag:
                log.error("【RUN】rssdownload任务正在执行中...")
            else:
                self.__rssdownload()
        except Exception as err:
            self.__running_flag = False
            log.error("【RUN】执行任务rssdownload出错：" + str(err))
            self.message.sendmsg("【NASTOOL】执行任务rssdownload出错！", str(err))

    def reset_cache_list(self):
        self.__rss_cache_list = []
        self.__rss_cache_name = []

    @staticmethod
    def __parse_rssxml(url):
        ret_array = []
        if not url:
            return ret_array
        try:
            log.info("【RSS】开始下载：" + url)
            ret = requests.get(url)
        except Exception as e:
            log.error("【RSS】下载失败：" + str(e))
            return ret_array
        if ret:
            ret_xml = ret.text
            try:
                # 解析XML
                dom_tree = xml.dom.minidom.parseString(ret_xml)
                rootNode = dom_tree.documentElement
                items = rootNode.getElementsByTagName("item")
                for item in items:
                    # 获取XML值
                    title = item.getElementsByTagName("title")[0].firstChild.data
                    category = item.getElementsByTagName("category")[0].firstChild.data
                    enclosure = item.getElementsByTagName("enclosure")[0].getAttribute("url")
                    tmp_dict = {'title': title, 'category': category, 'enclosure': enclosure}
                    ret_array.append(tmp_dict)
                log.info("【RSS】下载成功，发现更新：" + str(len(items)))
            except Exception as e2:
                log.error("【RSS】解析失败：" + str(e2))
                return ret_array
        return ret_array

    def __rssdownload(self):
        succ_list = []
        if not self.__rss_jobs:
            return
        self.__running_flag = True
        for rss_job, job_info in self.__rss_jobs.items():
            # 读取子配置
            rssurl = job_info['rssurl']
            if not rssurl:
                log.error("【RSS】%s 未配置rssurl，跳过..." % str(rss_job))
                continue
            movie_type = job_info['movie_type']
            movie_res = job_info['movie_re']
            log.info("【RSS】%s 电影规则清单：%s" % (rss_job, str(movie_res)))
            tv_res = job_info['tv_re']
            log.info("【RSS】%s 电视剧规则清单：%s" % (rss_job, str(tv_res)))
            # 下载RSS
            log.info("【RSS】正在处理：%s" % rss_job)
            rss_result = self.__parse_rssxml(rssurl)
            if len(rss_result) == 0:
                continue
            for res in rss_result:
                try:
                    title = res['title']
                    category = res['category']
                    enclosure = res['enclosure']
                    # 判断是否处理过
                    if enclosure not in self.__rss_cache_list:
                        self.__rss_cache_list.append(enclosure)
                    else:
                        log.debug("【RSS】%s 已处理过，跳过..." % title)
                        continue
                    match_flag = False
                    if movie_type and (category in movie_type):
                        search_type = "电影"
                        # 匹配种子标题是否匹配关键字
                        for movie_re in movie_res:
                            if re.search(movie_re, title):
                                match_flag = True
                                break
                    else:
                        search_type = "电视剧"
                        # 匹配种子标题是否匹配关键字
                        for tv_re in tv_res:
                            if re.search(tv_re, title):
                                match_flag = True
                                break
                    if match_flag:
                        log.info("【RSS】%s 种子标题匹配成功!" % title)

                    log.info("【RSS】开始检索媒体信息:" + title)
                    media_info = self.media.get_media_info_on_name(title, search_type)
                    if not media_info:
                        log.error("【RSS】检索媒体信息出错！")
                        continue
                    media_type = media_info["type"]
                    media_title = media_info["title"]
                    media_year = media_info["year"]
                    if media_info.get('backdrop_path'):
                        backdrop_path = media_info['backdrop_path']
                    else:
                        backdrop_path = ""
                    if backdrop_path:
                        backdrop_path = "https://image.tmdb.org/t/p/w500" + backdrop_path

                    if media_info.get('vote_average'):
                        vote_average = media_info['vote_average']
                    else:
                        vote_average = ""

                    if self.__rss_chinese and not is_chinese(media_title):
                        log.info("【RSS】该媒体在TMDB中没有中文描述，跳过：%s" % media_title)
                        continue

                    # 匹配媒体信息标题是否匹配关键字
                    if search_type == "电影":
                        # 匹配种子标题是否匹配关键字，需要完全匹配
                        for movie_re in movie_res:
                            if movie_re == media_title:
                                match_flag = True
                                log.info("【RSS】%s 电影名称匹配成功!" % title)
                                break
                    else:
                        # 匹配种子标题是否匹配关键字，需要完全匹配
                        for tv_re in tv_res:
                            if tv_re == media_title:
                                log.info("【RSS】%s 电视剧名称匹配成功!" % title)
                                match_flag = True
                                break

                    # 匹配后处理...
                    if match_flag:
                        # 判断是否已存在
                        if media_year:
                            media_name = media_title + " (" + media_year + ")"
                        else:
                            media_name = media_title
                        if search_type == "电影":
                            if media_name not in self.__rss_cache_name:
                                self.__rss_cache_name.append(media_name)
                            else:
                                log.debug("【RSS】电影标题已处理过，跳过：%s" % media_name)
                                continue
                            # 确认是否已存在
                            exist_flag = False
                            media_path = os.path.join(self.__movie_path, media_name)
                            if self.__movie_subtypedir:
                                for m_type in RMT_MOVIETYPE:
                                    media_path = os.path.join(self.__movie_path, m_type, media_name)
                                    # 目录是否存在
                                    if os.path.exists(media_path):
                                        exist_flag = True
                                        break
                            else:
                                exist_flag = os.path.exists(media_path)

                            if exist_flag:
                                log.info("【RSS】电影目录已存在该电影，跳过：%s" % media_path)
                                continue
                        else:
                            # 剧集目录
                            if self.__tv_subtypedir:
                                media_path = os.path.join(self.__tv_path, media_type, media_name)
                            else:
                                media_path = os.path.join(self.__tv_path, media_name)
                            # 剧集是否存在
                            # Sxx
                            file_season = self.media.get_media_file_season(title)
                            # 季 Season xx
                            season_str = "Season " + str(int(file_season.replace("S", "")))
                            season_dir = os.path.join(media_path, season_str)
                            # Exx
                            file_seq = self.media.get_media_file_seq(title)
                            if file_seq != "":
                                # 集 xx
                                file_seq_num = str(int(file_seq.replace("E", "").replace("P", "")))
                                # 文件路径
                                file_path = os.path.join(season_dir,
                                                         media_title + " - " +
                                                         file_season + file_seq + " - " +
                                                         "第 " + file_seq_num + " 集")
                                exist_flag = False
                                for ext in RMT_MEDIAEXT:
                                    log.debug("【RSS】路径：" + file_path + ext)
                                    if os.path.exists(file_path + ext):
                                        exist_flag = True
                                        log.error("【RSS】该剧集文件已存在，跳过：%s" % (file_path + ext))
                                        break
                                if exist_flag:
                                    continue
                        # 添加PT任务
                        log.info("【RSS】添加PT任务：%s，url= %s" % (title, enclosure))
                        try:
                            ret = None
                            if self.__pt_client == "qbittorrent":
                                if self.qbittorrent:
                                    ret = self.qbittorrent.add_qbittorrent_torrent(enclosure, self.__save_path)
                            elif self.__pt_client == "transmission":
                                if self.transmission:
                                    ret = self.transmission.add_transmission_torrent(enclosure, self.__save_path)
                            else:
                                log.error("【RSS】PT下载软件配置有误！")
                                return
                            if ret:
                                msg_item = "> " + media_name + "：" + title
                                if msg_item not in succ_list:
                                    succ_list.append(msg_item)
                                    if vote_average and vote_average != '0':
                                        msg_title = "%s（%s）评分：%s" % (media_title, media_year, str(vote_average))
                                    else:
                                        msg_title = "%s（%s）" % (media_title, media_year)
                                    self.message.sendmsg(msg_title,
                                                         "来自RSS的 %s %s 已开始下载" % (search_type, media_title + media_year),
                                                         backdrop_path)
                        except Exception as e:
                            log.error("【RSS】添加PT任务出错：%s" % str(e))
                    else:
                        log.info("【RSS】当前资源与规则不匹配，跳过...")
                except Exception as e:
                    log.error("【RSS】错误：%s" % str(e))
                    continue
            self.__running_flag = False
            log.info("【RSS】%s 处理结束！" % rss_job)


if __name__ == "__main__":
    RSSDownloader().run_schedule()
