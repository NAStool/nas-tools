import os
import threading
import traceback

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

import log
from app.conf import ModuleConf
from app.filetransfer import FileTransfer
from app.helper import DbHelper
from app.utils import PathUtils, ExceptionUtils
from app.utils.commons import singleton
from app.utils.types import SyncType
from config import RMT_MEDIAEXT

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
    sync_paths_config = {}
    _observer = []
    _sync_paths = []
    _synced_files = []
    _need_sync_paths = {}

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()
        self.filetransfer = FileTransfer()
        sync_paths_config = {}
        self.sync_dir_config = {}
        for sync_item in self.dbhelper.get_config_sync_paths():
            if not sync_item:
                continue
            # ID
            sync_id = sync_item.ID
            # 启用标志
            enabled = True if sync_item.ENABLED else False
            # 仅硬链接标志
            only_link = False if sync_item.RENAME else True
            # 兼容模式
            compatibility = True if sync_item.COMPATIBILITY else False
            # 转移方式
            syncmode = sync_item.MODE
            syncmode_enum = ModuleConf.RMT_MODES.get(syncmode)
            # 源目录|目的目录|未知目录
            monpath = sync_item.SOURCE
            target_path = sync_item.DEST
            unknown_path = sync_item.UNKNOWN
            # 输出日志
            log_content1, log_content2 = "", ""
            if target_path:
                log_content1 += f"目的目录：{target_path}，"
            if unknown_path:
                log_content1 += f"未识别目录：{unknown_path}，"
            if not only_link:
                log_content2 += "，启用识别和重命名"
            if compatibility:
                log_content2 += "，启用兼容模式"
            log.info(f"【Sync】读取到监控目录：{monpath}，{log_content1}转移方式：{syncmode_enum.value}{log_content2}")
            if not enabled:
                log.info(f"【Sync】{monpath} 不进行监控和同步：手动关闭")

            if target_path and not os.path.exists(target_path):
                log.info(f"【Sync】目的目录不存在，正在创建：{target_path}")
                os.makedirs(target_path)
            if unknown_path and not os.path.exists(unknown_path):
                log.info(f"【Sync】未识别目录不存在，正在创建：{unknown_path}")
                os.makedirs(unknown_path)
            # 登记关系
            sync_paths_config[str(sync_id)] = {
                'id': sync_id,
                'from': monpath,
                'to': target_path or "",
                'unknown': unknown_path or "",
                'syncmod': sync_item.MODE,
                'syncmod_name': syncmode_enum.value,
                "compatibility": compatibility,
                'rename': not only_link,
                'enabled': enabled
            }
            if monpath and os.path.exists(monpath):
                if enabled:
                    self.sync_dir_config[monpath] = {
                        'id': sync_id,
                        'target': target_path,
                        'unknown': unknown_path,
                        'onlylink': only_link,
                        'syncmod': syncmode_enum,
                        'compatibility': compatibility
                    }
            else:
                log.error(f"【Sync】{monpath} 目录不存在！")
        # 目录同步配置按源目录排序
        sync_paths_config = sorted(sync_paths_config.items(), key=lambda x: x[1]["from"]) if sync_paths_config else {}
        sync_paths_config = dict(sync_paths_config)
        self.sync_paths_config = sync_paths_config
        # 启动监控服务
        self.run_service()

    @property
    def sync_dirs(self):
        """
        所有的同步监控目录
        """
        if not self.sync_dir_config:
            return []
        return [os.path.normpath(key) for key in self.sync_dir_config.keys()]

    def get_sync_path_conf(self, sid=None):
        """
        获取目录同步配置
        """
        if sid:
            return self.sync_paths_config.get(str(sid)) or {}
        return self.sync_paths_config

    def check_source(self, source=None, sid=None):
        """
        检查关闭其他源目录相同或为父目录或为子目录的同步目录
        """
        if source:
            check_monpath = source
        elif sid:
            check_monpath = self.get_sync_path_conf(sid).get("from")
        else:
            return
        check_monpath = os.path.normpath(check_monpath)
        for sid, config in self.sync_paths_config.items():
            monpath = os.path.normpath(config.get("from"))
            if check_monpath in monpath or monpath in check_monpath and config.get("enabled"):
                self.dbhelper.check_config_sync_paths(sid=sid, enabled=0)

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
                    log.debug(f"【Sync】{event_path} 不在监控目录下，不处理 ...")
                    return
                # 目的目录的子文件不处理
                for tpath in self.sync_dir_config.values():
                    if not tpath:
                        continue
                    if PathUtils.is_path_in_path(tpath.get('target'), event_path):
                        log.error(f"【Sync】{event_path} -> {tpath.get('target')} 目的目录存在嵌套，无法同步！")
                        return
                    if PathUtils.is_path_in_path(tpath.get('unknown'), event_path):
                        log.error(f"【Sync】{event_path} -> {tpath.get('unknown')} 未识别目录存在嵌套，无法同步！")
                        return
                # 媒体库目录及子目录不处理
                if self.filetransfer.is_target_dir_path(event_path):
                    log.error(f"【Sync】{event_path} 是媒体库子目录，无法同步！")
                    return
                # 回收站及隐藏的文件不处理
                if PathUtils.is_invalid_path(event_path):
                    log.debug(f"【Sync】{event_path} 是回收站或隐藏的文件，不处理 ...")
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
        self.stop_service()
        for monpath, config in self.sync_dir_config.items():
            try:
                if config.get("compatibility"):
                    # 兼容模式，目录同步性能降低且NAS不能休眠，但可以兼容挂载的远程共享目录如SMB
                    observer = PollingObserver(timeout=10)
                else:
                    # 内部处理系统操作类型选择最优解
                    observer = Observer(timeout=10)
                self._observer.append(observer)
                observer.schedule(FileMonitorHandler(monpath, self), path=monpath, recursive=True)
                observer.daemon = True
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
                observer.join()
        self._observer = []

    def transfer_all_sync(self, sid=None):
        """
        全量转移Sync目录下的文件，WEB界面点击目录同步时获发
        """
        for monpath, target_dirs in self.sync_dir_config.items():
            if not monpath:
                continue
            if sid and sid != target_dirs.get('id'):
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
