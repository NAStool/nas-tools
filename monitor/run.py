import atexit
import os
import signal
import sys

import log
import settings
from message.send import sendmsg
from monitor.movie_trailer import create_movie_trailer
from monitor.movie_trailer import FileMonitorHandler as MovieTrailerHandler
from monitor.resiliosync import create_resilosync
from monitor.resiliosync import FileMonitorHandler as ResilioSyncHandler


def run_monitor():
    try:
        # 电影监控下载预告片
        movie_run = False
        movie_monpath = settings.get("monitor.movie_monpath")
        movie_flag = settings.get("monitor.movie_flag") == "ON" or False
        if movie_flag:
            if os.path.exists(movie_monpath):
                movie_trailer = create_movie_trailer()
                movie_trailer.schedule(MovieTrailerHandler, path=movie_monpath, recursive=True)  # recursive递归的
                movie_trailer.setDaemon(False)
                movie_trailer.start()
                movie_run = True
                log.info("【RUN】monitor.movie_trailer启动...")
            else:
                log.error("【RUN】" + movie_monpath + "目录不存在！")
        else:
            log.info("【RUN】" + movie_flag + "开关未打开！")

        # ResilioSync监控转移
        resiliosync_run = False
        resiliosync_flag = settings.get("monitor.resiliosync_flag") == "ON" or False
        resiliosync_monpath = settings.get("monitor.resiliosync_monpath")
        if os.path.exists(resiliosync_monpath) and resiliosync_flag:
            resiliosync = create_resilosync()
            resiliosync.schedule(ResilioSyncHandler, path=resiliosync_monpath, recursive=True)  # recursive递归的
            resiliosync.setDaemon(False)
            resiliosync.start()
            resiliosync_run = True
            log.info("【RUN】monitor.resilosync启动...")
        else:
            log.error("【ResilioSync】" + resiliosync_monpath + "目录不存在！")

        # 退出事件监听
        @atexit.register
        def atexit_fun():
            if movie_run:
                movie_trailer.stop()
            if resiliosync_run:
                resiliosync.stop()

        def signal_fun(signum, frame):
            log.info("【RUN】monitor捕捉到信号：" + str(signum) + '-' + str(frame) + "，开始退出...")
            sys.exit()

        signal.signal(signal.SIGTERM, signal_fun)
        signal.signal(signal.SIGINT, signal_fun)

    except Exception as err:
        log.error("【RUN】启动monitor失败：" + str(err))
        sendmsg("【NASTOOL】启动monitor失败！", str(err))
