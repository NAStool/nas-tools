import argparse
import os
import re
import shutil
import log
from tmdbv3api import TMDb, Search
from subprocess import call

from config import RMT_SUBEXT, get_config, RMT_MEDIAEXT, RMT_DISKFREESIZE, RMT_COUNTRY_EA, RMT_COUNTRY_AS, \
    RMT_MOVIETYPE
from functions import get_dir_files_by_ext, is_chinese, str_filesize, get_free_space_gb
from message.send import sendmsg


# 根据文件名转移对应字幕文件
def transfer_subtitles(org_name, new_name, rmt_mode="COPY"):
    dir_name = os.path.dirname(org_name)
    file_list = get_dir_files_by_ext(dir_name, RMT_SUBEXT)
    Media_FileNum = len(file_list)
    if Media_FileNum == 0:
        log.debug("【RMT】" + dir_name + " 目录下没有找到字幕文件...")
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
                    log.debug("【RMT】正在处理字幕：" + file_item + " 到 " + new_file)
                    if rmt_mode == "LINK":
                        rmt_mod_str = "硬链接"
                        retcode = call(["ln", file_item, new_file])
                    else:
                        rmt_mod_str = "复制"
                        retcode = call(["cp", file_item, new_file])
                    if retcode == 0:
                        log.info("【RMT】字幕" + rmt_mod_str + "完成：" + new_file)
                    else:
                        log.error("【RMT】字幕" + rmt_mod_str + "失败，错误码：" + str(retcode))
                else:
                    log.info("【RMT】字幕 " + new_file + "已存在！")
        if not find_flag:
            log.debug("【RMT】没有相同文件名的字幕文件，不处理！")


def transfer_bluray_dir(file_path, new_path, mv_flag=False, over_flag=False):
    config = get_config()
    if over_flag:
        log.warn("【RMT】正在删除已存在的目录：" + new_path)
        shutil.rmtree(new_path)
        log.warn("【RMT】" + new_path + " 已删除！")

    # 复制文件
    log.info("【RMT】正在复制目录：" + file_path + " 到 " + new_path)
    retcode = call(['cp -r', file_path, new_path])
    if retcode == 0:
        log.info("【RMT】文件复制完成：" + new_path)
    else:
        log.error("【RMT】文件复制失败，错误码：" + str(retcode))

    if mv_flag:
        if file_path != config['media'].get('movie_path') and file_path != config['media'].get('tv_path'):
            shutil.rmtree(file_path)
        log.info("【RMT】" + file_path + " 已删除！")


def transfer_file(file_item, new_file, over_flag=False, rmt_mode="COPY"):
    if over_flag and os.path.exists(new_file):
        if os.path.isfile(new_file):
            log.info("【RMT】正在删除已存在的文件：" + new_file)
            os.remove(new_file)
            log.warn("【RMT】" + new_file + " 已删除！")

    # 复制文件
    log.info("【RMT】正在转移文件：" + file_item + " 到 " + new_file)
    if rmt_mode == "LINK":
        rmt_mod_str = "硬链接"
        retcode = call(['ln', file_item, new_file])
    else:
        rmt_mod_str = "复制"
        retcode = call(['cp', file_item, new_file])
    if retcode == 0:
        log.info("【RMT】文件" + rmt_mod_str + "完成：" + new_file)
    else:
        log.error("【RMT】文件" + rmt_mod_str + "失败，错误码：" + str(retcode))

    # 处理字幕
    transfer_subtitles(file_item, new_file, rmt_mode)


