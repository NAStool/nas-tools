import os
from threading import Lock
from time import sleep

from requests.utils import dict_from_cookiejar

import log
from app.helper import SqlHelper
from app.media import MetaInfo, Media
from config import Config, PT_TAG
from app.message import Message
from app.downloader import Aria2, Client115, Qbittorrent, Transmission
from app.mediaserver import MediaServer
from app.sites import Sites, SiteConf
from app.utils import Torrent, StringUtils, RequestUtils, SystemUtils
from app.filetransfer import FileTransfer
from app.utils.types import MediaType, DownloaderType, SearchType, RmtMode, RMT_MODES

lock = Lock()


class Downloader:
    client = None
    __client_type = None
    __seeding_time = None
    __pt_monitor_only = None
    __download_order = None
    __pt_rmt_mode = None
    __downloaddir = {}
    message = None
    mediaserver = None
    filetransfer = None
    media = None
    sites = None

    def __init__(self):
        self.message = Message()
        self.mediaserver = MediaServer()
        self.filetransfer = FileTransfer()
        self.media = Media()
        self.sites = Sites()
        self.init_config()

    def init_config(self):
        config = Config()
        # 下载器配置
        pt = config.get_config('pt')
        if pt:
            pt_client = pt.get('pt_client')
            if pt_client == "qbittorrent":
                self.client = Qbittorrent()
                self.__client_type = DownloaderType.QB
            elif pt_client == "transmission":
                self.client = Transmission()
                self.__client_type = DownloaderType.TR
            elif pt_client == "client115":
                self.client = Client115()
                self.__client_type = DownloaderType.Client115
            elif pt_client == "aria2":
                self.client = Aria2()
                self.__client_type = DownloaderType.Aria2
            self.__seeding_time = pt.get('pt_seeding_time')
            if self.__seeding_time:
                try:
                    self.__seeding_time = round(float(self.__seeding_time) * 24 * 3600)
                except Exception as e:
                    log.error("【pt.pt_seeding_time 格式错误：%s" % str(e))
                    self.__seeding_time = None
            self.__pt_monitor_only = pt.get("pt_monitor_only")
            self.__download_order = pt.get("download_order")
            self.__pt_rmt_mode = RMT_MODES.get(pt.get("rmt_mode", "copy"), RmtMode.COPY)
        # 下载目录配置
        self.__downloaddir = config.get_config('downloaddir') or {}

    def add_pt_torrent(self,
                       media_info,
                       is_paused=None,
                       tag=None,
                       download_dir=None,
                       category=None,
                       content_layout=None,
                       upload_limit=None,
                       download_limit=None,
                       ratio_limit=None,
                       seeding_time_limit=None):
        """
        添加下载任务，根据当前使用的下载器分别调用不同的客户端处理
        :param media_info: 需下载的媒体信息，含URL地址
        :param is_paused: 是否默认暂停，只有需要进行下一步控制时，才会添加种子时默认暂停
        :param tag: 下载时对种子的标记
        :param download_dir: 指定下载目录
        :param category: 分类
        :param content_layout: 布局
        :param upload_limit: 上传限速 Mb/s
        :param download_limit: 下载限速 Mb/s
        :param ratio_limit: 分享率限制 保留两位小数
        :param seeding_time_limit: 做种时间限制 分钟
        """
        url = media_info.enclosure
        title = media_info.org_string
        page_url = media_info.page_url
        if not url:
            return None, "Url链接为空"
        _xpath = None
        _hash = False
        if url.startswith("["):
            _xpath = url[1:-1]
            url = page_url
        elif url.startswith("#"):
            _xpath = url[1:-1]
            _hash = True
            url = page_url
        if not url:
            return None, "Url链接为空"
        cookie = None
        ua = None
        if url.startswith("http"):
            # 获取站点维护中的信息
            site_info = self.sites.get_sites(siteurl=url)
            if site_info:
                cookie = site_info.get("cookie")
                ua = site_info.get("ua")
            else:
                # 获取公开站点信息
                site_info = SiteConf().get_public_sites(url=url)
                if site_info:
                    log.warn("【DOWNLOADER】公开站点，尝试自动获取Cookie ...")
                    try:
                        res = RequestUtils(timeout=10).get_res(StringUtils.get_base_url(url))
                        if res:
                            cookie = dict_from_cookiejar(res.cookies)
                    except Exception as err:
                        log.warn(f"【DOWNLOADER】自动获取公开站点cookie失败：{format(err)}")

            if _xpath:
                url = Torrent.parse_download_url(page_url=page_url,
                                                 xpath=_xpath,
                                                 cookie=cookie)
                if not url:
                    return None, "无法从详情页面：%s 解析出下载链接" % page_url
                if _hash:
                    url = Torrent.convert_hash_to_magnet(hash_text=url, title=title)
                    if not url:
                        return None, "%s 转换磁力链失败" % url

        if self.__client_type in [DownloaderType.Client115]:
            content = url
        else:
            content, retmsg = Torrent.get_torrent_content(url=url,
                                                          cookie=cookie,
                                                          ua=ua)
            if not content:
                log.error("【DOWNLOADER】%s" % retmsg)
                return None, retmsg

        ret = None
        if self.client:
            try:
                # 合并TAG
                if self.__pt_monitor_only:
                    if not tag:
                        tag = [PT_TAG]
                    elif isinstance(tag, list):
                        tag += [PT_TAG]
                    else:
                        tag = [PT_TAG, tag]
                if not download_dir:
                    download_info = self.__get_download_dir_info(media_info)
                    download_dir = download_info.get('path')
                    download_label = download_info.get('label')
                    if not category:
                        category = download_label
                if is_paused:
                    is_paused = True
                else:
                    is_paused = False
                log.info("【DOWNLOADER】添加下载任务：%s，目录：%s，Url：%s" % (title, download_dir, url))
                if self.__client_type == DownloaderType.TR:
                    ret = self.client.add_torrent(content,
                                                  is_paused=is_paused,
                                                  download_dir=download_dir)
                    if ret:
                        self.client.change_torrent(tid=ret.id,
                                                   tag=tag,
                                                   upload_limit=upload_limit,
                                                   download_limit=download_limit,
                                                   ratio_limit=ratio_limit,
                                                   seeding_time_limit=seeding_time_limit)
                elif self.__client_type == DownloaderType.QB:
                    ret = self.client.add_torrent(content,
                                                  is_paused=is_paused,
                                                  download_dir=download_dir,
                                                  tag=tag,
                                                  category=category,
                                                  content_layout=content_layout,
                                                  upload_limit=upload_limit,
                                                  download_limit=download_limit,
                                                  ratio_limit=ratio_limit,
                                                  seeding_time_limit=seeding_time_limit)
                else:
                    ret = self.client.add_torrent(content,
                                                  is_paused=is_paused,
                                                  tag=tag,
                                                  download_dir=download_dir,
                                                  category=category)
            except Exception as e:
                log.error("【DOWNLOADER】添加下载任务出错：%s" % str(e))
                return None, str(e)
        return ret, ""

    def pt_transfer(self):
        """
        转移下载完成的文件，进行文件识别重命名到媒体库目录
        """
        if self.client:
            try:
                lock.acquire()
                if self.__pt_monitor_only:
                    tag = [PT_TAG]
                else:
                    tag = None
                trans_tasks = self.client.get_transfer_task(tag=tag)
                if trans_tasks:
                    log.info("【DOWNLOADER】开始转移下载文件...")
                else:
                    return
                for task in trans_tasks:
                    done_flag, done_msg = self.filetransfer.transfer_media(in_from=self.__client_type,
                                                                           in_path=task.get("path"),
                                                                           rmt_mode=self.__pt_rmt_mode)
                    if not done_flag:
                        log.warn("【DOWNLOADER】%s 转移失败：%s" % (task.get("path"), done_msg))
                        self.client.set_torrents_status(task.get("id"))
                    else:
                        if self.__pt_rmt_mode in [RmtMode.MOVE, RmtMode.RCLONE, RmtMode.MINIO]:
                            log.warn("【DOWNLOADER】移动模式下删除种子文件：%s" % task.get("id"))
                            self.delete_torrents(task.get("id"))
                        else:
                            self.client.set_torrents_status(task.get("id"))
                log.info("【DOWNLOADER】下载文件转移结束")
            finally:
                lock.release()

    def pt_removetorrents(self):
        """
        做种清理，保种时间为空或0时，不进行清理操作
        """
        if not self.client:
            return False
        # 空或0不处理
        if not self.__seeding_time:
            return
        try:
            lock.acquire()
            if self.__pt_monitor_only:
                tag = [PT_TAG]
            else:
                tag = None
            log.info("【DOWNLOADER】开始执行做种清理，做种时间：%s..." % StringUtils.str_timelong(self.__seeding_time))
            torrents = self.client.get_remove_torrents(seeding_time=self.__seeding_time, tag=tag)
            for torrent in torrents:
                self.delete_torrents(torrent)
            log.info("【DOWNLOADER】做种清理完成")
        finally:
            lock.release()

    def pt_downloading_torrents(self):
        """
        查询正在下载中的种子信息
        :return: 客户端类型，下载中的种子信息列表
        """
        if not self.client:
            return []
        if self.__pt_monitor_only:
            tag = [PT_TAG]
        else:
            tag = None
        return self.__client_type, self.client.get_downloading_torrents(tag=tag)

    def get_torrents(self, torrent_ids):
        """
        根据ID或状态查询下载器中的种子信息
        :param torrent_ids: 种子ID列表
        :return: 客户端类型，种子信息列表
        """
        if not self.client:
            return None, []
        return self.__client_type, self.client.get_torrents(ids=torrent_ids)

    def start_torrents(self, ids):
        """
        下载控制：开始
        :param ids: 种子ID列表
        :return: 处理状态
        """
        if not self.client:
            return False
        return self.client.start_torrents(ids)

    def stop_torrents(self, ids):
        """
        下载控制：停止
        :param ids: 种子ID列表
        :return: 处理状态
        """
        if not self.client:
            return False
        return self.client.stop_torrents(ids)

    def delete_torrents(self, ids):
        """
        删除种子
        :param ids: 种子ID列表
        :return: 处理状态
        """
        if not self.client:
            return False
        return self.client.delete_torrents(delete_file=True, ids=ids)

    def check_and_add_pt(self, in_from: SearchType, media_list: list, need_tvs: dict = None):
        """
        根据命中的种子媒体信息，添加下载，由RSS或Searcher调用
        :param in_from: 来源
        :param media_list: 命中并已经识别好的媒体信息列表，包括名称、年份、季、集等信息
        :param need_tvs: 缺失的剧集清单，对于剧集只有在该清单中的季和集才会下载，对于电影无需输入该参数
        :return: 已经添加了下载的媒体信息表表、剩余未下载到的媒体信息
        """
        download_items = []
        # 返回按季、集数倒序排序的列表
        download_list = self.get_download_list(media_list)
        # 电视剧整季匹配
        if need_tvs:
            # 先把整季缺失的拿出来，看是否刚好有所有季都满足的种子
            need_seasons = {}
            for need_tmdbid, need_tv in need_tvs.items():
                for tv in need_tv:
                    if not tv:
                        continue
                    if not tv.get("episodes"):
                        if not need_seasons.get(need_tmdbid):
                            need_seasons[need_tmdbid] = []
                        need_seasons[need_tmdbid].append(tv.get("season") or 1)
            # 查找整季包含的种子，只处理整季没集的种子或者是集数超过季的种子
            for need_tmdbid, need_season in need_seasons.items():
                for item in download_list:
                    if item.type == MediaType.MOVIE:
                        continue
                    item_season = item.get_season_list()
                    item_episodes = item.get_episode_list()
                    if need_tmdbid == item.tmdb_id and not item_episodes:
                        if set(item_season).issubset(set(need_season)):
                            download_items.append(item)
                            # 删除已下载的季
                            need_season = list(set(need_season).difference(set(item_season)))
                            for sea in item_season:
                                for tv in need_tvs.get(need_tmdbid):
                                    if sea == tv.get("season") or (sea == 1 and not tv.get("season")):
                                        need_tvs[need_tmdbid].remove(tv)
                            if not need_tvs.get(need_tmdbid):
                                need_tvs.pop(need_tmdbid)
                                break
        # 电视剧季内的集匹配，也有可能没有找到整季
        if need_tvs:
            need_tv_list = list(need_tvs)
            for need_tmdbid in need_tv_list:
                need_tv = need_tvs.get(need_tmdbid)
                if not need_tv:
                    continue
                index = 0
                for tv in need_tv:
                    need_season = tv.get("season") or 1
                    need_episodes = tv.get("episodes")
                    total_episodes = tv.get("total_episodes")
                    # 缺失整季的转化为缺失集进行比较
                    if not need_episodes:
                        need_episodes = list(range(1, total_episodes + 1))
                    for item in download_list:
                        if item.type == MediaType.MOVIE:
                            continue
                        if item.tmdb_id == need_tmdbid:
                            item_season = item.get_season_list()
                            item_episodes = item.get_episode_list()
                            # 这里只处理单季含集的种子，从集最多的开始下
                            if len(item_season) == 1 and item_episodes and item_season[0] == need_season:
                                if set(item_episodes).issubset(set(need_episodes)):
                                    download_items.append(item)
                                    # 删除该季下已下载的集
                                    need_episodes = list(set(need_episodes).difference(set(item_episodes)))
                                    if need_episodes:
                                        need_tvs[need_tmdbid][index]["episodes"] = need_episodes
                                    else:
                                        need_tvs[need_tmdbid].pop(index)
                                        if not need_tvs.get(need_tmdbid):
                                            need_tvs.pop(need_tmdbid)
                                        break
                    index += 1

        # 处理所有电影
        for item in download_list:
            if item.type == MediaType.MOVIE:
                download_items.append(item)

        # 添加一遍任务
        return_items = []
        for item in download_items:
            log.info("【DOWNLOADER】添加下载任务：%s ..." % item.org_string)
            ret, ret_msg = self.add_pt_torrent(media_info=item)
            if ret:
                if item not in return_items:
                    return_items.append(item)
                self.message.send_download_message(in_from, item)
                # 登记下载历史
                SqlHelper.insert_download_history(item)
            else:
                log.error("【DOWNLOADER】添加下载任务 %s 失败：%s" % (item.get_title_string(), ret_msg or "请检查下载任务是否已存在"))
                if ret_msg:
                    self.message.send_download_fail_message(item, ret_msg)
                # 对于电视剧下载失败的集数要加回去
                if item.type != MediaType.MOVIE:
                    for title, need_tv in need_tvs.items():
                        if title != item.title:
                            continue
                        for tv in need_tv:
                            if not tv:
                                continue
                            if tv.get("season") == item.get_season_list()[0]:
                                tv["episodes"] = list(set(tv.get("episodes")).union(set(item.get_episode_list())))

        # 仍然缺失的剧集，从整季中选择需要的集数文件下载，仅支持QB和TR
        if need_tvs and self.__client_type in [DownloaderType.QB, DownloaderType.TR]:
            need_tv_list = list(need_tvs)
            for need_tmdbid in need_tv_list:
                need_tv = need_tvs.get(need_tmdbid)
                if not need_tv:
                    continue
                index = 0
                for tv in need_tv:
                    need_season = tv.get("season") or 1
                    need_episodes = tv.get("episodes")
                    if not need_episodes:
                        continue
                    for item in download_list:
                        if item in return_items:
                            continue
                        if item.type == MediaType.MOVIE:
                            continue
                        # 选中一个单季整季的或单季包括需要的所有集的
                        if item.tmdb_id == need_tmdbid \
                                and (not item.get_episode_list() or set(item.get_episode_list()).issuperset(set(need_episodes))) \
                                and len(item.get_season_list()) == 1 \
                                and item.get_season_list()[0] == need_season:
                            log.info("【DOWNLOADER】添加下载任务并暂停：%s ..." % item.org_string)
                            torrent_tag = "NT" + StringUtils.generate_random_str(5)
                            ret, ret_msg = self.add_pt_torrent(media_info=item,
                                                               is_paused=True,
                                                               tag=torrent_tag)
                            if not ret:
                                log.error("【DOWNLOADER】添加下载任务 %s 失败：%s" % (item.org_string, ret_msg or "请检查下载任务是否已存在"))
                                continue
                            # 获取刚添加的任务ID
                            torrent_id = None
                            if self.__client_type == DownloaderType.TR:
                                if ret:
                                    torrent_id = ret.id
                            else:
                                # QB添加下载后需要时间，重试5次每次等待5秒
                                for i in range(1, 6):
                                    sleep(5)
                                    torrent_id = self.client.get_last_add_torrentid_by_tag(torrent_tag)
                                    if torrent_id is None:
                                        continue
                                    else:
                                        self.client.remove_torrents_tag(torrent_id, torrent_tag)
                                        break
                            if not torrent_id:
                                log.error("【DOWNLOADER】获取下载器添加的任务信息出错：%s" % item.org_string)
                                continue
                            # 设置任务只下载想要的文件
                            selected_episodes = self.set_files_status(torrent_id, need_episodes)
                            if not selected_episodes:
                                log.info("【DOWNLOADER】种子 %s 没有需要的集，删除下载任务..." % item.org_string)
                                self.client.delete_torrents(delete_file=True, ids=torrent_id)
                                continue
                            else:
                                log.info("【DOWNLOADER】%s 选取文件完成，选中集数：%s" % (item.org_string, len(selected_episodes)))
                            # 重新开始任务
                            log.info("【DOWNLOADER】%s 开始下载" % item.org_string)
                            self.start_torrents(torrent_id)
                            # 记录下载项
                            return_items.append(item)
                            # 发送消息通知
                            self.message.send_download_message(in_from, item)
                            # 登记下载历史
                            SqlHelper.insert_download_history(item)
                            # 清除记忆并退出一层循环
                            need_episodes = list(set(need_episodes).difference(set(selected_episodes)))
                            if not need_episodes:
                                need_tvs[need_tmdbid].pop(index)
                                if not need_tvs.get(need_tmdbid):
                                    need_tvs.pop(need_tmdbid)
                                break
                            else:
                                need_tvs[need_tmdbid][index]["episodes"] = need_episodes
                index += 1

        # 返回下载的资源，剩下没下完的
        return return_items, need_tvs

    def check_exists_medias(self, meta_info, no_exists=None):
        """
        检查媒体库，查询是否存在，对于剧集同时返回不存在的季集信息
        :param meta_info: 已识别的媒体信息，包括标题、年份、季、集信息
        :param no_exists: 在调用该方法前已经存储的不存在的季集信息，有传入时该函数检索的内容将会叠加后输出
        :return: 当前媒体是否缺失，各标题总的季集和缺失的季集，需要发送的消息
        """
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
            tv_info = self.media.get_tmdb_info(mtype=MediaType.TV, tmdbid=meta_info.tmdb_id)
            if tv_info:
                # 传入检查季
                total_seasons = []
                if search_season:
                    for season in search_season:
                        episode_num = self.media.get_tmdb_season_episodes_num(tv_info=tv_info, sea=season)
                        if not episode_num:
                            log.info("【DOWNLOADER】%s 第%s季 不存在" % (meta_info.get_title_string(), season))
                            message_list.append("%s 第%s季 不存在" % (meta_info.get_title_string(), season))
                            continue
                        total_seasons.append({"season_number": season, "episode_count": episode_num})
                        log.info("【DOWNLOADER】%s 第%s季 共有 %s 集" % (meta_info.get_title_string(), season, episode_num))
                else:
                    # 共有多少季，每季有多少季
                    total_seasons = self.media.get_tmdb_seasons_list(tv_info=tv_info)
                    log.info(
                        "【DOWNLOADER】%s %s 共有 %s 季" % (
                            meta_info.type.value, meta_info.get_title_string(), len(total_seasons)))
                    message_list.append(
                        "%s %s 共有 %s 季" % (meta_info.type.value, meta_info.get_title_string(), len(total_seasons)))
                # 没有得到总季数时，返回None
                if not total_seasons:
                    return_flag = None
                else:
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
                            if not no_exists.get(meta_info.tmdb_id):
                                no_exists[meta_info.tmdb_id] = []
                            # 缺失集提示文本
                            exists_tvs_str = "、".join(["%s" % tv for tv in no_exists_episodes])
                            # 存入总缺失集
                            if len(no_exists_episodes) >= episode_count:
                                no_item = {"season": season_number, "episodes": [], "total_episodes": episode_count}
                                log.info(
                                    "【DOWNLOADER】%s 第%s季 缺失 %s 集" % (
                                        meta_info.get_title_string(), season_number, episode_count))
                                if search_season:
                                    message_list.append(
                                        "%s 第%s季 缺失 %s 集" % (meta_info.title, season_number, episode_count))
                                else:
                                    message_list.append("第%s季 缺失 %s 集" % (season_number, episode_count))
                            else:
                                no_item = {"season": season_number, "episodes": no_exists_episodes,
                                           "total_episodes": episode_count}
                                log.info(
                                    "【DOWNLOADER】%s 第%s季 缺失集：%s" % (
                                        meta_info.get_title_string(), season_number, exists_tvs_str))
                                if search_season:
                                    message_list.append(
                                        "%s 第%s季 缺失集：%s" % (meta_info.title, season_number, exists_tvs_str))
                                else:
                                    message_list.append("第%s季 缺失集：%s" % (season_number, exists_tvs_str))
                            if no_item not in no_exists.get(meta_info.tmdb_id):
                                no_exists[meta_info.tmdb_id].append(no_item)
                            # 输入检查集
                            if search_episode:
                                # 有集数，肯定只有一季
                                if not set(search_episode).intersection(set(no_exists_episodes)):
                                    # 搜索的跟不存在的没有交集，说明都存在了
                                    log.info("【DOWNLOADER】%s %s 在媒体库中已经存在" % (
                                        meta_info.get_title_string(), meta_info.get_season_episode_string()))
                                    message_list.append("%s %s 在媒体库中已经存在" % (
                                        meta_info.get_title_string(), meta_info.get_season_episode_string()))
                                    return_flag = True
                                    break
                        else:
                            log.info("【DOWNLOADER】%s 第%s季 共%s集 已全部存在" % (
                                meta_info.get_title_string(), season_number, episode_count))
                            if search_season:
                                message_list.append(
                                    "%s 第%s季 共%s集 已全部存在" % (meta_info.title, season_number, episode_count))
                            else:
                                message_list.append(
                                    "第%s季 共%s集 已全部存在" % (season_number, episode_count))
            else:
                log.info("【DOWNLOADER】%s 无法查询到媒体详细信息" % meta_info.get_title_string())
                message_list.append("%s 无法查询到媒体详细信息" % meta_info.get_title_string())
                return_flag = None
            # 全部存在
            if return_flag is False and not no_exists.get(meta_info.tmdb_id):
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
                log.info("【DOWNLOADER】媒体库中已经存在以下电影：\n * %s" % movies_str)
                message_list.append("在媒体库中已经存在以下电影：\n * %s" % movies_str)
                return True, {}, message_list
            return False, {}, message_list

    def set_files_status(self, tid, need_episodes):
        """
        设置文件下载状态，选中需要下载的季集对应的文件下载，其余不下载
        :param tid: 种子的hash或id
        :param need_episodes: 需要下载的文件的集信息
        :return: 返回选中的集的列表
        """
        sucess_epidised = []
        if self.__client_type == DownloaderType.TR:
            files_info = {}
            torrent_files = self.client.get_files(tid)
            if not torrent_files:
                return []
            for file_id, torrent_file in enumerate(torrent_files):
                meta_info = MetaInfo(torrent_file.name)
                if not meta_info.get_episode_list():
                    selected = False
                else:
                    selected = set(meta_info.get_episode_list()).issubset(set(need_episodes))
                    if selected:
                        sucess_epidised = list(set(sucess_epidised).union(set(meta_info.get_episode_list())))
                if not files_info.get(tid):
                    files_info[tid] = {file_id: {'priority': 'normal', 'selected': selected}}
                else:
                    files_info[tid][file_id] = {'priority': 'normal', 'selected': selected}
            if sucess_epidised and files_info:
                self.client.set_files(file_info=files_info)
        elif self.__client_type == DownloaderType.QB:
            file_ids = []
            torrent_files = self.client.get_files(tid)
            if not torrent_files:
                return []
            for torrent_file in torrent_files:
                meta_info = MetaInfo(torrent_file.get("name"))
                if not meta_info.get_episode_list() or not set(meta_info.get_episode_list()).issubset(
                        set(need_episodes)):
                    file_ids.append(torrent_file.get("index"))
                else:
                    sucess_epidised = list(set(sucess_epidised).union(set(meta_info.get_episode_list())))
            if sucess_epidised and file_ids:
                self.client.set_files(torrent_hash=tid, file_ids=file_ids, priority=0)
        return sucess_epidised

    def get_download_list(self, media_list):
        """
        对媒体信息进行排序、去重
        """
        if not media_list:
            return []

        # 排序函数，标题、站点、资源类型、做种数量
        def get_sort_str(x):
            season_len = str(len(x.get_season_list())).rjust(2, '0')
            episode_len = str(len(x.get_episode_list())).rjust(4, '0')
            # 排序：标题、资源类型、站点、做种、季集
            if self.__download_order == "seeder":
                return "%s%s%s%s%s" % (str(x.title).ljust(100, ' '),
                                       str(x.res_order).rjust(3, '0'),
                                       str(x.seeders).rjust(10, '0'),
                                       str(x.site_order).rjust(3, '0'),
                                       "%s%s" % (season_len, episode_len))
            else:
                return "%s%s%s%s%s" % (str(x.title).ljust(100, ' '),
                                       str(x.res_order).rjust(3, '0'),
                                       str(x.site_order).rjust(3, '0'),
                                       str(x.seeders).rjust(10, '0'),
                                       "%s%s" % (season_len, episode_len))

        # 匹配的资源中排序分组选最好的一个下载
        # 按站点顺序、资源匹配顺序、做种人数下载数逆序排序
        media_list = sorted(media_list, key=lambda x: get_sort_str(x), reverse=True)
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

    def get_download_dirs(self):
        """
        返回下载器中设置的保存目录
        """
        if not self.__downloaddir:
            return []
        return self.__downloaddir.keys()

    def __get_download_dir_info(self, media):
        """
        根据媒体信息读取一个下载目录的信息
        """
        if media and media.tmdb_info:
            for path, attr in self.__downloaddir.items():
                if not path or not attr:
                    continue
                if attr.get('type') and attr.get('type') != media.type.value:
                    continue
                if attr.get('category') and attr.get('category') != media.category:
                    continue
                if not attr.get('path'):
                    continue
                if not os.path.exists(attr.get('path')) \
                        or (media.size
                            and float(SystemUtils.get_free_space_gb(attr.get('path'))) < float(int(StringUtils.num_filesize(media.size)) / 1024 / 1024 / 1024)):
                    continue
                return {"path": path, "label": attr.get('label')}
        return {"path": None, "label": None}

    def get_type(self):
        """
        返回下载器类型
        """
        return self.__client_type
