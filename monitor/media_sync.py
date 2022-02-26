import os
import threading

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from config import get_config, RMT_MEDIAEXT, SYNC_DIR_CONFIG
from rmt.media import transfer_media

import log

# 全局设置
FINISHED_JOBS = []

lock = threading.Lock()


# 处理文件变化
def file_change_handler(event, text, event_path):
    global FINISHED_JOBS
    if not event.is_directory:  # 文件发生变化
        try:
            log.debug("【SYNC】" + text + "了文件: %s " % event_path)
            # 文件名
            name = os.path.basename(event_path)
            # 目的目录的子文件不处理
            for tpath in SYNC_DIR_CONFIG.values():
                if tpath:
                    if tpath in event_path:
                        return
            if not name:
                return
            # 以.开头的隐藏文件不处理
            if name.startswith("."):
                return
            # 判断是不是媒体文件
            ext = os.path.splitext(name)[-1]
            if ext not in RMT_MEDIAEXT:
                return
            # 判断是否处理过了
            need_handler_flag = False
            try:
                lock.acquire()
                if event_path not in FINISHED_JOBS:
                    FINISHED_JOBS.append(event_path)
                    need_handler_flag = True
            finally:
                lock.release()

            if not need_handler_flag:
                log.debug("【SYNC】文件已处理过：" + event_path)
                return

            log.info("【SYNC】开始处理：" + event_path)
            # 找到是哪个监控目录下的
            parent_dir = event_path
            for m_path in SYNC_DIR_CONFIG.keys():
                if m_path in event_path:
                    parent_dir = m_path

            # 查找目的目录
            target_dir = SYNC_DIR_CONFIG.get(parent_dir)
            if not transfer_media(in_from="目录监控", in_name=name, in_path=event_path, target_dir=target_dir):
                log.error("【SYNC】" + event_path + "处理失败！")
            else:
                log.info("【SYNC】" + event_path + "处理成功！")

        except Exception as e:
            log.error("【SYNC】发生错误：" + str(e))


# 监听文件夹
class FileMonitorHandler(FileSystemEventHandler):
    def __init__(self, monpath, **kwargs):
        super(FileMonitorHandler, self).__init__(**kwargs)
        # 监控目录 目录下面以device_id为目录存放各自的图片
        self._watch_path = monpath

    # 重写文件创建函数，文件创建都会触发文件夹变化
    def on_created(self, event):
        file_change_handler(event, "创建", event.src_path)

    def on_moved(self, event):
        file_change_handler(event, "移动", event.dest_path)

    def on_modified(self, event):
        file_change_handler(event, "修改", event.src_path)


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
                            transfer_media(in_from="目录监控", in_name=file_name, in_path=file_path)
                    except Exception as err:
                        log.error("【SYNC】发生错误：" + str(err))


if __name__ == "__main__":
    sync_all()
