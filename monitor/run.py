import log
from monitor.media_sync import Sync
from utils.functions import INSTANCES


def run_monitor():
    try:
        Sync()
    except Exception as err:
        log.error("【RUN】启动monitor失败：%s" % str(err))


def stop_monitor():
    try:
        for instance in INSTANCES:
            if instance.__dict__.get("__module__") == "monitor.media_sync":
                instance().stop_service()
                break
    except Exception as err:
        log.error("【RUN】停止monitor失败：%s" % str(err))
