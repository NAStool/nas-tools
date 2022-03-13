import atexit
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
import log
from config import get_config, AUTO_REMOVE_TORRENTS_INTERVAL, load_config, PT_TRANSFER_INTERVAL
from scheduler.autoremove_torrents import AutoRemoveTorrents
from scheduler.douban_sync import DoubanSync
from scheduler.pt_signin import PTSignin
from scheduler.pt_transfer import PTTransfer
from scheduler.rss_download import RSSDownloader


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

    config = get_config()
    if config.get('pt'):
        # PT种子清理
        pt_seeding_time = config['pt'].get('pt_seeding_time')
        if pt_seeding_time:
            scheduler.add_job(AutoRemoveTorrents().run_schedule,
                              'interval',
                              seconds=AUTO_REMOVE_TORRENTS_INTERVAL)
            log.info("【RUN】scheduler.autoremove_torrents启动...")

        # PT站签到
        ptsignin_cron = str(config['pt'].get('ptsignin_cron'))
        if ptsignin_cron and ptsignin_cron.find(':') != -1:
            scheduler.add_job(PTSignin().run_schedule, "cron",
                              hour=int(ptsignin_cron.split(":")[0]),
                              minute=int(ptsignin_cron.split(":")[1]))
            log.info("【RUN】scheduler.pt_signin启动．．．")

        # PT文件转移
        pt_monitor = config['pt'].get('pt_monitor')
        if pt_monitor:
            scheduler.add_job(PTTransfer().run_schedule, 'interval', seconds=PT_TRANSFER_INTERVAL)
            log.info("【RUN】scheduler.pt_transfer启动...")

        # RSS下载器
        pt_check_interval = config['pt'].get('pt_check_interval')
        if pt_check_interval:
            scheduler.add_job(RSSDownloader().run_schedule, 'interval', seconds=int(pt_check_interval))
            log.info("【RUN】scheduler.rss_download启动...")

    # 豆瓣电影同步
    if config.get('douban'):
        douban_interval = config['douban'].get('interval')
        if douban_interval:
            scheduler.add_job(DoubanSync().run_schedule, 'interval', seconds=int(douban_interval)*3600)
            log.info("【RUN】scheduler.douban_sync启动...")

    # 配置定时生效
    scheduler.add_job(load_config, 'interval', seconds=600)

    scheduler.start()
    log.info("【RUN】scheduler启动完成!")
