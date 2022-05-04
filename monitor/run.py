import log
from monitor.media_sync import Sync


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
