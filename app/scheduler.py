import datetime
import math
import random
import traceback

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler

import log
from app.doubansync import DoubanSync
from app.downloader import Downloader
from app.helper import MetaHelper
from app.mediaserver import MediaServer
from app.rss import Rss
from app.sites import Sites
from app.subscribe import Subscribe
from app.sync import Sync
from app.utils import ExceptionUtils
from app.utils.commons import singleton
from config import PT_TRANSFER_INTERVAL, METAINFO_SAVE_INTERVAL, \
    SYNC_TRANSFER_INTERVAL, RSS_CHECK_INTERVAL, REFRESH_PT_DATA_INTERVAL, \
    RSS_REFRESH_TMDB_INTERVAL, META_DELETE_UNKNOWN_INTERVAL, REFRESH_WALLPAPER_INTERVAL, Config
from web.backend.wallpaper import get_login_wallpaper


@singleton
class Scheduler:
    SCHEDULER = None
    _pt = None
    _douban = None
    _media = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        self._pt = Config().get_config('pt')
        self._media = Config().get_config('media')
        self._douban = Config().get_config('douban')

    def run_service(self):
        """
        读取配置，启动定时服务
        """
        self.SCHEDULER = BackgroundScheduler(timezone=Config().get_timezone(),
                                             executors={
                                                 'default': ThreadPoolExecutor(20)
                                             })
        if not self.SCHEDULER:
            return
        if self._pt:
            # 站点签到
            ptsignin_cron = str(self._pt.get('ptsignin_cron'))
            if ptsignin_cron:
                if '-' in ptsignin_cron:
                    try:
                        time_range = ptsignin_cron.split("-")
                        start_time_range_str = time_range[0]
                        end_time_range_str = time_range[1]
                        start_time_range_array = start_time_range_str.split(":")
                        end_time_range_array = end_time_range_str.split(":")
                        start_hour = int(start_time_range_array[0])
                        start_minute = int(start_time_range_array[1])
                        end_hour = int(end_time_range_array[0])
                        end_minute = int(end_time_range_array[1])

                        def start_random_job():
                            task_time_count = random.randint(start_hour * 60 + start_minute, end_hour * 60 + end_minute)
                            self.start_data_site_signin_job(math.floor(task_time_count / 60), task_time_count % 60)

                        self.SCHEDULER.add_job(start_random_job,
                                               "cron",
                                               hour=start_hour,
                                               minute=start_minute)
                        log.info("站点自动签到服务时间范围随机模式启动，起始时间于%s:%s" % (
                            str(start_hour).rjust(2, '0'), str(start_minute).rjust(2, '0')))
                    except Exception as e:
                        log.info("站点自动签到时间 时间范围随机模式 配置格式错误：%s %s" % (ptsignin_cron, str(e)))
                elif ptsignin_cron.find(':') != -1:
                    try:
                        hour = int(ptsignin_cron.split(":")[0])
                        minute = int(ptsignin_cron.split(":")[1])
                    except Exception as e:
                        log.info("站点自动签到时间 配置格式错误：%s" % str(e))
                        hour = minute = 0
                    self.SCHEDULER.add_job(Sites().signin,
                                           "cron",
                                           hour=hour,
                                           minute=minute)
                    log.info("站点自动签到服务启动")
                else:
                    try:
                        hours = float(ptsignin_cron)
                    except Exception as e:
                        log.info("站点自动签到时间 配置格式错误：%s" % str(e))
                        hours = 0
                    if hours:
                        self.SCHEDULER.add_job(Sites().signin,
                                               "interval",
                                               hours=hours)
                        log.info("站点自动签到服务启动")

            # 下载文件转移
            pt_monitor = self._pt.get('pt_monitor')
            if pt_monitor:
                self.SCHEDULER.add_job(Downloader().transfer, 'interval', seconds=PT_TRANSFER_INTERVAL)
                log.info("下载文件转移服务启动")

            # RSS下载器
            pt_check_interval = self._pt.get('pt_check_interval')
            if pt_check_interval:
                if isinstance(pt_check_interval, str) and pt_check_interval.isdigit():
                    pt_check_interval = int(pt_check_interval)
                else:
                    try:
                        pt_check_interval = round(float(pt_check_interval))
                    except Exception as e:
                        log.error("RSS订阅周期 配置格式错误：%s" % str(e))
                        pt_check_interval = 0
                if pt_check_interval:
                    if pt_check_interval < 300:
                        pt_check_interval = 300
                    self.SCHEDULER.add_job(Rss().rssdownload, 'interval', seconds=pt_check_interval)
                    log.info("RSS订阅服务启动")

            # RSS订阅定时检索
            search_rss_interval = self._pt.get('search_rss_interval')
            if search_rss_interval:
                if isinstance(search_rss_interval, str) and search_rss_interval.isdigit():
                    search_rss_interval = int(search_rss_interval)
                else:
                    try:
                        search_rss_interval = round(float(search_rss_interval))
                    except Exception as e:
                        log.error("订阅定时搜索周期 配置格式错误：%s" % str(e))
                        search_rss_interval = 0
                if search_rss_interval:
                    if search_rss_interval < 6:
                        search_rss_interval = 6
                    self.SCHEDULER.add_job(Subscribe().subscribe_search_all, 'interval', hours=search_rss_interval)
                    log.info("订阅定时搜索服务启动")

        # 豆瓣电影同步
        if self._douban:
            douban_interval = self._douban.get('interval')
            if douban_interval:
                if isinstance(douban_interval, str):
                    if douban_interval.isdigit():
                        douban_interval = int(douban_interval)
                    else:
                        try:
                            douban_interval = float(douban_interval)
                        except Exception as e:
                            log.info("豆瓣同步服务启动失败：%s" % str(e))
                            douban_interval = 0
                if douban_interval:
                    self.SCHEDULER.add_job(DoubanSync().sync, 'interval', hours=douban_interval)
                    log.info("豆瓣同步服务启动")

        # 媒体库同步
        if self._media:
            mediasync_interval = self._media.get("mediasync_interval")
            if mediasync_interval:
                if isinstance(mediasync_interval, str):
                    if mediasync_interval.isdigit():
                        mediasync_interval = int(mediasync_interval)
                    else:
                        try:
                            mediasync_interval = round(float(mediasync_interval))
                        except Exception as e:
                            log.info("豆瓣同步服务启动失败：%s" % str(e))
                            mediasync_interval = 0
                if mediasync_interval:
                    self.SCHEDULER.add_job(MediaServer().sync_mediaserver, 'interval', hours=mediasync_interval)
                    log.info("媒体库同步服务启动")

        # 元数据定时保存
        self.SCHEDULER.add_job(MetaHelper().save_meta_data, 'interval', seconds=METAINFO_SAVE_INTERVAL)

        # 定时把队列中的监控文件转移走
        self.SCHEDULER.add_job(Sync().transfer_mon_files, 'interval', seconds=SYNC_TRANSFER_INTERVAL)

        # RSS队列中检索
        self.SCHEDULER.add_job(Subscribe().subscribe_search, 'interval', seconds=RSS_CHECK_INTERVAL)

        # 站点数据刷新
        self.SCHEDULER.add_job(Sites().refresh_pt_date_now,
                               'interval',
                               hours=REFRESH_PT_DATA_INTERVAL,
                               next_run_time=datetime.datetime.now() + datetime.timedelta(minutes=1))

        # 豆瓣RSS转TMDB，定时更新TMDB数据
        self.SCHEDULER.add_job(Subscribe().refresh_rss_metainfo, 'interval', hours=RSS_REFRESH_TMDB_INTERVAL)

        # 定时清除未识别的缓存
        self.SCHEDULER.add_job(MetaHelper().delete_unknown_meta, 'interval', hours=META_DELETE_UNKNOWN_INTERVAL)

        # 定时刷新壁纸
        self.SCHEDULER.add_job(get_login_wallpaper,
                               'interval',
                               hours=REFRESH_WALLPAPER_INTERVAL,
                               next_run_time=datetime.datetime.now())

        self.SCHEDULER.print_jobs()

        self.SCHEDULER.start()

    def stop_service(self):
        """
        停止定时服务
        """
        try:
            if self.SCHEDULER:
                self.SCHEDULER.remove_all_jobs()
                self.SCHEDULER.shutdown()
                self.SCHEDULER = None
        except Exception as e:
            ExceptionUtils.exception_traceback(e)

    def start_data_site_signin_job(self, hour, minute):
        year = datetime.datetime.now().year
        month = datetime.datetime.now().month
        day = datetime.datetime.now().day
        # 随机数从1秒开始，不在整点签到
        second = random.randint(1, 59)
        log.info("站点自动签到时间 即将在%s-%s-%s,%s:%s:%s签到" % (
            str(year), str(month), str(day), str(hour), str(minute), str(second)))
        if hour < 0 or hour > 24:
            hour = -1
        if minute < 0 or minute > 60:
            minute = -1
        if hour < 0 or minute < 0:
            log.warn("站点自动签到时间 配置格式错误：不启动任务")
            return
        self.SCHEDULER.add_job(Sites().signin,
                               "date",
                               run_date=datetime.datetime(year, month, day, hour, minute, second))


def run_scheduler():
    """
    启动定时服务
    """
    try:
        Scheduler().run_service()
    except Exception as err:
        log.error("启动定时服务失败：%s - %s" % (str(err), traceback.format_exc()))


def stop_scheduler():
    """
    停止定时服务
    """
    try:
        Scheduler().stop_service()
    except Exception as err:
        log.debug("停止定时服务失败：%s" % str(err))


def restart_scheduler():
    """
    重启定时服务
    """
    stop_scheduler()
    run_scheduler()
