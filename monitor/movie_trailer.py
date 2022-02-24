import os
import shutil
from tmdbv3api import TMDb, Movie
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from xml.dom.minidom import parse

from config import YOUTUBE_DL_CMD, get_config, RMT_MOVIETYPE
from functions import get_dir_files_by_name, system_exec_command
from scheduler.hot_trailer import transfer_trailers

import log

handler_files = []


# 解析nfoXML文件，午到tmdbid
def get_movie_info_from_nfo(in_path):
    try:
        domTree = parse(in_path)
        rootNode = domTree.documentElement
        tmdbid = rootNode.getElementsByTagName("tmdbid")[0].firstChild.data
        title = rootNode.getElementsByTagName("title")[0].firstChild.data
        year = rootNode.getElementsByTagName("releasedate")[0].firstChild.data[0:4]
        return tmdbid, title, year
    except Exception as err:
        log.error("【TRAILER】解析nfo文件出错：" + str(err))
        return None, None, None


# 下载预告片
def download_movie_trailer(in_path):
    config = get_config()
    hottrailer_path = config['media'].get('hottrailer_path')
    exists_trailers = get_dir_files_by_name(in_path, "-trailer.")
    if len(exists_trailers) > 0:
        log.info("【TRAILER】" + in_path + "电影目录已存在预告片，跳过...")
        return True
    nfo_files = get_dir_files_by_name(in_path, ".nfo")
    if len(nfo_files) == 0:
        log.info("【TRAILER】" + in_path + "nfo文件不存在，等待下次处理...")
        return False
    movie_id, movie_title, movie_year = get_movie_info_from_nfo(nfo_files[0])
    if not movie_id or not movie_title or not movie_year:
        return False

    trailer_dir = hottrailer_path + "/" + movie_title + " (" + movie_year + ")"
    file_path = trailer_dir + "/" + movie_title + " (" + movie_year + ").%(ext)s"
    # 开始下载
    tmdb = TMDb()
    rmt_tmdbkey = config['app'].get('rmt_tmdbkey')
    if not rmt_tmdbkey:
        # 兼容旧配置
        rmt_tmdbkey = config['pt'].get('rmt_tmdbkey')
    tmdb.api_key = rmt_tmdbkey
    if not tmdb.api_key:
        log.error("【TRAILER】未配置rmt_tmdbkey，无法下载电影预告！")
        return False
    tmdb.language = 'en-US'
    tmdb.debug = True
    movie = Movie()
    try:
        movie_videos = movie.videos(movie_id)
    except Exception as err:
        log.error("【TRAILER】错误：" + str(err))
        return False
    log.info("【TRAILER】预告片总数：" + str(len(movie_videos)))
    if len(movie_videos) > 0:
        log.info("【TRAILER】下载预告片：" + str(movie_id) + " - " + movie_title)
        succ_flag = False
        for video in movie_videos:
            trailer_key = video.key
            log.debug(">下载：" + trailer_key)
            exec_cmd = YOUTUBE_DL_CMD.replace("$PATH", file_path).replace("$KEY", trailer_key)
            log.debug(">开始执行命令：" + exec_cmd)
            # 获取命令结果
            result_err, result_out = system_exec_command(exec_cmd, 600)
            if result_err:
                log.error(">错误信息：" + result_err)
            if result_out:
                log.info(">执行结果：" + result_out)
            if result_err != "":
                succ_flag = False
                continue
            else:
                succ_flag = True
                break
        if not succ_flag:
            shutil.rmtree(trailer_dir, ignore_errors=True)
        # 转移
        transfer_trailers(trailer_dir)
    else:
        log.info("【TRAILER】" + movie_title + " 未检索到预告片")
        return False
    return True


# 处理文件夹
def dir_change_handler(event, text):
    config = get_config()
    monpath = config['media']['movie_path']
    event_path = event.src_path
    if event.is_directory:  # 文件改变都会触发文件夹变化
        try:
            log.info("【TRAILER】" + text + "了文件夹: %s " % event_path)
            if not os.path.exists(event_path):
                return
            if os.path.samefile(monpath, event_path):
                # 根目录变化不处理
                return
            for movie_type in RMT_MOVIETYPE:
                if os.path.samefile(event_path, os.path.join(monpath, movie_type)):
                    # 分类目录变化不处理
                    return
            if os.path.isdir(event_path) and \
                    (event_path.startswith(".") != -1 or event_path.startswith("#") != -1 or event_path.startswith("@") != -1):
                # 带点或＃或＠开头的隐藏目录不处理
                return
            name = os.path.basename(event_path)
            if event_path not in handler_files:
                handler_files.append(event_path)
                log.info("【TRAILER】开始处理：" + event_path + "，名称：" + name)
                # 下载预告片
                if not download_movie_trailer(event_path):
                    handler_files.remove(event_path)
                    log.info("【TRAILER】" + event_path + "处理失败，等待下次处理...")
                else:
                    log.info("【TRAILER】" + event_path + "处理成功！")
            else:
                log.debug("【TRAILER】已处理过：" + name)
        except Exception as e:
            log.error("【TRAILER】发生错误：" + str(e))


# 监听文件夹
class FileMonitorHandler(FileSystemEventHandler):
    def __init__(self, monpath, **kwargs):
        super(FileMonitorHandler, self).__init__(**kwargs)
        # 监控目录 目录下面以device_id为目录存放各自的图片
        self._watch_path = monpath

    # 重写文件创建函数，文件创建都会触发文件夹变化
    def on_created(self, event):
        dir_change_handler(event, "创建")

    def on_moved(self, event):
        dir_change_handler(event, "移动")

    def on_modified(self, event):
        dir_change_handler(event, "修改")


def create_movie_trailer():
    config = get_config()
    movie_sys = config['app']['nas_sys']
    if movie_sys:
        observer = Observer()
    else:
        observer = PollingObserver()
    return observer


# 下载电影预告片
def movie_trailer_all():
    config = get_config()
    monpath = config['media']['movie_path']
    log.info("【TRAILER】开始检索和下载电影预告片！")
    movie_subtypedir = config['media'].get('movie_subtypedir', True)
    if movie_subtypedir:
        for movie_type in RMT_MOVIETYPE:
            movie_dir_list = os.listdir(os.path.join(monpath, movie_type))
            for movie_dir in movie_dir_list:
                movie_dir = os.path.join(monpath, movie_type, movie_dir)
                if os.path.isdir(movie_dir):
                    download_movie_trailer(movie_dir)
    else:
        for movie_dir in monpath:
            movie_dir = os.path.join(monpath, movie_dir)
            if os.path.isdir(movie_dir):
                download_movie_trailer(movie_dir)
    log.info("【TRAILER】电影预告片下载任务完成！")
