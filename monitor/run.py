import log
import settings
from message.send import sendmsg
from monitor.movie_trailer import run_movie_trailer
from monitor.resiliosync import run_resilosync


def run_monitor(config_file):
    settings.config_file_path = config_file
    settings.reload_config()
    try:
        run_movie_trailer()
    except Exception as err:
        log.error("【RUN】启动movie_trailer监控失败：" + str(err))
        sendmsg("【NASTOOL】启动movie_trailer监控失败！", str(err))
    try:
        run_resilosync()
    except Exception as err:
        log.error("【RUN】启动resilosync监控失败：" + str(err))
        sendmsg("【NASTOOL】启动resilosync监控失败！", str(err))
