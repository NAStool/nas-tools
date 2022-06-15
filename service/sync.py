import os
import threading
import traceback

from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from config import RMT_MEDIAEXT, Config
import log
from rmt.filetransfer import FileTransfer
from utils.functions import singleton, is_invalid_path, is_path_in_path, is_bluray_dir, get_dir_level1_medias, \
    get_dir_files
from utils.sqls import is_transfer_in_blacklist, insert_sync_history, is_sync_in_history
from utils.types import SyncType, OsType
from watchdog.events import FileSystemEventHandler

lock = threading.Lock()


class FileMonitorHandler(FileSystemEventHandler):
    """
    目录监控响应类
    """
    def __init__(self, monpath, sync, **kwargs):
        super(FileMonitorHandler, self).__init__(**kwargs)
        self._watch_path = monpath
        self.sync = sync

    def on_created(self, event):
        self.sync.file_change_handler(event, "创建", event.src_path)

    def on_moved(self, event):
        self.sync.file_change_handler(event, "移动", event.dest_path)

    def on_modified(self, event):
        self.sync.file_change_handler(event, "修改", event.src_path)


@singleton
class Sync(object):
    filetransfer = None
    sync_dir_config = {}
    __observer = []
    __sync_path = None
    __sync_sys = OsType.LINUX
    __synced_files = []
    __need_sync_paths = {}

    def __init__(self):
        self.filetransfer = FileTransfer()
        self.init_config()

    def init_config(self):
        config = Config()
        sync = config.get_config('sync')
        if sync:
            if sync.get('nas_sys') == "windows":
                self.__sync_sys = OsType.WINDOWS
            self.__sync_path = sync.get('sync_path')
            self.init_sync_dirs()

    def init_sync_dirs(self):
        """
        初始化监控文件配置
        """
        self.sync_dir_config = {}
        if self.__sync_path:
            for sync_monpath in self.__sync_path:
                if not sync_monpath:
                    continue
                only_link = False
                enabled = True
                if sync_monpath.startswith('#'):
                    enabled = False
                    sync_monpath = sync_monpath[1:-1]
                if sync_monpath.startswith('['):
                    only_link = True
                    sync_monpath = sync_monpath[1:-1]
                monpaths = sync_monpath.split('|')
                if monpaths[0]:
                    monpath = os.path.normpath(monpaths[0])
                else:
                    continue
                if len(monpaths) > 1:
                    if monpaths[1]:
                        target_path = os.path.normpath(monpaths[1])
                    else:
                        target_path = None
                    if len(monpaths) > 2:
                        if monpaths[2]:
                            unknown_path = os.path.normpath(monpaths[2])
                        else:
                            unknown_path = None
                    else:
                        unknown_path = None
                    if target_path and unknown_path:
                        log.info("【SYNC】读取到监控目录：%s，目的目录：%s，未识别目录：%s" % (monpath, target_path, unknown_path))
                    elif target_path:
                        log.info("【SYNC】读取到监控目录：%s，目的目录：%s" % (monpath, target_path))
                    else:
                        log.info("【SYNC】读取到监控目录：%s" % monpath)
                    if not enabled:
                        log.info("【SYNC】%s 不进行监控和同步：手动关闭" % monpath)
                        continue
                    if only_link:
                        log.info("【SYNC】%s 不进行识别和重命名" % monpath)
                    if target_path and not os.path.exists(target_path):
                        log.info("【SYNC】目的目录不存在，正在创建：%s" % target_path)
                        os.makedirs(target_path)
                    if unknown_path and not os.path.exists(unknown_path):
                        log.info("【SYNC】未识别目录不存在，正在创建：%s" % unknown_path)
                        os.makedirs(unknown_path)
                else:
                    target_path = None
                    unknown_path = None
                    log.info("【SYNC】读取到监控目录：%s" % monpath)
                # 登记关系
                if os.path.exists(monpath):
                    self.sync_dir_config[monpath] = {'target': target_path, 'unknown': unknown_path,
                                                     'onlylink': only_link}
                else:
                    log.error("【SYNC】%s 目录不存在！" % monpath)

    def file_change_handler(self, event, text, event_path):
        """
        处理文件变化
        :param event: 事件
        :param text: 事件描述
        :param event_path: 事件文件路径
        """
        if not event.is_directory:
            # 文件发生变化
            try:
                if not os.path.exists(event_path):
                    return
                log.debug("【SYNC】文件%s：%s" % (text, event_path))
                # 判断是否处理过了
                need_handler_flag = False
                try:
                    lock.acquire()
                    if event_path not in self.__synced_files:
                        self.__synced_files.append(event_path)
                        need_handler_flag = True
                finally:
                    lock.release()
                if not need_handler_flag:
                    log.debug("【SYNC】文件已处理过：%s" % event_path)
                    return
                # 不是监控目录下的文件不处理
                is_monitor_file = False
                for tpath in self.sync_dir_config.keys():
                    if is_path_in_path(tpath, event_path):
                        is_monitor_file = True
                        break
                if not is_monitor_file:
                    return
                # 目的目录的子文件不处理
                for tpath in self.sync_dir_config.values():
                    if not tpath:
                        continue
                    if is_path_in_path(tpath.get('target'), event_path):
                        return
                    if is_path_in_path(tpath.get('unknown'), event_path):
                        return
                # 媒体库目录及子目录不处理
                if self.filetransfer.is_target_dir_path(event_path):
                    return
                # 回收站及隐藏的文件不处理
                if is_invalid_path(event_path):
                    return
                # 上级目录
                from_dir = os.path.dirname(event_path)
                # 找到是哪个监控目录下的
                monitor_dir = event_path
                is_root_path = False
                for m_path in self.sync_dir_config.keys():
                    if is_path_in_path(m_path, event_path):
                        monitor_dir = m_path
                    if m_path == from_dir:
                        is_root_path = True

                # 查找目的目录
                target_dirs = self.sync_dir_config.get(monitor_dir)
                target_path = target_dirs.get('target')
                unknown_path = target_dirs.get('unknown')
                onlylink = target_dirs.get('onlylink')

                # 只做硬链接，不做识别重命名
                if onlylink:
                    if is_sync_in_history(event_path, target_path):
                        return
                    log.info("【SYNC】开始同步 %s" % event_path)
                    ret = self.filetransfer.link_sync_files(in_from=SyncType.MON,
                                                            src_path=monitor_dir,
                                                            in_file=event_path,
                                                            target_dir=target_path)
                    if ret != 0:
                        log.warn("【SYNC】%s 同步失败，错误码：%s" % (event_path, ret))
                    else:
                        insert_sync_history(event_path, monitor_dir, target_path)
                        log.info("【SYNC】%s 同步完成" % event_path)
                # 识别转移
                else:
                    # 不是媒体文件不处理
                    name = os.path.basename(event_path)
                    if not name:
                        return
                    if name.lower() != "index.bdmv":
                        ext = os.path.splitext(name)[-1]
                        if ext.lower() not in RMT_MEDIAEXT:
                            return
                    # 黑名单不处理
                    if is_transfer_in_blacklist(from_dir):
                        return
                    # 监控根目录下的文件发生变化时直接发走
                    if is_root_path:
                        ret, ret_msg = self.filetransfer.transfer_media(in_from=SyncType.MON,
                                                                        in_path=event_path,
                                                                        target_dir=target_path,
                                                                        unknown_dir=unknown_path)
                        if not ret:
                            log.warn("【SYNC】%s 转移失败：%s" % (event_path, ret_msg))
                    else:
                        try:
                            lock.acquire()
                            if self.__need_sync_paths.get(from_dir):
                                files = self.__need_sync_paths[from_dir].get('files')
                                if not files:
                                    files = [event_path]
                                else:
                                    if event_path not in files:
                                        files.append(event_path)
                                    else:
                                        return
                                self.__need_sync_paths[from_dir].update({'files': files})
                            else:
                                self.__need_sync_paths[from_dir] = {'target': target_path, 'unknown': unknown_path,
                                                                    'files': [event_path]}
                        finally:
                            lock.release()
            except Exception as e:
                log.error("【SYNC】发生错误：%s - %s" % (str(e), traceback.format_exc()))

    def transfer_mon_files(self):
        """
        批量转移文件，由定时服务定期调用执行
        """
        try:
            lock.acquire()
            items = list(self.__need_sync_paths)
            for path in items:
                if is_invalid_path(path):
                    continue
                target_info = self.__need_sync_paths.get(path)
                if os.path.exists(path):
                    log.info("【SYNC】开始转移监控目录文件...")
                    if not is_bluray_dir(path):
                        files = target_info.get('files')
                    else:
                        path = os.path.dirname(path) if os.path.normpath(path).endswith("BDMV") else path
                        files = []
                    target_path = target_info.get('target')
                    unknown_path = target_info.get('unknown')
                    ret, ret_msg = self.filetransfer.transfer_media(in_from=SyncType.MON,
                                                                    in_path=path,
                                                                    files=files,
                                                                    target_dir=target_path,
                                                                    unknown_dir=unknown_path)
                    if not ret:
                        log.warn("【SYNC】%s转移失败：%s" % (path, ret_msg))
                self.__need_sync_paths.pop(path)
        finally:
            lock.release()

    def run_service(self):
        """
        启动监控服务
        """
        self.__observer = []
        for monpath in self.sync_dir_config.keys():
            if monpath and os.path.exists(monpath):
                try:
                    if self.__sync_sys == OsType.LINUX:
                        # linux
                        observer = Observer()
                    else:
                        # 其他
                        observer = PollingObserver()
                    self.__observer.append(observer)
                    observer.schedule(FileMonitorHandler(monpath, self), path=monpath, recursive=True)
                    observer.setDaemon(True)
                    observer.start()
                    log.info("【RUN】%s 的监控服务启动..." % monpath)
                except Exception as e:
                    log.error("【RUN】%s 启动目录监控失败：%s" % (monpath, str(e)))

    def stop_service(self):
        """
        关闭监控服务
        """
        if self.__observer:
            for observer in self.__observer:
                observer.stop()
        self.__observer = []

    def transfer_all_sync(self):
        """
        全量转移Sync目录下的文件，WEB界面点击目录同步时获发
        """
        for monpath, target_dirs in self.sync_dir_config.items():
            if not monpath:
                continue
            target_path = target_dirs.get('target')
            unknown_path = target_dirs.get('unknown')
            onlylink = target_dirs.get('onlylink')
            # 只做硬链接，不做识别重命名
            if onlylink:
                for link_file in get_dir_files(monpath):
                    if is_sync_in_history(link_file, target_path):
                        continue
                    log.info("【SYNC】开始同步 %s" % link_file)
                    ret = self.filetransfer.link_sync_files(in_from=SyncType.MON,
                                                            src_path=monpath,
                                                            in_file=link_file,
                                                            target_dir=target_path)
                    if ret != 0:
                        log.warn("【SYNC】%s 同步失败，错误码：%s" % (link_file, ret))
                    else:
                        insert_sync_history(link_file, monpath, target_path)
                        log.info("【SYNC】%s 同步完成" % link_file)
            else:
                for path in get_dir_level1_medias(monpath, RMT_MEDIAEXT):
                    if is_invalid_path(path):
                        continue
                    if is_transfer_in_blacklist(path):
                        continue
                    ret, ret_msg = self.filetransfer.transfer_media(in_from=SyncType.MON,
                                                                    in_path=path,
                                                                    target_dir=target_path,
                                                                    unknown_dir=unknown_path)
                    if not ret:
                        log.error("【SYNC】%s 处理失败：%s" % (monpath, ret_msg))
