import argparse
import os
import re
import shutil

import requests
from requests import RequestException

import log
from tmdbv3api import TMDb, Search, Movie
from subprocess import call

from config import RMT_SUBEXT, get_config, RMT_MEDIAEXT, RMT_DISKFREESIZE, RMT_COUNTRY_EA, RMT_COUNTRY_AS, \
    RMT_MOVIETYPE, FANART_API_URL
from functions import get_dir_files_by_ext, is_chinese, str_filesize, get_free_space_gb
from message.send import Message


class Media:
    # TheMovieDB
    tmdb = None
    __app_config = None
    __media_config = None
    __pt_config = None
    __sync_config = None
    __pt_rmt_mode = None
    __sync_rmt_mode = None
    message = None

    def __init__(self):
        self.message = Message()

        self.tmdb = TMDb()
        config = get_config()
        self.__app_config = config.get('app', {})
        self.__media_config = config.get('media', {})
        self.__pt_config = config.get('pt', {})
        self.__sync_config = config.get('sync', {})

        self.__rmt_tmdbkey = self.__app_config.get('rmt_tmdbkey')
        self.tmdb.api_key = self.__rmt_tmdbkey
        self.tmdb.language = 'zh'
        self.tmdb.debug = True

        self.__pt_rmt_mode = self.__pt_config.get('rmt_mode', 'COPY').upper()
        self.__sync_rmt_mode = self.__sync_config.get('sync_mod', 'COPY').upper()

    # 根据文件名转移对应字幕文件
    @staticmethod
    def __transfer_subtitles(org_name, new_name, rmt_mode="COPY"):
        dir_name = os.path.dirname(org_name)
        file_list = get_dir_files_by_ext(dir_name, RMT_SUBEXT)
        Media_FileNum = len(file_list)
        if Media_FileNum == 0:
            log.debug("【RMT】%s 目录下没有找到字幕文件..." % dir_name)
        else:
            log.debug("【RMT】字幕文件清单：" + str(file_list))
            find_flag = False
            for file_item in file_list:
                org_subname = os.path.splitext(org_name)[0]
                if org_subname in file_item:
                    find_flag = True
                    file_ext = os.path.splitext(file_item)[-1]
                    if file_item.find(".zh-cn" + file_ext) != -1:
                        new_file = os.path.splitext(new_name)[0] + ".zh-cn" + file_ext
                    else:
                        new_file = os.path.splitext(new_name)[0] + file_ext
                    if not os.path.exists(new_file):
                        log.debug("【RMT】正在处理字幕：%s" % file_item)
                        if rmt_mode == "LINK":
                            rmt_mod_str = "硬链接"
                            retcode = call(["ln", file_item, new_file])
                        else:
                            rmt_mod_str = "复制"
                            retcode = call(["cp", file_item, new_file])
                        if retcode == 0:
                            log.info("【RMT】字幕%s完成：%s" % (rmt_mod_str, new_file))
                        else:
                            log.error("【RMT】字幕%s失败，错误码：%s" % (rmt_mod_str, str(retcode)))
                    else:
                        log.info("【RMT】字幕 %s 已存在！" % new_file)
            if not find_flag:
                log.debug("【RMT】没有相同文件名的字幕文件，不处理！")
        return True

    # 转移蓝光文件夹
    '''
    mv_flag：是否为移动，否则为复制
    over_falg：是否覆盖
    '''

    def __transfer_bluray_dir(self, file_path, new_path, mv_flag=False, over_flag=False):
        # 检查是不是正在处理目标文件
        curr_transfile = os.environ.get('NASTOOL_CURR_TRANS_FILE')
        if curr_transfile:
            if curr_transfile.find(new_path) > 0:
                log.error("【RMT】另一个进程正在处理此目录，本次操作取消：%s" % new_path)
                return False
            else:
                os.environ['NASTOOL_CURR_TRANS_FILE'] = os.environ['NASTOOL_CURR_TRANS_FILE'] + new_path
        else:
            os.environ['NASTOOL_CURR_TRANS_FILE'] = new_path

        if over_flag:
            log.warn("【RMT】正在删除已存在的目录：%s" % new_path)
            shutil.rmtree(new_path)
            log.warn("【RMT】%s 已删除！" % new_path)
        else:
            if os.path.exists(new_path):
                log.warn("【RMT】目录已存在：%s" % new_path)
                return False

        # 复制文件
        log.info("【RMT】正在复制目录：%s 到 %s" % (file_path, new_path))
        retcode = call(['cp', '-r', file_path, new_path])

        # 清空记录
        os.environ['NASTOOL_CURR_TRANS_FILE'] = os.environ['NASTOOL_CURR_TRANS_FILE'].replace(new_path, "")

        if retcode == 0:
            log.info("【RMT】文件复制完成：%s" % new_path)
        else:
            log.error("【RMT】文件复制失败，错误码：%s" % str(retcode))
            return False

        if mv_flag:
            if file_path != self.__media_config.get('movie_path') and file_path != self.__media_config.get('tv_path'):
                shutil.rmtree(file_path)
            log.info("【RMT】%s 已删除！" % file_path)
        return True

    # 按原文件名link文件到目的目录
    def __link_origin_file(self, file_item, target_dir, search_type):
        if os.path.isdir(file_item):
            log.warn("【RMT】目录不支持硬链接处理！")
            return False

        if not target_dir:
            if search_type == "电影":
                target_dir = self.__media_config.get('movie_path')
            elif search_type == "电视剧":
                target_dir = self.__media_config.get('tv_path')
            else:
                log.error("【RMT】媒体分类有误，无法确定目录文件夹！")
                return False
        # 文件名
        file_name = os.path.basename(file_item)
        # 取上一级目录
        parent_dir = os.path.basename(os.path.dirname(file_item))
        # 转移到nastool_failed目录
        target_dir = os.path.join(target_dir, 'nastool_failed', parent_dir)
        if not os.path.exists(target_dir):
            log.debug("【RMT】正在创建目录：%s" % target_dir)
            os.makedirs(target_dir)
        target_file = os.path.join(target_dir, file_name)
        retcode = call(['ln', file_item, target_file])
        if retcode == 0:
            log.info("【RMT】文件硬链接完成：%s" % target_file)
        else:
            log.error("【RMT】文件硬链接失败，错误码：%s" % retcode)
            return False
        return True

    # 复制或者硬链接一个文件
    def __transfer_file(self, file_item, new_file, over_flag=False, rmt_mode="COPY"):
        # 检查是不是正在处理目标文件
        if rmt_mode == "COPY":
            curr_transfile = os.environ.get('NASTOOL_CURR_TRANS_FILE')
            if curr_transfile:
                if curr_transfile.find(new_file) > 0:
                    log.error("【RMT】另一个进程正在处理此文件，本次操作取消：%s" % new_file)
                    return False
                else:
                    os.environ['NASTOOL_CURR_TRANS_FILE'] = os.environ['NASTOOL_CURR_TRANS_FILE'] + new_file
            else:
                os.environ['NASTOOL_CURR_TRANS_FILE'] = new_file

        if over_flag and os.path.exists(new_file):
            if os.path.isfile(new_file):
                log.info("【RMT】正在删除已存在的文件：%s" % new_file)
                os.remove(new_file)
                log.warn("【RMT】%s 已删除！" % new_file)
        else:
            if os.path.exists(new_file):
                log.warn("【RMT】文件已存在：%s" % new_file)
                return False

        # 复制文件
        log.info("【RMT】正在转移文件：%s 到 %s" % (file_item, new_file))
        if rmt_mode == "LINK":
            rmt_mod_str = "硬链接"
            retcode = call(['ln', file_item, new_file])
        else:
            rmt_mod_str = "复制"
            retcode = call(['cp', file_item, new_file])

        if rmt_mode == "COPY":
            # 清除当前文件记录
            os.environ['NASTOOL_CURR_TRANS_FILE'] = os.environ['NASTOOL_CURR_TRANS_FILE'].replace(new_file, "")

        if retcode == 0:
            log.info("【RMT】文件%s完成：%s" % (rmt_mod_str, new_file))
        else:
            log.error("【RMT】文件%s失败，错误码：%s" % (rmt_mod_str, str(retcode)))
            return False

        # 处理字幕
        return self.__transfer_subtitles(file_item, new_file, rmt_mode)

    # 转移识别媒体文件
    '''
    in_from：来源
    in_path：路径，可有是个目录也可能是一个文件
    target_dir：指定目的目录，否则按电影、电视剧目录
    '''

    def transfer_media(self,
                       in_from,
                       in_path,
                       target_dir=None):
        if not in_path:
            log.error("【RMT】输入参数错误!")
            return False

        # 进到这里来的，可能是一个大目录，目录中有电影也有电视剧；也有可能是一个电视剧目录或者一个电影目录；也有可能是一个文件

        if in_from in ['qBittorrent', 'transmission']:
            rmt_mode = self.__pt_rmt_mode
        else:
            rmt_mode = self.__sync_rmt_mode

        # 遍历文件
        in_path = in_path.replace('\\\\', '/').replace('\\', '/')
        log.info("【RMT】开始处理：%s" % in_path)

        if target_dir:
            # 有输入target_dir时，往这个目录放
            movie_dist = target_dir
        else:
            movie_dist = self.__media_config.get('movie_path')

        # 是否开始自动分类
        movie_subtypedir = self.__media_config.get('movie_subtypedir', True)

        bluray_disk_flag = False
        if os.path.isdir(in_path):
            # 如果传入的是个目录
            if not os.path.exists(in_path):
                log.error("【RMT】目录不存在：%s" % in_path)
                return False

            # 判断是不是原盘文件夹
            if os.path.exists(os.path.join(in_path, "BDMV/index.bdmv")):
                bluray_disk_flag = True

            # 处理蓝光原盘
            if bluray_disk_flag:
                if rmt_mode == "LINK":
                    log.warn("【RMT】硬链接下不支持蓝光原盘目录，不处理...")
                    return False
            # 开始处理里面的文件
            if bluray_disk_flag:
                file_list = [in_path]
                log.info("【RMT】当前为蓝光原盘文件夹：%s" % str(in_path))
            else:
                file_list = get_dir_files_by_ext(in_path, RMT_MEDIAEXT)
                Media_FileNum = len(file_list)
                log.debug("【RMT】文件清单：" + str(file_list))
                if Media_FileNum == 0:
                    log.warn("【RMT】目录下未找到媒体文件：%s" % in_path)
                    return False
        else:
            # 如果传入的是个文件
            if not os.path.exists(in_path):
                log.error("【RMT】文件不存在：%s" % in_path)
                return False
            ext = os.path.splitext(in_path)[-1]
            if ext not in RMT_MEDIAEXT:
                log.warn("【RMT】不支持的媒体文件格式，不处理：%s" % in_path)
                return False
            file_list = [in_path]

        # API检索出媒体信息，传入一个文件列表，得出每一个文件的名称，这里是当前目录下所有的文件了
        Medias = self.get_media_info(file_list)
        if not Medias:
            log.error("【RMT】检索媒体信息出错！")
            return False

        # 统计总的文件数、失败文件数
        failed_count = 0
        total_count = 0
        # 如果是电影，因为只会有一个文件，直接在循环里就发了消息
        # 但是电视剧可能有多集，如果在循环里发消息就太多了，要在外面发消息
        # 如果这个目录很复杂，有多集或者多部电影电视剧，则电视剧也要在外面统一发消息
        # title: {year, media_filesize, season_ary[], episode_ary}
        finished_tv_medias = {}

        for file_item, media in Medias.items():
            total_count = total_count + 1
            # 记录目录下是不是有多种类型，来决定怎么发通知
            Search_Type = media["search_type"]
            Media_Id = media["id"]

            if Media_Id != "0":

                Media_Title = media["title"]
                Media_Type = media["type"]
                Media_Year = media["year"]
                if Media_Year:
                    Title_Str = "%s (%s)" % (Media_Title, Media_Year)
                else:
                    Title_Str = Media_Title

                Media_Pix = media['media_pix']
                Vote_Average = ""
                Backdrop_Path = self.get_backdrop_image(media["backdrop_path"], Media_Id)

                if media.get("vote_average"):
                    Vote_Average = media['vote_average']

                if Search_Type == "电影":
                    # 是否新电影标志
                    new_movie_flag = False
                    exist_filenum = 0
                    # 检查剩余空间
                    disk_free_size = get_free_space_gb(movie_dist)
                    if float(disk_free_size) < RMT_DISKFREESIZE:
                        log.error("【RMT】目录 %s 剩余磁盘空间不足 %s GB，不处理！" % (movie_dist, RMT_DISKFREESIZE))
                        self.message.sendmsg("【RMT】磁盘空间不足", "目录 %s 剩余磁盘空间不足 %s GB！" % (movie_dist, RMT_DISKFREESIZE))
                        return False
                    media_path = os.path.join(movie_dist, Title_Str)
                    if movie_subtypedir:
                        # 启用了电影分类
                        exist_dir_flag = False
                        # 在所有分类下查找是否有当前目录了
                        for mtype in RMT_MOVIETYPE:
                            media_path = os.path.join(movie_dist, mtype, Title_Str)
                            if os.path.exists(media_path):
                                # 该电影已在分类目录中存在
                                exist_dir_flag = True
                                break
                        if not exist_dir_flag:
                            # 分类目录中未找到，则按媒体类型拼装新路径
                            media_path = os.path.join(movie_dist, Media_Type, Title_Str)

                    # 新路径是否存在
                    if not os.path.exists(media_path):
                        if bluray_disk_flag:
                            # 转移蓝光原盘
                            ret = self.__transfer_bluray_dir(file_item, media_path)
                            if ret:
                                log.info("【RMT】蓝光原盘 %s 转移成功！" % file_item)
                            else:
                                log.error("【RMT】蓝光原盘 %s 转移失败！" % file_item)
                            continue
                        else:
                            # 创建电影目录
                            log.debug("【RMT】正在创建目录：%s" % media_path)
                            os.makedirs(media_path)
                    else:
                        # 新路径存在
                        if bluray_disk_flag:
                            log.warn("【RMT】蓝光原盘目录已存在：%s" % media_path)
                            continue

                    # 开始判断和转移具体文件
                    media_filesize = os.path.getsize(file_item)
                    file_ext = os.path.splitext(file_item)[-1]
                    if Media_Pix != "":
                        if Media_Pix.upper() == "4K":
                            Media_Pix = "2160p"
                        new_file = os.path.join(media_path, Title_Str + " - " + Media_Pix.lower() + file_ext)
                    else:
                        new_file = os.path.join(media_path, Title_Str + file_ext)
                    if not os.path.exists(new_file):
                        ret = self.__transfer_file(file_item, new_file, False, rmt_mode)
                        if not ret:
                            continue
                        new_movie_flag = True
                    else:
                        exist_filenum = 1
                        if rmt_mode != "LINK":
                            existfile_size = os.path.getsize(new_file)
                            if media_filesize > existfile_size:
                                log.info("【RMT】文件 %s 已存在，但新文件质量更好，覆盖..." % new_file)
                                ret = self.__transfer_file(file_item, new_file, True, rmt_mode)
                                if not ret:
                                    continue
                                new_movie_flag = True
                            else:
                                log.warn("【RMT】文件 %s 已存在，且质量更好！" % new_file)
                        else:
                            log.warn("【RMT】文件 %s 已存在！" % new_file)

                    # 电影的话，处理一部马上开始发送消息
                    if not new_movie_flag:
                        continue
                    msg_title = Title_Str
                    if Vote_Average and Vote_Average != '0':
                        msg_title = Title_Str + " 评分：%s" % str(Vote_Average)
                    msg_str = "电影 %s 转移完成，大小：%s，来自：%s" \
                              % (Title_Str, str_filesize(media_filesize), in_from)
                    if exist_filenum != 0:
                        msg_str = msg_str + "，覆盖了 %s 个文件" % str(exist_filenum)
                    self.message.sendmsg(msg_title, msg_str, Backdrop_Path)
                    log.info("【RMT】%s 转移完成！" % Media_Title)

                elif Search_Type == "电视剧":
                    # 记录下来
                    if not finished_tv_medias.get(Title_Str):
                        finished_tv_medias[Title_Str] = {"Vote_Average": 0,
                                                         "Backdrop_Path": "",
                                                         "Season_Ary": [],
                                                         "Episode_Ary": [],
                                                         "Total_Size": 0,
                                                         "Exist_Files": 0}
                    # 评分
                    finished_tv_medias[Title_Str]['Vote_Average'] = Vote_Average
                    # 背景图
                    finished_tv_medias[Title_Str]['Backdrop_Path'] = Backdrop_Path

                    if bluray_disk_flag:
                        log.error("【RMT】识别有误：蓝光原盘目录被识别为电视剧！")
                        continue
                    # 检查剩余空间
                    if target_dir:
                        # 有输入target_dir时，往这个目录放
                        tv_dist = target_dir
                    else:
                        tv_dist = self.__media_config.get('tv_path')

                    disk_free_size = get_free_space_gb(tv_dist)
                    if float(disk_free_size) < RMT_DISKFREESIZE:
                        log.error("【RMT】目录 %s 剩余磁盘空间不足 %s GB，不处理！" % (tv_dist, RMT_DISKFREESIZE))
                        self.message.sendmsg("【RMT】磁盘空间不足", "目录 %s 剩余磁盘空间不足 %s GB，不处理！" % (tv_dist, RMT_DISKFREESIZE))
                        return False

                    # 新路径
                    media_path = os.path.join(tv_dist, Title_Str)
                    # 未配置时默认进行分类
                    tv_subtypedir = self.__media_config.get('tv_subtypedir', True)
                    if tv_subtypedir:
                        media_path = os.path.join(tv_dist, Media_Type, Title_Str)

                    # 创建目录
                    if not os.path.exists(media_path):
                        log.debug("【RMT】正在创建目录：%s" % media_path)
                        os.makedirs(media_path)

                    media_filesize = os.path.getsize(file_item)
                    finished_tv_medias[Title_Str]['Total_Size'] = finished_tv_medias[Title_Str][
                                                                      'Total_Size'] + media_filesize

                    file_ext = os.path.splitext(file_item)[-1]
                    file_name = os.path.basename(file_item)
                    # Sxx
                    file_season = self.get_media_file_season(file_name)
                    # Exx
                    file_seq = self.get_media_file_seq(file_name)
                    # 季 Season xx
                    season_str = "Season %s" % str(int(file_season.replace("S", ""))).strip()
                    season_dir = os.path.join(media_path, season_str)
                    # 集 xx
                    file_seq_num = str(int(file_seq.replace("E", "").replace("P", ""))).strip()
                    # 记录转移季数跟集数情况
                    season_seq_str = season_str.replace("Season", "").strip()
                    if season_seq_str not in finished_tv_medias[Title_Str].get('Season_Ary'):
                        finished_tv_medias[Title_Str]['Season_Ary'].append(season_seq_str)
                    file_seq_num_str = '%s-%s' % (season_seq_str, file_seq_num)
                    if file_seq_num_str not in finished_tv_medias[Title_Str].get('Episode_Ary'):
                        finished_tv_medias[Title_Str]['Episode_Ary'].append(file_seq_num_str)
                    # 创建目录
                    if not os.path.exists(season_dir):
                        log.debug("【RMT】正在创建剧集目录：%s" % season_dir)
                        os.makedirs(season_dir)
                    # 处理文件
                    new_file = os.path.join(season_dir,
                                            Media_Title + " - " + file_season + file_seq + " - " + "第 "
                                            + file_seq_num + " 集" + file_ext)
                    if not os.path.exists(new_file):
                        ret = self.__transfer_file(file_item, new_file, False, rmt_mode)
                        if not ret:
                            continue
                    else:
                        existfile_size = os.path.getsize(new_file)
                        if rmt_mode != "LINK":
                            if media_filesize > existfile_size:
                                log.info("【RMT】文件 %s 已存在，但新文件质量更好，覆盖..." % new_file)
                                ret = self.__transfer_file(file_item, new_file, True, rmt_mode)
                                if not ret:
                                    continue
                            else:
                                finished_tv_medias[Title_Str]['Exist_Files'] = finished_tv_medias[Title_Str][
                                                                                   'Exist_Files'] + 1
                                log.warn("【RMT】文件 %s 已存在！" % new_file)
                                continue
                        else:
                            log.warn("【RMT】文件 %s 已存在！" % new_file)
                            continue
                else:
                    log.error("【RMT】%s 无法识别是什么类型的媒体文件！" % file_item)
                    failed_count = failed_count + 1
                    continue
            else:
                log.error("【RMT】%s 媒体信息识别失败！" % file_item)
                failed_count = failed_count + 1
                # 如果是LINK模式，则原样链接过去 这里可能日目录也可能是文件
                if rmt_mode == "LINK":
                    log.warn("【RMT】按原文件名进行硬链接...")
                    self.__link_origin_file(file_item, target_dir, Search_Type)
                continue

        # 统计完成情况
        for title_str, item_info in finished_tv_medias.items():
            if len(item_info['Episode_Ary']) == 1:
                # 只有一集
                msg_str = "电视剧 %s 第%s季第%s集 转移完成，大小：%s，来自：%s" \
                          % (title_str,
                             item_info.get('Season_Ary')[0],
                             item_info.get('Episode_Ary')[0].split('-')[-1],
                             str_filesize(item_info.get('Total_Size')),
                             in_from)
            else:
                item_info.get('Season_Ary').sort()
                item_info.get('Episode_Ary').sort(key=int)
                msg_str = "电视剧 %s 转移完成，共 %s 季 %s 集，总大小：%s，来自：%s" % \
                          (title_str,
                           len(item_info.get('Season_Ary')),
                           len(item_info.get('Episode_Ary')),
                           str_filesize(item_info.get('Total_Size')),
                           in_from)
            if item_info.get('Exist_Files') != 0:
                msg_str = msg_str + "，覆盖了 %s 个文件" % str(item_info.get('Exist_Files'))

            msg_title = title_str
            if item_info.get('Vote_Average'):
                msg_title = title_str + " 评分：%s" % str(item_info.get('Vote_Average'))
            self.message.sendmsg(msg_title, msg_str, item_info.get('Backdrop_Path'))

        # 总结
        log.info("【RMT】%s 处理完成，总数：%s，失败：%s！" % (in_path, total_count, failed_count))
        return True

    @staticmethod
    def is_media_files_tv(file_list):
        flag = False
        # 不是list的转为list，避免发生字符级的拆分
        if not isinstance(file_list, list):
            file_list = [file_list]
        for tmp_file in file_list:
            tmp_name = os.path.basename(tmp_file)
            re_res = re.search(r"[\s.]*[SE]P?\d{1,3}", tmp_name, re.IGNORECASE)
            if re_res:
                flag = True
                break
        return flag

    # 获得媒体名称，用于API检索
    @staticmethod
    def __get_pt_media_name(in_name):
        if not in_name:
            return ""
        # 如果有后缀则去掉，避免干扰
        tmp_ext = os.path.splitext(in_name)[-1]
        if tmp_ext in RMT_MEDIAEXT:
            out_name = os.path.splitext(in_name)[0]
        else:
            out_name = in_name
        # 干掉一些固定的前缀 JADE AOD XXTV-X
        out_name = re.sub(r'^JADE[\s.]+|^AOD[\s.]+|^[A-Z]{2,4}TV[\-0-9UVHD]*[\s.]+', '', out_name,
                          flags=re.IGNORECASE).strip()
        # 查找关键字并切分
        num_pos1 = num_pos2 = len(out_name)
        # 查找年份/分辨率的位置
        re_res1 = re.search(r"[\s.]+\d{3,4}[PI]?[\s.]+|[\s.]+\d+K[\s.]+", out_name, re.IGNORECASE)
        if not re_res1:
            # 查询BluRay/REMUX/HDTV/WEB-DL/WEBRip/DVDRip/UHD的位置
            if not re_res1:
                re_res1 = re.search(
                    r"[\s.]+BLU-?RAY[\s.]+|[\s.]+REMUX[\s.]+|[\s.]+HDTV[\s.]+|[\s.]+WEB-DL[\s.]+|[\s.]+WEBRIP[\s.]+|[\s.]+DVDRIP[\s.]+|[\s.]+UHD[\s.]+",
                    out_name, re.IGNORECASE)
        if re_res1:
            num_pos1 = re_res1.span()[0]
        # 查找Sxx或Exx的位置
        re_res2 = re.search(r"[\s.]+[SE]P?\d{1,4}", out_name, re.IGNORECASE)
        if re_res2:
            num_pos2 = re_res2.span()[0]
        # 取三者最小
        num_pos = min(num_pos1, num_pos2, len(out_name))
        # 截取Year或Sxx或Exx前面的字符
        out_name = out_name[0:num_pos]
        # 如果带有Sxx-Sxx、Exx-Exx这类的要处理掉
        out_name = re.sub(r'[SsEePp]+\d{1,2}-?[SsEePp]*\d{0,2}', '', out_name).strip()
        if is_chinese(out_name):
            # 有中文的，把中文外的英文、字符、数字等全部去掉
            out_name = re.sub(r'[0-9a-zA-Z【】\-_.\[\]()\s]+', '', out_name).strip()
        else:
            # 不包括中文，则是英文名称
            out_name = out_name.replace(".", " ")
        return out_name

    # 获得媒体文件的集数S00
    @staticmethod
    def get_media_file_season(in_name):
        if in_name:
            # 查找Sxx
            re_res = re.search(r"[\s.]*(S\d{1,2})", in_name, re.IGNORECASE)
            if re_res:
                return re_res.group(1).upper()
        return "S01"

    # 获得媒体文件的集数E00
    @staticmethod
    def get_media_file_seq(in_name):
        ret_str = ""
        if in_name:
            # 查找Sxx
            re_res = re.search(r"[\s.]*S?\d*(EP?\d{1,4})[\s.]*", in_name, re.IGNORECASE)
            if re_res:
                ret_str = re_res.group(1).upper()
            else:
                # 可能数字就是全名，或者是第xx集
                ret_str = ""
                num_pos = in_name.find(".")
                if num_pos != -1:
                    split_char = "."
                else:
                    split_char = " "
                split_ary = in_name.split(split_char)
                for split_str in split_ary:
                    split_str = split_str.replace("第", "").replace("集", "").strip()
                    if split_str.isdigit() and (0 < int(split_str) < 1000):
                        ret_str = "E" + split_str
                        break
            if not ret_str:
                ret_str = ""
        return ret_str

    # 获得媒体文件的分辨率
    @staticmethod
    def __get_media_file_pix(in_name):
        if in_name:
            # 查找Sxx
            re_res = re.search(r"[\s.]+[SUHD]*(\d{3,4}[PI]+)[\s.]+", in_name, re.IGNORECASE)
            if re_res:
                return re_res.group(1).upper()
            else:
                re_res = re.search(r"[\s.]+(\d+K)[\s.]+", in_name, re.IGNORECASE)
                if re_res:
                    return re_res.group(1).upper()
        return ""

    # 获得媒体文件的Year
    @staticmethod
    def __get_media_file_year(in_name):
        if in_name:
            # 查找Sxx
            re_res = re.search(r"[\s.(]+(\d{4})[\s.)]+", in_name, re.IGNORECASE)
            if re_res:
                return re_res.group(1).upper()
        return ""

    # 检索tmdb中的媒体信息，传入名字、年份、类型
    # 返回媒体信息对象
    def __search_tmdb(self, file_media_name, media_year, search_type, language=None):
        if not file_media_name:
            log.error("【RMT】检索关键字有误！")
            return None
        if language:
            self.tmdb.language = language
        else:
            self.tmdb.language = 'zh'
        info = {}
        media_id = "0"
        media_type = ""
        media_title = ""
        backdrop_path = ""
        vote_average = ""

        if search_type == "电影":
            search = Search()
            log.info("【RMT】正在检索电影：%s, 年份=%s ..." % (file_media_name, media_year))
            if media_year:
                movies = search.movies({"query": file_media_name, "year": media_year})
            else:
                movies = search.movies({"query": file_media_name})
            log.debug("【RMT】API返回：%s" % str(search.total_results))
            if len(movies) == 0:
                log.warn("【RMT】%s 未找到媒体信息!" % file_media_name)
            else:
                info = movies[0]
                for movie in movies:
                    if movie.title == file_media_name or movie.release_date[0:4] == media_year:
                        # 优先使用名称或者年份完全匹配的，匹配不到则取第一个
                        info = movie
                        break
                media_id = info.id
                media_title = info.title
                log.info(">电影ID：%s, 上映日期：%s, 电影名称：%s" % (str(info.id), info.release_date, info.title))
                media_year = info.release_date[0:4]
                backdrop_path = info.backdrop_path
                vote_average = str(info.vote_average)
                # 国家
                media_language = info.original_language
                if 'zh' in media_language or \
                        'bo' in media_language or \
                        'za' in media_language or \
                        'cn' in media_language:
                    media_type = "华语电影"
                else:
                    media_type = "外语电影"
        else:
            search = Search()
            log.info("【RMT】正在检索剧集：%s, 年份=%s ..." % (file_media_name, media_year))
            if media_year:
                tvs = search.tv_shows({"query": file_media_name, "year": media_year})
            else:
                tvs = search.tv_shows({"query": file_media_name})
            log.debug("【RMT】API返回：%s" % str(search.total_results))
            if len(tvs) == 0:
                log.warn("【RMT】%s 未找到媒体信息!" % file_media_name)
                info = {}
            else:
                info = tvs[0]
                for tv in tvs:
                    if tv.get('first_air_date'):
                        if tv.name == file_media_name and tv.first_air_date[0:4] == media_year:
                            # 优先使用名称或者年份完全匹配的，匹配不到则取第一个
                            info = tv
                            break
                    elif tv.name == file_media_name:
                        info = tv
                        break

                media_id = info.id
                media_title = info.name
                log.info(">剧集ID：%s, 剧集名称：%s, 上映日期：%s" % (str(info.id), info.name, info.get('first_air_date')))
                if info.get('first_air_date'):
                    media_year = info.first_air_date[0:4]
                backdrop_path = info.backdrop_path
                vote_average = str(info.vote_average)

                # 类型 动漫、纪录片、儿童、综艺
                media_genre_ids = info.genre_ids
                if 16 in media_genre_ids:
                    # 动漫
                    media_type = "动漫"
                elif 99 in media_genre_ids:
                    # 纪录片
                    media_type = "纪录片"
                elif 10762 in media_genre_ids:
                    # 儿童
                    media_type = "儿童"
                elif 10764 in media_genre_ids or 10767 in media_genre_ids:
                    # 综艺
                    media_type = "综艺"
                else:
                    # 国家
                    media_country = info.origin_country
                    if 'CN' in media_country or 'TW' in media_country:
                        media_type = "国产剧"
                    elif set(RMT_COUNTRY_EA).intersection(set(media_country)):
                        media_type = "欧美剧"
                    elif set(RMT_COUNTRY_AS).intersection(set(media_country)):
                        media_type = "日韩剧"
                    else:
                        media_type = "其它剧"
        return {"name": file_media_name,
                "search_type": search_type,
                "type": media_type,
                "id": str(media_id),
                "title": media_title,
                "year": str(media_year),
                "info": info,
                "backdrop_path": backdrop_path,
                "vote_average": vote_average}

    # 只有个名称和类型，用于RSS类的搜刮毁体信息
    def get_media_info_on_name(self, in_name, in_type):
        media_name = self.__get_pt_media_name(in_name)
        media_year = self.__get_media_file_year(in_name)
        # 调用TMDB API
        file_media_info = self.__search_tmdb(media_name, media_year, in_type)
        if file_media_info:
            # 分辨率
            media_pix = self.__get_media_file_pix(in_name)
            file_media_info['media_pix'] = media_pix

        return file_media_info

    # 搜刮媒体信息和类型，返回每个文件对应的媒体信息
    '''
    输入：file_list：文件路径清单, 可能是一个目录，也可能是一个文件清单
    输出：类型，文件路径：媒体信息的List
    '''

    def get_media_info(self, file_list):
        # 存储文件路径与媒体的对应关系
        return_media_infos = {}

        # 不是list的转为list
        if not isinstance(file_list, list):
            file_list = [file_list]

        # 存储所有识别的名称与媒体信息的对应关系
        media_names = {}

        # 遍历每个文件，看得出来的名称是不是不一样，不一样的先搜索媒体信息
        for file_path in file_list:
            if not os.path.exists(file_path):
                log.error("【RMT】%s 不存在！" % file_path)
                continue
            # 解析媒体名称
            file_name = os.path.basename(file_path)
            file_media_name = self.__get_pt_media_name(file_name)
            # 优先使用文件的名称，没有就拿上级的
            if not file_media_name:
                tmp_path = os.path.basename(os.path.dirname(file_path))
                file_media_name = self.__get_pt_media_name(tmp_path)
                if not file_media_name:
                    # 最多找两级
                    tmp_path = os.path.basename(os.path.dirname(file_path))
                    file_media_name = self.__get_pt_media_name(tmp_path)
            if not file_media_name:
                log.warn("【RMT】文件 %s 无法识别到标题！" % file_path)
                continue

            # 确定是电影还是电视剧
            search_type = "电影"
            if self.is_media_files_tv(file_path):
                search_type = "电视剧"

            # 是否处理过
            if not media_names.get(file_media_name):

                media_year = self.__get_media_file_year(file_name)
                if not media_year:
                    # 没有文件的则使用目录里的
                    media_year = self.__get_media_file_year(file_path)
                if media_year:
                    log.debug("【RMT】识别年份为：%s" % str(media_year))
                else:
                    log.debug("【RMT】未识别出年份！")

                # 解析分辨率
                media_pix = self.__get_media_file_pix(file_name)
                if not media_pix:
                    media_pix = self.__get_media_file_year(file_path)
                if media_pix:
                    log.debug("【RMT】识别分辨率为：%s" % str(media_pix))
                else:
                    log.debug("【RMT】未识别分辨率！")

                # 调用TMDB API
                file_media_info = self.__search_tmdb(file_media_name, media_year, search_type)
                if file_media_info:
                    file_media_info['media_pix'] = media_pix
                    # 记录为已检索
                    media_names[file_media_name] = file_media_info
            if not media_names.get(file_media_name):
                media_names[file_media_name] = {'id': '0', 'search_type': search_type}
            # 存入结果清单返回
            return_media_infos[file_path] = media_names.get(file_media_name)

        return return_media_infos

    # 查询电影TMDB详细信息
    def get_moive_metainfo(self, movie_id, language=None):
        if language:
            self.tmdb.language = language
        else:
            self.tmdb.language = 'zh'
        movie = Movie()
        return movie.videos(movie_id)

    # 查询电影TMDB详细信息
    def get_moive_now_playing(self, page, language=None):
        if language:
            self.tmdb.language = language
        else:
            self.tmdb.language = 'zh'
        movie = Movie()
        return movie.now_playing(page)

    # 查询电影TMDB详细信息
    def get_moive_upcoming(self, page, language=None):
        if language:
            self.tmdb.language = language
        else:
            self.tmdb.language = 'zh'
        movie = Movie()
        return movie.upcoming(page)

    # 检查标题中是否匹配资源类型
    # 返回：是否匹配，匹配的序号，匹配的值
    @staticmethod
    def check_resouce_types(t_title, t_types):
        if t_types is None:
            return False, 99, ""
        c_seq = 0
        for t_type in t_types:
            c_seq = c_seq + 1
            t_type = str(t_type)
            if t_type.upper() == "BLURAY":
                match_str = r'blu-?ray'
            elif t_type.upper() == "4K":
                match_str = r'4k|2160p'
            else:
                match_str = t_type
            re_res = re.search(match_str, t_title, re.IGNORECASE)
            if re_res:
                # 命中
                return True, c_seq, t_type

        return False, 99, ""

    # 获取消息媒体图片
    @staticmethod
    def get_backdrop_image(backdrop_path, tmdbid):
        if tmdbid:
            try:
                ret = requests.get(FANART_API_URL % tmdbid)
                if ret:
                    moviethumbs = ret.json().get('moviethumb')
                    if moviethumbs:
                        moviethumb = moviethumbs[0].get('url')
                        if moviethumb:
                            # 有则返回FanArt的图片
                            return moviethumb
            except RequestException as e:
                log.debug("【RMT】拉取FanArt图片出错：%s" % str(e))
            except Exception as e:
                log.debug("【RMT】拉取FanArt图片出错：%s" % str(e))
        if not backdrop_path:
            return ""
        return "https://image.tmdb.org/t/p/w500%s" % backdrop_path

    # 从种子名称中获取季和集的数字
    @staticmethod
    def get_sestring_from_name(name):
        re_res = re.search(r'([SEP]+\d{1,2}-?[SEP]*\d{0,2})', name, re.IGNORECASE)
        if re_res:
            return re_res.group(1).upper()
        else:
            return None


