import os
import threading
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from xml.dom.minidom import parse
from config import YOUTUBE_DL_CMD, get_config, RMT_MOVIETYPE
from functions import get_dir_files_by_name, system_exec_command
import log

handler_files = []
lock = threading.Lock()


class Trailer:
    __observer = None
    __tmdb = None
    media = None
    __movie_monpath = None
    __movie_trailer = None

    def __init__(self):
        config = get_config()
        if config.get('app'):
            movie_sys = config['app'].get('nas_sys')
            if movie_sys:
                self.__observer = Observer()
            else:
                self.__observer = PollingObserver()
        if config.get('media'):
            __movie_monpath = config['media'].get('movie_path')
            __movie_trailer = config['media'].get('movie_trailer')

    # 解析nfoXML文件，午到tmdbid
    @staticmethod
    def get_movie_info_from_nfo(in_path):
        try:
            domTree = parse(in_path)
            rootNode = domTree.documentElement
            tmdbid = rootNode.getElementsByTagName("tmdbid")[0].firstChild.data
            title = rootNode.getElementsByTagName("title")[0].firstChild.data
            year = rootNode.getElementsByTagName("releasedate")[0].firstChild.data[0:4]
            return tmdbid, title, year
        except Exception as err:
            log.error("【TRAILER】解析nfo文件出错：%s" % str(err))
            return None, None, None

    # 下载预告片
    def download_movie_trailer(self, in_path):
        dir_name = os.path.dirname(in_path)
        nfo_files = get_dir_files_by_name(dir_name, ".nfo")
        if len(nfo_files) == 0:
            log.info("【TRAILER】%s nfo文件不存在，等待下次处理..." % dir_name)
            return False

        movie_id, movie_title, movie_year = self.get_movie_info_from_nfo(nfo_files[0])
        if not movie_id or not movie_title or not movie_year:
            return False

        file_path = os.path.join(dir_name, "/" + movie_title + " (" + movie_year + ")-trailer.%(ext)s")
        # 开始下载
        try:
            movie_videos = self.media.get_moive_metainfo(movie_id)
        except Exception as err:
            log.error("【TRAILER】错误：%s" % str(err))
            return False
        log.debug("【TRAILER】预告片总数：%s" % str(len(movie_videos)))
        if len(movie_videos) > 0:
            log.info("【TRAILER】下载预告片：%s - %s" % (str(movie_id), movie_title))
            for video in movie_videos:
                trailer_key = video.key
                log.debug(">下载：%s" % trailer_key)
                exec_cmd = YOUTUBE_DL_CMD.replace("$PATH", file_path).replace("$KEY", trailer_key)
                log.debug(">开始执行命令：%s" % exec_cmd)
                # 获取命令结果
                result_err, result_out = system_exec_command(exec_cmd, 600)
                if result_err:
                    log.error(">错误信息：%s" % result_err)
                if result_out:
                    log.info(">执行结果：%s" % result_out)
                if result_err != "":
                    continue
                else:
                    break
        else:
            log.info("【TRAILER】%s 未检索到预告片" % movie_title)
            return False
        return True

    # 处理文件夹
    def dir_change_handler(self, event, text, event_path):
        global handler_files
        if not event.is_directory:  # 监控文件变化
            try:
                log.debug("【TRAILER】%s了文件: %s " % (text, event_path))
                if not os.path.exists(event_path):
                    return
                name = os.path.basename(event_path)
                if name.startswith(".") or name.startswith("#") or name.startswith("@"):
                    # 带点或＃或＠开头的隐藏目录不处理
                    return

                # 判断是否处理过了
                need_handler_flag = False
                try:
                    lock.acquire()
                    if event_path not in handler_files:
                        handler_files.append(event_path)
                        need_handler_flag = True
                finally:
                    lock.release()

                if need_handler_flag:
                    log.info("【TRAILER】开始处理：%s" % event_path)
                    # 下载预告片
                    if not self.download_movie_trailer(event_path):
                        handler_files.remove(event_path)
                        log.info("【TRAILER】 %s 预告片下载失败！" % event_path)
                    else:
                        log.info("【TRAILER】 %s 预告片下载成功！" % event_path)
                else:
                    log.debug("【TRAILER】预告片下载已处理过：%s" % name)
            except Exception as e:
                log.error("【TRAILER】发生错误：%s" % str(e))

    # 启动服务
    def run_service(self):
        if self.__movie_monpath and self.__movie_trailer:
            if os.path.exists(self.__movie_monpath):
                self.__observer.schedule(FileMonitorHandler(self.__movie_monpath),
                                         path=self.__movie_monpath,
                                         recursive=True)
                self.__observer.setDaemon(False)
                self.__observer.start()
                log.info("【RUN】monitor.movie_trailer启动...")
            else:
                log.info("【RUN】%s 目录不存在！" % self.__movie_monpath)

    # 关闭服务
    def stop_service(self):
        if self.__observer:
            self.__observer.stop()


# 监听文件夹
class FileMonitorHandler(FileSystemEventHandler):
    trailer = Trailer()

    def __init__(self, monpath, **kwargs):
        super(FileMonitorHandler, self).__init__(**kwargs)
        # 监控目录 目录下面以device_id为目录存放各自的图片
        self._watch_path = monpath

    # 重写文件创建函数，文件创建都会触发文件夹变化
    def on_created(self, event):
        self.trailer.dir_change_handler(event, "创建", event.src_path)

    def on_moved(self, event, ):
        self.trailer.dir_change_handler(event, "移动", event.dest_path)


# 下载电影预告片
def movie_trailer_all():
    config = get_config()
    monpath = config['media'].get('movie_path')
    log.info("【TRAILER】开始检索和下载电影预告片！")
    movie_subtypedir = config['media'].get('movie_subtypedir', True)
    trailer = Trailer()
    if movie_subtypedir:
        for movie_type in RMT_MOVIETYPE:
            movie_dir_list = os.listdir(os.path.join(monpath, movie_type))
            for movie_dir in movie_dir_list:
                movie_dir = os.path.join(monpath, movie_type, movie_dir)
                if os.path.isdir(movie_dir):
                    trailer.download_movie_trailer(movie_dir)
    else:
        for movie_dir in monpath:
            movie_dir = os.path.join(monpath, movie_dir)
            if os.path.isdir(movie_dir):
                trailer.download_movie_trailer(movie_dir)
    log.info("【TRAILER】电影预告片下载任务完成！")
