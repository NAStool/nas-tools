import os
import re
import shutil
import time
import log
from tmdbv3api import TMDb, Search
from subprocess import call

import settings
from functions import get_dir_files_by_ext, is_chinese, mysql_exec_sql, str_filesize
from message.send import sendmsg


# 根据文件名转移对应字幕文件
def transfer_subtitles(in_path, org_name, new_name, mv_flag=False):
    file_list = get_dir_files_by_ext(in_path, settings.get('rmt.rmt_subext'))
    log.debug("【RMT】字幕文件清单：" + str(file_list))
    Media_FileNum = len(file_list)
    if Media_FileNum == 0:
        log.info("【RMT】没有支持的字幕文件，不处理！")
    else:
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
                    if mv_flag:
                        log.debug("【RMT】正在移动字幕：" + file_item + " 到 " + new_file)
                        # shutil.move(file_item, new_file)
                        call(["mv", file_item, new_file])
                        log.info("【RMT】字幕移动完成：" + new_file)
                    else:
                        log.debug("【RMT】正在复制字幕：" + file_item + " 到 " + new_file)
                        # shutil.copy(file_item, new_file)
                        call(["cp", file_item, new_file])
                        log.info("【RMT】字幕复制完成：" + new_file)
                else:
                    log.info("【RMT】字幕 " + new_file + "已存在！")
        if not find_flag:
            log.debug("【RMT】没有相同文件名的字幕文件，不处理！")


def transfer_bluray_dir(file_path, new_path, mv_flag=False, over_flag=False):
    if over_flag:
        log.debug("【RMT】正在删除已存在的目录：" + new_path)
        shutil.rmtree(new_path)
        log.info("【RMT】" + new_path + " 已删除！")

    # 复制文件
    log.info("【RMT】正在复制目录：" + file_path + " 到 " + new_path)
    call(['cp -r', file_path, new_path])
    log.info("【RMT】文件复制完成：" + new_path)

    if mv_flag:
        if file_path != settings.get('rmt.rmt_moviepath') and file_path != settings.get('rmt.rmt_tvpath'):
            shutil.rmtree(file_path)
        log.info("【RMT】" + file_path + " 已删除！")


def transfer_files(file_path, file_item, new_file, mv_flag=False, over_flag=False):
    if over_flag:
        log.debug("【RMT】正在删除已存在的文件：" + new_file)
        os.remove(new_file)
        log.info("【RMT】" + new_file + " 已删除！")

    # 复制文件
    log.info("【RMT】正在复制文件：" + file_item + " 到 " + new_file)
    # shutil.copy(file_item, new_file)
    call(['cp', file_item, new_file])
    log.info("【RMT】文件复制完成：" + new_file)
    transfer_subtitles(file_path, file_item, new_file, False)

    if mv_flag:
        if file_path != settings.get('rmt.rmt_moviepath') and file_path != settings.get('rmt.rmt_tvpath'):
            shutil.rmtree(file_path)
        log.info("【RMT】" + file_path + " 已删除！")


