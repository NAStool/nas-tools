import argparse
import os
import shutil
from subprocess import call

import log
from config import RMT_SUBEXT, get_config, RMT_MEDIAEXT, RMT_DISKFREESIZE, RMT_MOVIETYPE
from functions import get_dir_files_by_ext, get_free_space_gb, str_filesize
from message.send import Message
from rmt.media import Media


class FileTransfer:
    __media_config = None
    __app_config = None
    __pt_config = None
    __sync_config = None
    __pt_rmt_mode = None
    __sync_rmt_mode = None
    media = None

    def __init__(self):
        self.media = Media()
        self.message = Message()
        config = get_config()
        self.__media_config = config.get('media', {})
        self.__app_config = config.get('app', {})
        self.__media_config = config.get('media', {})
        self.__pt_config = config.get('pt', {})
        self.__sync_config = config.get('sync', {})
        self.__pt_rmt_mode = self.__pt_config.get('rmt_mode', 'COPY').upper()
        self.__sync_rmt_mode = self.__sync_config.get('sync_mod', 'COPY').upper()

    # 根据文件名转移对应字幕文件
    @staticmethod
    def transfer_subtitles(org_name, new_name, rmt_mode="COPY"):
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

    def transfer_bluray_dir(self, file_path, new_path, mv_flag=False, over_flag=False):
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
    def link_origin_file(self, file_item, target_dir, search_type):
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
    def transfer_file(self, file_item, new_file, over_flag=False, rmt_mode="COPY"):
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
        return self.transfer_subtitles(file_item, new_file, rmt_mode)

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

        if in_from in ['Qbittorrent', 'Transmission']:
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
        Medias = self.media.get_media_info(file_list)
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
                Backdrop_Path = self.media.get_backdrop_image(media["backdrop_path"], Media_Id)

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
                            ret = self.transfer_bluray_dir(file_item, media_path)
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
                        ret = self.transfer_file(file_item, new_file, False, rmt_mode)
                        if not ret:
                            continue
                        new_movie_flag = True
                    else:
                        if rmt_mode != "LINK":
                            existfile_size = os.path.getsize(new_file)
                            if media_filesize > existfile_size:
                                log.info("【RMT】文件 %s 已存在，但新文件质量更好，覆盖..." % new_file)
                                ret = self.transfer_file(file_item, new_file, True, rmt_mode)
                                if not ret:
                                    continue
                                new_movie_flag = True
                            else:
                                log.warn("【RMT】文件 %s 已存在！" % new_file)
                                exist_filenum = exist_filenum + 1
                        else:
                            log.warn("【RMT】文件 %s 已存在！" % new_file)
                            exist_filenum = exist_filenum + 1

                    # 电影的话，处理一部马上开始发送消息
                    if in_from not in ['Qbittorrent', 'Transmission']:
                        #  不是PT转移的，只有有变化才通知
                        if not new_movie_flag:
                            continue

                    msg_title = Title_Str
                    if Vote_Average and Vote_Average != '0':
                        msg_title = Title_Str + " 评分：%s" % str(Vote_Average)
                    if Media_Pix:
                        msg_str = "电影 %s 转移完成，质量：%s，大小：%s，来自：%s" \
                                  % (Title_Str, Media_Pix, str_filesize(media_filesize), in_from)
                    else:
                        msg_str = "电影 %s 转移完成, 大小：%s, 来自：%s" \
                                  % (Title_Str, str_filesize(media_filesize), in_from)
                    if exist_filenum != 0:
                        msg_str = msg_str + "，%s 个文件已存在" % str(exist_filenum)
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
                    finished_tv_medias[Title_Str]['Total_Size'] = finished_tv_medias[Title_Str]['Total_Size'] + media_filesize

                    file_ext = os.path.splitext(file_item)[-1]
                    file_name = os.path.basename(file_item)
                    # Sxx
                    file_season = self.media.get_media_file_season(file_name)
                    # Exx
                    file_seq = self.media.get_media_file_seq(file_name)
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
                        ret = self.transfer_file(file_item, new_file, False, rmt_mode)
                        if not ret:
                            continue
                    else:
                        existfile_size = os.path.getsize(new_file)
                        if rmt_mode != "LINK":
                            if media_filesize > existfile_size:
                                log.info("【RMT】文件 %s 已存在，但新文件质量更好，覆盖..." % new_file)
                                ret = self.transfer_file(file_item, new_file, True, rmt_mode)
                                if not ret:
                                    continue
                            else:
                                log.warn("【RMT】文件 %s 已存在！" % new_file)
                                finished_tv_medias[Title_Str]['Exist_Files'] = finished_tv_medias[Title_Str]['Exist_Files'] + 1
                                continue
                        else:
                            log.warn("【RMT】文件 %s 已存在！" % new_file)
                            finished_tv_medias[Title_Str]['Exist_Files'] = finished_tv_medias[Title_Str]['Exist_Files'] + 1
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
                    self.link_origin_file(file_item, target_dir, Search_Type)
                continue

        # 统计完成情况，发送通知
        for title_str, item_info in finished_tv_medias.items():
            # PT的不管是否有修改文件均发通知，其他渠道没变化不发通知
            send_message_flag = False
            if in_from in ['Qbittorrent', 'Transmission']:
                send_message_flag = True
            else:
                if item_info.get('Exist_Files') < len(item_info.get('Episode_Ary')):
                    send_message_flag = True

            if send_message_flag:
                if len(item_info['Episode_Ary']) == 1:
                    # 只有一集
                    msg_str = "电视剧 %s 第 %s 季第 %s 集 转移完成，大小：%s，来自：%s" \
                              % (title_str,
                                 item_info.get('Season_Ary')[0],
                                 item_info.get('Episode_Ary')[0].split('-')[-1],
                                 str_filesize(item_info.get('Total_Size')),
                                 in_from)
                else:
                    msg_str = "电视剧 %s 转移完成，共 %s 季 %s 集，总大小：%s，来自：%s" % \
                              (title_str,
                               len(item_info.get('Season_Ary')),
                               len(item_info.get('Episode_Ary')),
                               str_filesize(item_info.get('Total_Size')),
                               in_from)
                if item_info.get('Exist_Files') != 0:
                    msg_str = msg_str + "，%s 个文件已存在" % str(item_info.get('Exist_Files'))

                msg_title = title_str
                if item_info.get('Vote_Average'):
                    msg_title = title_str + " 评分：%s" % str(item_info.get('Vote_Average'))
                self.message.sendmsg(msg_title, msg_str, item_info.get('Backdrop_Path'))

        # 总结
        log.info("【RMT】%s 处理完成，总数：%s，失败：%s！" % (in_path, total_count, failed_count))
        return True

    # 全量转移，用于使用命令调用
    def transfer_manually(self, s_path, t_path):
        if not s_path:
            return
        if not os.path.exists(s_path):
            print("【RMT】源目录不存在：%s" % s_path)
            return
        if t_path:
            if not os.path.exists(t_path):
                print("【RMT】目的目录不存在：%s" % t_path)
                return
        print("【RMT】正在转移以下目录中的全量文件：%s" % s_path)
        print("【RMT】转移模式为：%s" % self.__sync_rmt_mode)
        ret = self.transfer_media(in_from="手动整理", in_path=s_path, target_dir=t_path)
        if not ret:
            print("【RMT】%s 处理失败！" % s_path)
        else:
            print("【RMT】%s 处理完成！" % s_path)

    # 全量转移Sync目录下的文件
    def transfer_all_sync(self):
        monpaths = self.__sync_config.get('sync_path')
        if monpaths:
            log.info("【SYNC】开始全量转移...")
            if not isinstance(monpaths, list):
                monpaths = [monpaths]
            for monpath in monpaths:
                # 目录是两段式，需要把配对关系存起来
                if monpath.find('|') != -1:
                    # 源目录|目的目录，这个格式的目的目录在源目录同级建立
                    s_path = monpath.split("|")[0]
                    t_path = monpath.split("|")[1]
                else:
                    s_path = monpath
                    t_path = None
                ret = self.transfer_media(in_from="目录监控", in_path=s_path, target_dir=t_path)
                if not ret:
                    log.error("【SYNC】%s 处理失败！" % s_path)
                else:
                    log.info("【SYNC】%s 处理成功！" % s_path)


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
        FileTransfer().transfer_manually(args.s_path, args.t_path)
    else:
        print("【RMT】未设置环境变量，请先设置 NASTOOL_CONFIG 环境变量为配置文件地址")
