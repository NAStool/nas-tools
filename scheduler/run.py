import threading

import log
from scheduler.scheduler import Scheduler


def run_scheduler():
    try:
        scheduler = threading.Thread(target=Scheduler().run_service)
        scheduler.setDaemon(False)
        scheduler.start()
    except Exception as err:
        log.error("【RUN】启动scheduler失败：%s" % str(err))


def stop_scheduler():
    try:
        Scheduler().stop_service()
    except Exception as err:
        log.debug("【RUN】停止scheduler失败：%s" % str(err))


def restart_scheduler():
    stop_scheduler()
    run_scheduler()
