import os
import threading
from hashlib import md5

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from config import get_config, RMT_MEDIAEXT, SYNC_DIR_CONFIG
from functions import get_dir_files_by_ext
from rmt.media import transfer_directory

import log

# 全局设置
FINISHED_JOBS = {}
# 加锁
lock = threading.Lock()


# 处理文件夹
def dir_change_handler(event, text):
    global FINISHED_JOBS
    config = get_config()
    event_path = event.src_path
    monpaths = SYNC_DIR_CONFIG.keys()
    if event.is_directory:  # 文件改变都会触发文件夹变化
        try:
            log.debug("【SYNC】" + text + "了文件夹: %s " % event_path)
            name = os.path.basename(event_path)
            for monpath in monpaths:
                if os.path.samefile(monpath, event_path):
                    # 源目录的根目录变化不处理
                    return
            # 目的目录的子目录不处理
            for tpath in SYNC_DIR_CONFIG.values():
                if tpath:
                    if tpath in event_path:
                        return
            if not name:
                return
            if name.startswith(".") or name.startswith("#") or name.startswith("@"):
                # 带点或＃或＠开头的隐藏目录不处理
                return
            movie_path = config['media'].get('movie_path')
            if os.path.samefile(movie_path, event_path):
                # 电影目的目录的变化不处理
                return
            tv_path = config['media'].get('tv_path')
            if os.path.samefile(tv_path, event_path):
                # 电视剧目的目录的变化不处理
                return

            files_num = len(get_dir_files_by_ext(event_path, RMT_MEDIAEXT))
            if files_num == 0:
                return
            job_key = md5(event_path.encode("utf-8")).hexdigest()
            need_handler_flag = False
            noti_flag = True

            # 加锁
            try:
                lock.acquire()
                if not FINISHED_JOBS.get(job_key):
                    # 等待10秒，让文件移完
                    need_handler_flag = True
                    FINISHED_JOBS[job_key] = files_num
                else:
                    # 判断文件数，看是不是有变化，有文件增加就要重新处理
                    if FINISHED_JOBS.get(job_key) < files_num:
                        # 文件数有变化，但只处理增量的，重复的文件不通知
                        FINISHED_JOBS[job_key] = files_num
                        need_handler_flag = True
                        noti_flag = False
                    else:
                        log.debug("【SYNC】已处理过：" + event_path)
            finally:
                lock.release()

            if need_handler_flag:
                # 找到是哪个监控目录下的
                parent_dir = event_path
                for m_path in SYNC_DIR_CONFIG.keys():
                    if m_path in event_path:
                        parent_dir = m_path
                # 查找目的目录
                target_dir = SYNC_DIR_CONFIG.get(parent_dir)
                log.info("【SYNC】开始处理：" + event_path)
                if not transfer_directory(in_from="目录监控", in_name=name, in_path=event_path, noti_flag=noti_flag, target_dir=target_dir):
                    log.error("【SYNC】" + event_path + "处理失败！")
                else:
                    log.info("【SYNC】" + event_path + "处理成功！")

        except Exception as e:
            log.error("【SYNC】发生错误：" + str(e))
    else:
        # 只有根目录下的文件才处理
        dirpath = os.path.dirname(event_path)
        name = os.path.basename(event_path)

        need_handler_flag = False
        # 是根目录之一才继续处理
        for monpath in monpaths:
            if os.path.samefile(monpath, dirpath):
                need_handler_flag = True

        # 不是媒体文件不处理
        ext = os.path.splitext(name)[-1]
        if ext in RMT_MEDIAEXT:
            need_handler_flag = True

        if not need_handler_flag:
            return

        # 开始处理
        job_key = md5(event_path.encode("utf-8")).hexdigest()
        log.info("【SYNC】开始处理：" + event_path)
        if not FINISHED_JOBS.get(job_key):
            FINISHED_JOBS[job_key] = 1
            if not transfer_directory(in_from="目录监控", in_name=name, in_path=event_path, noti_flag=True):
                log.error("【SYNC】" + event_path + "处理失败！")
            else:
                log.info("【SYNC】" + event_path + "处理成功！")
        else:
            log.debug("【SYNC】已处理过：" + event_path)


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


def create_sync():
    config = get_config()
    sync_sys = config['app'].get('nas_sys', "Linux") == "Linux" or False
    if sync_sys:
        # linux
        observer = Observer()
    else:
        # 其他
        observer = PollingObserver()
    return observer


# 全量转移
def sync_all():
    handler_files = []
    config = get_config()
    sync_crg = config.get('sync')
    if sync_crg:
        monpaths = config['sync'].get('sync_path')
        if monpaths:
            log.info("【SYNC】开始全量转移...")
            for monpath in monpaths:
                # 目录是两段式，需要把配对关系存起来
                if monpath.find('|') != -1:
                    # 源目录|目的目录，这个格式的目的目录在源目录同级建立
                    monpath = monpath.split("|")[0]
                for cdir in os.listdir(monpath):
                    if cdir.startswith(".") or cdir.startswith("#") or cdir.startswith("@"):
                        continue
                    file_path = os.path.join(monpath, cdir)
                    file_name = os.path.basename(file_path)
                    log.info("【SYNC】开始处理：" + file_path)
                    try:
                        if file_name not in handler_files:
                            handler_files.append(file_name)
                            transfer_directory(in_from="目录监控", in_name=file_name, in_path=file_path, noti_flag=True)
                    except Exception as err:
                        log.error("【SYNC】发生错误：" + str(err))


if __name__ == "__main__":
    sync_all()
