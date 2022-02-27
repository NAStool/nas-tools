import argparse
import os
import re
import shutil
import log
from tmdbv3api import TMDb, Search, Movie
from subprocess import call

from config import RMT_SUBEXT, get_config, RMT_MEDIAEXT, RMT_DISKFREESIZE, RMT_COUNTRY_EA, RMT_COUNTRY_AS, \
    RMT_MOVIETYPE
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

        self.__pt_rmt_mode = self.__pt_config.get('rmt_mode')
        self.__sync_rmt_mode = self.__sync_config.get('sync_mod')

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

    # 转移蓝光文件夹
    '''
    mv_flag：是否为移动，否则为复制
    over_falg：是否覆盖
    '''

    def __transfer_bluray_dir(self, file_path, new_path, mv_flag=False, over_flag=False):
        if over_flag:
            log.warn("【RMT】正在删除已存在的目录：%s" % new_path)
            shutil.rmtree(new_path)
            log.warn("【RMT】%s 已删除！" % new_path)

        # 复制文件
        log.info("【RMT】正在复制目录：%s 到 %s" % (file_path, new_path))
        retcode = call(['cp -r', file_path, new_path])
        if retcode == 0:
            log.info("【RMT】文件复制完成：%s" % new_path)
        else:
            log.error("【RMT】文件复制失败，错误码：%s" % str(retcode))

        if mv_flag:
            if file_path != self.__media_config.get('movie_path') and file_path != self.__media_config.get('tv_path'):
                shutil.rmtree(file_path)
            log.info("【RMT】%s 已删除！" % file_path)

    # 复制或者硬链接一个文件
    def __transfer_file(self, file_item, new_file, over_flag=False, rmt_mode="COPY"):
        if over_flag and os.path.exists(new_file):
            if os.path.isfile(new_file):
                log.info("【RMT】正在删除已存在的文件：%s" % new_file)
                os.remove(new_file)
                log.warn("【RMT】%s 已删除！" % new_file)

        # 复制文件
        log.info("【RMT】正在转移文件：%s 到 %s" % (file_item, new_file))
        if rmt_mode == "LINK":
            rmt_mod_str = "硬链接"
            retcode = call(['ln', file_item, new_file])
        else:
            rmt_mod_str = "复制"
            retcode = call(['cp', file_item, new_file])
        if retcode == 0:
            log.info("【RMT】文件%s完成：%s" % (rmt_mod_str, new_file))
        else:
            log.error("【RMT】文件%s失败，错误码：%s" % (rmt_mod_str, str(retcode)))

        # 处理字幕
        self.__transfer_subtitles(file_item, new_file, rmt_mode)

    # 转移识别媒体文件
    '''
    in_from：来源
    in_name：名称，用于识别
    in_path：路径，可有是个目录也可能是一个文件
    target_dir：指定目的目录，否则按电影、电视剧目录
    '''

    def transfer_media(self, in_from, in_name, in_path,
                       in_title=None,
                       in_year=None,
                       in_season=None,
                       in_type=None,
                       target_dir=None):
        if not in_name or not in_path:
            log.error("【RMT】输入参数错误!")
            return False

        if in_from == "目录监控":
            rmt_mode = self.__sync_rmt_mode
        else:
            rmt_mode = self.__pt_rmt_mode

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
                Media_FileNum = 1
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
            Media_FileNum = 1

        # API检索出媒体信息，传入一个文件列表，得出每一个文件的名称
        Search_Type, Medias = self.get_media_info(file_list, in_name, in_type, in_year)
        if not Medias:
            log.error("【RMT】检索媒体信息出错！")
            return False

        # 对检索结果列表进行处理
        for file_item, media in Medias.items():
            # file_item 可能是目录也可能是文件
            Media_Type = media["type"]
            Media_Id = media["id"]

            if in_title:
                Media_Title = in_title
            else:
                Media_Title = media["title"]

            Media_Year = media["year"]
            if Media_Year:
                Year_Str = " (" + Media_Year + ")"
            else:
                Year_Str = ""

            Media_Pix = media['media_pix']
            Exist_FileNum = 0
            Media_FileSize = 0
            Backdrop_Path = ""
            Vote_Average = ""
            if media.get("backdrop_path"):
                Backdrop_Path = "https://image.tmdb.org/t/p/w500" + media["backdrop_path"]
            if media.get("vote_average"):
                Vote_Average = media['vote_average']

            if Media_Id != "0":
                if Search_Type == "电影":
                    # 是否新电影标志
                    new_movie_flag = False
                    # 检查剩余空间
                    disk_free_size = get_free_space_gb(movie_dist)
                    if float(disk_free_size) < RMT_DISKFREESIZE:
                        log.error("【RMT】目录 %s 剩余磁盘空间不足 %s GB，不处理！" % (movie_dist, RMT_DISKFREESIZE))
                        self.message.sendmsg("【RMT】磁盘空间不足", "目录 %s 剩余磁盘空间不足 %s GB！" % (movie_dist, RMT_DISKFREESIZE))
                        return False
                    media_path = os.path.join(movie_dist, Media_Title + Year_Str)
                    if movie_subtypedir:
                        # 启用了电影分类
                        exist_dir_flag = False
                        # 在所有分类下查找是否有当前目录了
                        for mtype in RMT_MOVIETYPE:
                            media_path = os.path.join(movie_dist, mtype, Media_Title + Year_Str)
                            if os.path.exists(media_path):
                                if bluray_disk_flag:
                                    log.warn("【RMT】蓝光原盘目录已存在：%s" % media_path)
                                    return True
                                else:
                                    # 该电影已在分类目录中存在
                                    exist_dir_flag = True
                                    break
                        if not exist_dir_flag:
                            # 分类目录中未找到，则按媒体类型拼装新路径
                            media_path = os.path.join(movie_dist, Media_Type, Media_Title + Year_Str)

                    # 新路径是否存在
                    if not os.path.exists(media_path):
                        if bluray_disk_flag:
                            # 转移蓝光原盘
                            self.__transfer_bluray_dir(file_item, media_path)
                            return True
                        else:
                            # 创建电影目录
                            log.debug("【RMT】正在创建目录：%s" % media_path)
                            os.makedirs(media_path)
                    else:
                        # 新路径存在
                        if bluray_disk_flag:
                            log.warn("【RMT】蓝光原盘目录已存在：%s" % media_path)
                            return True

                    # 开始判断和转移具体文件
                    Media_FileSize = Media_FileSize + os.path.getsize(file_item)
                    file_ext = os.path.splitext(file_item)[-1]
                    if Media_Pix != "":
                        if Media_Pix.upper() == "4K":
                            Media_Pix = "2160p"
                        new_file = os.path.join(media_path,
                                                Media_Title + Year_Str + " - " + Media_Pix.lower() + file_ext)
                    else:
                        new_file = os.path.join(media_path, Media_Title + Year_Str + file_ext)
                    if not os.path.exists(new_file):
                        new_movie_flag = True
                        self.__transfer_file(file_item, new_file, False, rmt_mode)
                    else:
                        Exist_FileNum = Exist_FileNum + 1
                        if rmt_mode != "LINK":
                            ExistFile_Size = os.path.getsize(new_file)
                            if Media_FileSize > ExistFile_Size:
                                log.info("【RMT】文件 %s 已存在，但新文件质量更好，覆盖..." % new_file)
                                new_movie_flag = True
                                self.__transfer_file(file_item, new_file, True, rmt_mode)
                            else:
                                log.warn("【RMT】文件 %s 已存在，且质量更好！" % new_file)
                        else:
                            log.debug("【RMT】文件 %s 已存在！" % new_file)
                    log.info("【RMT】%s 转移完成！" % Media_Title)

                    # 开始发送消息
                    if not new_movie_flag:
                        return True
                    msg_title = Media_Title + Year_Str
                    if Vote_Average and Vote_Average != '0':
                        msg_title = Media_Title + Year_Str + " 评分：" + str(Vote_Average)
                    msg_str = "电影 %s 转移完成，大小：%s，来自：%s" \
                              % ((Media_Title + Year_Str), str_filesize(Media_FileSize), in_from)
                    if Exist_FileNum != 0:
                        msg_str = msg_str + "，覆盖了 %s 个文件" % str(Exist_FileNum)
                    self.message.sendmsg(msg_title, msg_str, Backdrop_Path)

                elif Search_Type == "电视剧":

                    if bluray_disk_flag:
                        log.error("【RMT】识别有误：蓝光原盘目录被识别为电视剧！")
                        return False

                    season_ary = []
                    episode_ary = []

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
                    media_path = os.path.join(tv_dist, Media_Title + Year_Str)
                    # 未配置时默认进行分类
                    tv_subtypedir = self.__media_config.get('tv_subtypedir', True)
                    if tv_subtypedir:
                        media_path = os.path.join(tv_dist, Media_Type, Media_Title + Year_Str)

                    # 创建目录
                    if not os.path.exists(media_path):
                        log.debug("【RMT】正在创建目录：%s" % media_path)
                        os.makedirs(media_path)

                    Media_FileSize = Media_FileSize + os.path.getsize(file_item)
                    file_ext = os.path.splitext(file_item)[-1]
                    file_name = os.path.basename(file_item)
                    # Sxx
                    if in_season:
                        file_season = in_season
                    else:
                        file_season = self.get_media_file_season(file_name)
                    # Exx
                    file_seq = self.get_media_file_seq(file_name)
                    # 季 Season xx
                    season_str = "Season " + str(int(file_season.replace("S", "")))
                    season_dir = os.path.join(media_path, season_str)
                    # 集 xx
                    file_seq_num = str(int(file_seq.replace("E", "").replace("P", "")))
                    # 创建目录
                    if not os.path.exists(season_dir):
                        log.debug("【RMT】正在创建剧集目录：%s" % season_dir)
                        os.makedirs(season_dir)
                    # 处理文件
                    new_file = os.path.join(season_dir,
                                            Media_Title + " - " + file_season + file_seq + " - " + "第 "
                                            + file_seq_num + " 集" + file_ext)
                    if not os.path.exists(new_file):
                        if season_str not in season_ary:
                            season_ary.append(season_str)
                        if file_seq_num not in episode_ary:
                            episode_ary.append(file_seq_num)
                        self.__transfer_file(file_item, new_file, False, rmt_mode)
                    else:
                        ExistFile_Size = os.path.getsize(new_file)
                        if rmt_mode != "LINK":
                            if Media_FileSize > ExistFile_Size:
                                log.info("【RMT】文件 %s 已存在，但新文件质量更好，覆盖..." % new_file)
                                if season_str not in season_ary:
                                    season_ary.append(season_str)
                                if file_seq_num not in episode_ary:
                                    episode_ary.append(file_seq_num)
                                self.__transfer_file(file_item, new_file, True, rmt_mode)
                            else:
                                Exist_FileNum = Exist_FileNum + 1
                                log.warn("【RMT】文件  %s 已存在且质量更好，不处理！" % new_file)
                        else:
                            log.debug("【RMT】文件  %s 已存在！" % new_file)
                    log.info("【RMT】 %s  转移完成！" % Media_Title)

                    if not episode_ary:
                        return True

                    season_ary.sort()
                    episode_ary.sort(key=int)

                    # 开始发送消息
                    msg_title = Media_Title + Year_Str
                    if Vote_Average and Vote_Average != '0':
                        msg_title = msg_title + " 评分：" + str(Vote_Average)

                    msg_str = ""
                    if len(episode_ary) == 1:
                        # 只变更了一集
                        msg_str = "电视剧 %s 第%s季第%s集 转移完成，大小：%s，来自：%s" \
                                  % ((Media_Title + Year_Str),
                                     season_ary[0].replace("Season ", ""),
                                     episode_ary[0],
                                     str_filesize(Media_FileSize),
                                     in_from)
                    else:
                        msg_str = "电视剧 %s 转移完成，季：%s，集：%s，总大小：%s，来自：%s" % \
                                  ((Media_Title + Year_Str),
                                   '、'.join(season_ary),
                                   '、'.join(episode_ary),
                                   str_filesize(Media_FileSize),
                                   in_from)
                    if Exist_FileNum != 0:
                        msg_str = msg_str + "，覆盖了 %s 个文件" % str(Exist_FileNum)
                    # TODO
                    self.message.sendmsg(msg_title, "\n".join(msg_str), Backdrop_Path)
                else:
                    log.error("【RMT】 %s  无法识别是什么类型的媒体文件！" % in_name)
                    self.message.sendmsg("【RMT】无法识别媒体类型！", "来源：%s \n种子名称：%s" % (in_from, in_name))
                    return False
            else:
                self.message.sendmsg("【RMT】媒体搜刮失败！", "来源：%s \n种子名称：%s \n识别类型：%s" % (in_from, in_name, Search_Type))
                return False
        return True

    @staticmethod
    def __is_media_files_tv(file_list):
        flag = False
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
        num_pos1 = num_pos2 = len(out_name)
        # 查找4位数字年份/分辨率的位置
        re_res1 = re.search(r"[\s.]+\d{4}[\s.-]+", out_name)
        # 查找Sxx或Exx的位置
        re_res2 = re.search(r"[\s.]+[SE]P?\d{1,4}", out_name, re.IGNORECASE)
        if re_res1:
            num_pos1 = re_res1.span()[0]
        if re_res2:
            num_pos2 = re_res2.span()[0]
        # 取三都最小
        num_pos = min(num_pos1, num_pos2, len(out_name))
        # 截取Year或Sxx或Exx前面的字符
        out_name = out_name[0:num_pos]
        if is_chinese(out_name):
            # 是否有空格，有就取前面的
            num_pos = out_name.find(' ')
            if num_pos != -1:
                out_name = out_name[0:num_pos]
            # 是否有点，有就取前面的
            num_pos = out_name.find('.')
            if num_pos != -1:
                out_name = out_name[0:num_pos]
            # 如果带有Sxx-Sxx、Exx-Exx这类的要处理掉
            out_name = re.sub(r'[SsEePp]+\d{1,2}-?[SsEePp]*\d{0,2}', '', out_name).strip()
            # 把中文中的英文、字符等全部去掉，数字要留下
            out_name = re.sub(r'[a-zA-Z【】\-.\[\]()\s]+', '', out_name).strip()
        else:
            # 如果带有Sxx-Sxx、Exx-Exx这类的要处理掉
            out_name = re.sub(r'[SsEePp]+\d{1,2}-?[SsEePp]*\d{0,2}', '', out_name).strip()
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
            re_res = re.search(r"[\s.]+[SUHD]*(\d{4}p)[\s.]+", in_name, re.IGNORECASE)
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
            re_res = re.search(r"[\s.(]+(\d{4})[\s.)-]+", in_name, re.IGNORECASE)
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
            log.info("【RMT】正在检索电影：%s ..." % file_media_name)
            if media_year:
                movies = search.movies({"query": file_media_name, "year": media_year})
            else:
                movies = search.movies({"query": file_media_name})
            log.debug("【RMT】API返回：" + str(search.total_results))
            if len(movies) == 0:
                log.warn("【RMT】 %s  未找到媒体信息!" % file_media_name)
            else:
                info = movies[0]
                for movie in movies:
                    if movie.title == file_media_name or movie.release_date[0:4] == media_year:
                        # 优先使用名称或者年份完全匹配的，匹配不到则取第一个
                        info = movie
                        break
                media_id = info.id
                media_title = info.title
                log.info(">电影ID：%s ，上映日期： %s ，电影名称：%s" % (str(info.id), info.release_date, info.title))
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
            log.info("【RMT】正在检索剧集： %s ..." % file_media_name)
            if media_year:
                tvs = search.tv_shows({"query": file_media_name, "year": media_year})
            else:
                tvs = search.tv_shows({"query": file_media_name})
            log.debug("【RMT】API返回：" + str(search.total_results))
            if len(tvs) == 0:
                log.error("【RMT】 %s 未找到媒体信息!" % file_media_name)
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
                log.info(">剧集ID： %s ，剧集名称： %s ，上映日期：%s" % (str(info.id), info.name, info.get('first_air_date')))
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
                    if 'CN' in media_country:
                        media_type = "国产剧"
                    elif set(RMT_COUNTRY_EA).intersection(set(media_country)):
                        media_type = "欧美剧"
                    elif set(RMT_COUNTRY_AS).intersection(set(media_country)):
                        media_type = "日韩剧"
                    else:
                        media_type = "其它剧"
        return {"name": file_media_name,
                "type": media_type,
                "id": media_id,
                "title": media_title,
                "year": media_year,
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
    输入：file_list：文件路径清单, in_name 文件目录的名称, in_type 指定搜索类型，in_year 指定搜索年份, in_name有输入则优先使用
    输出：类型，文件路径：媒体信息的List
    '''
    def get_media_info(self, file_list, in_name, in_type=None, in_year=None):
        # 存储文件路径与媒体的对应关系
        return_media_infos = {}

        # 当前处理一次被认为是一个整体，有可能是：电影文件夹只有1个电影、电影文件夹但有多个电影、电视剧文件夹
        # 解析媒体类型
        if in_type:
            if in_type == "电影":
                search_type = "电影"
            else:
                search_type = "电视剧"
        else:
            if len(file_list) == 1 and os.path.exists(os.path.join(file_list[0], "BDMV/index.bdmv")):
                # 蓝光原盘文件夹
                search_type = "电影"
            elif self.__is_media_files_tv(file_list):
                # 电视剧
                search_type = "电视剧"
            else:
                search_type = "电影"

        log.debug("【RMT】检索类型为：" + search_type)

        # 传入的目名称来识别的媒体名称
        media_name = self.__get_pt_media_name(in_name)

        if not in_year:
            media_year = self.__get_media_file_year(in_name)
        else:
            media_year = in_year

        media_pix = self.__get_media_file_pix(in_name)

        # 存储所有识别的名称与媒体信息的对应关系
        media_names = {}

        # 遍历每个文件，看得出来的名称是不是不一样，不一样的先搜索媒体信息
        for file_path in file_list:
            # 解析媒体名称
            file_name = os.path.basename(file_path)
            file_media_name = self.__get_pt_media_name(file_name)
            # 优先使用文件的名称，没有才拿输入的
            if not file_media_name:
                if not media_name:
                    # 输入的没有，只能从上级路径中拿了
                    tmp_path = os.path.basename(os.path.dirname(file_path))
                    file_media_name = self.__get_pt_media_name(tmp_path)
                    if not file_media_name:
                        # 最多找两级
                        tmp_path = os.path.basename(os.path.dirname(file_path))
                        file_media_name = self.__get_pt_media_name(tmp_path)
                else:
                    file_media_name = media_name

            # 是否处理过
            if not media_names.get(file_media_name):
                file_year = self.__get_media_file_year(file_name)
                if file_year:
                    # 优先用文件的
                    media_year = file_year
                else:
                    # 没有文件的则使用上级的
                    if not media_year:
                        # 上级还没有，取路径里的
                        media_year = self.__get_media_file_year(file_path)

                if media_year:
                    log.debug("【RMT】识别年份为：%s" % str(media_year))
                else:
                    log.debug("【RMT】未识别出年份！")

                # 解析分辨率
                file_pix = self.__get_media_file_pix(file_name)
                if file_pix:
                    media_pix = file_pix
                else:
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

            # 存入结果清单返回
            return_media_infos[file_path] = media_names[file_media_name]

        return search_type, return_media_infos

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


# 全量转移
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
        file_name = os.path.basename(file_path)
        print("【RMT】开始处理：%s" % file_path)
        try:
            Media().transfer_media(in_from="PT", in_name=file_name, in_path=file_path, target_dir=t_path)
            print("【RMT】处理完成：%s" % file_path)
        except Exception as err:
            print("【RMT】发生错误：%s" % str(err))
    print("【RMT】 %s  处理完成！" % s_path)


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
