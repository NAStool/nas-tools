import re

import log
from config import Config
from message.send import Message
from pt.client.qbittorrent import Qbittorrent
from pt.client.transmission import Transmission
from rmt.filetransfer import FileTransfer
from rmt.media import Media
from utils.functions import str_filesize
from utils.types import MediaType, DownloaderType, SearchType
from web.backend.emby import Emby


class Downloader:
    client = None
    __client_type = None
    __seeding_time = None
    message = None
    emby = None
    filetransfer = None
    media = None

    def __init__(self):
        self.message = Message()
        self.emby = Emby()
        self.filetransfer = FileTransfer()
        self.media = Media()
        self.init_config()

    def init_config(self):
        config = Config()
        pt = config.get_config('pt')
        if pt:
            pt_client = pt.get('pt_client')
            if pt_client == "qbittorrent":
                self.client = Qbittorrent()
                self.__client_type = DownloaderType.QB
            elif pt_client == "transmission":
                self.client = Transmission()
                self.__client_type = DownloaderType.TR
            self.__seeding_time = pt.get('pt_seeding_time')

    # 添加下载任务
    def add_pt_torrent(self, url, mtype=MediaType.MOVIE):
        ret = None
        if self.client:
            try:
                ret = self.client.add_torrent(url, mtype)
                if ret and ret.find("Ok") != -1:
                    log.info("【PT】添加PT任务：%s" % url)
            except Exception as e:
                log.error("【PT】添加PT任务出错：" + str(e))
        return ret

    # 转移PT下载文人年
    def pt_transfer(self):
        if self.client:
            log.info("【PT】开始转移文件...")
            trans_torrents, trans_tasks = self.client.get_transfer_task()
            for task in trans_tasks:
                done_flag, done_msg = self.filetransfer.transfer_media(in_from=self.__client_type,
                                                                       in_path=task.get("path"))
                if not done_flag:
                    log.warn("【PT】%s 转移失败：%s" % (task.get("path"), done_msg))
                else:
                    self.client.set_torrents_status(task.get("id"))
            log.info("【PT】文件转移结束")
            medias = []
            for torrent in trans_torrents:
                medias.append(self.media.get_media_info(torrent))
            self.emby.refresh_emby_library_by_medias(medias)

    # 做种清理
    def pt_removetorrents(self):
        if not self.client:
            return False
        log.info("【PT】开始执行transmission做种清理...")
        torrents = self.client.get_remove_torrents(self.__seeding_time)
        for torrent in torrents:
            self.delete_torrents(torrent)
        log.info("【PT】transmission做种清理完成")

    # 获取种子列表信息
    def get_pt_torrents(self, torrent_ids=None, status_filter=None):
        if not self.client:
            return None, []
        return self.__client_type, self.client.get_torrents(ids=torrent_ids, status=status_filter)

    # 下载控制：开始
    def start_torrents(self, ids):
        if not self.client:
            return False
        return self.client.start_torrents(ids)

    # 下载控制：停止
    def stop_torrents(self, ids):
        if not self.client:
            return False
        return self.client.stop_torrents(ids)

    # 下载控制：删除
    def delete_torrents(self, ids):
        if not self.client:
            return False
        return self.client.delete_torrents(delete_file=True, ids=ids)

    # 检查是否存在决定是否添加下载
    def check_and_add_pt(self, in_from, media_list, need_tv_episodes=None):
        download_medias = []
        downloaded_items = []
        for can_item in self.__get_download_list(in_from, media_list):
            # 是否在Emby媒体库中存在
            if self.emby.check_emby_exists(can_item):
                log.info("【PT】%s%s 在Emby媒体库中已存在，跳过..." % (
                    can_item.get_title_string(), can_item.get_season_episode_string()))
                continue
            elif self.filetransfer.is_media_file_exists(can_item):
                log.info("【PT】%s%s 在媒体库目录中已存在，跳过..." % (
                    can_item.get_title_string(), can_item.get_season_episode_string()))
                continue
            # 添加PT任务
            if can_item.type != MediaType.MOVIE:
                # 标题中的季
                seasons = can_item.get_season_list()
                episodes = can_item.get_episode_list()
                # 根据缺失的集过滤
                if need_tv_episodes:
                    # 需要的季包含了标题中的季才下
                    need_seasons = []
                    for need_season in need_tv_episodes:
                        need_seasons.append(need_season.get("season"))
                    if need_seasons != seasons and set(need_seasons).issubset(set(seasons)):
                        # 标题中的季比需要的季多
                        log.info("【PT】%s %s 季过多，跳过..." % (
                            can_item.get_title_string(), can_item.get_season_episode_string()))
                        continue
                    else:
                        # 季符合要求, 要么相等，要么是要的季的子集
                        if len(seasons) == 1:
                            # 只有一季，看集数是不是想到的
                            need_episodes = []
                            if episodes:
                                for need_season in need_tv_episodes:
                                    if need_season.get("season") == seasons[0]:
                                        need_episodes = need_season.get("episodes")
                                        break
                                if need_episodes != episodes and not set(need_episodes).intersection(set(episodes)):
                                    # 不相等而且没有交集，不要
                                    continue
                            else:
                                # 标题中没有集，说明是一整季，下！
                                pass
                        else:
                            # 有多季，且都是想要的季，保留下载
                            pass
                # 记录下了的季和集，同一批不要重了：标题年份季集
                need_download = False
                for season in can_item.get_season_list():
                    season_str = "%s%s%s" % (can_item.title, can_item.year, str(season).rjust(2, "0"))
                    season_episodes = can_item.get_episode_list()
                    if season_episodes:
                        # 有集的，看整季或者集是不是有下过
                        for episode in season_episodes:
                            episode_str = str(episode).rjust(2, "0")
                            season_episode_str = "%s%s" % (season_str, episode_str)
                            if "%s00" % season_str in downloaded_items:
                                # 下过整季了，有集的丢掉
                                continue
                            if season_episode_str not in downloaded_items:
                                need_download = True
                                downloaded_items.append(season_episode_str)
                    else:
                        # 没集的，看整季是不是有下过
                        season_episode_str = "%s00" % season_str
                        if season_episode_str not in downloaded_items:
                            need_download = True
                            downloaded_items.append(season_episode_str)

                if not need_download:
                    log.info("【PT】%s %s 下载重复，跳过..." % (
                        can_item.get_title_string(), can_item.get_season_episode_string()))
                    continue

            # 开始真正的下载
            download_medias.append(can_item)
            log.info("【PT】添加PT任务：%s ..." % can_item.org_string)
            ret = self.add_pt_torrent(can_item.enclosure, can_item.type)
            if ret:
                self.message.send_download_message(in_from, can_item)
            else:
                log.error("【PT】添加下载任务失败：%s" % can_item.title)
                self.message.sendmsg("【PT】添加PT任务失败：%s" % can_item.title)
        return download_medias

    # 排序、去重 选种
    @staticmethod
    def __get_download_list(in_from, media_list):
        if not media_list:
            return []

        # 排序函数，标题、PT站、资源类型、做种数量，同时还要把有季和集且最长排前面
        def get_sort_str(x):
            if in_from == SearchType.RSS:
                return "%s%s%s%s" % (str(x.title).ljust(100, ' '),
                                     str(x.site_order).rjust(3, '0'),
                                     str(x.res_order).rjust(3, '0'),
                                     str(len(x.get_episode_list())).rjust(3, '0'))
            else:
                return "%s%s%s%s%s" % (str(x.title).ljust(100, ' '),
                                       str(len(x.get_episode_list())).rjust(3, '0'),
                                       str(x.res_order).rjust(3, '0'),
                                       str(x.seeders).rjust(10, '0'),
                                       str(x.site_order).rjust(3, '0'))

        # 匹配的资源中排序分组选最好的一个下载
        # 按站点顺序、资源匹配顺序、做种人数下载数逆序排序
        media_list = sorted(media_list, key=lambda x: get_sort_str(x), reverse=True)
        log.debug("【PT】种子信息排序后如下：")
        for media_item in media_list:
            log.info(">站点：%s，"
                     "标题：%s，"
                     "类型：%s，"
                     "大小：%s，"
                     "做种数：%s，"
                     "季集：%s，"
                     "种子名称：%s" % (media_item.site,
                                  media_item.get_title_string(),
                                  media_item.get_resource_type_string(),
                                  str_filesize(media_item.size),
                                  media_item.seeders,
                                  media_item.get_season_episode_string(),
                                  media_item.org_string))
        # 控重
        can_download_list_item = []
        can_download_list = []
        # 排序后重新加入数组，按真实名称控重，即只取每个名称的第一个
        for t_item in media_list:
            # 控重的主链是名称、年份、季、集
            if t_item.type != MediaType.MOVIE:
                media_name = "%s%s" % (t_item.get_title_string(),
                                       t_item.get_season_episode_string())
            else:
                media_name = t_item.get_title_string()
            if media_name not in can_download_list:
                can_download_list.append(media_name)
                can_download_list_item.append(t_item)

        return can_download_list_item

    # 检查标题中是否匹配资源类型
    # 返回：是否匹配，匹配的序号，匹配的值
    @staticmethod
    def check_resouce_types(t_title, t_types):
        if not t_types:
            # 未配置默认不过滤
            return True, 0, ""
        if isinstance(t_types, list):
            # 如果是个列表，说明是旧配置
            c_seq = 100
            for t_type in t_types:
                c_seq = c_seq - 1
                t_type = str(t_type)
                if t_type.upper() == "BLURAY":
                    match_str = r'blu-?ray'
                elif t_type.upper() == "4K":
                    match_str = r'4k|2160p'
                else:
                    match_str = r'%s' % t_type
                re_res = re.search(match_str, t_title, re.IGNORECASE)
                if re_res:
                    return True, c_seq, t_type
            return False, 0, ""
        else:
            # 必须包括的项
            includes = t_types.get('include')
            if includes:
                if isinstance(includes, str):
                    includes = [includes]
                include_flag = True
                for include in includes:
                    if not include:
                        continue
                    re_res = re.search(r'%s' % include, t_title, re.IGNORECASE)
                    if not re_res:
                        include_flag = False
                if not include_flag:
                    return False, 0, ""

            # 不能包含的项
            excludes = t_types.get('exclude')
            if excludes:
                if isinstance(excludes, str):
                    excludes = [excludes]
                exclude_flag = False
                exclude_count = 0
                for exclude in excludes:
                    if not exclude:
                        continue
                    exclude_count += 1
                    re_res = re.search(r'%s' % exclude, t_title, re.IGNORECASE)
                    if not re_res:
                        exclude_flag = True
                if exclude_count != 0 and not exclude_flag:
                    return False, 0, ""
            return True, 0, ""

    # 种子大小匹配
    @staticmethod
    def is_torrent_match_size(media_info, t_types, t_size):
        if media_info.type != MediaType.MOVIE:
            return True
        # 大小
        if t_size:
            sizes = t_types.get('size')
            if sizes:
                if sizes.find(',') != -1:
                    if sizes[0].isdigit():
                        begin_size = int(sizes[0].strip())
                    else:
                        begin_size = 0
                    if sizes[1].isdigit():
                        end_size = int(sizes[1].strip())
                    else:
                        end_size = 0
                else:
                    begin_size = 0
                    if sizes.isdight():
                        end_size = int(sizes.strip())
                    else:
                        end_size = 0
                if not begin_size * 1024 * 1024 * 1024 <= int(t_size) << end_size * 1024 * 1024 * 1024:
                    log.debug("【JACKETT】%s：%s 文件大小不符合要求" % (media_info.type.value, media_info.get_title_string()))
                    return False
        return True

    # 种子名称关键字匹配
    @staticmethod
    def is_torrent_match_sey(media_info, s_num, e_num, year_str):
        if s_num:
            if not media_info.is_in_seasion(s_num):
                log.info("【JACKETT】%s：%s %s %s 不匹配季：%s" % (media_info.type.value,
                                                           media_info.get_title_string(),
                                                           media_info.get_season_episode_string(),
                                                           media_info.get_resource_type_string(), s_num))
                return False
        if e_num:
            if not media_info.is_in_episode(e_num):
                log.info("【JACKETT】%s：%s %s %s 不匹配集：%s" % (media_info.type.value,
                                                           media_info.get_title_string(),
                                                           media_info.get_season_episode_string(),
                                                           media_info.get_resource_type_string(), e_num))
                return False
        if year_str:
            if str(media_info.year) != year_str:
                log.info("【JACKETT】%s：%s %s %s 不匹配年份：%s" % (media_info.type.value,
                                                            media_info.get_title_string(),
                                                            media_info.get_season_episode_string(),
                                                            media_info.get_resource_type_string(), year_str))
                return False
        return True
