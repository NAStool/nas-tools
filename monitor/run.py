import log
from monitor.media_sync import Sync


def run_monitor():
    try:
        Sync()
    except Exception as err:
        log.error("【RUN】启动monitor失败：%s" % str(err))


def stop_monitor():
    try:
        Sync().stop_service()
    except Exception as err:
        log.error("【RUN】停止monitor失败：%s" % str(err))
