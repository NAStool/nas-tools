import signal
import sys
import log
from web.main import FlaskApp


def run_web():
    try:
        app = FlaskApp()

        def signal_fun(signum, frame):
            log.info("【RUN】web捕捉到信号：" + str(signum) + "，开始退出...")
            sys.exit()

        signal.signal(signal.SIGTERM, signal_fun)
        signal.signal(signal.SIGINT, signal_fun)

        app.run_service()

    except Exception as err:
        log.error("【RUN】启动web服务失败：" + str(err))
