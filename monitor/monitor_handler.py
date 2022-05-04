from watchdog.events import FileSystemEventHandler


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
