import log
from service.scheduler import Scheduler
from service.sync import Sync


def run_scheduler():
    """
    启动定时服务
    """
    try:
        Scheduler().run_service()
    except Exception as err:
        log.error("【RUN】启动scheduler失败：%s" % str(err))


def stop_scheduler():
    """
    停止定时服务
    """
    try:
        Scheduler().stop_service()
    except Exception as err:
        log.debug("【RUN】停止scheduler失败：%s" % str(err))


def restart_scheduler():
    """
    重启定时服务
    """
    stop_scheduler()
    run_scheduler()


def run_monitor():
    """
    启动监控
    """
    try:
        Sync().run_service()
    except Exception as err:
        log.error("【RUN】启动monitor失败：%s" % str(err))


def stop_monitor():
    """
    停止监控
    """
    try:
        Sync().stop_service()
    except Exception as err:
        log.error("【RUN】停止monitor失败：%s" % str(err))


def restart_monitor():
    """
    重启监控
    """
    stop_monitor()
    run_monitor()
