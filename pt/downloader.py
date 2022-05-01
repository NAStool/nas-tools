import log
from config import Config
from message.send import Message
from pt.client.qbittorrent import Qbittorrent
from pt.client.transmission import Transmission
from rmt.filetransfer import FileTransfer
from rmt.media import Media
from rmt.media_server import MediaServer
from utils.functions import str_filesize, str_timelong
from utils.types import MediaType, DownloaderType


class Downloader:
    client = None
    __client_type = None
    __seeding_time = None
    message = None
    mediaserver = None
    filetransfer = None
    media = None

    def __init__(self):
        self.message = Message()
        self.mediaserver = MediaServer()
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
            if self.__seeding_time:
                if isinstance(self.__seeding_time, str):
                    if self.__seeding_time.isdigit():
                        self.__seeding_time = int(self.__seeding_time)
                    else:
                        try:
                            self.__seeding_time = round(float(self.__seeding_time))
                        except Exception as e:
                            log.error("【PT】pt.pt_seeding_time 格式错误：%s" % str(e))
                            self.__seeding_time = 0
                else:
                    self.__seeding_time = round(self.__seeding_time)

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
            trans_tasks = self.client.get_transfer_task()
            for task in trans_tasks:
                done_flag, done_msg = self.filetransfer.transfer_media(in_from=self.__client_type,
                                                                       in_path=task.get("path"))
                if not done_flag:
                    log.warn("【PT】%s 转移失败：%s" % (task.get("path"), done_msg))
                else:
                    self.client.set_torrents_status(task.get("id"))
            log.info("【PT】文件转移结束")

    # 做种清理
    def pt_removetorrents(self):
        if not self.client:
            return False
        if not self.__seeding_time:
            return
        log.info("【PT】开始执行PT做种清理，做种时间：%s..." % str_timelong(self.__seeding_time))
        torrents = self.client.get_remove_torrents(self.__seeding_time)
        for torrent in torrents:
            self.delete_torrents(torrent)
        log.info("【PT】PT做种清理完成")

    # 正在下载
    def pt_downloading_torrents(self):
        if not self.client:
            return []
        return self.__client_type, self.client.get_downloading_torrents()

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
    # 输入：需要检查下载的媒体列表，缺失的季集
    # 返回：下载了的媒体信息、剩余没下载的季集
    def check_and_add_pt(self, in_from, media_list, need_tvs=None):
        download_items = []
        # 返回按季、集数倒序排序的列表
        download_list = self.__get_download_list(media_list)
        # 电视剧整季匹配
        if need_tvs:
            # 先把整季缺失的拿出来，看是否刚好有所有季都满足的种子
            need_seasons = {}
            for need_title, need_tv in need_tvs.items():
                for tv in need_tv:
                    if not tv:
                        continue
                    if not tv.get("episodes"):
                        if not need_seasons.get(need_title):
                            need_seasons[need_title] = []
                        need_seasons[need_title].append(tv.get("season"))
            # 查找整季包含的种子，只处理整季没集的种子或者是集数超过季的种子
            for need_title, need_season in need_seasons.items():
                for item in download_list:
                    item_season = item.get_season_list()
                    item_episodes = item.get_episode_list()
                    if need_title == item.get_title_string() and item.type != MediaType.MOVIE and not item_episodes:
                        if set(item_season).issubset(set(need_season)):
                            download_items.append(item)
                            # 删除已下载的季
                            need_season = list(set(need_season).difference(set(item_season)))
                            for sea in item_season:
                                for tv in need_tvs.get(need_title):
                                    if sea == tv.get("season"):
                                        need_tvs[need_title].remove(tv)
                            if not need_tvs.get(need_title):
                                need_tvs.pop(need_title)
                                break
        # 电视剧季内的集匹配，也有可能没有找到整季
        if need_tvs:
            need_tv_list = list(need_tvs)
            for need_title in need_tv_list:
                need_tv = need_tvs.get(need_title)
                if not need_tv:
                    continue
                index = 0
                for tv in need_tv:
                    need_season = tv.get("season")
                    need_episodes = tv.get("episodes")
                    total_episodes = tv.get("total_episodes")
                    # 缺失整季的转化为缺失集进行比较
                    if not need_episodes:
                        need_episodes = list(range(1, total_episodes + 1))
                    for item in download_list:
                        if item.get_title_string() == need_title and item.type != MediaType.MOVIE:
                            item_season = item.get_season_list()
                            item_episodes = item.get_episode_list()
                            # 这里只处理单季含集的种子，从集最多的开始下
                            if len(item_season) == 1 and item_episodes and item_season[0] == need_season:
                                if set(item_episodes).issubset(set(need_episodes)):
                                    download_items.append(item)
                                    # 删除该季下已下载的集
                                    need_episodes = list(set(need_episodes).difference(set(item_episodes)))
                                    if need_episodes:
                                        need_tvs[need_title][index]["episodes"] = need_episodes
                                    else:
                                        need_tvs[need_title].pop(index)
                                        if not need_tvs.get(need_title):
                                            need_tvs.pop(need_title)
                                        break
                    index += 1
        else:
            # 电影
            for item in download_list:
                if item.type == MediaType.MOVIE:
                    download_items.append(item)

        # 添加PT任务
        return_items = []
        for item in download_items:
            log.info("【PT】添加PT任务：%s ..." % item.org_string)
            ret = self.add_pt_torrent(item.enclosure, item.type)
            if ret:
                if item not in return_items:
                    return_items.append(item)
                self.message.send_download_message(in_from, item)
            else:
                log.error("【PT】添加下载任务失败：%s" % item.get_title_string())
                self.message.sendmsg("添加PT任务失败：%s" % item.get_title_string())
        # 返回下载的资源，剩下没下完的
        return return_items, need_tvs

    # 检查控重
    # 输入：媒体信息，需要补充的缺失季集信息
    # 返回：当前媒体是否缺失，总的季集和缺失的季集，需要发送的消息
    def check_exists_medias(self, meta_info, no_exists=None):
        if not no_exists:
            no_exists = {}
        # 查找的季
        if not meta_info.begin_season:
            search_season = None
        else:
            search_season = meta_info.get_season_list()
        # 查找的集
        search_episode = meta_info.get_episode_list()
        if search_episode and not search_season:
            search_season = [1]

        # 返回的消息列表
        message_list = []
        if meta_info.type != MediaType.MOVIE:
            # 是否存在的标志
            return_flag = False
            # 检索电视剧的信息
            tv_info = self.media.get_tmdb_tv_info(meta_info.tmdb_id)
            if tv_info:
                # 传入检查季
                total_seasons = []
                if search_season:
                    for season in search_season:
                        episode_num = self.media.get_tmdb_season_episodes_num(tv_info=tv_info, sea=season)
                        if not episode_num:
                            log.info("【PT】%s 第%s季 不存在" % (meta_info.get_title_string(), season))
                            message_list.append("%s 第%s季 不存在" % (meta_info.get_title_string(), season))
                            continue
                        total_seasons.append({"season_number": season, "episode_count": episode_num})
                        log.info("【PT】%s 第%s季 共有 %s 集" % (meta_info.get_title_string(), season, episode_num))
                else:
                    # 共有多少季，每季有多少季
                    total_seasons = self.media.get_tmdb_seasons_info(tv_info=tv_info)
                    log.info(
                        "【PT】%s %s 共有 %s 季" % (meta_info.type.value, meta_info.get_title_string(), len(total_seasons)))
                    message_list.append(
                        "%s %s 共有 %s 季" % (meta_info.type.value, meta_info.get_title_string(), len(total_seasons)))
                # 查询缺少多少集
                for season in total_seasons:
                    season_number = season.get("season_number")
                    episode_count = season.get("episode_count")
                    if not season_number or not episode_count:
                        continue
                    # 检查Emby
                    no_exists_episodes = self.mediaserver.get_no_exists_episodes(meta_info,
                                                                                 season_number,
                                                                                 episode_count)
                    # 没有配置Emby
                    if no_exists_episodes is None:
                        no_exists_episodes = self.filetransfer.get_no_exists_medias(meta_info,
                                                                                    season_number,
                                                                                    episode_count)
                    if no_exists_episodes:
                        # 排序
                        no_exists_episodes.sort()
                        # 缺失集初始化
                        if not no_exists.get(meta_info.get_title_string()):
                            no_exists[meta_info.get_title_string()] = []
                        # 缺失集提示文本
                        exists_tvs_str = "、".join(["%s" % tv for tv in no_exists_episodes])
                        # 存入总缺失集
                        if len(no_exists_episodes) >= episode_count:
                            no_item = {"season": season_number, "episodes": [], "total_episodes": episode_count}
                            log.info(
                                "【PT】%s 第%s季 缺失 %s 集" % (meta_info.get_title_string(), season_number, episode_count))
                            message_list.append("第%s季 缺失 %s 集" % (season_number, episode_count))
                        else:
                            no_item = {"season": season_number, "episodes": no_exists_episodes,
                                       "total_episodes": episode_count}
                            log.info(
                                "【PT】%s 第%s季 缺失集：%s" % (meta_info.get_title_string(), season_number, exists_tvs_str))
                            message_list.append("第%s季 缺失集：%s" % (season_number, exists_tvs_str))
                        if no_item not in no_exists.get(meta_info.get_title_string()):
                            no_exists[meta_info.get_title_string()].append(no_item)
                        # 输入检查集
                        if search_episode:
                            # 有集数，肯定只有一季
                            if not set(search_episode).intersection(set(no_exists_episodes)):
                                # 搜索的跟不存在的没有交集，说明都存在了
                                log.info("【PT】%s %s 在媒体库中已经存在" % (
                                    meta_info.get_title_string(), meta_info.get_season_episode_string()))
                                message_list.append("%s %s 在媒体库中已经存在" % (
                                    meta_info.get_title_string(), meta_info.get_season_episode_string()))
                                return_flag = True
                                break
                    else:
                        log.info(
                            "【PT】%s 第%s季 共%s集 已全部存在" % (meta_info.get_title_string(), season_number, episode_count))
                        message_list.append("第%s季 共%s集 已全部存在" % (season_number, episode_count))
            else:
                log.info("【PT】%s 无法查询到媒体详细信息" % meta_info.get_title_string())
                message_list.append("%s 无法查询到媒体详细信息" % meta_info.get_title_string())
                return_flag = None
            # 全部存在
            if return_flag is False and not no_exists.get(meta_info.get_title_string()):
                return_flag = True
            # 返回
            return return_flag, no_exists, message_list
        # 检查电影
        else:
            exists_movies = self.mediaserver.get_movies(meta_info.title, meta_info.year)
            if exists_movies is None:
                exists_movies = self.filetransfer.get_no_exists_medias(meta_info)
            if exists_movies:
                movies_str = "\n * ".join(["%s (%s)" % (m.get('title'), m.get('year')) for m in exists_movies])
                log.info("【PT】媒体库中已经存在以下电影：\n * %s" % movies_str)
                message_list.append("在媒体库中已经存在以下电影：\n * %s" % movies_str)
                return True, None, message_list
            return False, None, message_list

    # 排序、去重 选种
    @staticmethod
    def __get_download_list(media_list):
        if not media_list:
            return []

        # 排序函数，标题、PT站、资源类型、做种数量
        def get_sort_str(x):
            season_len = str(len(x.get_season_list())).rjust(3, '0')
            episode_len = str(len(x.get_episode_list())).rjust(3, '0')
            # 排序：标题、季集、资源类型、站点、做种
            return "%s%s%s%s%s" % (str(x.title).ljust(100, ' '),
                                   "%s%s" % (season_len, episode_len),
                                   str(x.res_order).rjust(3, '0'),
                                   str(x.site_order).rjust(3, '0'),
                                   str(x.seeders).rjust(10, '0'))

        # 匹配的资源中排序分组选最好的一个下载
        # 按站点顺序、资源匹配顺序、做种人数下载数逆序排序
        media_list = sorted(media_list, key=lambda x: get_sort_str(x), reverse=True)
        log.debug("【PT】种子信息排序后如下：")
        for media_item in media_list:
            log.debug(">站点：%s，"
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
