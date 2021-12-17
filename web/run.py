import atexit
import signal
import sys

import log
from functions import get_host_name
from message.send import sendmsg
from scheduler.sensors import get_temperature
from web.main import create_app


def run_webhook():
    try:
        app = create_app()

        @atexit.register
        def atexit_fun():
            app.stop()

        def signal_fun(signum, frame):
            log.info("【RUN】webhook捕捉到信号：" + str(signum) + "，开始退出...")
            sendmsg("【NASTOOL】" + get_host_name() + "正在关闭！", "当前温度：" + str(get_temperature()))
            sys.exit()

        signal.signal(signal.SIGTERM, signal_fun)
        signal.signal(signal.SIGINT, signal_fun)

        app.run(
            host='0.0.0.0',
            port=3000,
            debug=False,
            use_reloader=False
        )
    except Exception as err:
        log.error("【RUN】启动web服务失败：" + str(err))
        sendmsg("【NASTOOL】启动web服务失败！", str(err))
