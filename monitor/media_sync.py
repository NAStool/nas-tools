import os
from hashlib import md5

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from config import get_config, RMT_MEDIAEXT
from functions import get_dir_files_by_ext
from rmt.media import transfer_directory

import log

# 全局设置
FINISHED_JOBS = {}


# 处理文件夹
def dir_change_handler(event, text):
    global FINISHED_JOBS
    config = get_config()
    monpaths = config['media'].get('sync_path')
    event_path = event.src_path
    if event.is_directory:  # 文件改变都会触发文件夹变化
        try:
            log.debug("【SYNC】" + text + "了文件夹: %s " % event_path)
            name = os.path.basename(event_path)
            for monpath in monpaths:
                if os.path.samefile(monpath, event_path):
                    # 根目录变化不处理
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
            job_key = md5(event_path.encode("utf-8")).hexdigest()
            need_handler_flag = False
            noti_flag = True
            if not FINISHED_JOBS.get(job_key):
                # 等待10秒，让文件移完
                need_handler_flag = True
                FINISHED_JOBS[job_key] = files_num
            else:
                # 判断文件数，看是不是有变化，有变化就要重新处理
                if FINISHED_JOBS.get(job_key) != files_num:
                    # 文件数有变化，但只处理增量的，重复的文件不通知
                    FINISHED_JOBS[job_key] = files_num
                    need_handler_flag = True
                    noti_flag = False
                else:
                    log.debug("【SYNC】已处理过：" + event_path)

            if need_handler_flag:
                log.info("【SYNC】开始处理：" + event_path)
                if not transfer_directory(in_from="Sync", in_name=name, in_path=event_path, noti_flag=noti_flag):
                    log.error("【SYNC】" + event_path + "处理失败！")
                else:
                    log.info("【SYNC】" + event_path + "处理成功！")

        except Exception as e:
            log.error("【SYNC】发生错误：" + str(e))
    else:
        # 只有根目录下的文件才处理
        dirpath = os.path.dirname(event_path)
        name = os.path.basename(event_path)
        job_key = md5(event_path.encode("utf-8")).hexdigest()
        need_handler_flag = False
        for monpath in monpaths:
            if os.path.samefile(monpath, dirpath):
                need_handler_flag = True
        # 需要处理
        if need_handler_flag:
            log.info("【SYNC】开始处理：" + event_path)
            if not FINISHED_JOBS.get(job_key):
                if not transfer_directory(in_from="Sync", in_name=name, in_path=event_path, noti_flag=True):
                    FINISHED_JOBS[job_key] = 1
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
    global FINISHED_JOBS
    config = get_config()
    monpaths = config['media'].get('sync_path')
    if monpaths:
        log.info("【SYNC】开始全量转移...")
        for monpath in monpaths:
            for dir in os.listdir(monpath):
                file_path = os.path.join(monpath, dir)
                if dir.find(".sync") == -1:
                    file_name = os.path.basename(file_path)
                    log.info("【SYNC】开始处理：" + file_path)
                    try:
                        if file_name not in handler_files:
                            handler_files.append(file_name)
                            transfer_directory(in_from="Sync", in_name=file_name, in_path=file_path, noti_flag=False)
                    except Exception as err:
                        log.error("【SYNC】发生错误：" + str(err))


if __name__ == "__main__":
    sync_all()
