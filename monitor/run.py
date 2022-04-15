import threading

import log
from monitor.media_sync import Sync


def run_monitor():
    try:
        monitor = threading.Thread(target=Sync().run_service)
        monitor.setDaemon(False)
        monitor.start()
    except Exception as err:
        log.error("【RUN】启动monitor失败：%s" % str(err))


def stop_monitor():
    try:
        Sync().stop_service()
    except Exception as err:
        log.error("【RUN】停止monitor失败：%s" % str(err))


def restart_monitor():
    stop_monitor()
    run_monitor()
