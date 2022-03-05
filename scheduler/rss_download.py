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
        # 已经检索过的信息不要重复查
        media_names = {}
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

            for res in rss_result:
                try:
                    title = res['title']
                    enclosure = res['enclosure']
                    # 判断是否处理过
                    if enclosure not in self.__rss_cache_list:
                        self.__rss_cache_list.append(enclosure)
                    else:
                        log.debug("【RSS】%s 已处理过，跳过..." % title)
                        continue

                    log.info("【RSS】开始检索媒体信息:" + title)

                    media_name = self.media.get_pt_media_name(title)
                    media_year = self.media.get_media_file_year(title)
                    media_key = "%s%s" % (media_name, media_year)
                    if not media_names.get(media_key):
                        media_info = self.media.get_media_info_on_name(title, media_name, media_year)
                        media_names[media_key] = media_info
                    else:
                        media_info = media_names.get(media_key)

                    if not media_info:
                        continue
                    if self.__rss_chinese and not is_chinese(media_info["title"]):
                        log.info("【RSS】该媒体在TMDB中没有中文描述，跳过：%s" % media_info["title"])
                        continue
                    # 检查种子名称或者标题是否匹配
                    match_flag = self.__is_torrent_match(title, media_info["title"], media_info["search_type"], movie_keys, tv_keys)
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
                    dir_exist_flag, ret_dir_path, file_exist_flag, ret_file_path = self.filetransfer.is_media_exists(media_info['search_type'], media_info['type'], media_info['title'], media_info['year'])
                    if dir_exist_flag:
                        log.info("【RSS】电影目录已存在该电影：%s" % title)
                        continue

                    # site_order res_order 从小到大排序
                    res_info = {"site_order": order_seq,
                                "site": rss_job,
                                "type": media_info['search_type'],
                                "title": media_info['title'],
                                "year": media_info['year'],
                                "enclosure": enclosure,
                                "torrent_name": title,
                                "vote_average": media_info['vote_average'],
                                "res_order": res_order,
                                "res_type": res_typestr,
                                "backdrop_path": media_info['backdrop_path']}
                    if res_info not in rss_download_torrents:
                        rss_download_torrents.append(res_info)
                except Exception as e:
                    log.error("【RSS】错误：%s" % str(e))
                    continue
            log.info("【RSS】%s 处理结束，共匹配到 %s 个资源！" % (rss_job, len(rss_download_torrents)))

        # 所有site都检索完成，开始选种下载
        # 用来控重
        can_download_list = []
        # 用来存储信息
        can_download_list_item = []
        if rss_download_torrents:
            # 按真实名称、站点序号、资源序号进行排序
            rss_download_torrents = sorted(rss_download_torrents, key=lambda x: x['title'] + str(x['site_order']).rjust(3, '0') + str(x['res_order']).rjust(3, '0'), reverse=True)
            # 排序后重新加入数组，按真实名称控重，即只取每个名称的第一个
            for t_item in rss_download_torrents:
                media_name = "%s (%s)" % (t_item.get('title'), t_item.get('year'))
                if media_name not in can_download_list:
                    can_download_list.append(media_name)
                    can_download_list_item.append(t_item)

        log.info("【RSS】RSS订阅处理完成，共有 %s 个需要添加下载！" % len(can_download_list))

        # 开始添加下载
        for can_item in can_download_list_item:
            # 添加PT任务
            log.info("【RSS】添加PT任务：%s，url= %s" % (can_item.get('title'), can_item.get('enclosure')))
            ret = self.downloader.add_pt_torrent(can_item.get('enclosure'))
            if ret:
                self.__send_rss_message(can_item)
            else:
                log.error("【RSS】添加PT任务出错：%s" % can_item.get('title'))

        self.__running_flag = False

    @staticmethod
    def __is_torrent_match(title, media_title, search_type, movie_keys, tv_keys):
        # 按种子标题匹配
        if search_type == MediaType.MOVIE:
            # 按电影匹配
            for key in movie_keys:
                if re.search(str(key), title):
                    return True
        else:
            # 按电视剧匹配
            for key in tv_keys:
                if re.search(str(key), title):
                    return True
        # 按媒体信息匹配
        if search_type == MediaType.MOVIE:
            # 按电影匹配
            for key in movie_keys:
                if str(key) == media_title:
                    return True
        else:
            # 按电视剧匹配
            for key in tv_keys:
                if str(key) == media_title:
                    return True
        return False

    def __send_rss_message(self, can_item):
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
            msg_text = "来自RSS的%s %s %s 已开始下载" % (tp, msg_title, se)
        else:
            msg_text = "来自RSS的%s %s 已开始下载" % (tp, msg_title)
        if va and va != '0':
            msg_title = "%s 评分：%s" % (msg_title, str(va))
        self.message.sendmsg(msg_title, msg_text, bp)


if __name__ == "__main__":
    RSSDownloader().run_schedule()