# 转移一个目录下的所有文件
def transfer_directory(in_from, in_name, in_path, in_year=None, in_type=None, mv_flag=False, noti_flag=True):
    if in_name == "" or in_path == "":
        log.error("【RMT】输入参数错误!")
        return False
    # 遍历文件
    in_path = in_path.replace('\\\\', '/').replace('\\', '/')
    log.info("【RMT】开始处理：" + in_path)
    # 判断是不是原盘文件夹
    bluray_disk_flag = True if os.path.exists(os.path.join(in_path, "BDMV/index.bdmv")) else False
    file_list = get_dir_files_by_ext(in_path, settings.get('rmt.rmt_mediaext'))
    Media_FileNum = len(file_list)
    if bluray_disk_flag:
        in_type = "电影"
        log.info("【RMT】检测到蓝光原盘文件夹")
    else:
        log.debug("【RMT】文件清单：" + str(file_list))
        if Media_FileNum == 0:
            log.error("【RMT】没有支持的文件格式，不处理！")
            if noti_flag:
                sendmsg("【RMT】没有支持的文件格式！", "来源：" + in_from
                        + "\n\n名称：" + in_name)
            return False

    # API检索出媒体信息
    media = get_media_info(in_path, in_name, in_type, in_year)
    Search_Type = media['search']
    Media_Type = media["type"]
    Media_Id = media["id"]
    Media_Title = media["name"]
    Media_Year = media["year"]
    Media_Pix = media['pix']
    Exist_FileNum = 0
    Media_File = ""
    Media_FileSize = 0

    if (settings.get('rmt.rmt_forcetrans').upper() == "TRUE" and Media_Type != "") or (
            Media_Id != "0" and Media_Type != ""):
        if Search_Type == "电影":
            # 检查精选中是否已存在
            media_path = os.path.join(settings.get('rmt.rmt_moviepath'), settings.get('rmt.rmt_favtype'),
                                      Media_Title + " (" + Media_Year + ")")
            if not os.path.exists(media_path):
                # 新路径
                media_path = os.path.join(settings.get('rmt.rmt_moviepath'), Media_Type,
                                          Media_Title + " (" + Media_Year + ")")
                # 创建目录
                if not os.path.exists(media_path):
                    log.debug("【RMT】正在创建目录：" + media_path)
                    os.makedirs(media_path)
                else:
                    if bluray_disk_flag:
                        log.error("【RMT】蓝光原盘目录已存在：" + media_path)
                        return
            else:
                if bluray_disk_flag:
                    log.error("【RMT】蓝光原盘目录已存在：" + media_path)
                    return
            if bluray_disk_flag:
                transfer_bluray_dir(in_path, media_path)
            else:
                for file_item in file_list:
                    Media_FileSize = Media_FileSize + os.path.getsize(file_item)
                    file_ext = os.path.splitext(file_item)[-1]
                    if Media_Pix != "":
                        if Media_Pix.upper() == "4K":
                            Media_Pix = "2160p"
                        new_file = os.path.join(media_path,
                                                Media_Title + " (" + Media_Year + ") - " + Media_Pix.lower() + file_ext)
                    else:
                        new_file = os.path.join(media_path, Media_Title + " (" + Media_Year + ")" + file_ext)
                    Media_File = new_file
                    if not os.path.exists(new_file):
                        transfer_files(in_path, file_item, new_file, mv_flag)
                    else:
                        ExistFile_Size = os.path.getsize(new_file)
                        if Media_FileSize > ExistFile_Size:
                            log.error("【RMT】文件" + new_file + "已存在，但新文件质量更好，覆盖...")
                            transfer_files(in_path, file_item, new_file, mv_flag, True)
                        else:
                            Exist_FileNum = Exist_FileNum + 1
                            log.error("【RMT】文件 " + new_file + "已存在，且质量更好！")
            log.info("【RMT】" + in_name + " 转移完成！")
            msg_str = '时间：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) \
                      + "\n\n来源：" + in_from \
                      + "\n\n名称：" + in_name \
                      + "\n\nTMDB：" + str(Media_Id) \
                      + "\n\n标题：" + Media_Title \
                      + "\n\n类型：" + Media_Type \
                      + "\n\n年份：" + str(Media_Year) \
                      + "\n\n文件数：" + str(Media_FileNum) \
                      + "\n\n文件大小：" + str_filesize(Media_FileSize)
            save_path = media_path
            if Media_FileNum == 1:
                save_path = Media_File
            msg_str = msg_str + "\n\n路径：" + save_path
            save_note = ""
            if Exist_FileNum != 0:
                save_note = str(Exist_FileNum) + " 个文件已存在！"
                msg_str = msg_str + "\n\n备注：" + save_note
            sendmsg("【RMT】" + Media_Title + " 转移完成！", msg_str)
            insert_media_log(in_from, in_name, str(Media_Id), Media_Title, Media_Type, Media_Year, '', '',
                             Media_FileNum, str_filesize(Media_FileSize), save_path, save_note)
        elif Search_Type == "电视剧":
            if bluray_disk_flag:
                log.error("【RMT】识别有误：蓝光原盘目录被识别为电视剧")
                return
            season_ary = []
            episode_ary = []
            # 新路径
            media_path = os.path.join(settings.get('rmt.rmt_tvpath'), Media_Type, Media_Title + " (" + Media_Year + ")")
            # 创建目录
            if not os.path.exists(media_path):
                log.debug("【RMT】正在创建目录：" + media_path)
                os.makedirs(media_path)
            for file_item in file_list:
                Media_FileSize = Media_FileSize + os.path.getsize(file_item)
                file_ext = os.path.splitext(file_item)[-1]
                file_name = os.path.basename(file_item)
                # Sxx
                file_season = get_media_file_season(file_name)
                # Exx
                file_seq = get_media_file_seq(file_name)
                # 季 Season xx
                season_str = "Season " + str(int(file_season.replace("S", "")))
                if season_str not in season_ary:
                    season_ary.append(season_str)
                season_dir = os.path.join(media_path, season_str)
                # 集 xx
                file_seq_num = str(int(file_seq.replace("E", "").replace("P", "")))
                if file_seq_num not in episode_ary:
                    episode_ary.append(file_seq_num)
                # 创建目录
                if not os.path.exists(season_dir):
                    log.debug("【RMT】正在创建剧集目录：" + season_dir)
                    os.makedirs(season_dir)
                # 处理文件
                new_file = os.path.join(season_dir,
                                        Media_Title + " - " + file_season + file_seq + " - " + "第 "
                                        + file_seq_num + " 集" + file_ext)
                Media_File = new_file
                if not os.path.exists(new_file):
                    transfer_files(in_path, file_item, new_file, mv_flag)
                else:
                    ExistFile_Size = os.path.getsize(new_file)
                    if Media_FileSize > ExistFile_Size:
                        log.error("【RMT】文件" + new_file + "已存在，但新文件质量更好，覆盖...")
                        transfer_files(in_path, file_item, new_file, mv_flag, True)
                    else:
                        Exist_FileNum = Exist_FileNum + 1
                        log.error("【RMT】文件 " + new_file + "已存在，且质量更好！")
            log.info("【RMT】" + in_name + " 转移完成！")
            season_ary.sort()
            episode_ary.sort(key=int)
            msg_str = '时间：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) \
                      + "\n\n来源：" + in_from \
                      + "\n\n名称：" + in_name \
                      + "\n\nTMDB：" + str(Media_Id) \
                      + "\n\n标题：" + Media_Title \
                      + "\n\n类型：" + Media_Type \
                      + "\n\n年份：" + str(Media_Year) \
                      + "\n\n季：" + ', '.join(season_ary) \
                      + "\n\n集：" + ', '.join(episode_ary) \
                      + "\n\n文件数：" + str(Media_FileNum) \
                      + "\n\n文件大小：" + str_filesize(Media_FileSize)
            save_path = media_path
            if Media_FileNum == 1:
                save_path = Media_File
            msg_str = msg_str + "\n\n路径：" + save_path
            save_note = ""
            if Exist_FileNum != 0:
                save_note = str(Exist_FileNum) + " 个文件已存在！"
                msg_str = msg_str + "\n\n备注：" + save_note
            sendmsg("【RMT】" + Media_Title + " 转移完成！", msg_str)
            insert_media_log(in_from, in_name, str(Media_Id), Media_Title, Media_Type, Media_Year,
                             ', '.join(season_ary), ', '.join(episode_ary),
                             Media_FileNum, str_filesize(Media_FileSize), save_path, save_note)
        else:
            log.error("【RMT】" + in_name + " 无法识别是什么类型的媒体文件！")
            sendmsg("【RMT】无法识别媒体类型！",
                    '时间：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                    + "\n\n来源：" + in_from
                    + "\n\n名称：" + in_name)
            return False
    else:
        sendmsg("【RMT】媒体搜刮失败！", '时间：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                + "\n\n来源：" + in_from
                + "\n\n名称：" + in_name
                + "\n\n识别标题：" + Media_Title
                + "\n\n识别类型：" + Search_Type)
        return False
    return True