# 转移一个目录下的所有文件
def transfer_media(in_from, in_name, in_path,
                   in_title=None, in_year=None, in_season=None, in_type=None, target_dir=None):
    config = get_config()
    if in_from == "目录监控":
        rmt_mode = config['sync'].get('sync_mod', 'COPY').upper()
    else:
        rmt_mode = config['pt'].get('rmt_mode', 'COPY').upper()
    if not in_name or not in_path:
        log.error("【RMT】输入参数错误!")
        return False
    # 遍历文件
    in_path = in_path.replace('\\\\', '/').replace('\\', '/')
    log.info("【RMT】开始处理：" + in_path)

    if target_dir:
        # 有输入target_dir时，往这个目录放
        movie_dist = target_dir
    else:
        movie_dist = config['media'].get('movie_path')

    # 是否开始自动分类
    movie_subtypedir = config['media'].get('movie_subtypedir', True)

    bluray_disk_flag = False
    if os.path.isdir(in_path):
        # 如果传入的是个目录
        if not os.path.exists(in_path):
            log.error("【RMT】目录不存在：" + in_path)
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
            log.info("【RMT】当前为蓝光原盘文件夹：" + str(in_path))
        else:
            file_list = get_dir_files_by_ext(in_path, RMT_MEDIAEXT)
            Media_FileNum = len(file_list)
            log.debug("【RMT】文件清单：" + str(file_list))
            if Media_FileNum == 0:
                log.warn("【RMT】目录下未找到媒体文件：" + in_path)
                return False
    else:
        # 如果传入的是个文件
        if not os.path.exists(in_path):
            log.error("【RMT】文件不存在：" + in_path)
            return False
        ext = os.path.splitext(in_path)[-1]
        if ext not in RMT_MEDIAEXT:
            log.warn("【RMT】不支持的媒体文件格式，不处理：" + in_path)
            return False
        file_list = [in_path]
        Media_FileNum = 1

    # API检索出媒体信息，传入一个文件列表，得出每一个文件的名称
    Search_Type, Medias = get_media_info(file_list, in_name, in_type, in_year)
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
        if media["backdrop_path"]:
            Backdrop_Path = "https://image.tmdb.org/t/p/w500" + media["backdrop_path"]

        if Media_Id != "0":
            if Search_Type == "电影":
                # 是否新电影标志
                new_movie_flag = False
                # 检查剩余空间
                disk_free_size = get_free_space_gb(movie_dist)
                if float(disk_free_size) < RMT_DISKFREESIZE:
                    log.error("【RMT】目录" + movie_dist + "剩余磁盘空间不足" + RMT_DISKFREESIZE + "GB，不处理！")
                    sendmsg("【RMT】磁盘空间不足", "目录" + movie_dist + "剩余磁盘空间不足" + RMT_DISKFREESIZE + "GB！")
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
                                log.warn("【RMT】蓝光原盘目录已存在：" + media_path)
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
                        transfer_bluray_dir(file_item, media_path)
                        return True
                    else:
                        # 创建电影目录
                        log.info("【RMT】正在创建目录：" + media_path)
                        os.makedirs(media_path)
                else:
                    # 新路径存在
                    if bluray_disk_flag:
                        log.warn("【RMT】蓝光原盘目录已存在：" + media_path)
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
                    transfer_file(file_item, new_file, False, rmt_mode)
                else:
                    Exist_FileNum = Exist_FileNum + 1
                    if rmt_mode != "LINK":
                        ExistFile_Size = os.path.getsize(new_file)
                        if Media_FileSize > ExistFile_Size:
                            log.info("【RMT】文件" + new_file + "已存在，但新文件质量更好，覆盖...")
                            new_movie_flag = True
                            transfer_file(file_item, new_file, True, rmt_mode)
                        else:
                            log.warn("【RMT】文件 " + new_file + "已存在，且质量更好！")
                    else:
                        log.debug("【RMT】文件 " + new_file + "已存在！")
                log.info("【RMT】" + Media_Title + " 转移完成！")

                # 开始发送消息
                if not new_movie_flag:
                    return True

                msg_str = []
                if Media_Pix:
                    msg_str.append("质量：" + str(Media_Pix).lower())
                if Media_FileSize:
                    msg_str.append("大小：" + str_filesize(Media_FileSize))
                msg_str.append("来自：" + in_from)
                if Exist_FileNum != 0:
                    save_note = str(Exist_FileNum) + " 个文件已存在！"
                    msg_str.append("备注：" + save_note)
                sendmsg("电影 " + Media_Title + " 转移完成", "\n".join(msg_str), Backdrop_Path)

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
                    tv_dist = config['media'].get('tv_path')

                disk_free_size = get_free_space_gb(tv_dist)
                if float(disk_free_size) < RMT_DISKFREESIZE:
                    log.error("【RMT】目录" + tv_dist + "剩余磁盘空间不足" + RMT_DISKFREESIZE + "GB，不处理！")
                    sendmsg("【RMT】磁盘空间不足", "目录" + tv_dist + "剩余磁盘空间不足" + RMT_DISKFREESIZE + "GB，不处理！")
                    return False

                # 新路径
                media_path = os.path.join(tv_dist, Media_Title + Year_Str)
                # 未配置时默认进行分类
                tv_subtypedir = config['media'].get('tv_subtypedir', True)
                if tv_subtypedir:
                    media_path = os.path.join(tv_dist, Media_Type, Media_Title + Year_Str)

                # 创建目录
                if not os.path.exists(media_path):
                    log.info("【RMT】正在创建目录：" + media_path)
                    os.makedirs(media_path)

                Media_FileSize = Media_FileSize + os.path.getsize(file_item)
                file_ext = os.path.splitext(file_item)[-1]
                file_name = os.path.basename(file_item)
                # Sxx
                if in_season:
                    file_season = in_season
                else:
                    file_season = get_media_file_season(file_name)
                # Exx
                file_seq = get_media_file_seq(file_name)
                # 季 Season xx
                season_str = "Season " + str(int(file_season.replace("S", "")))
                season_dir = os.path.join(media_path, season_str)
                # 集 xx
                file_seq_num = str(int(file_seq.replace("E", "").replace("P", "")))
                # 创建目录
                if not os.path.exists(season_dir):
                    log.debug("【RMT】正在创建剧集目录：" + season_dir)
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
                    transfer_file(file_item, new_file, False, rmt_mode)
                else:
                    ExistFile_Size = os.path.getsize(new_file)
                    if rmt_mode != "LINK":
                        if Media_FileSize > ExistFile_Size:
                            log.info("【RMT】文件" + new_file + "已存在，但新文件质量更好，覆盖...")
                            if season_str not in season_ary:
                                season_ary.append(season_str)
                            if file_seq_num not in episode_ary:
                                episode_ary.append(file_seq_num)
                            transfer_file(file_item, new_file, True, rmt_mode)
                        else:
                            Exist_FileNum = Exist_FileNum + 1
                            log.warn("【RMT】文件 " + new_file + "已存在且质量更好，不处理！")
                    else:
                        log.debug("【RMT】文件 " + new_file + "已存在！")
                log.info("【RMT】" + Media_Title + " 转移完成！")

                if not episode_ary:
                    return True

                season_ary.sort()
                episode_ary.sort(key=int)

                # 开始发送消息
                msg_title = Media_Title
                msg_str = []

                if len(episode_ary) == 1:
                    # 只变更了一集
                    msg_title = msg_title + " 第" + season_ary[0].replace("Season ", "") + \
                                "季第" + episode_ary[0] + "集 转移完成"
                    if Media_FileSize:
                        msg_str.append("大小：" + str_filesize(Media_FileSize))
                else:
                    if season_ary:
                        msg_str.append("季：" + ', '.join(season_ary))
                    if episode_ary:
                        msg_str.append("集：" + ', '.join(episode_ary))
                    if Media_FileNum:
                        msg_str.append("文件数：" + str(Media_FileNum))
                    if Media_FileSize:
                        msg_str.append("总大小：" + str_filesize(Media_FileSize))
                msg_str.append("来自：" + in_from)
                if Exist_FileNum != 0:
                    save_note = str(Exist_FileNum) + " 个文件已存在！"
                    msg_str.append("备注：" + save_note)
                sendmsg("电视剧 " + msg_title + " 转移完成", "\n".join(msg_str), Backdrop_Path)
            else:
                log.error("【RMT】" + in_name + " 无法识别是什么类型的媒体文件！")
                sendmsg("【RMT】无法识别媒体类型！", "来源：" + in_from
                        + "\n种子名称：" + in_name)
                return False
        else:
            sendmsg("【RMT】媒体搜刮失败！", "来源：" + in_from
                    + "\n种子名称：" + in_name
                    + "\n识别类型：" + Search_Type)
            return False
    return True


