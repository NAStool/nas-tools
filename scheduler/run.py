from apscheduler.schedulers.blocking import BlockingScheduler
import os
import log
from scheduler.autoremove_torrents import run_autoremovetorrents
from scheduler.hot_trailer import run_hottrailers
from scheduler.icloudpd import run_icloudpd
from scheduler.pt_signin import run_ptsignin
import settings
from scheduler.qb_transfer import run_qbtransfer
from scheduler.smzdm_signin import run_smzdmsignin
from scheduler.unicom_signin import run_unicomsignin

logger = log.Logger("scheduler").logger
os.environ['TZ'] = 'Asia/Shanghai'


def run_scheduler():
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.remove_all_jobs()
    # Icloud照片同步
    icloudpd_flag = settings.get("scheduler.icloudpd_flag") == "ON" or False
    if icloudpd_flag:
        scheduler.add_job(run_icloudpd, 'interval',
                          seconds=int(settings.get("scheduler.icloudpd_interval")))
        logger.info("scheduler.icloudpd启动...")
    # PT种子清理
    autoremovetorrents_flag = settings.get("scheduler.autoremovetorrents_flag") == "ON" or False
    if autoremovetorrents_flag:
        scheduler.add_job(run_autoremovetorrents, 'interval',
                          seconds=int(settings.get("scheduler.autoremovetorrents_interval")))
        logger.info("scheduler.autoremovetorrents启动...")
    # 列新电影预告
    hottrailer_flag = settings.get("scheduler.hottrailer_flag") == "ON" or False
    if hottrailer_flag:
        hottrailer_cron = settings.get("scheduler.hottrailer_cron")
        scheduler.add_job(run_hottrailers, 'cron',
                          hour=int(hottrailer_cron.split(":")[0]),
                          minute=int(hottrailer_cron.split(":")[1]))
        logger.info("scheduler.hottrailers启动...")
    # PT站签到
    ptsignin_flag = settings.get("scheduler.ptsignin_flag") == "ON" or False
    if ptsignin_flag:
        ptsignin_cron = settings.get("scheduler.ptsignin_cron")
        scheduler.add_job(run_ptsignin, "cron",
                          hour=int(ptsignin_cron.split(":")[0]),
                          minute=int(ptsignin_cron.split(":")[1]))
        logger.info("scheduler.ptsignin启动．．．")
    # 什么值得买签到
    smzdmsignin_flag = settings.get("scheduler.smzdmsignin_flag") == "ON" or False
    if smzdmsignin_flag:
        smzdmsignin_cron = settings.get("scheduler.smzdmsignin_cron")
        scheduler.add_job(run_smzdmsignin, "cron",
                          hour=int(smzdmsignin_cron.split(":")[0]),
                          minute=int(smzdmsignin_cron.split(":")[1]))
        logger.info("scheduler.smzdmsignin启动．．．")
    # 联通营业厅签到
    unicomsignin_flag = settings.get("scheduler.unicomsignin_flag") == "ON" or False
    if unicomsignin_flag:
        unicomsignin_cron = settings.get("scheduler.unicomsignin_cron")
        scheduler.add_job(run_unicomsignin, "cron",
                          hour=int(unicomsignin_cron.split(":")[0]),
                          minute=int(unicomsignin_cron.split(":")[1]))
        logger.info("scheduler.unicomsignin启动．．．")

    # qbittorrent文件转移
    qbtransfer_flag = settings.get("scheduler.qbtransfer_flag") == "ON" or False
    if qbtransfer_flag:
        scheduler.add_job(run_qbtransfer, 'interval',
                          seconds=int(settings.get("scheduler.qbtransfer_interval")))
        logger.info("scheduler.qbtransfer启动...")

    scheduler.start()
    logger.info("scheduler启动完成!")


if __name__ == "__main__":
    run_scheduler()