# 登记数据库
def insert_media_log(source, org_name, tmdbid, title, type, year, season, episode, filenum, filesize, path, note):
    # SQL 插入语句
    sql = "INSERT INTO emby_media_log " \
          "(`source`, `org_name`, `tmdbid`, `title`, `type`, `year`, `season`, `episode`, `filenum`, `filesize`, " \
          "`path`, `note`, `time`) " \
          "VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', %s, '%s', '%s', '%s', now())" % \
          (source, org_name, tmdbid, title, type, year, season, episode, filenum, filesize, path, note)
    if mysql_exec_sql(sql):
        log.debug("数据库登记成功！")
    else:
        log.error("数据库登记失败：" + sql)


def is_media_files_tv(in_path):
    flag = False
    tmp_list = get_dir_files_by_ext(in_path, settings.get('rmt.rmt_mediaext'))
    for tmp_file in tmp_list:
        tmp_name = os.path.basename(tmp_file)
        re_res = re.search(r"[\s\.]+[SE]P?\d{1,4}", tmp_name, re.IGNORECASE)
        if re_res:
            flag = True
            break
    if flag is False and len(tmp_list) > 2:
        # 目录下有多个附合后缀的文件，也认为是剧集
        flag = True
    return flag


# 获得媒体名称，用于API检索
def get_qb_media_name(in_name):
    out_name = in_name
    num_pos1 = num_pos2 = len(out_name)
    # 查找4位数字年份/分辨率的位置
    re_res1 = re.search(r"[\s\.]+\d{4}[\s\.]+", out_name)
    # 查找Sxx或Exx的位置
    re_res2 = re.search(r"[\s\.]+[SE]P?\d{1,4}", out_name, re.IGNORECASE)
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
        # 把中文中的英文、字符等全部去掉，数字要留下
        out_name = re.sub(r'[a-zA-Z【】\-\.\[\]\(\)\s]+', '', out_name, re.IGNORECASE).strip()
    else:
        # 不包括中文，则是英文名称
        out_name = out_name.replace(".", " ")
    return out_name


