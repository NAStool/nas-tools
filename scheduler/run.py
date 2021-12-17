import atexit
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
import log
from scheduler.autoremove_torrents import run_autoremovetorrents
from scheduler.hot_trailer import run_hottrailers
from scheduler.icloudpd import run_icloudpd
from scheduler.pt_signin import run_ptsignin
import settings
from scheduler.qb_transfer import run_qbtransfer
from scheduler.rss_download import run_rssdownload
from scheduler.sensors import run_sensors
from scheduler.smzdm_signin import run_smzdmsignin
from scheduler.unicom_signin import run_unicomsignin


def run_scheduler():
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")

    @atexit.register
    def atexit_fun():
        if scheduler.running:
            scheduler.shutdown()

    def signal_fun(signum, frame):
        log.info("【RUN】scheduler捕捉到信号：" + str(signum) + "，开始退出...")
        sys.exit()

    signal.signal(signal.SIGTERM, signal_fun)
    signal.signal(signal.SIGINT, signal_fun)

    scheduler.remove_all_jobs()
    # Icloud照片同步
    icloudpd_flag = settings.get("scheduler.icloudpd_flag") == "ON" or False
    if icloudpd_flag:
        icloudpd_cron = settings.get("scheduler.icloudpd_cron")
        scheduler.add_job(run_icloudpd, 'cron',
                          hour=int(icloudpd_cron.split(":")[0]),
                          minute=int(icloudpd_cron.split(":")[1]))
        log.info("【RUN】scheduler.icloudpd启动...")
    # PT种子清理
    autoremovetorrents_flag = settings.get("scheduler.autoremovetorrents_flag") == "ON" or False
    if autoremovetorrents_flag:
        scheduler.add_job(run_autoremovetorrents, 'interval',
                          seconds=int(settings.get("scheduler.autoremovetorrents_interval")))
        log.info("【RUN】scheduler.autoremovetorrents启动...")
    # 列新电影预告
    hottrailer_flag = settings.get("scheduler.hottrailer_flag") == "ON" or False
    if hottrailer_flag:
        hottrailer_cron = settings.get("scheduler.hottrailer_cron")
        scheduler.add_job(run_hottrailers, 'cron',
                          hour=int(hottrailer_cron.split(":")[0]),
                          minute=int(hottrailer_cron.split(":")[1]))
        log.info("【RUN】scheduler.hottrailers启动...")
    # PT站签到
    ptsignin_flag = settings.get("scheduler.ptsignin_flag") == "ON" or False
    if ptsignin_flag:
        ptsignin_cron = settings.get("scheduler.ptsignin_cron")
        scheduler.add_job(run_ptsignin, "cron",
                          hour=int(ptsignin_cron.split(":")[0]),
                          minute=int(ptsignin_cron.split(":")[1]))
        log.info("【RUN】scheduler.ptsignin启动．．．")
    # 什么值得买签到
    smzdmsignin_flag = settings.get("scheduler.smzdmsignin_flag") == "ON" or False
    if smzdmsignin_flag:
        smzdmsignin_cron = settings.get("scheduler.smzdmsignin_cron")
        scheduler.add_job(run_smzdmsignin, "cron",
                          hour=int(smzdmsignin_cron.split(":")[0]),
                          minute=int(smzdmsignin_cron.split(":")[1]))
        log.info("【RUN】scheduler.smzdmsignin启动．．．")
    # 联通营业厅签到
    unicomsignin_flag = settings.get("scheduler.unicomsignin_flag") == "ON" or False
    if unicomsignin_flag:
        unicomsignin_cron = settings.get("scheduler.unicomsignin_cron")
        scheduler.add_job(run_unicomsignin, "cron",
                          hour=int(unicomsignin_cron.split(":")[0]),
                          minute=int(unicomsignin_cron.split(":")[1]))
        log.info("【RUN】scheduler.unicomsignin启动．．．")

    # qbittorrent文件转移
    qbtransfer_flag = settings.get("scheduler.qbtransfer_flag") == "ON" or False
    if qbtransfer_flag:
        scheduler.add_job(run_qbtransfer, 'interval',
                          seconds=int(settings.get("scheduler.qbtransfer_interval")))
        log.info("【RUN】scheduler.qbtransfer启动...")

    # RSS下载器
    rssdownload_flag = settings.get("scheduler.rssdownload_flag") == "ON" or False
    if rssdownload_flag:
        scheduler.add_job(run_rssdownload, 'interval',
                          seconds=int(settings.get("scheduler.rssdownload_interval")))
        log.info("【RUN】scheduler.rssdownload启动...")

    # RSS下载器
    sensors_flag = settings.get("scheduler.sensors_flag") == "ON" or False
    if sensors_flag:
        scheduler.add_job(run_sensors, 'interval',
                          seconds=int(settings.get("scheduler.sensors_check_interval")))
        log.info("【RUN】scheduler.sensors启动...")

    scheduler.start()
    log.info("【RUN】scheduler启动完成!")
