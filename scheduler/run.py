import log
from scheduler.scheduler import Scheduler


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
