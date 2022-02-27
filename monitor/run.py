import atexit
import signal
import sys
import log
from message.send import Message
from monitor.media_sync import Sync
from monitor.movie_trailer import Trailer

trailer = Trailer()
sync = Sync()


def run_monitor():
    try:
        # 电影监控下载预告片
        trailer.run_service()
        # 目录监控服务
        sync.run_service()

        # 退出事件监听
        @atexit.register
        def atexit_fun():
            trailer.stop_service()
            sync.stop_service()

        def signal_fun(signum, frame):
            sys.exit()

        signal.signal(signal.SIGTERM, signal_fun)
        signal.signal(signal.SIGINT, signal_fun)

    except Exception as err:
        log.error("【RUN】启动monitor失败：" + str(err))
        Message().sendmsg("【NASTOOL】启动monitor失败！", str(err))
