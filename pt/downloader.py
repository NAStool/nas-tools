import log
from config import get_config
from message.send import Message
from pt.client.qbittorrent import Qbittorrent
from pt.client.transmission import Transmission
from rmt.filetransfer import FileTransfer

from utils.types import MediaType, DownloaderType, SearchType
from web.backend.emby import Emby


class Downloader:
    client = None
    __client_type = None
    __seeding_time = None
    message = None
    emby = None
    filetransfer = None

    def __init__(self):
        self.message = Message()
        self.emby = Emby()
        self.filetransfer = FileTransfer()

        config = get_config()
        if config.get('pt'):
            pt_client = config['pt'].get('pt_client')
            if pt_client == "qbittorrent":
                self.client = Qbittorrent()
                self.__client_type = DownloaderType.QB
            elif pt_client == "transmission":
                self.client = Transmission()
                self.__client_type = DownloaderType.TR
            self.__seeding_time = config['pt'].get('pt_seeding_time')

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
            return self.client.transfer_task()

    # 做种清理
    def pt_removetorrents(self):
        if not self.client:
            return False
        return self.client.remove_torrents(self.__seeding_time)

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
    def check_and_add_pt(self, in_from, media_list):
        download_medias = []
        download_items = {}
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
                # 如果是电视剧，控制一下，不要下重了
                media_key = "%s%s" % (can_item.title, can_item.year)
                if download_items.get(media_key):
                    # 下过了
                    if len(seasons) > 1:
                        # 有多季，看看剧是不是有重复
                        for season in seasons:
                            if download_items[media_key].get(str(season)):
                                # 这个季下过了，不下了
                                continue
                            else:
                                # 这个季都没下过，记下来
                                download_items[media_key][str(season)] = [0]
                    else:
                        # 只有1季，看集是不是有重复
                        if download_items[media_key].get(str(seasons[0])):
                            if download_items[media_key].get(str(seasons[0]))[0] == 0:
                                # 下过整季了就不下集了
                                continue
                            elif set(download_items[media_key].get(str(seasons[0]))).issuperset(
                                    can_item.get_episode_list()):
                                # 下过的集大于等于当前的，当前不用下了
                                continue
                            else:
                                # 当前有之前不存在的，要下，且要合并一下
                                download_items[media_key][str(seasons[0])] = list(
                                    set(download_items[media_key].get(str(seasons[0]))).union(
                                        set(can_item.get_episode_list())))
                        else:
                            # 这个季都没下过，记下来
                            download_items[media_key][str(seasons[0])] = can_item.get_episode_list()
                else:
                    # 没下过
                    if len(seasons) > 1:
                        # 有多季，把下过的季存起来
                        download_items[media_key] = {}
                        for season in can_item.get_season_list():
                            download_items[media_key][str(season)] = [0]
                    else:
                        # 只有一季，把下过的集存起来
                        download_items[media_key] = {}
                        download_items[media_key][str(seasons[0])] = can_item.get_episode_list()
            # 开始添加下载
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
            log.debug(">标题：%s，"
                      "序号：%s，"
                      "资源类型：%s，"
                      "大小：%s，"
                      "做种：%s，"
                      "下载：%s，"
                      "季：%s，"
                      "集：%s，"
                      "种子：%s" % (media_item.title,
                                 media_item.site_order,
                                 media_item.res_type,
                                 media_item.size,
                                 media_item.seeders,
                                 media_item.peers,
                                 media_item.get_season_string(),
                                 media_item.get_episode_string(),
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
