import os
import shutil
import settings
from pymkv import MKVFile, MKVTrack, MKVAttachment

from functions import get_dir_files_by_ext

MOVIE_PATH = settings.get('rmt.rmt_moviepath')
MOVIE_TYPES = settings.get("rmt.rmt_movietype").split(",")


# 存量电影分类
def dispatch_directory(in_path, in_name):
    # 遍历文件
    print("开始处理：", in_name)

    # 查找最大的m2ts文件
    stream_path = os.path.join(in_path, "BDMV", "STREAM")
    m2ts_list = get_dir_files_by_ext(stream_path, ".m2ts")

    mkv_handler = MKVFile()
    max_file_size = 0
    max_m2ts_file = ""
    track_list = []
    for tmp_file in m2ts_list:
        if tmp_file.count("@eaDir"):
            continue
        m2ts_file = os.path.join(stream_path, tmp_file)
        track_list.append(m2ts_file)
        m2ts_file_size = os.path.getsize(m2ts_file)
        if m2ts_file_size > max_file_size:
            max_file_size = m2ts_file_size
            max_m2ts_file = m2ts_file
    if not max_m2ts_file:
        return
    else:
        print("已找到最大的m2ts文件：" + max_m2ts_file + "，大小：" + str(max_file_size))

    in_track = MKVTrack(max_m2ts_file)
    print("添加主视频：" + max_m2ts_file)
    mkv_handler.add_track(in_track)
    for track_file in track_list:
        print("Track：" + track_file)
        try:
            track = MKVTrack(track_file)
            if track.track_type:
                print("track.track_type=" + track.track_type)
            else:
                continue
            if track.track_name:
                print("track.track_name=" + track.track_name)
            if track.language:
                print("track.language=" + track.language)
            if track.track_type == "audio":
                print("添加音频：" + track_file)
                mkv_handler.add_track(track)
            elif track.track_type == "subtitles":
                print("添加字幕：" + track_file)
                mkv_handler.add_track(track)
        except Exception as err:
            print("出错：" + str(err))
    # 输出
    out_file = os.path.join(in_path, in_name + ".mkv")
    print("输出：" + out_file)
    mkv_handler.mux(out_file)
    # 删除旧文件
    cerfificate = os.path.join(in_path, "CERTIFICATE")
    bdmv = os.path.join(in_path, "BDMV")
    shutil.rmtree(cerfificate)
    print(cerfificate + "已删除！")
    shutil.rmtree(bdmv)
    print(bdmv + "已删除！")
    print(in_name + "处理结束！")


for movie_type in MOVIE_TYPES:
    print("类型：" + movie_type)
    type_dir = os.path.join(MOVIE_PATH, movie_type)
    for movie_dir in os.listdir(type_dir):
        movie_path = os.path.join(type_dir, movie_dir)
        bdmv_file = os.path.join(movie_path, "BDMV", "index.bdmv")
        if not os.path.exists(bdmv_file):
            print(movie_path + " 不是BlueRay文件夹，跳过...")
            continue
        dispatch_directory(movie_path, movie_dir)


