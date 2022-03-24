import log
from monitor.media_sync import Sync


def run_monitor():
    try:
        # 目录监控服务
        Sync().run_service()
    except Exception as err:
        log.error("【RUN】启动monitor失败：%s" % str(err))
