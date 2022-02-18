import atexit
import os
import signal
import sys
import log
from config import get_config
from message.send import sendmsg
from monitor.movie_trailer import create_movie_trailer
from monitor.movie_trailer import FileMonitorHandler as MovieTrailerHandler
from monitor.resiliosync import create_resilosync
from monitor.resiliosync import FileMonitorHandler as ResilioSyncHandler


def run_monitor():
    try:
        # 电影监控下载预告片
        config = get_config()
        movie_run = False
        movie_monpath = config['media']['movie_path']
        if movie_monpath:
            if os.path.exists(movie_monpath):
                movie_trailer = create_movie_trailer()
                movie_trailer.schedule(MovieTrailerHandler(movie_monpath), path=movie_monpath, recursive=True)  # recursive递归的
                movie_trailer.setDaemon(False)
                movie_trailer.start()
                movie_run = True
                log.info("【RUN】monitor.movie_trailer启动...")
            else:
                log.error("【RUN】" + movie_monpath + "目录不存在！")
        else:
            log.info("【RUN】monitor.movie_flag开关未打开！")

        # ResilioSync监控转移
        resiliosync_run = False
        resiliosync_monpaths = config['media']['resiliosync_path']
        for resiliosync_monpath in resiliosync_monpaths:
            if os.path.exists(resiliosync_monpath):
                resiliosync = create_resilosync()
                resiliosync.schedule(ResilioSyncHandler(resiliosync_monpath), path=resiliosync_monpath, recursive=True)  # recursive递归的
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
            sys.exit()

        signal.signal(signal.SIGTERM, signal_fun)
        signal.signal(signal.SIGINT, signal_fun)

    except Exception as err:
        log.error("【RUN】启动monitor失败：" + str(err))
        sendmsg("【NASTOOL】启动monitor失败！", str(err))
