import os
from time import sleep

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from config import get_config
from rmt.media import transfer_directory

import log

# 全局设置
handler_files = []


# 处理文件夹
def dir_change_handler(event, text):
    config = get_config()
    monpaths = config['media'].get('sync_path')
    event_path = event.src_path
    if event.is_directory:  # 文件改变都会触发文件夹变化
        try:
            log.debug("【SYNC】" + text + "了文件夹: %s " % event_path)
            if event_path in monpaths:
                return
            if event_path.find(".sync") != -1:
                return
            name = os.path.basename(event_path)
            if event_path not in handler_files:
                handler_files.append(event_path)
                # 等待10秒，让文件移完
                sleep(10)
                log.info("【SYNC】开始处理：" + event_path + "，名称：" + name)
                if not transfer_directory(in_from="Sync", in_name=name, in_path=event_path, noti_flag=False):
                    handler_files.remove(event_path)
                    log.error("【SYNC】" + event_path + "处理失败！")
                else:
                    log.info("【SYNC】" + event_path + "处理成功！")
            else:
                log.debug("【SYNC】已处理过：" + name)
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
                            transfer_directory(in_from="SYNC", in_name=file_name, in_path=file_path, noti_flag=False)
                    except Exception as err:
                        log.error("【SYNC】发生错误：" + str(err))


if __name__ == "__main__":
    sync_all()
