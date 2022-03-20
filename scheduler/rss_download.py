import re
import log
from config import get_config
from utils.functions import parse_rssxml, is_chinese
from message.send import Message
from pt.downloader import Downloader
from rmt.media import Media
from utils.sqls import get_movie_keys, get_tv_keys, is_torrent_rssd_by_name, insert_rss_torrents
from utils.types import MediaType, SearchType

RSS_RUNNING_FLAG = False
RSS_CACHED_TORRENTS = []


class RSSDownloader:
    __movie_subtypedir = True
    __tv_subtypedir = True
    __movie_path = None
    __tv_path = None
    __rss_chinese = None

    message = None
    media = None
    downloader = None

    def __init__(self):
        self.message = Message()
        self.media = Media()
        self.downloader = Downloader()

        config = get_config()
        if config.get('pt'):
            self.__rss_chinese = config['pt'].get('rss_chinese')
        if config.get('media'):
            self.__movie_path = config['media'].get('movie_path')
            self.__tv_path = config['media'].get('tv_path')
            self.__movie_subtypedir = config['media'].get('movie_subtypedir', True)
            self.__tv_subtypedir = config['media'].get('tv_subtypedir', True)

    def run_schedule(self):
        global RSS_RUNNING_FLAG
        try:
            if RSS_RUNNING_FLAG:
                log.error("【RUN】rssdownload任务正在执行中...")
            else:
                RSS_RUNNING_FLAG = True
                self.__rssdownload()
                RSS_RUNNING_FLAG = False
        except Exception as err:
            RSS_RUNNING_FLAG = False
            log.error("【RUN】执行任务rssdownload出错：" + str(err))

    def __rssdownload(self):
        global RSS_CACHED_TORRENTS
        config = get_config()
        pt = config.get('pt')
        if not pt:
            return
        sites = pt.get('sites')
        if not sites:
            return
        log.info("【RSS】开始RSS订阅...")

        # 读取关键字配置
        movie_keys = get_movie_keys()
        if not movie_keys:
            log.warn("【RSS】未配置电影订阅关键字！")
        else:
            log.info("【RSS】电影订阅规则清单：%s" % " ".join('%s' % key for key in movie_keys))

        tv_keys = get_tv_keys()
        if not tv_keys:
            log.warn("【RSS】未配置电视剧订阅关键字！")
        else:
            log.info("【RSS】电视剧订阅规则清单：%s" % " ".join('%s' % key for key in tv_keys))

        if not movie_keys and not tv_keys:
            return

        # 代码站点配置优先级的序号
        order_seq = 0
        rss_download_torrents = []
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
                    torrent_name = res['title']
                    # 去掉第1个以[]开关的种子名称，有些站会把类型加到种子名称上，会误导识别
                    # 非贪婪只匹配一个
                    torrent_name = re.sub(r'^\[.+?]', "", torrent_name, count=1)
                    enclosure = res['enclosure']
                    # 判断是否处理过
                    if enclosure in RSS_CACHED_TORRENTS:
                        log.info("【RSS】%s 已处理过，跳过..." % torrent_name)
                        continue
                    else:
                        RSS_CACHED_TORRENTS.append(enclosure)

                    log.info("【RSS】开始检索媒体信息:" + torrent_name)

                    # 识别种子名称，开始检索TMDB
                    media_info = self.media.get_media_info(torrent_name)
                    if not media_info or not media_info.tmdb_info:
                        continue
                    if self.__rss_chinese and not is_chinese(media_info.title):
                        log.info("【RSS】该媒体在TMDB中没有中文描述，跳过：%s" % media_info.title)
                        continue
                    # 检查这个名字是不是下过了
                    if is_torrent_rssd_by_name(media_info.title,
                                               media_info.year,
                                               media_info.get_season_string(),
                                               media_info.get_season_episode_string()):
                        log.info("【RSS】%s %s 已处理过，跳过..." % (media_info.title, media_info.year))
                        continue
                    # 检查种子名称或者标题是否匹配
                    match_flag = self.__is_torrent_match(media_info, movie_keys, tv_keys)
                    if match_flag:
                        log.info("【RSS】%s 匹配成功！" % torrent_name)
                    else:
                        log.info("【RSS】%s 不匹配关键字！" % torrent_name)
                        continue
                    # 匹配后，看资源类型是否满足
                    # 代表资源类型在配置中的优先级顺序
                    res_order = 99
                    res_typestr = ""
                    if match_flag:
                        # 确定标题中是否有资源类型关键字，并返回关键字的顺序号
                        match_flag, res_order, res_typestr = self.media.check_resouce_types(torrent_name, res_type)
                        if not match_flag:
                            log.info("【RSS】%s 资源类型不匹配！" % torrent_name)
                            continue
                    # 插入数据库
                    insert_rss_torrents(media_info)
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
            log.info("【RSS】%s 处理结束，匹配到 %s 个有效资源！" % (rss_job, res_num))
        log.info("【RSS】所有RSS处理结束，共 %s 个有效资源！" % len(rss_download_torrents))

        # 去重择优后开始添加下载
        download_medias = self.downloader.check_and_add_pt(SearchType.RSS, rss_download_torrents)
        log.info("【RSS】实际下载了 %s 个资源！" % len(download_medias))

        self.__running_flag = False

    @staticmethod
    def __is_torrent_match(media_info, movie_keys, tv_keys):
        # 按种子标题匹配
        check_title = "%s %s %s" % (media_info.cn_name, media_info.en_name, media_info.year)
        if media_info.type == MediaType.MOVIE:
            # 按电影匹配
            for key in movie_keys:
                # 中英文名跟年份都纳入匹配
                if re.search(r"%s" % key, check_title, re.IGNORECASE):
                    return True
        else:
            # 按电视剧匹配
            for key in tv_keys:
                # 中英文名跟年份都纳入匹配
                if re.search(r"%s" % key, check_title, re.IGNORECASE):
                    return True
        # 按媒体信息匹配
        if media_info.type == MediaType.MOVIE:
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


if __name__ == "__main__":
    RSSDownloader().run_schedule()
