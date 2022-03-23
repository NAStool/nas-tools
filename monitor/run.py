import atexit
import signal
import sys
import log
from monitor.media_sync import Sync


def run_monitor():
    try:

        # 目录监控服务
        sync = Sync()
        sync.run_service()

        # 退出事件监听
        @atexit.register
        def atexit_fun():
            sync.stop_service()

        def signal_fun(signum, frame):
            sys.exit()

        signal.signal(signal.SIGTERM, signal_fun)
        signal.signal(signal.SIGINT, signal_fun)

    except Exception as err:
        log.error("【RUN】启动monitor失败：%s" % str(err))
