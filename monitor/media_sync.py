import os
import threading
from datetime import datetime

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from config import RMT_MEDIAEXT, SYNC_DIR_CONFIG, Config
import log
from rmt.filetransfer import FileTransfer
from utils.types import SyncType

lock = threading.Lock()
# 已经同步过的文件
SYNCED_FILES = []
# 需要同步的文件清单
NEED_SYNC_PATHS = {}
# 上一次同步的时间
LAST_SYNC_TIME = datetime.now()


class Sync:
    filetransfer = None
    __observer = []
    __sync_path = None
    __sync_sys = "Linux"
    __config = None

    def __init__(self):
        self.filetransfer = FileTransfer()
        self.__config = Config()
        app = self.__config.get_config('app')
        if app:
            self.__sync_sys = app.get('nas_sys', "Linux")
        sync = self.__config.get_config('sync')
        if sync:
            self.__sync_path = sync.get('sync_path')

    # 处理文件变化
    def file_change_handler(self, event, text, event_path):
        global SYNCED_FILES
        if not event.is_directory:  # 文件发生变化
            try:
                log.debug("【SYNC】%s了文件: %s " % (text, event_path))
                # 目的目录的子文件不处理
                for tpath in SYNC_DIR_CONFIG.values():
                    if tpath:
                        if tpath in event_path:
                            return
                # 回收站及隐藏的文件不处理
                if event_path.find('/@Recycle/') != -1 or event_path.find('/#recycle/') != -1 or event_path.find('/.') != -1:
                    return False
                # 文件名
                name = os.path.basename(event_path)
                if not name:
                    return
                # 判断是不是媒体文件
                ext = os.path.splitext(name)[-1]
                if ext not in RMT_MEDIAEXT:
                    return
                # 判断是否处理过了
                need_handler_flag = False
                try:
                    lock.acquire()
                    if event_path not in SYNCED_FILES:
                        SYNCED_FILES.append(event_path)
                        need_handler_flag = True
                finally:
                    lock.release()

                if not need_handler_flag:
                    log.debug("【SYNC】文件已处理过：%s" % event_path)
                    return

                log.info("【SYNC】开始处理：%s" % event_path)
                # 找到是哪个监控目录下的
                parent_dir = event_path
                for m_path in SYNC_DIR_CONFIG.keys():
                    if m_path in event_path:
                        parent_dir = m_path

                # 查找目的目录
                target_dir = SYNC_DIR_CONFIG.get(parent_dir)
                # TODO 文件变化一次转移一次并触发通知，导致PT下载剧集时，集中推送大量通知
                if not self.filetransfer.transfer_media(in_from=SyncType.MON, in_path=event_path, target_dir=target_dir):
                    log.error("【SYNC】%s 处理失败！" % event_path)
                else:
                    log.info("【SYNC】%s 处理成功！" % event_path)

            except Exception as e:
                log.error("【SYNC】发生错误：%s" % str(e))
        else:
            # TODO 考虑是否可以通过监控文件夹的变化统一处理文件变化，以达到同一个目录下的文件集中通知的目上的
            # 文件变化时上级文件夹也会变化
            # 当文件变化数等于目录下的总文件数时，批量转移一次
            # 当目录变化改变时转移一次
            # 其他情况，间隔超过5分钟没有变化，但仍有未转移的文件时，转移一次
            # 好复杂，还没想好怎么做...
            pass

    # 启动进程
    def run_service(self):
        # Sync监控转移
        if self.__sync_path:
            for sync_monpath in self.__sync_path:
                # 目录是两段式，需要把配对关系存起来
                if sync_monpath.find('|') != -1:
                    # 源目录|目的目录，这个格式的目的目录在源目录同级建立
                    monpath = sync_monpath.split("|")[0]
                    target_path = sync_monpath.split("|")[1]
                    if target_path:
                        log.info("【SYNC】读取到监控目录：%s，目的目录：%s" % (monpath, target_path))
                        if not os.path.exists(target_path):
                            log.info("【SYNC】目的目录不存在，正在创建：%s" % target_path)
                            os.makedirs(target_path)
                        # 去掉末尾的/
                        if monpath.endswith('/'):
                            monpath = monpath[0:-1]
                        SYNC_DIR_CONFIG[monpath] = target_path
                else:
                    monpath = sync_monpath
                    SYNC_DIR_CONFIG[monpath] = None
                    log.info("【SYNC】读取监控目录：%s" % monpath)

                if os.path.exists(monpath):
                    if self.__sync_sys == "Linux":
                        # linux
                        observer = Observer()
                    else:
                        # 其他
                        observer = PollingObserver()
                    self.__observer.append(observer)

                    observer.schedule(FileMonitorHandler(monpath), path=monpath, recursive=True)
                    observer.setDaemon(False)
                    observer.start()
                    log.info("【RUN】%s 的monitor.media_sync启动..." % monpath)
                else:
                    log.error("【SYNC】%s 目录不存在！" % sync_monpath)

    # 关闭服务
    def stop_service(self):
        if self.__observer:
            for observer in self.__observer:
                observer.stop()


# 监听文件夹
class FileMonitorHandler(FileSystemEventHandler):
    sync = None

    def __init__(self, monpath, **kwargs):
        super(FileMonitorHandler, self).__init__(**kwargs)
        # 监控目录 目录下面以device_id为目录存放各自的图片
        self._watch_path = monpath
        self.sync = Sync()

    # 重写文件创建函数，文件创建都会触发文件夹变化
    def on_created(self, event):
        self.sync.file_change_handler(event, "创建", event.src_path)

    def on_moved(self, event):
        self.sync.file_change_handler(event, "移动", event.dest_path)

    def on_modified(self, event):
        self.sync.file_change_handler(event, "修改", event.src_path)
