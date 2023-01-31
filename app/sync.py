import os
import threading
import traceback

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

import log
from app.conf import ModuleConf
from app.helper import DbHelper
from config import RMT_MEDIAEXT, Config
from app.filetransfer import FileTransfer
from app.utils.commons import singleton
from app.utils import PathUtils, ExceptionUtils
from app.utils.types import SyncType, OsType

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

    """
    def on_modified(self, event):
        self.sync.file_change_handler(event, "修改", event.src_path)
    """


@singleton
class Sync(object):
    filetransfer = None
    dbhelper = None

    sync_dir_config = {}
    _observer = []
    _sync_paths = []
    _sync_sys = OsType.LINUX
    _synced_files = []
    _need_sync_paths = {}

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()
        self.filetransfer = FileTransfer()
        sync = Config().get_config('sync')
        sync_paths = self.dbhelper.get_config_sync_paths()
        if sync and sync_paths:
            if sync.get('nas_sys') == "windows":
                self._sync_sys = OsType.WINDOWS
            self._sync_paths = sync_paths
            self.init_sync_dirs()

    def init_sync_dirs(self):
        """
        初始化监控文件配置
        """
        self.sync_dir_config = {}
        if self._sync_paths:
            for sync_item in self._sync_paths:
                if not sync_item:
                    continue
                # 启用标志
                enabled = True if sync_item.ENABLED else False
                # 仅硬链接标志
                only_link = False if sync_item.RENAME else True
                # 转移方式
                path_syncmode = ModuleConf.RMT_MODES.get(sync_item.MODE)
                # 源目录|目的目录|未知目录
                monpath = sync_item.SOURCE
                target_path = sync_item.DEST
                unknown_path = sync_item.UNKNOWN
                if target_path and unknown_path:
                    log.info("【Sync】读取到监控目录：%s，目的目录：%s，未识别目录：%s，转移方式：%s" % (
                        monpath, target_path, unknown_path, path_syncmode.value))
                elif target_path:
                    log.info(
                        "【Sync】读取到监控目录：%s，目的目录：%s，转移方式：%s" % (monpath, target_path, path_syncmode.value))
                else:
                    log.info("【Sync】读取到监控目录：%s，转移方式：%s" % (monpath, path_syncmode.value))
                if not enabled:
                    log.info("【Sync】%s 不进行监控和同步：手动关闭" % monpath)
                    continue
                if only_link:
                    log.info("【Sync】%s 不进行识别和重命名" % monpath)
                if target_path and not os.path.exists(target_path):
                    log.info("【Sync】目的目录不存在，正在创建：%s" % target_path)
                    os.makedirs(target_path)
                if unknown_path and not os.path.exists(unknown_path):
                    log.info("【Sync】未识别目录不存在，正在创建：%s" % unknown_path)
                    os.makedirs(unknown_path)
                # 登记关系
                if os.path.exists(monpath):
                    self.sync_dir_config[monpath] = {'target': target_path, 'unknown': unknown_path,
                                                     'onlylink': only_link, 'syncmod': path_syncmode}
                else:
                    log.error("【Sync】%s 目录不存在！" % monpath)

    def get_sync_dirs(self):
        """
        返回所有的同步监控目录
        """
        if not self.sync_dir_config:
            return []
        return [os.path.normpath(key) for key in self.sync_dir_config.keys()]

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
                log.debug("【Sync】文件%s：%s" % (text, event_path))
                # 判断是否处理过了
                need_handler_flag = False
                try:
                    lock.acquire()
                    if event_path not in self._synced_files:
                        self._synced_files.append(event_path)
                        need_handler_flag = True
                finally:
                    lock.release()
                if not need_handler_flag:
                    log.debug("【Sync】文件已处理过：%s" % event_path)
                    return
                # 不是监控目录下的文件不处理
                is_monitor_file = False
                for tpath in self.sync_dir_config.keys():
                    if PathUtils.is_path_in_path(tpath, event_path):
                        is_monitor_file = True
                        break
                if not is_monitor_file:
                    return
                # 目的目录的子文件不处理
                for tpath in self.sync_dir_config.values():
                    if not tpath:
                        continue
                    if PathUtils.is_path_in_path(tpath.get('target'), event_path):
                        return
                    if PathUtils.is_path_in_path(tpath.get('unknown'), event_path):
                        return
                # 媒体库目录及子目录不处理
                if self.filetransfer.is_target_dir_path(event_path):
                    return
                # 回收站及隐藏的文件不处理
                if PathUtils.is_invalid_path(event_path):
                    return
                # 上级目录
                from_dir = os.path.dirname(event_path)
                # 找到是哪个监控目录下的
                monitor_dir = event_path
                is_root_path = False
                for m_path in self.sync_dir_config.keys():
                    if PathUtils.is_path_in_path(m_path, event_path):
                        monitor_dir = m_path
                    if os.path.normpath(m_path) == os.path.normpath(from_dir):
                        is_root_path = True

                # 查找目的目录
                target_dirs = self.sync_dir_config.get(monitor_dir)
                target_path = target_dirs.get('target')
                unknown_path = target_dirs.get('unknown')
                onlylink = target_dirs.get('onlylink')
                sync_mode = target_dirs.get('syncmod')

                # 只做硬链接，不做识别重命名
                if onlylink:
                    if self.dbhelper.is_sync_in_history(event_path, target_path):
                        return
                    log.info("【Sync】开始同步 %s" % event_path)
                    ret, msg = self.filetransfer.link_sync_file(src_path=monitor_dir,
                                                                in_file=event_path,
                                                                target_dir=target_path,
                                                                sync_transfer_mode=sync_mode)
                    if ret != 0:
                        log.warn("【Sync】%s 同步失败，错误码：%s" % (event_path, ret))
                    elif not msg:
                        self.dbhelper.insert_sync_history(event_path, monitor_dir, target_path)
                        log.info("【Sync】%s 同步完成" % event_path)
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
                    # 监控根目录下的文件发生变化时直接发走
                    if is_root_path:
                        ret, ret_msg = self.filetransfer.transfer_media(in_from=SyncType.MON,
                                                                        in_path=event_path,
                                                                        target_dir=target_path,
                                                                        unknown_dir=unknown_path,
                                                                        rmt_mode=sync_mode)
                        if not ret:
                            log.warn("【Sync】%s 转移失败：%s" % (event_path, ret_msg))
                    else:
                        try:
                            lock.acquire()
                            if self._need_sync_paths.get(from_dir):
                                files = self._need_sync_paths[from_dir].get('files')
                                if not files:
                                    files = [event_path]
                                else:
                                    if event_path not in files:
                                        files.append(event_path)
                                    else:
                                        return
                                self._need_sync_paths[from_dir].update({'files': files})
                            else:
                                self._need_sync_paths[from_dir] = {'target': target_path,
                                                                   'unknown': unknown_path,
                                                                   'syncmod': sync_mode,
                                                                   'files': [event_path]}
                        finally:
                            lock.release()
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                log.error("【Sync】发生错误：%s - %s" % (str(e), traceback.format_exc()))

    def transfer_mon_files(self):
        """
        批量转移文件，由定时服务定期调用执行
        """
        try:
            lock.acquire()
            finished_paths = []
            for path in list(self._need_sync_paths):
                if not PathUtils.is_invalid_path(path) and os.path.exists(path):
                    log.info("【Sync】开始转移监控目录文件...")
                    target_info = self._need_sync_paths.get(path)
                    bluray_dir = PathUtils.get_bluray_dir(path)
                    if not bluray_dir:
                        src_path = path
                        files = target_info.get('files')
                    else:
                        src_path = bluray_dir
                        files = []
                    if src_path not in finished_paths:
                        finished_paths.append(src_path)
                    else:
                        continue
                    target_path = target_info.get('target')
                    unknown_path = target_info.get('unknown')
                    sync_mode = target_info.get('syncmod')
                    # 判断是否根目录
                    is_root_path = False
                    for m_path in self.sync_dir_config.keys():
                        if os.path.normpath(m_path) == os.path.normpath(src_path):
                            is_root_path = True
                    ret, ret_msg = self.filetransfer.transfer_media(in_from=SyncType.MON,
                                                                    in_path=src_path,
                                                                    files=files,
                                                                    target_dir=target_path,
                                                                    unknown_dir=unknown_path,
                                                                    rmt_mode=sync_mode,
                                                                    root_path=is_root_path)
                    if not ret:
                        log.warn("【Sync】%s转移失败：%s" % (path, ret_msg))
                self._need_sync_paths.pop(path)
        finally:
            lock.release()

    def run_service(self):
        """
        启动监控服务
        """
        self._observer = []
        for monpath in self.sync_dir_config.keys():
            if monpath and os.path.exists(monpath):
                try:
                    if self._sync_sys == OsType.WINDOWS:
                        # 考虑到windows的docker需要直接指定才能生效(修改配置文件为windows)
                        observer = PollingObserver(timeout=10)
                    else:
                        # 内部处理系统操作类型选择最优解
                        observer = Observer(timeout=10)
                    self._observer.append(observer)
                    observer.schedule(FileMonitorHandler(monpath, self), path=monpath, recursive=True)
                    observer.setDaemon(True)
                    observer.start()
                    log.info("%s 的监控服务启动" % monpath)
                except Exception as e:
                    ExceptionUtils.exception_traceback(e)
                    log.error("%s 启动目录监控失败：%s" % (monpath, str(e)))

    def stop_service(self):
        """
        关闭监控服务
        """
        if self._observer:
            for observer in self._observer:
                observer.stop()
        self._observer = []

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
            sync_mode = target_dirs.get('syncmod')
            # 只做硬链接，不做识别重命名
            if onlylink:
                for link_file in PathUtils.get_dir_files(monpath):
                    if self.dbhelper.is_sync_in_history(link_file, target_path):
                        continue
                    log.info("【Sync】开始同步 %s" % link_file)
                    ret, msg = self.filetransfer.link_sync_file(src_path=monpath,
                                                                in_file=link_file,
                                                                target_dir=target_path,
                                                                sync_transfer_mode=sync_mode)
                    if ret != 0:
                        log.warn("【Sync】%s 同步失败，错误码：%s" % (link_file, ret))
                    elif not msg:
                        self.dbhelper.insert_sync_history(link_file, monpath, target_path)
                        log.info("【Sync】%s 同步完成" % link_file)
            else:
                for path in PathUtils.get_dir_level1_medias(monpath, RMT_MEDIAEXT):
                    if PathUtils.is_invalid_path(path):
                        continue
                    ret, ret_msg = self.filetransfer.transfer_media(in_from=SyncType.MON,
                                                                    in_path=path,
                                                                    target_dir=target_path,
                                                                    unknown_dir=unknown_path,
                                                                    rmt_mode=sync_mode)
                    if not ret:
                        log.error("【Sync】%s 处理失败：%s" % (monpath, ret_msg))


def run_monitor():
    """
    启动监控
    """
    try:
        Sync().run_service()
    except Exception as err:
        ExceptionUtils.exception_traceback(err)
        log.error("启动目录同步服务失败：%s" % str(err))


def stop_monitor():
    """
    停止监控
    """
    try:
        Sync().stop_service()
    except Exception as err:
        ExceptionUtils.exception_traceback(err)
        log.error("停止目录同步服务失败：%s" % str(err))


def restart_monitor():
    """
    重启监控
    """
    stop_monitor()
    run_monitor()