# 获得媒体文件的集数S00
def get_media_file_season(in_name):
    # 查找Sxx
    re_res = re.search(r"[\s\.]+(S\d{1,2})", in_name, re.IGNORECASE)
    if re_res:
        return re_res.group(1).upper()
    return "S01"


# 获得媒体文件的集数E00
def get_media_file_seq(in_name):
    # 查找Sxx
    re_res = re.search(r"[\s\.]+S?\d*(EP?\d{1,4})[\s\.]+", in_name, re.IGNORECASE)
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
    # 查找Sxx
    re_res = re.search(r"[\s\.]+[SUHD]*(\d{4}p)[\s\.]+", in_name, re.IGNORECASE)
    if re_res:
        return re_res.group(1).upper()
    else:
        re_res = re.search(r"[\s\.]+(\d+K)[\s\.]+", in_name, re.IGNORECASE)
        if re_res:
            return re_res.group(1).upper()
    return ""


# 获得媒体文件的Year
def get_media_file_year(in_name):
    # 查找Sxx
    re_res = re.search(r"[\s\.]+(\d{4})[\s\.]+", in_name, re.IGNORECASE)
    if re_res:
        return re_res.group(1).upper()
    return ""


# 搜刮媒体信息和类型
def get_media_info(in_path, in_name, in_type=None, in_year=None):
    # TheMovieDB
    tmdb = TMDb()
    tmdb.api_key = settings.get('rmt.rmt_tmdbkey')
    tmdb.language = 'zh'
    tmdb.debug = True

    info = {}
    media_id = "0"
    media_type = ""
    media_pix = ""

    # 解析媒体名称
    media_name = get_qb_media_name(in_name)
    media_title = media_name

    # 解析媒体类型
    if in_type:
        if in_type == "电影":
            search_type = "电影"
        else:
            search_type = "电视剧"
    else:
        # 文件列表中有Sxx或者Exx的就是剧集，否则就是电影
        if is_media_files_tv(in_path):
            search_type = "电视剧"
        else:
            search_type = "电影"

    log.debug("【RMT】检索类型为：" + search_type)
    if not in_year:
        media_year = get_media_file_year(in_path)
    else:
        media_year = in_year
    log.debug("【RMT】识别年份为：" + str(media_year))

    if search_type == "电影":
        search = Search()
        log.info("【RMT】正在检索电影：" + media_name + '...')
        if media_year != "":
            movie = search.movies({"query": media_name, "year": media_year})
        else:
            movie = search.movies({"query": media_name})
        log.debug("【RMT】API返回：" + str(search.total_results))
        if len(movie) == 0:
            log.error("【RMT】未找到媒体信息!")
        else:
            info = movie[0]
            media_id = info.id
            media_title = info.title
            log.info(">电影ID：" + str(info.id) + "，上映日期：" + info.release_date + "，电影名称：" + info.title)
            media_year = info.release_date[0:4]
            if media_type == "":
                # 国家
                media_language = info.original_language
                if 'zh' in media_language:
                    media_type = "华语电影"
                else:
                    media_type = "外语电影"
        # 解析分辨率
        media_pix = get_media_file_pix(in_path)

    else:
        search = Search()
        log.info("【RMT】正在检索剧集：" + media_name + '...')
        if media_year != "":
            tv = search.tv_shows({"query": media_name, "year": media_year})
        else:
            tv = search.tv_shows({"query": media_name})
        log.debug("【RMT】API返回：" + str(search.total_results))
        if len(tv) == 0:
            log.error("【RMT】未找到媒体信息!")
            info = {}
        else:
            info = tv[0]
            media_id = info.id
            media_title = info.name
            log.info(">剧集ID：" + str(info.id) + "，剧集名称：" + info.name + "，上映日期：" + info.first_air_date)
            media_year = info.first_air_date[0:4]
            if media_type == "":
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
                    elif set(eval(settings.get('rmt.rmt_country_ea'))).intersection(set(media_country)):
                        media_type = "欧美剧"
                    elif set(eval(settings.get('rmt.rmt_country_as'))).intersection(set(media_country)):
                        media_type = "日韩剧"
                    else:
                        media_type = "国产剧"
    log.debug("【RMT】剧集类型：" + media_type)
    return {"search": search_type, "type": media_type, "id": media_id, "name": media_title, "year": media_year,
            "info": info, "pix": media_pix}
