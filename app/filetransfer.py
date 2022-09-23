import argparse
import os
import platform
import random
import re
import shutil
import traceback
from enum import Enum
from subprocess import call
from threading import Lock
from time import sleep

import log
from app.db import SqlHelper
from config import RMT_SUBEXT, RMT_MEDIAEXT, RMT_FAVTYPE, Config, RMT_MIN_FILESIZE, DEFAULT_MOVIE_FORMAT, \
    DEFAULT_TV_FORMAT
from app.message import Message
from app.mediaserver import MediaServer
from app.subtitle import Subtitle
from app.media import Media, MetaInfo, Category, Scraper
from app.utils import EpisodeFormat, PathUtils, StringUtils, SystemUtils, ThreadHelper
from app.utils.types import MediaType, SyncType, RmtMode, OsType, RMT_MODES

lock = Lock()


class FileTransfer:
    media = None
    message = None
    category = None
    mediaserver = None
    scraper = None
    threadhelper = None

    __system = OsType.LINUX
    __default_rmt_mode = None
    __movie_path = None
    __tv_path = None
    __anime_path = None
    __movie_category_flag = None
    __tv_category_flag = None
    __anime_category_flag = None
    __unknown_path = None
    __min_filesize = RMT_MIN_FILESIZE
    __filesize_cover = False
    __movie_dir_rmt_format = ""
    __movie_file_rmt_format = ""
    __tv_dir_rmt_format = ""
    __tv_season_rmt_format = ""
    __tv_file_rmt_format = ""
    __scraper_flag = False
    __scraper_nfo = {}
    __scraper_pic = {}
    __refresh_mediaserver = False

    def __init__(self):
        self.media = Media()
        self.message = Message()
        self.category = Category()
        self.mediaserver = MediaServer()
        self.scraper = Scraper()
        self.threadhelper = ThreadHelper()
        self.init_config()

    def init_config(self):
        self.__system = SystemUtils.get_system()
        config = Config()
        media = config.get_config('media')
        self.__scraper_flag = media.get("nfo_poster")
        self.__scraper_nfo = config.get_config('scraper_nfo')
        self.__scraper_pic = config.get_config('scraper_pic')
        if media:
            # 刷新媒体库开关
            self.__refresh_mediaserver = media.get("refresh_mediaserver")
            # 电影目录
            self.__movie_path = media.get('movie_path')
            if not isinstance(self.__movie_path, list):
                if self.__movie_path:
                    self.__movie_path = [self.__movie_path]
                else:
                    self.__movie_path = []
            # 电影分类
            self.__movie_category_flag = self.category.get_movie_category_flag()
            # 电视剧目录
            self.__tv_path = media.get('tv_path')
            if not isinstance(self.__tv_path, list):
                if self.__tv_path:
                    self.__tv_path = [self.__tv_path]
                else:
                    self.__tv_path = []
            # 电视剧分类
            self.__tv_category_flag = self.category.get_tv_category_flag()
            # 动漫目录
            self.__anime_path = media.get('anime_path')
            if not isinstance(self.__anime_path, list):
                if self.__anime_path:
                    self.__anime_path = [self.__anime_path]
                else:
                    self.__anime_path = []
            # 动漫分类
            self.__anime_category_flag = self.category.get_anime_category_flag()
            # 没有动漫目漫切换为电视剧目录和分类
            if not self.__anime_path:
                self.__anime_path = self.__tv_path
                self.__anime_category_flag = self.__tv_category_flag
            # 未识别目录
            self.__unknown_path = media.get('unknown_path')
            if not isinstance(self.__unknown_path, list):
                if self.__unknown_path:
                    self.__unknown_path = [self.__unknown_path]
                else:
                    self.__unknown_path = []
            # 最小文件大小
            min_filesize = media.get('min_filesize')
            if isinstance(min_filesize, int):
                self.__min_filesize = min_filesize * 1024 * 1024
            elif isinstance(min_filesize, str) and min_filesize.isdigit():
                self.__min_filesize = int(min_filesize) * 1024 * 1024
            # 高质量文件覆盖
            self.__filesize_cover = media.get('filesize_cover')
            # 电影重命名格式
            movie_name_format = media.get('movie_name_format') or DEFAULT_MOVIE_FORMAT
            movie_formats = movie_name_format.split('/')
            if movie_formats:
                self.__movie_dir_rmt_format = movie_formats[0]
                if len(movie_formats) > 1:
                    self.__movie_file_rmt_format = movie_formats[1]
            # 电视剧重命名格式
            tv_name_format = media.get('tv_name_format') or DEFAULT_TV_FORMAT
            tv_formats = tv_name_format.split('/')
            if tv_formats:
                self.__tv_dir_rmt_format = tv_formats[0]
                if len(tv_formats) > 1:
                    self.__tv_season_rmt_format = tv_formats[1]
                if len(tv_formats) > 2:
                    self.__tv_file_rmt_format = tv_formats[2]
        self.__default_rmt_mode = RMT_MODES.get(config.get_config('pt').get('rmt_mode', 'copy'), RmtMode.COPY)

    def __transfer_command(self, file_item, target_file, rmt_mode):
        """
        使用系统命令处理单个文件
        :param file_item: 文件路径
        :param target_file: 目标文件路径
        :param rmt_mode: RmtMode转移方式
        """
        try:
            lock.acquire()
            if self.__system == OsType.WINDOWS:
                if rmt_mode == RmtMode.LINK:
                    retcode = os.system('mklink /H "{}" "{}"'.format(target_file, file_item))
                elif rmt_mode == RmtMode.SOFTLINK:
                    retcode = os.system('mklink "{}" "{}"'.format(target_file, file_item))
                elif rmt_mode == RmtMode.MOVE:
                    retcode = os.system('rename "{}" "{}"'.format(file_item, os.path.basename(target_file)))
                    if retcode != 0:
                        return retcode
                    retcode = os.system('move /Y "{}" "{}"'.format(
                        os.path.join(os.path.dirname(file_item), os.path.basename(target_file)), target_file))
                    log.info("移动状态: {}".format(retcode))
                elif rmt_mode == RmtMode.RCLONE or rmt_mode == RmtMode.RCLONECOPY:
                    if target_file.startswith("/") or target_file.startswith("\\"):
                        target_file = target_file[1:]
                    if rmt_mode == RmtMode.RCLONE:
                        retcode = os.system('rclone.exe moveto "{}" NASTOOL:"{}"'.format(file_item, target_file))
                    else:
                        retcode = os.system('rclone.exe copyto "{}" NASTOOL:"{}"'.format(file_item, target_file))
                else:
                    retcode = os.system('copy /Y "{}" "{}"'.format(file_item, target_file))
            else:
                if rmt_mode == RmtMode.LINK:
                    if platform.release().find("-z4-") >= 0:
                        tmp = "%s/%s" % (PathUtils.get_parent_paths(target_file, 2), os.path.basename(target_file))
                        retcode = call(["ln", file_item, tmp])
                        if retcode == 0:
                            retcode = call(["mv", tmp, target_file])
                    else:
                        retcode = call(["ln", file_item, target_file])
                elif rmt_mode == RmtMode.SOFTLINK:
                    retcode = call(["ln", "-s", file_item, target_file])
                elif rmt_mode == RmtMode.MOVE:
                    tmp_file = os.path.join(os.path.dirname(file_item), os.path.basename(target_file))
                    retcode = call(["mv", file_item, tmp_file])
                    if retcode == 0:
                        retcode = call(["mv", tmp_file, target_file])
                elif rmt_mode == RmtMode.RCLONE or rmt_mode == RmtMode.RCLONECOPY:
                    if target_file.startswith("/") or target_file.startswith("\\"):
                        target_file = target_file[1:]
                    if rmt_mode == RmtMode.RCLONE:
                        retcode = call(["rclone", "moveto", file_item, "NASTOOL:" + target_file])
                    else:
                        retcode = call(["rclone", "copyto", file_item, "NASTOOL:" + target_file])
                else:
                    retcode = call(["cp", file_item, target_file])
        finally:
            lock.release()
        return retcode

    def __transfer_subtitles(self, org_name, new_name, rmt_mode):
        """
        根据文件名转移对应字幕文件
        :param org_name: 原文件名
        :param new_name: 新文件名
        :param rmt_mode: RmtMode转移方式
        """
        dir_name = os.path.dirname(org_name)
        file_name = os.path.basename(org_name)
        file_list = PathUtils.get_dir_level1_files(dir_name, RMT_SUBEXT)
        if len(file_list) == 0:
            log.debug("【RMT】%s 目录下没有找到字幕文件..." % dir_name)
        else:
            log.debug("【RMT】字幕文件清单：" + str(file_list))
            metainfo = MetaInfo(title=file_name)
            for file_item in file_list:
                sub_metainfo = MetaInfo(title=os.path.basename(file_item))
                if (sub_metainfo.cn_name and sub_metainfo.cn_name == metainfo.cn_name) \
                        or (sub_metainfo.en_name and sub_metainfo.en_name == metainfo.en_name):
                    if metainfo.get_season_string() and metainfo.get_season_string() != sub_metainfo.get_season_string():
                        continue
                    if metainfo.get_episode_string() and metainfo.get_episode_string() != sub_metainfo.get_episode_string():
                        continue
                    file_ext = os.path.splitext(file_item)[-1]
                    sub_language = os.path.basename(file_item).split(".")[-2]
                    if sub_language and (sub_language.lower() in ["zh-cn", "cn", "zh", "zh_cn", "chs", "cht"]
                                         or "简" in sub_language
                                         or "中" in sub_language
                                         or "双" in sub_language):
                        new_file = os.path.splitext(new_name)[0] + ".zh-cn" + file_ext
                    else:
                        new_file = os.path.splitext(new_name)[0] + file_ext
                    if not os.path.exists(new_file):
                        log.debug("【RMT】正在处理字幕：%s" % os.path.basename(file_item))
                        retcode = self.__transfer_command(file_item=file_item,
                                                          target_file=new_file,
                                                          rmt_mode=rmt_mode)
                        if retcode == 0:
                            log.info("【RMT】字幕 %s %s完成" % (os.path.basename(file_item), rmt_mode.value))
                        else:
                            log.error("【RMT】字幕 %s %s失败，错误码 %s" % (file_name, rmt_mode.value, str(retcode)))
                            return retcode
                    else:
                        log.info("【RMT】字幕 %s 已存在" % new_file)
        return 0

    def __transfer_bluray_dir(self, file_path, new_path, rmt_mode):
        """
        转移蓝光文件夹
        :param file_path: 原路径
        :param new_path: 新路径
        :param rmt_mode: RmtMode转移方式
        """
        log.info("【RMT】正在%s目录：%s 到 %s" % (rmt_mode.value, file_path, new_path))
        # 复制
        retcode = self.__transfer_dir_files(src_dir=file_path,
                                            target_dir=new_path,
                                            rmt_mode=rmt_mode,
                                            bludir=True)
        if retcode == 0:
            log.info("【RMT】文件 %s %s完成" % (file_path, rmt_mode.value))
        else:
            log.error("【RMT】文件%s %s失败，错误码 %s" % (file_path, rmt_mode.value, str(retcode)))
        return retcode

    def is_target_dir_path(self, path):
        """
        判断是否为目的路径下的路径
        :param path: 路径
        :return: True/False
        """
        if not path:
            return False
        for tv_path in self.__tv_path:
            if PathUtils.is_path_in_path(tv_path, path):
                return True
        for movie_path in self.__movie_path:
            if PathUtils.is_path_in_path(movie_path, path):
                return True
        for anime_path in self.__anime_path:
            if PathUtils.is_path_in_path(anime_path, path):
                return True
        for unknown_path in self.__unknown_path:
            if PathUtils.is_path_in_path(unknown_path, path):
                return True
        return False

    def __transfer_dir_files(self, src_dir, target_dir, rmt_mode, bludir=False):
        """
        按目录结构转移所有文件
        :param src_dir: 原路径
        :param target_dir: 新路径
        :param rmt_mode: RmtMode转移方式
        :param bludir: 是否蓝光目录
        """
        file_list = PathUtils.get_dir_files(src_dir)
        retcode = 0
        for file in file_list:
            new_file = file.replace(src_dir, target_dir)
            if os.path.exists(new_file):
                log.warn("【RMT】%s 文件已存在" % new_file)
                continue
            new_dir = os.path.dirname(new_file)
            if not os.path.exists(new_dir):
                os.makedirs(new_dir)
            retcode = self.__transfer_command(file_item=file,
                                              target_file=new_file,
                                              rmt_mode=rmt_mode)
            if retcode != 0:
                break
            else:
                if not bludir:
                    SqlHelper.insert_transfer_blacklist(file)
        if retcode == 0 and bludir:
            SqlHelper.insert_transfer_blacklist(src_dir)
        return retcode

    def __transfer_origin_file(self, file_item, target_dir, rmt_mode):
        """
        按原文件名link文件到目的目录
        :param file_item: 原文件路径
        :param target_dir: 目的目录
        :param rmt_mode: RmtMode转移方式
        """
        if not file_item or not target_dir:
            return -1
        if not os.path.exists(file_item):
            log.warn("【RMT】%s 不存在" % file_item)
            return -1
        # 计算目录目录
        parent_name = os.path.basename(os.path.dirname(file_item))
        target_dir = os.path.join(target_dir, parent_name)
        if not os.path.exists(target_dir):
            log.debug("【RMT】正在创建目录：%s" % target_dir)
            os.makedirs(target_dir)
        # 目录
        if os.path.isdir(file_item):
            log.info("【RMT】正在%s目录：%s 到 %s" % (rmt_mode.value, file_item, target_dir))
            retcode = self.__transfer_dir_files(src_dir=file_item,
                                                target_dir=target_dir,
                                                rmt_mode=rmt_mode)
        # 文件
        else:
            target_file = os.path.join(target_dir, os.path.basename(file_item))
            if os.path.exists(target_file):
                log.warn("【RMT】%s 文件已存在" % target_file)
                return 0
            retcode = self.__transfer_command(file_item=file_item,
                                              target_file=target_file,
                                              rmt_mode=rmt_mode)
            if retcode == 0:
                SqlHelper.insert_transfer_blacklist(file_item)
        if retcode == 0:
            log.info("【RMT】%s %s到unknown完成" % (file_item, rmt_mode.value))
        else:
            log.error("【RMT】%s %s到unknown失败，错误码 %s" % (file_item, rmt_mode.value, retcode))
        return retcode

    def __transfer_file(self, file_item, new_file, rmt_mode, over_flag=False):
        """
        转移一个文件，同时处理字幕
        :param file_item: 原文件路径
        :param new_file: 新文件路径
        :param rmt_mode: RmtMode转移方式
        :param over_flag: 是否覆盖，为True时会先删除再转移
        """
        file_name = os.path.basename(file_item)
        if not over_flag and os.path.exists(new_file):
            log.warn("【RMT】文件已存在：%s" % new_file)
            return 0
        if over_flag and os.path.isfile(new_file):
            log.info("【RMT】正在删除已存在的文件：%s" % new_file)
            os.remove(new_file)
        log.info("【RMT】正在转移文件：%s 到 %s" % (file_name, new_file))
        retcode = self.__transfer_command(file_item=file_item,
                                          target_file=new_file,
                                          rmt_mode=rmt_mode)
        if retcode == 0:
            log.info("【RMT】文件 %s %s完成" % (file_name, rmt_mode.value))
            SqlHelper.insert_transfer_blacklist(file_item)
        else:
            log.error("【RMT】文件 %s %s失败，错误码 %s" % (file_name, rmt_mode.value, str(retcode)))
            return retcode
        # 处理字幕
        return self.__transfer_subtitles(org_name=file_item,
                                         new_name=new_file,
                                         rmt_mode=rmt_mode)

    def transfer_media(self,
                       in_from: Enum,
                       in_path,
                       rmt_mode: RmtMode = None,
                       files: list = None,
                       target_dir=None,
                       unknown_dir=None,
                       tmdb_info=None,
                       media_type: MediaType = None,
                       season=None,
                       episode: (EpisodeFormat, bool) = None,
                       min_filesize=None,
                       udf_flag=False):
        """
        识别并转移一个文件、多个文件或者目录
        :param in_from: 来源，即调用该功能的渠道
        :param in_path: 转移的路径，可能是一个文件也可以是一个目录
        :param files: 文件清单，非空时以该文件清单为准，为空时从in_path中按后缀和大小限制检索需要处理的文件清单
        :param target_dir: 目的文件夹，非空的转移到该文件夹，为空时则按类型转移到配置文件中的媒体库文件夹
        :param unknown_dir: 未识别文件夹，非空时未识别的媒体文件转移到该文件夹，为空时则使用配置文件中的未识别文件夹
        :param rmt_mode: 文件转移方式
        :param tmdb_info: 手动识别转移时传入的TMDB信息对象，如未输入，则按名称笔TMDB实时查询
        :param media_type: 手动识别转移时传入的文件类型，如未输入，则自动识别
        :param season: 手动识别目录或文件时传入的的字号，如未输入，则自动识别
        :param episode: (EpisodeFormat，是否批处理匹配)
        :param min_filesize: 过滤小文件大小的上限值
        :param udf_flag: 自定义转移标志，为True时代表是自定义转移，此时很多处理不一样
        :return: 处理状态，错误信息
        """
        episode = (None, False) if not episode else episode
        if not in_path:
            log.error("【RMT】输入路径错误!")
            return False, "输入路径错误"

        if not rmt_mode:
            rmt_mode = self.__default_rmt_mode

        log.info("【RMT】开始处理：%s，转移方式：%s" % (in_path, rmt_mode.value))

        success_flag = True
        error_message = ""
        bluray_disk_dir = None
        if not files:
            # 如果传入的是个目录
            if os.path.isdir(in_path):
                if not os.path.exists(in_path):
                    log.error("【RMT】文件转移失败，目录不存在 %s" % in_path)
                    return False, "目录不存在"
                # 回收站及隐藏的文件不处理
                if PathUtils.is_invalid_path(in_path):
                    return False, "回收站或者隐藏文件夹"
                # 判断是不是原盘文件夹
                bluray_disk_dir = PathUtils.get_bluray_dir(in_path)
                if bluray_disk_dir:
                    file_list = [bluray_disk_dir]
                    log.info("【RMT】当前为蓝光原盘文件夹：%s" % str(in_path))
                else:
                    if udf_flag:
                        # 自定义转移时未输入大小限制默认不限制
                        now_filesize = 0 if not str(min_filesize).isdigit() else int(
                            min_filesize) * 1024 * 1024
                    else:
                        # 未输入大小限制默认为配置大小限制
                        now_filesize = self.__min_filesize if not str(min_filesize).isdigit() else int(
                            min_filesize) * 1024 * 1024
                    # 查找目录下的文件
                    file_list = PathUtils.get_dir_files(in_path=in_path, episode_format=episode[0], exts=RMT_MEDIAEXT,
                                                        filesize=now_filesize)
                    log.debug("【RMT】文件清单：" + str(file_list))
                    if len(file_list) == 0:
                        log.warn(
                            "【RMT】%s 目录下未找到媒体文件，当前最小文件大小限制为 %s" % (in_path, StringUtils.str_filesize(now_filesize)))
                        return False, "目录下未找到媒体文件，当前最小文件大小限制为 %s" % StringUtils.str_filesize(now_filesize)
            # 传入的是个文件
            else:
                if not os.path.exists(in_path):
                    log.error("【RMT】文件转移失败，文件不存在：%s" % in_path)
                    return False, "文件不存在"
                if os.path.splitext(in_path)[-1].lower() not in RMT_MEDIAEXT:
                    log.warn("【RMT】不支持的媒体文件格式，不处理：%s" % in_path)
                    return False, "不支持的媒体文件格式"
                # 判断是不是原盘文件夹
                bluray_disk_dir = PathUtils.get_bluray_dir(in_path)
                if bluray_disk_dir:
                    file_list = [bluray_disk_dir]
                    log.info("【RMT】当前为蓝光原盘文件夹：%s" % bluray_disk_dir)
                else:
                    file_list = [in_path]
        else:
            # 传入的是个文件列表，这些文失件是in_path下面的文件
            file_list = files

        # 目录同步模式下，过滤掉文件列表中已处理过的
        if in_from == SyncType.MON:
            file_list = list(filter(SqlHelper.is_transfer_notin_blacklist, file_list))
            if not file_list:
                log.info("【RMT】所有文件均已成功转移过，没有需要处理的文件！如需重新处理，请清理缓存（服务->清理转移缓存）")
                return True, "没有新文件需要处理"
        # API检索出媒体信息，传入一个文件列表，得出每一个文件的名称，这里是当前目录下所有的文件了
        Medias = self.media.get_media_info_on_files(file_list, tmdb_info, media_type, season, episode[0])
        if not Medias:
            log.error("【RMT】检索媒体信息出错！")
            return False, "检索媒体信息出错"

        # 统计总的文件数、失败文件数、需要提醒的失败数
        failed_count = 0
        alert_count = 0
        total_count = 0
        # 电视剧可能有多集，如果在循环里发消息就太多了，要在外面发消息
        message_medias = {}
        # 需要刷新媒体库的清单
        refresh_library_items = []
        # 需要下载字段的清单
        download_subtitle_items = []
        # 处理识别后的每一个文件或单个文件夹
        for file_item, media in Medias.items():
            try:
                if not udf_flag:
                    if re.search(r'[./\s\[]+Sample[/.\s\]]+', file_item, re.IGNORECASE):
                        log.warn("【RMT】%s 可能是预告片，跳过..." % file_item)
                        continue
                # 总数量
                total_count = total_count + 1
                # 文件名
                file_name = os.path.basename(file_item)
                # 上级目录
                file_path = os.path.dirname(file_item)

                # 数据库记录的路径
                if bluray_disk_dir:
                    reg_path = bluray_disk_dir
                elif media.type == MediaType.MOVIE:
                    reg_path = file_item
                else:
                    reg_path = max(file_path, in_path)
                # 未识别
                if not media or not media.tmdb_info or not media.get_title_string():
                    log.warn("【RMT】%s 无法识别媒体信息！" % file_name)
                    success_flag = False
                    error_message = "无法识别媒体信息"
                    if udf_flag:
                        return success_flag, error_message
                    # 记录未识别
                    SqlHelper.insert_transfer_unknown(reg_path, target_dir)
                    failed_count += 1
                    alert_count += 1
                    # 原样转移过去
                    if unknown_dir:
                        log.warn("【RMT】%s 按原文件名转移到unknown目录：%s" % (file_name, unknown_dir))
                        self.__transfer_origin_file(file_item=file_item, target_dir=unknown_dir, rmt_mode=rmt_mode)
                    elif self.__unknown_path:
                        unknown_path = self.__get_best_unknown_path(in_path)
                        if not unknown_path:
                            continue
                        log.warn("【RMT】%s 按原文件名转移到unknown目录：%s" % (file_name, unknown_path))
                        self.__transfer_origin_file(file_item=file_item, target_dir=unknown_path, rmt_mode=rmt_mode)
                    else:
                        log.error("【RMT】%s 无法识别媒体信息！" % file_name)
                    continue
                # 当前文件大小
                media.size = os.path.getsize(file_item)
                # 目的目录，有输入target_dir时，往这个目录放
                if target_dir:
                    dist_path = target_dir
                else:
                    dist_path = self.__get_best_target_path(mtype=media.type, in_path=in_path, size=media.size)
                if not dist_path:
                    log.error("【RMT】文件转移失败，目的路径不存在！")
                    success_flag = False
                    error_message = "目的路径不存在"
                    failed_count += 1
                    alert_count += 1
                    continue
                if dist_path and not os.path.exists(dist_path):
                    return False, "目录不存在：%s" % dist_path

                # 判断文件是否已存在，返回：目录存在标志、目录名、文件存在标志、文件名
                dir_exist_flag, ret_dir_path, file_exist_flag, ret_file_path = self.__is_media_exists(dist_path, media)
                # 已存在的文件数量
                exist_filenum = 0
                handler_flag = False
                # 路径存在
                if dir_exist_flag:
                    # 蓝光原盘
                    if bluray_disk_dir:
                        log.warn("【RMT】蓝光原盘目录已存在：%s" % ret_dir_path)
                        if udf_flag:
                            return False, "蓝光原盘目录已存在：%s" % ret_dir_path
                        failed_count += 1
                        continue
                    # 文年存在
                    if file_exist_flag:
                        exist_filenum = exist_filenum + 1
                        if rmt_mode != RmtMode.SOFTLINK:
                            if media.size > os.path.getsize(ret_file_path) and self.__filesize_cover or udf_flag:
                                log.info("【RMT】文件 %s 已存在，覆盖..." % ret_file_path)
                                ret = self.__transfer_file(file_item=file_item,
                                                           new_file=ret_file_path,
                                                           rmt_mode=rmt_mode,
                                                           over_flag=True)
                                if ret != 0:
                                    success_flag = False
                                    error_message = "文件转移失败，错误码 %s" % ret
                                    if udf_flag:
                                        return success_flag, error_message
                                    failed_count += 1
                                    alert_count += 1
                                    continue
                                handler_flag = True
                            else:
                                log.warn("【RMT】文件 %s 已存在" % ret_file_path)
                                failed_count += 1
                                continue
                        else:
                            log.warn("【RMT】文件 %s 已存在" % ret_file_path)
                            failed_count += 1
                            continue
                # 路径不存在
                else:
                    if not ret_dir_path:
                        log.error("【RMT】拼装目录路径错误，无法从文件名中识别出季集信息：%s" % file_item)
                        success_flag = False
                        error_message = "识别失败，无法从文件名中识别出季集信息"
                        if udf_flag:
                            return success_flag, error_message
                        # 记录未识别
                        SqlHelper.insert_transfer_unknown(reg_path, target_dir)
                        failed_count += 1
                        alert_count += 1
                        continue
                    else:
                        # 创建电录
                        log.debug("【RMT】正在创建目录：%s" % ret_dir_path)
                        os.makedirs(ret_dir_path)
                # 转移蓝光原盘
                if bluray_disk_dir:
                    ret = self.__transfer_bluray_dir(file_item, ret_dir_path, rmt_mode)
                    if ret != 0:
                        success_flag = False
                        error_message = "蓝光目录转移失败，错误码：%s" % ret
                        if udf_flag:
                            return success_flag, error_message
                        failed_count += 1
                        alert_count += 1
                        continue
                else:
                    # 开始转移文件
                    if not handler_flag:
                        file_ext = os.path.splitext(file_item)[-1]
                        if not ret_file_path:
                            log.error("【RMT】拼装文件路径错误，无法从文件名中识别出集数：%s" % file_item)
                            success_flag = False
                            error_message = "识别失败，无法从文件名中识别出集数"
                            if udf_flag:
                                return success_flag, error_message
                            # 记录未识别
                            SqlHelper.insert_transfer_unknown(reg_path, target_dir)
                            failed_count += 1
                            alert_count += 1
                            continue
                        new_file = "%s%s" % (ret_file_path, file_ext)
                        ret = self.__transfer_file(file_item=file_item,
                                                   new_file=new_file,
                                                   rmt_mode=rmt_mode,
                                                   over_flag=False)
                        if ret != 0:
                            success_flag = False
                            error_message = "文件转移失败，错误码 %s" % ret
                            if udf_flag:
                                return success_flag, error_message
                            failed_count += 1
                            alert_count += 1
                            continue
                # 媒体库刷新条目：类型-类别-标题-年份
                refresh_item = {"type": media.type, "category": media.category, "title": media.title,
                                "year": media.year, "target_path": dist_path}
                # 登记媒体库刷新
                if refresh_item not in refresh_library_items:
                    refresh_library_items.append(refresh_item)
                # 下载字幕条目
                subtitle_item = {"type": media.type, "file": ret_file_path, "file_ext": os.path.splitext(file_item)[-1],
                                 "name": media.get_name(), "title": media.title, "year": media.year,
                                 "season": media.begin_season, "episode": media.begin_episode,
                                 "bluray": True if bluray_disk_dir else False}
                # 登记字幕下载
                if subtitle_item not in download_subtitle_items:
                    download_subtitle_items.append(subtitle_item)
                # 转移历史记录
                SqlHelper.insert_transfer_history(in_from, rmt_mode, reg_path, dist_path, media)
                # 未识别手动识别或历史记录重新识别的批处理模式
                if isinstance(episode[1], bool) and episode[1]:
                    # 未识别手动识别，更改未识别记录为已处理
                    SqlHelper.update_transfer_unknown_state(file_item)
                # 电影立即发送消息
                if media.type == MediaType.MOVIE:
                    self.message.send_transfer_movie_message(in_from,
                                                             media,
                                                             exist_filenum,
                                                             self.__movie_category_flag)
                # 否则登记汇总发消息
                else:
                    # 按季汇总
                    message_key = "%s-%s" % (media.get_title_string(), media.get_season_string())
                    if not message_medias.get(message_key):
                        message_medias[message_key] = media
                    # 汇总集数、大小
                    if not message_medias[message_key].is_in_episode(media.get_episode_list()):
                        message_medias[message_key].total_episodes += media.total_episodes
                        message_medias[message_key].size += media.size
                # 生成nfo及poster
                if self.__scraper_flag:
                    # 查询TMDB详情
                    media.set_tmdb_info(self.media.get_tmdb_info(mtype=media.type, tmdbid=media.tmdb_id))
                    # 生成刮削文件
                    self.scraper.gen_scraper_files(media=media,
                                                   scraper_nfo=self.__scraper_nfo,
                                                   scraper_pic=self.__scraper_pic,
                                                   dir_path=ret_dir_path,
                                                   file_name=os.path.basename(ret_file_path))
                # 移动模式随机休眠（兼容一些网盘挂载目录）
                if rmt_mode == RmtMode.MOVE:
                    sleep(round(random.uniform(0, 1), 1))

            except Exception as err:
                log.error("【RMT】文件转移时发生错误：%s - %s" % (str(err), traceback.format_exc()))
        # 循环结束
        # 统计完成情况，发送通知
        if message_medias:
            self.message.send_transfer_tv_message(message_medias, in_from)
        # 刷新媒体库
        if refresh_library_items and self.__refresh_mediaserver:
            self.mediaserver.refresh_library_by_items(refresh_library_items)
        # 启新进程下载字幕
        if download_subtitle_items:
            self.threadhelper.start_thread(Subtitle().download_subtitle, (download_subtitle_items,))
        # 总结
        log.info("【RMT】%s 处理完成，总数：%s，失败：%s" % (in_path, total_count, failed_count))
        if alert_count > 0:
            self.message.send_transfer_fail_message(in_path, alert_count)
        elif failed_count == 0:
            # 删除空目录
            if rmt_mode == RmtMode.MOVE \
                    and os.path.exists(in_path) \
                    and os.path.isdir(in_path) \
                    and not PathUtils.get_dir_files(in_path=in_path, exts=RMT_MEDIAEXT) \
                    and not PathUtils.get_dir_files(in_path=in_path, exts=['.!qb', '.part']):
                log.info("【RMT】目录下已无媒体文件及正在下载的文件，移动模式下删除目录：%s" % in_path)
                shutil.rmtree(in_path)
        return success_flag, error_message

    def transfer_manually(self, s_path, t_path, mode):
        """
        全量转移，用于使用命令调用
        :param s_path: 源目录
        :param t_path: 目的目录
        :param mode: 转移方式
        """
        if not s_path:
            return
        if not os.path.exists(s_path):
            print("【RMT】源目录不存在：%s" % s_path)
            return
        if t_path:
            if not os.path.exists(t_path):
                print("【RMT】目的目录不存在：%s" % t_path)
                return
        rmt_mode = RMT_MODES.get(mode)
        if not rmt_mode:
            print("【RMT】转移模式错误！")
            return
        print("【RMT】转移模式为：%s" % rmt_mode.value)
        print("【RMT】正在转移以下目录中的全量文件：%s" % s_path)
        for path in PathUtils.get_dir_level1_medias(s_path, RMT_MEDIAEXT):
            if PathUtils.is_invalid_path(path):
                continue
            ret, ret_msg = self.transfer_media(in_from=SyncType.MAN,
                                               in_path=path,
                                               target_dir=t_path,
                                               rmt_mode=rmt_mode)
            if not ret:
                print("【RMT】%s 处理失败：%s" % (path, ret_msg))

    def __is_media_exists(self,
                          media_dest,
                          media):
        """
        判断媒体文件是否忆存在
        :param media_dest: 媒体文件所在目录
        :param media: 已识别的媒体信息
        :return: 目录是否存在，目录路径，文件是否存在，文件路径
        """
        # 返回变量
        dir_exist_flag = False
        file_exist_flag = False
        ret_dir_path = None
        ret_file_path = None
        # 电影
        if media.type == MediaType.MOVIE:
            # 目录名称
            dir_name, file_name = self.get_moive_dest_path(media)
            # 默认目录路径
            file_path = os.path.join(media_dest, dir_name)
            # 开启分类时目录路径
            if self.__movie_category_flag:
                file_path = os.path.join(media_dest, media.category, dir_name)
                for m_type in [RMT_FAVTYPE, media.category]:
                    type_path = os.path.join(media_dest, m_type, dir_name)
                    # 目录是否存在
                    if os.path.exists(type_path):
                        file_path = type_path
                        break
            # 返回路径
            ret_dir_path = file_path
            # 路径存在标志
            if os.path.exists(file_path):
                dir_exist_flag = True
            # 文件路径
            file_dest = os.path.join(file_path, file_name)
            # 返回文件路径
            ret_file_path = file_dest
            # 文件是否存在
            for ext in RMT_MEDIAEXT:
                ext_dest = "%s%s" % (file_dest, ext)
                if os.path.exists(ext_dest):
                    file_exist_flag = True
                    ret_file_path = ext_dest
                    break
        # 电视剧或者动漫
        else:
            # 目录名称
            dir_name, season_name, file_name = self.get_tv_dest_path(media)
            # 剧集目录
            if (media.type == MediaType.TV and self.__tv_category_flag) or (
                    media.type == MediaType.ANIME and self.__anime_category_flag):
                media_path = os.path.join(media_dest, media.category, dir_name)
            else:
                media_path = os.path.join(media_dest, dir_name)
            # 季
            if media.get_season_list():
                # 季路径
                season_dir = os.path.join(media_path, season_name)
                # 返回目录路径
                ret_dir_path = season_dir
                # 目录是否存在
                if os.path.exists(season_dir):
                    dir_exist_flag = True
                # 处理集
                episodes = media.get_episode_list()
                if episodes:
                    # 集文件路径
                    file_path = os.path.join(season_dir, file_name)
                    # 返回文件路径
                    ret_file_path = file_path
                    # 文件存在标志
                    for ext in RMT_MEDIAEXT:
                        ext_dest = "%s%s" % (file_path, ext)
                        if os.path.exists(ext_dest):
                            file_exist_flag = True
                            ret_file_path = ext_dest
                            break
        return dir_exist_flag, ret_dir_path, file_exist_flag, ret_file_path

    def transfer_embyfav(self, item_path):
        """
        Emby/Jellyfin点红星后转移电影文件到精选分类
        :param item_path: 文件路径
        """
        if not item_path:
            return False
        if not self.__movie_category_flag or not self.__movie_path:
            return False
        if os.path.isdir(item_path):
            movie_dir = item_path
        else:
            movie_dir = os.path.dirname(item_path)
        # 已经是精选下的不处理
        movie_type = os.path.basename(os.path.dirname(movie_dir))
        if movie_type == RMT_FAVTYPE \
                or movie_type not in self.category.get_movie_categorys():
            return False
        movie_name = os.path.basename(movie_dir)
        movie_path = self.__get_best_target_path(mtype=MediaType.MOVIE, in_path=movie_dir)
        # 开始转移文件，转移到同目录下的精选目录
        org_path = os.path.join(movie_path, movie_type, movie_name)
        new_path = os.path.join(movie_path, RMT_FAVTYPE, movie_name)
        if os.path.exists(org_path):
            log.info("【RMT】开始转移文件 %s 到 %s ..." % (org_path, new_path))
            if os.path.exists(new_path):
                log.info("【RMT】目录 %s 已存在" % new_path)
                return False
            ret = os.system("mv '%s' '%s'" % (org_path, new_path))
            if ret == 0:
                return True
        else:
            log.info("【RMT】%s 目录不存在" % org_path)
        return False

    def get_dest_path_by_info(self, dest, meta_info):
        """
        拼装转移重命名后的新文件地址
        :param dest: 目的目录
        :param meta_info: 媒体信息
        """
        if not dest or not meta_info:
            return None
        if meta_info.type == MediaType.MOVIE:
            dir_name, _ = self.get_moive_dest_path(meta_info)
            if self.__movie_category_flag:
                return os.path.join(dest, meta_info.category, dir_name)
            else:
                return os.path.join(dest, dir_name)
        else:
            dir_name, season_name, _ = self.get_tv_dest_path(meta_info)
            if self.__tv_category_flag:
                return os.path.join(dest, meta_info.category, dir_name, season_name)
            else:
                return os.path.join(dest, dir_name, season_name)

    def get_no_exists_medias(self, meta_info, season=None, total_num=None):
        """
        根据媒体库目录结构，判断媒体是否存在
        :param meta_info: 已识别的媒体信息
        :param season: 季号，数字，剧集时需要
        :param total_num: 该季总集数，剧集时需要
        :return: 如果是电影返回已存在的电影清单：title、year，如果是剧集，则返回不存在的集的清单
        """
        # 电影
        if meta_info.type == MediaType.MOVIE:
            dir_name, _ = self.get_moive_dest_path(meta_info)
            for dest_path in self.__movie_path:
                # 判断精选
                fav_path = os.path.join(dest_path, RMT_FAVTYPE, dir_name)
                fav_files = PathUtils.get_dir_files(fav_path, RMT_MEDIAEXT)
                # 其它分类
                if self.__movie_category_flag:
                    dest_path = os.path.join(dest_path, meta_info.category, dir_name)
                else:
                    dest_path = os.path.join(dest_path, dir_name)
                files = PathUtils.get_dir_files(dest_path, RMT_MEDIAEXT)
                if len(files) > 0 or len(fav_files) > 0:
                    return [{'title': meta_info.title, 'year': meta_info.year}]
            return []
        # 电视剧
        else:
            dir_name, season_name, _ = self.get_tv_dest_path(meta_info)
            if not season or not total_num:
                return []
            if meta_info.type == MediaType.ANIME:
                dest_paths = self.__anime_path
                category_flag = self.__anime_category_flag
            else:
                dest_paths = self.__tv_path
                category_flag = self.__tv_category_flag
            # 总需要的集
            total_episodes = [episode for episode in range(1, total_num + 1)]
            # 已存在的集
            exists_episodes = []
            for dest_path in dest_paths:
                if category_flag:
                    dest_path = os.path.join(dest_path, meta_info.category, dir_name, season_name)
                else:
                    dest_path = os.path.join(dest_path, dir_name, season_name)
                # 目录不存在
                if not os.path.exists(dest_path):
                    continue
                files = PathUtils.get_dir_files(dest_path, RMT_MEDIAEXT)
                for file in files:
                    file_meta_info = MetaInfo(os.path.basename(file))
                    if not file_meta_info.get_season_list() or not file_meta_info.get_episode_list():
                        continue
                    if file_meta_info.get_name() != meta_info.title:
                        continue
                    if not file_meta_info.is_in_season(season):
                        continue
                    exists_episodes = list(set(exists_episodes).union(set(file_meta_info.get_episode_list())))
            return list(set(total_episodes).difference(set(exists_episodes)))

    def __get_best_target_path(self, mtype, in_path=None, size=0):
        """
        查询一个最好的目录返回，有in_path时找与in_path同路径的，没有in_path时，顺序查找1个符合大小要求的，没有in_path和size时，返回第1个
        :param mtype: 媒体类型：电影、电视剧、动漫
        :param in_path: 源目录
        :param size: 文件大小
        """
        if not mtype:
            return None
        if mtype == MediaType.MOVIE:
            dest_paths = self.__movie_path
        elif mtype == MediaType.TV:
            dest_paths = self.__tv_path
        else:
            dest_paths = self.__anime_path
        if not dest_paths:
            return None
        if not isinstance(dest_paths, list):
            return dest_paths
        if isinstance(dest_paths, list) and len(dest_paths) == 1:
            return dest_paths[0]
        # 有输入路径的，匹配有共同上级路径的
        if in_path:
            # 先用自定义规则匹配 找同级目录最多的路径
            max_return_path = None
            max_path_len = 0
            for dest_path in dest_paths:
                try:
                    path_len = len(os.path.commonpath([in_path, dest_path]))
                    if path_len > max_path_len:
                        max_path_len = path_len
                        max_return_path = dest_path
                except Exception as err:
                    print(str(err))
                    continue
            if max_return_path:
                return max_return_path
        # 有输入大小的，匹配第1个满足空间存储要求的
        if size:
            for path in dest_paths:
                disk_free_size = SystemUtils.get_free_space_gb(path)
                if float(disk_free_size) > float(size / 1024 / 1024 / 1024):
                    return path
        # 默认返回第1个
        return dest_paths[0]

    def __get_best_unknown_path(self, in_path):
        """
        查找最合适的unknown目录
        :param in_path: 源目录
        """
        if not self.__unknown_path:
            return None
        for unknown_path in self.__unknown_path:
            if os.path.commonpath([in_path, unknown_path]) not in ["/", "\\"]:
                return unknown_path
        return self.__unknown_path[0]

    def link_sync_files(self, src_path, in_file, target_dir, sync_transfer_mode):
        """
        对文件做纯链接处理，不做识别重命名，则监控模块调用
        :param : 来源渠道
        :param src_path: 源目录
        :param in_file: 源文件
        :param target_dir: 目的目录
        :param sync_transfer_mode: 明确的转移方式
        """
        new_file = in_file.replace(src_path, target_dir)
        new_dir = os.path.dirname(new_file)
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)
        return self.__transfer_command(file_item=in_file,
                                       target_file=new_file,
                                       rmt_mode=sync_transfer_mode)

    @staticmethod
    def get_format_dict(media):
        """
        根据媒体信息，返回Format字典
        """
        if not media:
            return {}
        return {
            "title": StringUtils.clear_file_name(media.title),
            "en_title": StringUtils.clear_file_name(media.en_name),
            "original_name": StringUtils.clear_file_name(os.path.splitext(media.org_string)[0]),
            "original_title": StringUtils.clear_file_name(media.original_title),
            "year": media.year,
            "edition": media.resource_type,
            "videoFormat": media.resource_pix,
            "releaseGroup": media.resource_team,
            "videoCodec": media.video_encode,
            "audioCodec": media.audio_encode,
            "tmdbid": media.tmdb_id,
            "season": media.get_season_seq(),
            "episode": media.get_episode_seqs(),
            "season_episode": "%s%s" % (media.get_season_item(), media.get_episode_items()),
            "part": media.part
        }

    def get_moive_dest_path(self, media_info):
        """
        计算电影文件路径
        :return: 电影目录、电影名称
        """
        format_dict = self.get_format_dict(media_info)
        dir_name = re.sub(r"[-_\s.]*None", "", self.__movie_dir_rmt_format.format(**format_dict))
        file_name = re.sub(r"[-_\s.]*None", "", self.__movie_file_rmt_format.format(**format_dict))
        return dir_name, file_name

    def get_tv_dest_path(self, media_info):
        """
        计算电视剧文件路径
        :return: 电视剧目录、季目录、集名称
        """
        format_dict = self.get_format_dict(media_info)
        dir_name = re.sub(r"[-_\s.]*None", "", self.__tv_dir_rmt_format.format(**format_dict))
        season_name = re.sub(r"[-_\s.]*None", "", self.__tv_season_rmt_format.format(**format_dict))
        file_name = re.sub(r"[-_\s.]*None", "", self.__tv_file_rmt_format.format(**format_dict))
        return dir_name, season_name, file_name


if __name__ == "__main__":
    """
    手工转移时，使用命名行调用
    """
    parser = argparse.ArgumentParser(description='文件转移工具')
    parser.add_argument('-m', '--mode', dest='mode', required=True,
                        help='转移模式：link copy softlink move rclone rclonecopy')
    parser.add_argument('-s', '--source', dest='s_path', required=True, help='硬链接源目录路径')
    parser.add_argument('-d', '--target', dest='t_path', required=False, help='硬链接目的目录路径')
    args = parser.parse_args()
    if os.environ.get('NASTOOL_CONFIG'):
        print("【RMT】配置文件地址：%s" % os.environ.get('NASTOOL_CONFIG'))
        print("【RMT】源目录路径：%s" % args.s_path)
        if args.t_path:
            print("【RMT】目的目录路径：%s" % args.t_path)
        else:
            print("【RMT】目的目录为配置文件中的电影、电视剧媒体库目录")
        FileTransfer().transfer_manually(args.s_path, args.t_path, args.mode)
    else:
        print("【RMT】未设置环境变量，请先设置 NASTOOL_CONFIG 环境变量为配置文件地址")
