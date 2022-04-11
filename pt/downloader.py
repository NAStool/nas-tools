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
                            for sea in item_season:
                                for tv in need_tvs.get(need_title):
                                    if sea == tv.get("season"):
                                        need_tvs[need_title].remove(tv)
                            if not need_tvs.get(need_title):
                                need_tvs.pop(need_title)
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
                    for item in download_list:
                        if item.get_title_string() == need_title and item.type != MediaType.MOVIE:
                            item_season = item.get_season_list()
                            item_episodes = item.get_episode_list()
                            # 这里只处理单季含集的种子，从集最多的开始下
                            if len(item_season) == 1 and item_episodes and item_season[0] == need_season:
                                # 缺失整季的转化为缺失集进行比较
                                if not need_episodes:
                                    need_episodes = list(range(1, total_episodes + 1))
                                if set(item_episodes).issubset(set(need_episodes)):
                                    download_items.append(item)
                                    # 删除该季下已下载的集
                                    left_episode = list(set(need_episodes).difference(set(item_episodes)))
                                    if left_episode:
                                        need_tvs[need_title][index]["episodes"] = left_episode
                                    else:
                                        need_tvs[need_title].pop(index)
                                    if not need_tvs.get(need_title):
                                        need_tvs.pop(need_title)
                    index += 1
        else:
            # 电影
            for item in download_list:
                if item.type == MediaType.MOVIE:
                    download_items.append(item)

        # 添加PT任务
        for item in download_items:
            log.info("【PT】添加PT任务：%s ..." % item.org_string)
            ret = self.add_pt_torrent(item.enclosure, item.type)
            if ret:
                self.message.send_download_message(in_from, item)
            else:
                log.error("【PT】添加下载任务失败：%s" % item.get_title_string())
                self.message.sendmsg("【PT】添加PT任务失败：%s" % item.get_title_string())
        log.info("【PT】实际下载了 %s 个资源" % len(download_items))
        # 返回下载数以及，剩下没下完的
        return len(download_items), need_tvs

    # 检查控重，返回是否存在标志，如果是剧集，返回每季的缺失集
    def check_exists_medias(self, in_from, meta_info):
        # 没有季只有集，默认为第1季
        search_season = meta_info.get_season_list()
        search_episode = meta_info.get_episode_list()
        # 电影、动漫
        if meta_info.type != MediaType.MOVIE:
            message_list = []
            total_tv_no_exists = {}
            return_flag = None
            # 检索电视剧的信息
            tv_info = self.media.get_tmdb_tv_info(meta_info.tmdb_id)
            if tv_info:
                # 没有输入季
                if not search_season:
                    # 共有多少季，每季有多少季
                    total_seasons = self.get_tmdb_seasons_info(tv_info.get("seasons"))
                    log.info("【PT】电视剧 %s 共有 %s 季" % (meta_info.get_title_string(), len(total_seasons)))
                    message_list.append("电视剧 %s 共有 %s 季" % (meta_info.get_title_string(), len(total_seasons)))
                else:
                    # 有输入季
                    total_seasons = []
                    for season in search_season:
                        episode_num = self.get_tmdb_season_episodes_num(tv_info.get("seasons"), season)
                        if not episode_num:
                            log.info("【PT】电视剧 %s 第%s季 不存在" % (meta_info.get_title_string(), season))
                            message_list.append("电视剧 %s 第%s季 不存在" % (meta_info.get_title_string(), season))
                            continue
                        total_seasons.append({"season_number": season, "episode_count": episode_num})
                        log.info("【PT】电视剧 %s 第%s季 共有 %s 集" % (meta_info.get_title_string(), season, episode_num))
                        message_list.append("电视剧 %s 第%s季 共有 %s 集" % (meta_info.get_title_string(), season, episode_num))
                # 查询缺少多少集
                for season in total_seasons:
                    season_number = season.get("season_number")
                    episode_count = season.get("episode_count")
                    if not season_number or not episode_count:
                        continue
                    # 检查Emby
                    no_exists_tv_episodes = self.emby.get_emby_no_exists_episodes(meta_info,
                                                                                  season_number,
                                                                                  episode_count)
                    # 没有配置Emby
                    if no_exists_tv_episodes is None:
                        no_exists_tv_episodes = self.filetransfer.get_no_exists_medias(meta_info,
                                                                                       season_number,
                                                                                       episode_count)
                    if no_exists_tv_episodes:
                        no_exists_tv_episodes.sort()
                        if not total_tv_no_exists.get(meta_info.get_title_string()):
                            total_tv_no_exists[meta_info.get_title_string()] = []
                        # 存在缺失
                        exists_tvs_str = "、".join(["%s" % tv for tv in no_exists_tv_episodes])
                        if search_episode:
                            # 有集数，肯定只有一季
                            if not set(search_episode).intersection(set(no_exists_tv_episodes)):
                                # 搜索的跟不存在的没有交集，说明都存在了
                                log.info("【PT】%s 在媒体库中已经存在，本次下载取消" % meta_info.get_title_string())
                                message_list.append("%s 在媒体库中已经存在，本次下载取消" % meta_info.get_title_string())
                                return_flag = True
                                break
                            else:
                                total_tv_no_exists[meta_info.get_title_string()] = [
                                    {"season": season_number, "episodes": [search_episode],
                                     "total_episodes": episode_count}]
                                break
                        else:
                            if len(no_exists_tv_episodes) >= episode_count:
                                total_tv_no_exists[meta_info.get_title_string()].append(
                                    {"season": season_number, "episodes": [], "total_episodes": episode_count})
                                log.info("【PT】第%s季 缺失%s集" % (season_number, episode_count))
                                message_list.append("第%s季 缺失%s集" % (season_number, episode_count))
                            else:
                                total_tv_no_exists[meta_info.get_title_string()].append(
                                    {"season": season_number, "episodes": no_exists_tv_episodes,
                                     "total_episodes": episode_count})
                                log.info("【PT】第%s季 缺失集：%s" % (season_number, exists_tvs_str))
                                message_list.append("第%s季 缺失集：%s" % (season_number, exists_tvs_str))
                    else:
                        log.info("【PT】第%s季 共%s集 已全部存在" % (season_number, episode_count))
                        message_list.append("第%s季 共%s集 已全部存在" % (season_number, episode_count))
            else:
                log.info("【PT】%s 无法查询到媒体详细信息" % meta_info.get_title_string())
                message_list.append("%s 无法查询到媒体详细信息" % meta_info.get_title_string())
                return_flag = None
            # 发送消息
            if message_list and in_from == SearchType.WX:
                self.message.sendmsg(title="\n".join(message_list))
            # 全部存在
            if not return_flag and not total_tv_no_exists:
                return_flag = True
            # 返回
            return return_flag, total_tv_no_exists
        # 检查电影
        else:
            exists_movies = self.emby.get_emby_movies(meta_info.title, meta_info.year)
            if exists_movies is None:
                exists_movies = self.filetransfer.get_no_exists_medias(meta_info)
            if exists_movies:
                movies_str = "\n * ".join(["%s (%s)" % (m.get('title'), m.get('year')) for m in exists_movies])
                log.info("【PT】媒体库中已经存在以下电影：\n * %s" % movies_str)
                if in_from == SearchType.WX:
                    self.message.sendmsg(title="在媒体库中已经存在以下电影：\n * %s" % movies_str)
                return True, None
            return False, None

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
            if not isinstance(t_types, dict):
                return True, 0, ""
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
        if not isinstance(t_types, dict):
            return True
        # 大小
        if t_size:
            sizes = t_types.get('size')
            if sizes:
                if sizes.find(',') != -1:
                    sizes = sizes.split(',')
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
                    if sizes.isdigit():
                        end_size = int(sizes.strip())
                    else:
                        end_size = 0
                if not begin_size * 1024 * 1024 * 1024 <= int(t_size) <= end_size * 1024 * 1024 * 1024:
                    log.info("【JACKETT】%s：%s 文件大小：%s 不符合要求" % (media_info.type.value, media_info.get_title_string(), str_filesize(int(t_size))))
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

    # 从TMDB的季集信息中获得季的组
    @staticmethod
    def get_tmdb_seasons_info(seasons):
        if not seasons:
            return []
        total_seasons = []
        for season in seasons:
            if season.get("season_number") != 0:
                total_seasons.append(
                    {"season_number": season.get("season_number"), "episode_count": season.get("episode_count")})
        return total_seasons

    # 从TMDB的季信息中获得具体季有多少集
    @staticmethod
    def get_tmdb_season_episodes_num(seasons, sea):
        if not seasons:
            return 0
        for season in seasons:
            if season.get("season_number") == sea:
                return season.get("episode_count")
        return 0
