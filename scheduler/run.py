import atexit
import os.path
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
import log
from config import get_config, AUTO_REMOVE_TORRENTS_INTERVAL, HOT_TRAILER_INTERVAL, load_config, PT_TRANSFER_INTERVAL
from scheduler.autoremove_torrents import run_autoremovetorrents
from scheduler.hot_trailer import run_hottrailers
from scheduler.pt_signin import run_ptsignin
from scheduler.pt_transfer import run_pttransfer
from scheduler.rss_download import run_rssdownload


def run_scheduler():
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")

    @atexit.register
    def atexit_fun():
        if scheduler.running:
            scheduler.shutdown()

    def signal_fun(signum, frame):
        sys.exit()

    signal.signal(signal.SIGTERM, signal_fun)
    signal.signal(signal.SIGINT, signal_fun)

    scheduler.remove_all_jobs()
    # PT种子清理
    config = get_config()
    pt_seeding_time = config['pt'].get('pt_seeding_time')
    if pt_seeding_time:
        scheduler.add_job(run_autoremovetorrents, 'interval', seconds=AUTO_REMOVE_TORRENTS_INTERVAL)
        log.info("【RUN】scheduler.autoremove_torrents启动...")
    # 更新电影预告
    hottrailer_path = config['media'].get('hottrailer_path')
    if hottrailer_path and os.path.exists(hottrailer_path):
        scheduler.add_job(run_hottrailers, 'interval', seconds=HOT_TRAILER_INTERVAL)
        log.info("【RUN】scheduler.hot_trailer启动...")
    # PT站签到
    ptsignin_cron = str(config['pt'].get('ptsignin_cron'))
    if ptsignin_cron and ptsignin_cron.find(':') != -1:
        scheduler.add_job(run_ptsignin, "cron",
                          hour=int(ptsignin_cron.split(":")[0]),
                          minute=int(ptsignin_cron.split(":")[1]))
        log.info("【RUN】scheduler.pt_signin启动．．．")

    # PT文件转移
    scheduler.add_job(run_pttransfer, 'interval', seconds=PT_TRANSFER_INTERVAL)
    log.info("【RUN】scheduler.pt_transfer启动...")

    # RSS下载器
    pt_check_interval = config['pt'].get('pt_check_interval')
    if pt_check_interval:
        scheduler.add_job(run_rssdownload, 'interval', seconds=int(pt_check_interval))
        log.info("【RUN】scheduler.rss_download启动...")

    # 配置定时生效
    scheduler.add_job(load_config, 'interval', seconds=600)

    scheduler.start()
    log.info("【RUN】scheduler启动完成!")
