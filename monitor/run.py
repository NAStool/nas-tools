import log
from message.send import sendmsg
from monitor.movie_trailer import run_movie_trailer
from monitor.resiliosync import run_resilosync

logger = log.Logger("run").logger


def run_monitor():
    try:
        run_movie_trailer()
    except Exception as err:
        logger.error("【RUN】启动movie_trailer监控失败：" + str(err))
        sendmsg("【NASTOOL】启动movie_trailer监控失败！", str(err))
    try:
        run_resilosync()
    except Exception as err:
        logger.error("【RUN】启动resilosync监控失败：" + str(err))
        sendmsg("【NASTOOL】启动resilosync监控失败！", str(err))


if __name__ == "__main__":
    run_monitor()
