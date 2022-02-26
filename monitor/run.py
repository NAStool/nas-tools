import atexit
import os
import signal
import sys
import log
from config import get_config, SYNC_DIR_CONFIG
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
                if os.path.exists(movie_monpath) and os.path.exists(movie_trailer):
                    global trailer
                    trailer = create_movie_trailer()
                    trailer.schedule(MovieTrailerHandler(movie_monpath), path=movie_monpath, recursive=True)
                    trailer.setDaemon(False)
                    trailer.start()
                    log.info("【RUN】monitor.movie_trailer启动...")

            # Sync监控转移
            sync_crg = config.get('sync')
            if sync_crg:
                sync_monpaths = config['sync'].get('sync_path')
                if sync_monpaths:
                    for sync_monpath in sync_monpaths:
                        # 目录是两段式，需要把配对关系存起来
                        if sync_monpath.find('|') != -1:
                            # 源目录|目的目录，这个格式的目的目录在源目录同级建立
                            monpath = sync_monpath.split("|")[0]
                            target_path = sync_monpath.split("|")[1]
                            if target_path:
                                log.info("【SYNC】读取到监控目录：" + monpath + "，目的目录：" + target_path)
                                if not os.path.exists(target_path):
                                    log.info("【SYNC】目的目录不存在，正在创建：" + target_path)
                                    os.makedirs(target_path)
                                # 去掉末尾的/
                                if monpath.endswith('/'):
                                    monpath = monpath[0:-1]
                                SYNC_DIR_CONFIG[monpath] = target_path
                        else:
                            monpath = sync_monpath
                            SYNC_DIR_CONFIG[monpath] = None
                            log.info("【SYNC】读取监控目录：" + monpath)

                        if os.path.exists(monpath):
                            global sync
                            sync = create_sync()
                            sync.schedule(SyncHandler(monpath), path=monpath, recursive=True)  # recursive递归的
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