# 全量转移，用于使用命令调用
def transfer_all(s_path, t_path):
    if not s_path:
        return
    if not os.path.exists(s_path):
        print("【RMT】源目录不存在：%s" % s_path)
        return
    if t_path:
        if not os.path.exists(t_path):
            print("【RMT】目的目录不存在：%s" % t_path)
            return
    config = get_config()
    print("【RMT】正在转移以下目录中的全量文件：%s" % s_path)
    print("【RMT】转移模式为：%s" % config['sync'].get('sync_mod'))
    for f_dir in os.listdir(s_path):
        file_path = os.path.join(s_path, f_dir)
        try:
            ret = Media().transfer_media(in_from="手动整理", in_path=file_path, target_dir=t_path)
            if not ret:
                print("【RMT】%s 处理失败！" % file_path)
        except Exception as err:
            print("【RMT】发生错误：%s" % str(err))
    print("【RMT】%s 处理完成！" % s_path)


if __name__ == "__main__":
    # 参数
    parser = argparse.ArgumentParser(description='Rename Media Tool')
    parser.add_argument('-s', '--source', dest='s_path', required=True, help='硬链接源目录路径')
    parser.add_argument('-d', '--target', dest='t_path', required=False, help='硬链接目的目录路径')
    args = parser.parse_args()
    if os.environ.get('NASTOOL_CONFIG'):
        print("【RMT】配置文件地址：%s" % os.environ['NASTOOL_CONFIG'])
        print("【RMT】源目录路径：%s" % args.s_path)
        if args.t_path:
            print("【RMT】目的目录路径：%s" % args.t_path)
        else:
            print("【RMT】目的目录为配置文件中的电影、电视剧媒体库目录")
        transfer_all(args.s_path, args.t_path)
    else:
        print("【RMT】未设置环境变量，请先设置 NASTOOL_CONFIG 环境变量为配置文件地址")