def is_media_files_tv(file_list):
    flag = False
    for tmp_file in file_list:
        tmp_name = os.path.basename(tmp_file)
        re_res = re.search(r"[\s.]*[SE]P?\d{1,3}", tmp_name, re.IGNORECASE)
        if re_res:
            flag = True
            break
    return flag


# 获得媒体名称，用于API检索
def get_pt_media_name(in_name):
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
    re_res1 = re.search(r"[\s.]+\d{4}[\s.]+", out_name)
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
        out_name = re.sub(r'[SsEePp]+\d{1,2}-?[SsEePp]*\d{0,2}', '', out_name, re.IGNORECASE).strip()
        # 把中文中的英文、字符等全部去掉，数字要留下
        out_name = re.sub(r'[a-zA-Z【】\-.\[\]()\s]+', '', out_name, re.IGNORECASE).strip()
    else:
        # 如果带有Sxx-Sxx、Exx-Exx这类的要处理掉
        out_name = re.sub(r'[SsEePp]+\d{1,2}-?[SsEePp]*\d{0,2}', '', out_name, re.IGNORECASE).strip()
        # 不包括中文，则是英文名称
        out_name = out_name.replace(".", " ")
    return out_name


# 获得媒体文件的集数S00
def get_media_file_season(in_name):
    if in_name:
        # 查找Sxx
        re_res = re.search(r"[\s.]*(S\d{1,2})", in_name, re.IGNORECASE)
        if re_res:
            return re_res.group(1).upper()
    return "S01"


