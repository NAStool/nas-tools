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

    _sync_path_confs = {}
    _monitor_sync_path_ids = []
    _observer = []
    _sync_paths = []
    _synced_files = []
    _need_sync_paths = {}

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()
        self.filetransfer = FileTransfer()
        self._sync_path_confs = {}
        self._monitor_sync_path_ids = []
        for sync_conf in self.dbhelper.get_config_sync_paths():
            if not sync_conf:
                continue
            # ID
            sid = sync_conf.ID
            # 启用标志
            enabled = True if sync_conf.ENABLED else False
            # 仅硬链接标志
            rename = True if sync_conf.RENAME else False
            # 兼容模式
            compatibility = True if sync_conf.COMPATIBILITY else False
            # 转移方式
            syncmode = sync_conf.MODE
            syncmode_enum = ModuleConf.RMT_MODES.get(syncmode)
            # 源目录|目的目录|未知目录
            monpath = sync_conf.SOURCE
            target_path = sync_conf.DEST
            unknown_path = sync_conf.UNKNOWN
            # 输出日志
            log_content1, log_content2 = "", ""
            if target_path:
                log_content1 += f"目的目录：{target_path}，"
            if unknown_path:
                log_content1 += f"未识别目录：{unknown_path}，"
            if rename:
                log_content2 += "，启用识别和重命名"
            if compatibility:
                log_content2 += "，启用兼容模式"
            log.info(f"【Sync】读取到监控目录：{monpath}，{log_content1}转移方式：{syncmode_enum.value}{log_content2}")
            if not enabled:
                log.info(f"【Sync】{monpath} 不进行监控和同步：手动关闭")
            if target_path and not os.path.exists(target_path) and syncmode_enum not in ModuleConf.REMOTE_RMT_MODES:
                log.info(f"【Sync】目的目录不存在，正在创建：{target_path}")
                os.makedirs(target_path)
            if unknown_path and not os.path.exists(unknown_path):
                log.info(f"【Sync】未识别目录不存在，正在创建：{unknown_path}")
                os.makedirs(unknown_path)
            # 登记关系
            self._sync_path_confs[str(sid)] = {
                'id': sid,
                'from': monpath,
                'to': target_path or "",
                'unknown': unknown_path or "",
                'syncmod': syncmode,
                'syncmod_name': syncmode_enum.value,
                "compatibility": compatibility,
                'rename': rename,
                'enabled': enabled
            }
            if monpath and os.path.exists(monpath):
                if enabled:
                    self._monitor_sync_path_ids.append(sid)
            else:
                log.error(f"【Sync】{monpath} 目录不存在！")
        # 启动监控服务
        self.run_service()

    @property
    def monitor_sync_path_ids(self):
        """
        监控目录同步配置id
        """
        return self._monitor_sync_path_ids

    def get_sync_path_conf(self, sid=None):
        """
        获取目录同步配置
        """
        if sid:
            return self._sync_path_confs.get(str(sid)) or {}
        return self._sync_path_confs

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
        for sid, config in self._sync_path_confs.items():
            monpath = os.path.normpath(config.get("from"))
            if PathUtils.is_path_in_path(monpath, check_monpath) \
                    or PathUtils.is_path_in_path(check_monpath, monpath) \
                    and config.get("enabled"):
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

                # 上级目录
                from_dir = os.path.dirname(event_path)
                # 判断是否在监控目录下
                sync_id = None
                is_root_path = False
                for sid in self._monitor_sync_path_ids:
                    sync_path_conf = self.get_sync_path_conf(sid)
                    mon_path = sync_path_conf.get('from')
                    target_path = sync_path_conf.get('to')
                    unknown_path = sync_path_conf.get('unknown')
                    # 判断是否在监控目录下
                    if PathUtils.is_path_in_path(mon_path, event_path):
                        if os.path.normpath(mon_path) == os.path.normpath(from_dir):
                            is_root_path = True
                        sync_id = sid
                    # 目的目录下不处理
                    if PathUtils.is_path_in_path(target_path, event_path):
                        log.error(f"【Sync】{event_path} -> {target_path} 目的目录存在嵌套，无法同步！")
                        return
                    # 未识别目录下不处理
                    if PathUtils.is_path_in_path(unknown_path, event_path):
                        log.error(f"【Sync】{event_path} -> {unknown_path} 未识别目录存在嵌套，无法同步！")
                        return
                # 不在监控目录下，不处理
                if not sync_id:
                    log.debug(f"【Sync】{event_path} 不在监控目录下，不处理 ...")
                    return
                # 媒体库目录及子目录不处理
                if self.filetransfer.is_target_dir_path(event_path):
                    log.error(f"【Sync】{event_path} 是媒体库子目录，无法同步！")
                    return
                # 回收站及隐藏的文件不处理
                if PathUtils.is_invalid_path(event_path):
                    log.debug(f"【Sync】{event_path} 是回收站或隐藏的文件，不处理 ...")
                    return

                # 应用的同步配置
                sync_path_conf = self.get_sync_path_conf(sync_id)
                mon_path = sync_path_conf.get('from')
                target_path = sync_path_conf.get('to')
                unknown_path = sync_path_conf.get('unknown')
                rename = sync_path_conf.get('rename')
                sync_mode = ModuleConf.RMT_MODES.get(sync_path_conf.get('syncmod'))

                # 不做识别重命名
                if not rename:
                    self.__link(event_path, mon_path, target_path, sync_mode)
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
                    for sid in self._monitor_sync_path_ids:
                        if os.path.normpath(self.get_sync_path_conf(sid).get("from")) == os.path.normpath(src_path):
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
        for sid in self._monitor_sync_path_ids:
            sync_path_conf = self.get_sync_path_conf(sid)
            if not sync_path_conf:
                continue
            mon_path = sync_path_conf.get("from")
            try:
                if sync_path_conf.get("compatibility"):
                    # 兼容模式，目录同步性能降低且NAS不能休眠，但可以兼容挂载的远程共享目录如SMB
                    observer = PollingObserver(timeout=10)
                else:
                    # 内部处理系统操作类型选择最优解
                    observer = Observer(timeout=10)
                self._observer.append(observer)
                observer.schedule(FileMonitorHandler(mon_path, self), path=mon_path, recursive=True)
                observer.daemon = True
                observer.start()
                log.info(f"{mon_path} 的监控服务启动")
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                err_msg = str(e)
                if "inotify" in err_msg and "reached" in err_msg:
                    log.warn(f"目录监控服务启动出现异常：{err_msg}，请在宿主机上（不是docker容器内）执行以下命令并重启："
                             + """
                             echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
                             echo fs.inotify.max_user_instances=524288 | sudo tee -a /etc/sysctl.conf
                             sudo sysctl -p
                             """)
                else:
                    log.error(f"{mon_path} 启动目录监控失败：{err_msg}")

    def stop_service(self):
        """
        关闭监控服务
        """
        if self._observer:
            for observer in self._observer:
                try:
                    observer.stop()
                    observer.join()
                except Exception as e:
                    print(str(e))
        self._observer = []

    def transfer_sync(self, sid=None):
        """
        全量转移Sync目录下的文件，WEB界面点击目录同步时获发
        """
        if not sid:
            sids = self._monitor_sync_path_ids
        elif isinstance(sid, list):
            sids = sid
        else:
            sids = [sid]
        for sid in sids:
            sync_path_conf = self.get_sync_path_conf(sid)
            mon_path = sync_path_conf.get("from")
            target_path = sync_path_conf.get("to")
            unknown_path = sync_path_conf.get("unknown")
            rename = sync_path_conf.get("rename")
            sync_mode = ModuleConf.RMT_MODES.get(sync_path_conf.get("syncmod"))
            # 不做识别重命名
            if not rename:
                for link_file in PathUtils.get_dir_files(mon_path):
                    self.__link(link_file, mon_path, target_path, sync_mode)
            else:
                for path in PathUtils.get_dir_level1_medias(mon_path, RMT_MEDIAEXT):
                    if PathUtils.is_invalid_path(path):
                        continue
                    ret, ret_msg = self.filetransfer.transfer_media(in_from=SyncType.MON,
                                                                    in_path=path,
                                                                    target_dir=target_path,
                                                                    unknown_dir=unknown_path,
                                                                    rmt_mode=sync_mode)
                    if not ret:
                        log.error("【Sync】%s 处理失败：%s" % (mon_path, ret_msg))

    def __link(self, event_path, mon_path, target_path, sync_mode):
        """
        只转移不识别
        """
        if self.dbhelper.is_sync_in_history(event_path, target_path):
            return
        log.info("【Sync】开始同步 %s" % event_path)
        try:
            ret, msg = self.filetransfer.link_sync_file(src_path=mon_path,
                                                        in_file=event_path,
                                                        target_dir=target_path,
                                                        sync_transfer_mode=sync_mode)
            if ret != 0:
                log.warn("【Sync】%s 同步失败，错误码：%s" % (event_path, ret))
            elif not msg:
                self.dbhelper.insert_sync_history(event_path, mon_path, target_path)
                log.info("【Sync】%s 同步完成" % event_path)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            log.error("【Sync】%s 同步失败：%s" % (event_path, str(err)))

    def delete_sync_path(self, sid):
        """
        删除配置的同步目录
        """
        ret = self.dbhelper.delete_config_sync_path(sid=sid)
        self.init_config()
        return ret

    def insert_sync_path(self, source, dest, unknown, mode, compatibility, rename, enabled, note=None):
        """
        添加同步目录配置
        """
        ret = self.dbhelper.insert_config_sync_path(source=source,
                                                    dest=dest,
                                                    unknown=unknown,
                                                    mode=mode,
                                                    compatibility=compatibility,
                                                    rename=rename,
                                                    enabled=enabled,
                                                    note=note)
        self.init_config()
        return ret

    def check_sync_paths(self, sid=None, compatibility=None, rename=None, enabled=None):
        """
        检查配置的同步目录
        """
        ret = self.dbhelper.check_config_sync_paths(
            sid=sid,
            compatibility=compatibility,
            rename=rename,
            enabled=enabled
        )
        self.init_config()
        return ret
