import atexit
import os
import signal
import sys
import log
from config import get_config
from message.send import sendmsg
from monitor.movie_trailer import create_movie_trailer
from monitor.movie_trailer import FileMonitorHandler as MovieTrailerHandler
from monitor.media_sync import create_sync
from monitor.media_sync import FileMonitorHandler as SyncHandler

trailer = None
sync = None


def run_monitor():
    try:
        # 电影监控下载预告片
        config = get_config()
        media = config.get('media')
        if media:
            movie_monpath = config['media'].get('movie_path')
            movie_trailer = config['media'].get('movie_trailer')
            if movie_monpath and movie_trailer:
                if os.path.exists(movie_monpath):
                    global trailer
                    trailer = create_movie_trailer()
                    trailer.schedule(MovieTrailerHandler(movie_monpath), path=movie_monpath, recursive=True)  # recursive递归的
                    trailer.setDaemon(False)
                    trailer.start()
                    log.info("【RUN】monitor.movie_trailer启动...")
                else:
                    log.error("【RUN】" + movie_monpath + "目录不存在！")

            # Sync监控转移
            sync_monpaths = config['media'].get('sync_path')
            if sync_monpaths:
                for sync_monpath in sync_monpaths:
                    if os.path.exists(sync_monpath):
                        global sync
                        sync = create_sync()
                        sync.schedule(SyncHandler(sync_monpath), path=sync_monpath, recursive=True)  # recursive递归的
                        sync.setDaemon(False)
                        sync.start()
                        log.info("【RUN】monitor.media_sync启动...")
                    else:
                        log.error("【SYNC】" + sync_monpath + "目录不存在！")

        # 退出事件监听
        @atexit.register
        def atexit_fun():
            if trailer:
                trailer.stop()
            if sync:
                sync.stop()

        def signal_fun(signum, frame):
            sys.exit()

        signal.signal(signal.SIGTERM, signal_fun)
        signal.signal(signal.SIGINT, signal_fun)

    except Exception as err:
        log.error("【RUN】启动monitor失败：" + str(err))
        sendmsg("【NASTOOL】启动monitor失败！", str(err))
