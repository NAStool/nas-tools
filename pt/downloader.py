import re

import log
from config import Config
from message.send import Message
from pt.client.qbittorrent import Qbittorrent
from pt.client.transmission import Transmission
from rmt.filetransfer import FileTransfer
from rmt.media import Media
from rmt.metainfo import MetaInfo
from utils.functions import str_filesize
from utils.types import MediaType, DownloaderType, SearchType
from web.backend.emby import Emby


class Downloader:
    __config = None
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
        self.__config = Config()
        pt = self.__config.get_config('pt')
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
            log.info("【PT】开始转移PT下载文件...")
            trans_torrents, trans_tasks = self.client.get_transfer_task()
            for task in trans_tasks:
                done_flag = self.filetransfer.transfer_media(in_from=self.__client_type, in_path=task.get("path"))
                if not done_flag:
                    log.warn("【PT】%s 转移失败！" % task.get("path"))
                else:
                    self.client.set_torrents_status(task.get("id"))
            log.info("【PT】PT下载文件转移结束！")
            self.emby.refresh_emby_library_by_names(trans_torrents)

    # 做种清理
    def pt_removetorrents(self):
        if not self.client:
            return False
        log.info("【PT】开始执行transmission做种清理...")
        torrents = self.client.get_remove_torrents(self.__seeding_time)
        for torrent in torrents:
            log.info("【PT】%s 做种时间：%s（秒），已达清理条件，进行清理..." % (torrent, self.__seeding_time))
            self.delete_torrents(torrent)
        log.info("【PT】transmission做种清理完成！")

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
                log.info("【PT】%s(%s)%s%s 在Emby媒体库中已存在，跳过..." % (
                    can_item.title, can_item.year, can_item.get_season_string(), can_item.get_episode_string()))
                continue
            elif self.filetransfer.is_media_file_exists(can_item):
                log.info("【PT】%s(%s)%s%s 在媒体库目录中已存在，跳过..." % (
                    can_item.title, can_item.year, can_item.get_season_string(), can_item.get_episode_string()))
                continue
            # 添加PT任务
            if can_item.type == MediaType.TV:
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
                        log.info("【PT】%s(%s)%s%s 季过多，跳过..." % (
                            can_item.title, can_item.year, can_item.get_season_string(), can_item.get_episode_string()))
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
                    log.info("【PT】%s(%s)%s%s 下载重复，跳过..." % (
                        can_item.title, can_item.year, can_item.get_season_string(), can_item.get_episode_string()))
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
                return "%s%s%s%s" % (
                    str(x.title).ljust(100, ' '), str(x.site_order).rjust(3, '0'), str(x.res_order).rjust(3, '0'),
                    str(len(x.get_episode_list())).rjust(3, '0'))
            else:
                return "%s%s%s%s%s" % (str(x.title).ljust(100, ' '),
                                       str(x.res_order).rjust(3, '0'),
                                       str(x.seeders).rjust(10, '0'),
                                       str(x.site_order).rjust(3, '0'),
                                       str(len(x.get_episode_list())).rjust(3, '0'))

        # 匹配的资源中排序分组选最好的一个下载
        # 按站点顺序、资源匹配顺序、做种人数下载数逆序排序
        media_list = sorted(media_list, key=lambda x: get_sort_str(x), reverse=True)
        log.debug("【PT】种子信息排序后如下：")
        for media_item in media_list:
            log.info(">站点：%s，"
                     "标题：%s (%s)，"
                     "类型：%s，"
                     "大小：%s，"
                     "做种数：%s，"
                     "季集：%s，"
                     "种子名称：%s" % (media_item.site,
                                  media_item.title,
                                  media_item.year,
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
            # 控重的主链是名称、节份、季、集
            if t_item.type == MediaType.TV:
                media_name = "%s%s%s%s" % (t_item.title,
                                           t_item.year,
                                           t_item.get_season_string(),
                                           t_item.get_episode_string())
            else:
                media_name = "%s%s" % (t_item.title, t_item.year)
            if media_name not in can_download_list:
                can_download_list.append(media_name)
                can_download_list_item.append(t_item)

        return can_download_list_item

    # 处理种子标题中的错误信息
    @staticmethod
    def prepare_torrent_name(torrent_name):
        # 去掉第1个以[]开关的种子名称，有些站会把类型加到种子名称上，会误导识别
        # 非贪婪只匹配一个
        new_name = re.sub(r'^\[.+?]', "", torrent_name, count=1)
        meta_info = MetaInfo(new_name)
        if meta_info.get_name():
            return new_name
        else:
            return torrent_name
