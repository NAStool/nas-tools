import os
from time import sleep

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from rmt.qbittorrent import transfer_directory

import log
import settings

# 全局设置
resiliosync_flag = settings.get("monitor.resiliosync_flag") == "ON" or False
monpath = settings.get("monitor.resiliosync_monpath")

logger = log.Logger("monitor").logger
handler_files = []


# 处理文件夹
def dir_change_handler(event, text):
    event_path = event.src_path
    if event.is_directory:  # 文件改变都会触发文件夹变化
        try:
            logger.info(text + "了文件夹: %s " % event_path)
            if event_path == monpath:
                return
            if event_path.find(".sync") != -1:
                return
            name = os.path.basename(event_path)
            logger.info("名称：" + name)
            if event_path not in handler_files:
                handler_files.append(event_path)
                # 等待10秒，让文件移完
                sleep(10)
                logger.info("开始处理：" + event_path)
                if not transfer_directory(name, event_path, "", "", False, "ResilioSync", False):
                    handler_files.remove(event_path)
                    logger.error(event_path + "处理失败！")
                else:
                    logger.info(event_path + "处理成功！")
            else:
                logger.error("已处理过：" + name)
        except Exception as e:
            logger.error("发生错误：" + str(e))


# 监听文件夹
class FileMonitorHandler(FileSystemEventHandler):
    def __init__(self, **kwargs):
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


def run_resilosync():
    if os.path.exists(monpath) and resiliosync_flag:
        event_handler = FileMonitorHandler()
        observer = Observer()
        observer.schedule(event_handler, path=monpath, recursive=True)  # recursive递归的
        observer.setDaemon(False)
        observer.start()
        logger.info("monitor.resilosync启动...")
    else:
        logger.error(monpath + "目录不存在！")


if __name__ == "__main__":
    # 全量转移
    logger.info("开始全量转移...")
    for dir in os.listdir(monpath):
        file_path = os.path.join(monpath, dir)
        if dir.find(".sync") == -1:
            file_name = os.path.basename(file_path)
            logger.info("开始处理：" + file_path)
            try:
                if file_name not in handler_files:
                    handler_files.append(file_name)
                    transfer_directory(file_name, file_path, "", "", False, "ResilioSync", False)
            except Exception as err:
                logger.error("发生错误：" + str(err))
