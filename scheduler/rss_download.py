import re
import log
from config import get_config
from rmt.filetransfer import FileTransfer
from utils.functions import parse_rssxml, is_chinese
from message.send import Message
from pt.downloader import Downloader
from rmt.media import Media
from utils.types import MediaType


class RSSDownloader:
    __rss_cache_list = []
    __running_flag = False

    __movie_subtypedir = True
    __tv_subtypedir = True
    __movie_path = None
    __tv_path = None
    __rss_chinese = None

    message = None
    media = None
    downloader = None
    filetransfer = None

    def __init__(self):
        self.message = Message()
        self.media = Media()
        self.downloader = Downloader()
        self.filetransfer = FileTransfer()

        config = get_config()
        if config.get('pt'):
            self.__rss_chinese = config['pt'].get('rss_chinese')
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

    def __rssdownload(self):
        config = get_config()
        pt = config.get('pt')
        if not pt:
            return
        sites = pt.get('sites')
        if not sites:
            return
        log.info("【RSS】开始RSS订阅...")

        # 读取关键字配置
        movie_keys = pt.get('movie_keys')
        if not movie_keys:
            log.warn("【RSS】未配置电影订阅关键字！")
        else:
            if not isinstance(movie_keys, list):
                movie_keys = [movie_keys]
            log.info("【RSS】电影订阅规则清单：%s" % " ".join('%s' % key for key in movie_keys))

        tv_keys = pt.get('tv_keys')
        if not tv_keys:
            log.warn("【RSS】未配置电视剧订阅关键字！")
        else:
            if not isinstance(tv_keys, list):
                tv_keys = [tv_keys]
            log.info("【RSS】电视剧订阅规则清单：%s" % " ".join('%s' % key for key in tv_keys))

        if not movie_keys and not tv_keys:
            return

        self.__running_flag = True
        # 保存命中的资源信息
        rss_download_torrents = []
        # 代码站点配置优先级的序号
        order_seq = 0
        for rss_job, job_info in sites.items():
            order_seq = order_seq + 1
            # 读取子配置
            rssurl = job_info.get('rssurl')
            if not rssurl:
                log.error("【RSS】%s 未配置rssurl，跳过..." % str(rss_job))
                continue
            res_type = job_info.get('res_type')
            if res_type and not isinstance(res_type, list):
                res_type = [res_type]

            # 开始下载RSS
            log.info("【RSS】正在处理：%s" % rss_job)
            rss_result = parse_rssxml(rssurl)
            if len(rss_result) == 0:
                log.warn("【RSS】%s 未下载到数据！" % rss_job)
                continue
            else:
                log.warn("【RSS】%s 发现更新：%s" % (rss_job, len(rss_result)))

            res_num = 0
            for res in rss_result:
                try:
                    title = res['title']
                    # 去掉第1个以[]开关的种子名称，有些站会把类型加到种子名称上，会误导识别
                    # 非贪婪只匹配一个
                    title = re.sub(r'^\[.+?]', "", title, count=1)
                    enclosure = res['enclosure']
                    # 判断是否处理过
                    if enclosure not in self.__rss_cache_list:
                        self.__rss_cache_list.append(enclosure)
                    else:
                        log.debug("【RSS】%s 已处理过，跳过..." % title)
                        continue

                    log.info("【RSS】开始检索媒体信息:" + title)

                    # 识别种子名称，开始检索TMDB
                    media_info = self.media.get_media_info(title)
                    if not media_info.tmdb_info:
                        continue
                    search_type = media_info.type
                    media_year = media_info.year
                    media_title = media_info.title
                    media_catagory = media_info.category
                    vote_average = media_info.vote_average
                    backdrop_path = media_info.backdrop_path
                    if self.__rss_chinese and not is_chinese(media_title):
                        log.info("【RSS】该媒体在TMDB中没有中文描述，跳过：%s" % media_title)
                        continue
                    # 检查种子名称或者标题是否匹配
                    match_flag = self.__is_torrent_match(media_info, search_type, movie_keys, tv_keys)
                    if match_flag:
                        log.info("【RSS】%s 匹配成功！" % title)
                    else:
                        log.info("【RSS】%s 与规则不匹配！" % title)
                        continue
                    # 匹配后，看资源类型是否满足
                    # 代表资源类型在配置中的优先级顺序
                    res_order = 99
                    res_typestr = ""
                    if match_flag and res_type:
                        # 确定标题中是否有资源类型关键字，并返回关键字的顺序号
                        match_flag, res_order, res_typestr = self.media.check_resouce_types(title, res_type)
                        if not match_flag:
                            log.info("【RSS】%s 资源类型不匹配！" % title)
                            continue
                    # 是否在媒体库中存在
                    if search_type == MediaType.TV:
                        media_dest = self.__tv_path
                    else:
                        media_dest = self.__movie_path
                    dir_exist_flag, ret_dir_path, file_exist_flag, ret_file_path = self.filetransfer.is_media_exists(media_dest, search_type, media_catagory, media_title, media_year)
                    if dir_exist_flag:
                        log.info("【RSS】电影目录已存在该电影：%s" % title)
                        continue
                    # 返回对象
                    res_info = {"site_order": order_seq,
                                "site": rss_job,
                                "type": search_type,
                                "title": media_title,
                                "year": media_year,
                                "enclosure": enclosure,
                                "torrent_name": title,
                                "vote_average": vote_average,
                                "res_order": res_order,
                                "res_type": res_typestr,
                                "backdrop_path": backdrop_path,
                                "es_string": media_info.get_season_episode_string()}
                    if res_info not in rss_download_torrents:
                        res_num = res_num + 1
                        rss_download_torrents.append(res_info)
                except Exception as e:
                    log.error("【RSS】错误：%s" % str(e))
                    continue
            log.info("【RSS】%s 处理结束，匹配到 %s 个有效资源！" % (rss_job, res_num))
        log.info("【RSS】所有RSS处理结束，共 %s 个有效资源！" % len(rss_download_torrents))
        # 开始添加下载
        can_download_list = self.__get_download_list(rss_download_torrents)
        log.info("【RSS】共有 %s 个需要添加下载！" % len(can_download_list))
        for can_item in can_download_list:
            # 添加PT任务
            log.info("【RSS】添加PT任务：%s，url= %s" % (can_item.get('title'), can_item.get('enclosure')))
            ret = self.downloader.add_pt_torrent(can_item.get('enclosure'))
            if ret:
                self.message.send_download_message("RSS", can_item, can_item.get('es_string'))
            else:
                log.error("【RSS】添加PT任务出错：%s" % can_item.get('title'))

        self.__running_flag = False

    @staticmethod
    def __is_torrent_match(media_info, search_type, movie_keys, tv_keys):
        # 按种子标题匹配
        check_title = "%s %s %s" % (media_info.cn_name, media_info.en_name, media_info.year)
        if search_type == MediaType.MOVIE:
            # 按电影匹配
            for key in movie_keys:
                # 中英文名跟年份都纳入匹配
                if re.search(str(key), check_title, re.IGNORECASE):
                    return True
        else:
            # 按电视剧匹配
            for key in tv_keys:
                # 中英文名跟年份都纳入匹配
                if re.search(str(key), check_title, re.IGNORECASE):
                    return True
        # 按媒体信息匹配
        if search_type == MediaType.MOVIE:
            # 按电影匹配
            for key in movie_keys:
                if str(key) == media_info.title:
                    return True
        else:
            # 按电视剧匹配
            for key in tv_keys:
                if str(key) == media_info.title:
                    return True
        return False

    # 排序、去重、选种
    @staticmethod
    def __get_download_list(media_list):
        if not media_list:
            return []

        # 排序函数
        def get_sort_str(x):
            return "%s%s%s" % (str(x['title']).ljust(100, ' '), str(x['site_order']).rjust(3, '0'), str(x['res_order']).rjust(3, '0'))
        # 所有site都检索完成，开始选种下载
        # 用来控重
        can_download_list = []
        # 用来存储信息
        can_download_list_item = []
        # 按真实名称、站点序号、资源序号进行排序
        media_list = sorted(media_list, key=lambda x: get_sort_str(x), reverse=True)
        # 排序后重新加入数组，按真实名称控重，即只取每个名称的第一个
        for t_item in media_list:
            media_name = "%s (%s)" % (t_item.get('title'), t_item.get('year'))
            if media_name not in can_download_list:
                can_download_list.append(media_name)
                can_download_list_item.append(t_item)

        return can_download_list_item


if __name__ == "__main__":
    RSSDownloader().run_schedule()