# 获得媒体文件的集数E00
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
def get_media_file_pix(in_name):
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
def get_media_file_year(in_name):
    if in_name:
        # 查找Sxx
        re_res = re.search(r"[\s.(]+(\d{4})[\s.)]+", in_name, re.IGNORECASE)
        if re_res:
            return re_res.group(1).upper()
    return ""


# 检索tmdb中的媒体信息，传入名字、年份、类型
# 返回媒体信息对象
def search_tmdb(file_media_name, media_year, search_type):
    if not file_media_name:
        log.error("【RMT】检索关键字有误！")
        return None
    # TheMovieDB
    tmdb = TMDb()
    config = get_config()
    rmt_tmdbkey = config['app'].get('rmt_tmdbkey')
    tmdb.api_key = rmt_tmdbkey
    tmdb.language = 'zh'
    tmdb.debug = True

    info = {}
    media_id = "0"
    media_type = ""
    media_title = ""
    backdrop_path = ""

    if search_type == "电影":
        search = Search()
        log.info("【RMT】正在检索电影：" + file_media_name + '...')
        if media_year:
            movies = search.movies({"query": file_media_name, "year": media_year})
        else:
            movies = search.movies({"query": file_media_name})
        log.debug("【RMT】API返回：" + str(search.total_results))
        if len(movies) == 0:
            log.warn("【RMT】" + file_media_name + " 未找到媒体信息!")
        else:
            info = movies[0]
            for movie in movies:
                if movie.title == file_media_name or movie.release_date[0:4] == media_year:
                    # 优先使用名称或者年份完全匹配的，匹配不到则取第一个
                    info = movie
                    break
            media_id = info.id
            media_title = info.title
            log.info(">电影ID：" + str(info.id) + "，上映日期：" + info.release_date + "，电影名称：" + info.title)
            media_year = info.release_date[0:4]
            backdrop_path = info.backdrop_path
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
        log.info("【RMT】正在检索剧集：" + file_media_name + '...')
        if media_year:
            tvs = search.tv_shows({"query": file_media_name, "year": media_year})
        else:
            tvs = search.tv_shows({"query": file_media_name})
        log.debug("【RMT】API返回：" + str(search.total_results))
        if len(tvs) == 0:
            log.error("【RMT】" + file_media_name + "未找到媒体信息!")
            info = {}
        else:
            info = tvs[0]
            for tv in tvs:
                if tv.first_air_date:
                    if tv.name == file_media_name and tv.first_air_date[0:4] == media_year:
                        # 优先使用名称或者年份完全匹配的，匹配不到则取第一个
                        info = tv
                        break
                elif tv.name == file_media_name:
                    info = tv
                    break

            media_id = info.id
            media_title = info.name
            log.info(">剧集ID：" + str(info.id) + "，剧集名称：" + info.name + "，上映日期：" + info.first_air_date)
            if info.first_air_date:
                media_year = info.first_air_date[0:4]
            backdrop_path = info.backdrop_path
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
            "backdrop_path": backdrop_path}


# 只有个名称和类型，用于RSS类的搜刮毁体信息
def get_media_info_on_name(in_name, in_type):
    search_type = in_type
    media_name = get_pt_media_name(in_name)
    media_year = get_media_file_year(in_name)
    # 调用TMDB API
    file_media_info = search_tmdb(media_name, media_year, in_type)
    if file_media_info:
        # 分辨率
        media_pix = get_media_file_pix(in_name)
        file_media_info['media_pix'] = media_pix

    return file_media_info


