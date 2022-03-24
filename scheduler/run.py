from apscheduler.schedulers.blocking import BlockingScheduler
import log
from config import AUTO_REMOVE_TORRENTS_INTERVAL, PT_TRANSFER_INTERVAL, Config
from monitor.media_sync import Sync
from scheduler.autoremove_torrents import AutoRemoveTorrents
from scheduler.douban_sync import DoubanSync
from scheduler.pt_signin import PTSignin
from scheduler.pt_transfer import PTTransfer
from scheduler.rss_download import RSSDownloader
from utils.meta_helper import MetaHelper


def run_scheduler():

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.remove_all_jobs()

    config = Config()
    pt = config.get_config('pt')
    if pt:
        # PT种子清理
        pt_seeding_time = pt.get('pt_seeding_time')
        if pt_seeding_time:
            scheduler.add_job(AutoRemoveTorrents().run_schedule,
                              'interval',
                              seconds=AUTO_REMOVE_TORRENTS_INTERVAL)
            log.info("【RUN】scheduler.autoremove_torrents启动...")

        # PT站签到
        ptsignin_cron = str(pt.get('ptsignin_cron'))
        if ptsignin_cron and ptsignin_cron.find(':') != -1:
            scheduler.add_job(PTSignin().run_schedule, "cron",
                              hour=int(ptsignin_cron.split(":")[0]),
                              minute=int(ptsignin_cron.split(":")[1]))
            log.info("【RUN】scheduler.pt_signin启动．．．")

        # PT文件转移
        pt_monitor = pt.get('pt_monitor')
        if pt_monitor:
            scheduler.add_job(PTTransfer().run_schedule, 'interval', seconds=PT_TRANSFER_INTERVAL)
            log.info("【RUN】scheduler.pt_transfer启动...")

        # RSS下载器
        pt_check_interval = pt.get('pt_check_interval')
        if pt_check_interval:
            scheduler.add_job(RSSDownloader().run_schedule, 'interval', seconds=int(pt_check_interval))
            log.info("【RUN】scheduler.rss_download启动...")

    # 豆瓣电影同步
    douban = config.get_config('douban')
    if douban:
        douban_interval = douban.get('interval')
        if douban_interval:
            scheduler.add_job(DoubanSync().run_schedule, 'interval', seconds=int(douban_interval)*3600)
            log.info("【RUN】scheduler.douban_sync启动...")

    # 配置定时生效
    scheduler.add_job(Config().load_config, 'interval', seconds=600)

    # 元数据定时保存
    scheduler.add_job(MetaHelper().save_meta_data, 'interval', seconds=600)

    # 定时把队列中的监控文件转移走
    scheduler.add_job(Sync().transfer_mon_files, 'interval', seconds=300)

    scheduler.start()
    log.info("【RUN】scheduler启动完成!")
