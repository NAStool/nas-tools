import re
import requests
from xml.dom.minidom import parse
import xml.dom.minidom
import log
from config import Config
from utils.functions import is_chinese
from message.send import Message
from pt.downloader import Downloader
from rmt.media import Media
from utils.sqls import get_movie_keys, get_tv_keys, is_torrent_rssd_by_name, insert_rss_torrents
from utils.types import MediaType, SearchType

RSS_CACHED_TORRENTS = []


class Rss:
    __rss_chinese = None
    __sites = None
    message = None
    media = None
    downloader = None

    def __init__(self):
        self.message = Message()
        self.media = Media()
        self.downloader = Downloader()
        self.init_config()

    def init_config(self):
        config = Config()
        pt = config.get_config('pt')
        if pt:
            self.__rss_chinese = pt.get('rss_chinese')
            self.__sites = pt.get('sites')

    def rssdownload(self):
        global RSS_CACHED_TORRENTS
        if not self.__sites:
            return
        log.info("【RSS】开始RSS订阅...")

        # 读取关键字配置
        movie_keys = get_movie_keys()
        if not movie_keys:
            log.warn("【RSS】未配置电影订阅关键字")
        else:
            log.info("【RSS】电影订阅规则清单：%s" % " ".join('%s' % key for key in movie_keys))

        tv_keys = get_tv_keys()
        if not tv_keys:
            log.warn("【RSS】未配置电视剧订阅关键字")
        else:
            log.info("【RSS】电视剧订阅规则清单：%s" % " ".join('%s' % key for key in tv_keys))

        if not movie_keys and not tv_keys:
            return

        # 代码站点配置优先级的序号
        order_seq = 100
        rss_download_torrents = []
        no_exists = []
        for rss_job, job_info in self.__sites.items():
            order_seq -= 1
            # 读取子配置
            rssurl = job_info.get('rssurl')
            if not rssurl:
                log.error("【RSS】%s 未配置rssurl，跳过..." % str(rss_job))
                continue
            res_type = job_info.get('res_type')
            if isinstance(res_type, str):
                res_type = [res_type]

            # 开始下载RSS
            log.info("【RSS】正在处理：%s" % rss_job)
            rss_result = self.parse_rssxml(rssurl)
            if len(rss_result) == 0:
                log.warn("【RSS】%s 未下载到数据" % rss_job)
                continue
            else:
                log.info("【RSS】%s 发现更新：%s" % (rss_job, len(rss_result)))

            res_num = 0
            for res in rss_result:
                try:
                    torrent_name = res.get('title')
                    enclosure = res.get('enclosure')
                    description = res.get('description')
                    size = res.get('size')
                    # 判断是否处理过
                    if enclosure in RSS_CACHED_TORRENTS:
                        log.info("【RSS】%s 已处理过，跳过..." % torrent_name)
                        continue
                    else:
                        RSS_CACHED_TORRENTS.append(enclosure)

                    log.info("【RSS】开始处理：%s" % torrent_name)

                    # 识别种子名称，开始检索TMDB
                    media_info = self.media.get_media_info(title=torrent_name, subtitle=description)
                    if not media_info or not media_info.tmdb_info:
                        continue
                    if self.__rss_chinese and not is_chinese(media_info.title):
                        log.info("【RSS】%s 没有中文信息，跳过..." % media_info.title)
                        continue
                    # 检查这个名字是不是下过了
                    if is_torrent_rssd_by_name(media_info.title,
                                               media_info.year,
                                               media_info.get_season_string(),
                                               media_info.get_episode_string()):
                        log.info("【RSS】%s 已处理过，跳过..." % (media_info.get_title_string()))
                        continue
                    # 检查种子名称或者标题是否匹配
                    match_flag = self.is_torrent_match(media_info, movie_keys, tv_keys)
                    if match_flag:
                        log.info("【RSS】%s: %s %s %s 匹配成功" % (media_info.type.value,
                                                             media_info.get_title_string(),
                                                             media_info.get_season_episode_string(),
                                                             media_info.get_resource_type_string()))
                    else:
                        log.info("【RSS】%s: %s %s %s 不匹配订阅关键字" % (media_info.type.value,
                                                                 media_info.get_title_string(),
                                                                 media_info.get_season_episode_string(),
                                                                 media_info.get_resource_type_string()))
                        continue
                    # 匹配后，看资源类型是否满足
                    # 代表资源类型在配置中的优先级顺序
                    res_order = 99
                    res_typestr = ""
                    if match_flag:
                        # 确定标题中是否有资源类型关键字，并返回关键字的顺序号
                        match_flag, res_order, res_typestr = self.downloader.check_resouce_types(torrent_name, res_type)
                        if not match_flag:
                            log.info("【RSS】%s 不符合过滤条件" % torrent_name)
                            continue
                    # 判断文件大小是否匹配，只针对电影
                    if match_flag:
                        match_flag = self.downloader.is_torrent_match_size(media_info, res_type, size)
                        if not match_flag:
                            continue
                    # 插入数据库
                    insert_rss_torrents(media_info)
                    # 检查是否存在，电视剧返回不存在的集清单
                    exist_flag, no_exists = self.downloader.check_exists_medias(in_from=SearchType.RSS,
                                                                                meta_info=media_info)
                    if exist_flag:
                        continue
                    # 返回对象
                    media_info.set_torrent_info(site_order=order_seq,
                                                site=rss_job,
                                                enclosure=enclosure,
                                                res_type=res_typestr,
                                                res_order=res_order)
                    if media_info not in rss_download_torrents:
                        rss_download_torrents.append(media_info)
                        res_num = res_num + 1
                except Exception as e:
                    log.error("【RSS】错误：%s" % str(e))
                    continue
            log.info("【RSS】%s 处理结束，匹配到 %s 个有效资源" % (rss_job, res_num))
        log.info("【RSS】所有RSS处理结束，共 %s 个有效资源" % len(rss_download_torrents))
        # 去重择优后开始添加下载
        download_medias = self.downloader.check_and_add_pt(SearchType.RSS, rss_download_torrents, no_exists)
        log.info("【RSS】实际下载了 %s 个资源" % len(download_medias))

    @staticmethod
    def is_torrent_match(media_info, movie_keys, tv_keys):
        if media_info.type == MediaType.MOVIE:
            for key in movie_keys:
                if not key:
                    continue
                key = key[0]
                # 匹配种子标题
                if re.search(r"%s" % key, media_info.org_string, re.IGNORECASE):
                    return True
                # 匹配媒体名称
                if str(key).strip() == media_info.title:
                    return True
                # 匹配年份
                if str(key).strip() == str(media_info.year):
                    return True
        else:
            # 匹配种子标题
            for key in tv_keys:
                if not key:
                    continue
                key = key[0]
                # 中英文名跟年份都纳入匹配
                if re.search(r"%s" % key, media_info.org_string, re.IGNORECASE):
                    return True
                # 匹配媒体名称
                if str(key).strip() == media_info.title:
                    return True
                # 匹配年份
                if str(key).strip() == str(media_info.year):
                    return True
        return False

    # 解析RSS的XML，返回标题及URL
    @staticmethod
    def parse_rssxml(url):
        ret_array = []
        if not url:
            return []
        try:
            ret = requests.get(url, timeout=30)
        except Exception as e2:
            print(str(e2))
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
                        # 大小
                        size = 0
                        tagNames = item.getElementsByTagName("enclosure")
                        if tagNames:
                            enclosure = tagNames[0].getAttribute("url")
                            size = tagNames[0].getAttribute("length")
                        if not enclosure:
                            continue
                        if size and size.isdigit():
                            size = int(size)
                        else:
                            size = 0
                        # 描述
                        description = ""
                        tagNames = item.getElementsByTagName("description")
                        if tagNames:
                            firstChild = tagNames[0].firstChild
                            if firstChild:
                                description = firstChild.data
                        tmp_dict = {'title': title, 'enclosure': enclosure, 'size': size, 'description': description}
                        ret_array.append(tmp_dict)
                    except Exception as e1:
                        print(str(e1))
                        continue
            except Exception as e2:
                print(str(e2))
                return ret_array
        return ret_array