# 搜刮媒体信息和类型，返回每个文件对应的媒体信息
# 输入：file_list：文件路径清单, in_name 文件目录的名称, in_type 指定搜索类型，in_year 指定搜索年份, in_name有输入则优先使用
# 输出：类型，文件路径：媒体信息的List
def get_media_info(file_list, in_name, in_type=None, in_year=None):
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
        elif is_media_files_tv(file_list):
            # 电视剧
            search_type = "电视剧"
        else:
            search_type = "电影"

    log.debug("【RMT】检索类型为：" + search_type)

    # 传入的目名称来识别的媒体名称
    media_name = get_pt_media_name(in_name)

    if not in_year:
        media_year = get_media_file_year(in_name)
    else:
        media_year = in_year

    media_pix = get_media_file_pix(in_name)

    # 存储所有识别的名称与媒体信息的对应关系
    media_names = {}

    # 遍历每个文件，看得出来的名称是不是不一样，不一样的先搜索媒体信息
    for file_path in file_list:
        # 解析媒体名称
        file_name = os.path.basename(file_path)
        if media_name:
            # 优先以传入的为准 PT等
            file_media_name = media_name
        else:
            # 传入不准时优先拿文件名的
            file_media_name = get_pt_media_name(file_name)

        if not file_media_name:
            # 还是没有，只能从上级路径中拿了
            tmp_path = os.path.basename(os.path.dirname(file_path))
            file_media_name = get_pt_media_name(tmp_path)
            if not file_media_name:
                # 最多找两级
                tmp_path = os.path.basename(os.path.dirname(file_path))
                file_media_name = get_pt_media_name(tmp_path)

        if not media_names.get(file_media_name):
            if not media_year:
                # 传入的名称没有，则取文件里的
                file_year = get_media_file_year(file_name)
                if not file_year:
                    # 还没有，取路径里的
                    media_year = get_media_file_year(file_path)
                else:
                    media_year = file_year

            if media_year:
                log.debug("【RMT】识别年份为：" + str(media_year))
            else:
                log.debug("【RMT】未识别出年份！")

            # 解析分辨率
            if not media_pix:
                file_pix = get_media_file_pix(file_name)
                if not file_pix:
                    media_pix = get_media_file_pix(file_path)
                else:
                    media_pix = file_pix

            if media_pix:
                log.debug("【RMT】识别分辨率为：" + str(media_pix))
            else:
                log.debug("【RMT】未识别分辨率！")

            # 调用TMDB API
            file_media_info = search_tmdb(file_media_name, media_year, search_type)
            if file_media_info:
                file_media_info['media_pix'] = media_pix
                # 记录为已检索
                media_names[file_media_name] = file_media_info

        # 存入结果清单返回
        return_media_infos[file_path] = media_names[file_media_name]

    return search_type, return_media_infos


# 全量转移
def transfer_all(s_path, t_path):
    if not s_path:
        return
    if not os.path.exists(s_path):
        print("【RMT】源目录不存在：" + s_path)
        return
    if not os.path.exists(t_path):
        print("【RMT】目的目录不存在：" + t_path)
        return
    config = get_config()
    print("【RMT】正在转移以下目录中的全量文件：" + s_path)
    print("【RMT】转移模式为：" + config['pt'].get('rmt_mode'))
    for f_dir in os.listdir(s_path):
        file_path = os.path.join(s_path, f_dir)
        file_name = os.path.basename(file_path)
        print("【RMT】开始处理：" + file_path)
        try:
            transfer_media(in_from="PT", in_name=file_name, in_path=file_path, target_dir=t_path)
            print("【RMT】处理完成：" + file_path)
        except Exception as err:
            print("【RMT】发生错误：" + str(err))
    print("【RMT】" + s_path + " 处理完成！")


if __name__ == "__main__":
    # 参数
    parser = argparse.ArgumentParser(description='Rename Media Tool')
    parser.add_argument('-c', '--config', dest='config_file', required=True, help='配置文件的路径')
    parser.add_argument('-s', '--source', dest='s_path', required=True, help='硬链接源目录路径')
    parser.add_argument('-d', '--target', dest='t_path', required=True, help='硬链接目的目录路径')
    args = parser.parse_args()
    print("【RMT】配置文件地址：" + args.config_file)
    print("【RMT】源路径：" + args.s_path)
    print("【RMT】目的路径：" + args.t_path)
    os.environ['NASTOOL_CONFIG'] = args.config_file
    transfer_all(args.s_path, args.t_path)
