import datetime
import random
from apscheduler.triggers.cron import CronTrigger
from apscheduler.util import undefined

import math

import log


class SchedulerUtils:

    @staticmethod
    def start_job(scheduler, func, func_desc, cron, next_run_time=undefined):
        """
        解析任务的定时规则,启动定时服务
        :param func: 可调用的一个函数,在指定时间运行
        :param func_desc: 函数的描述,在日志中提现
        :param cron 时间表达式 三种配置方法：
        :param next_run_time: 下次运行时间
          1、配置cron表达式，只支持5位的cron表达式
          2、配置时间范围，如08:00-09:00，表示在该时间范围内随机执行一次；
          3、配置固定时间，如08:00；
          4、配置间隔，单位小时，比如23.5；
        """
        if cron:
            cron = cron.strip()
            if cron.count(" ") == 4:
                try:
                    scheduler.add_job(func=func,
                                      trigger=CronTrigger.from_crontab(cron),
                                      next_run_time=next_run_time)
                except Exception as e:
                    log.info("%s时间cron表达式配置格式错误：%s %s" % (func_desc, cron, str(e)))
            elif '-' in cron:
                try:
                    time_range = cron.split("-")
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
                        SchedulerUtils.start_range_job(scheduler=scheduler,
                                                       func=func,
                                                       func_desc=func_desc,
                                                       hour=math.floor(task_time_count / 60),
                                                       minute=task_time_count % 60,
                                                       next_run_time=next_run_time)

                    scheduler.add_job(start_random_job,
                                      "cron",
                                      hour=start_hour,
                                      minute=start_minute,
                                      next_run_time=next_run_time)
                    log.info("%s服务时间范围随机模式启动，起始时间于%s:%s" % (
                        func_desc, str(start_hour).rjust(2, '0'), str(start_minute).rjust(2, '0')))
                except Exception as e:
                    log.info("%s时间 时间范围随机模式 配置格式错误：%s %s" % (func_desc, cron, str(e)))
            elif cron.find(':') != -1:
                try:
                    hour = int(cron.split(":")[0])
                    minute = int(cron.split(":")[1])
                except Exception as e:
                    log.info("%s时间 配置格式错误：%s" % (func_desc, str(e)))
                    hour = minute = 0
                scheduler.add_job(func,
                                  "cron",
                                  hour=hour,
                                  minute=minute,
                                  next_run_time=next_run_time)
                log.info("%s服务启动" % func_desc)
            else:
                try:
                    hours = float(cron)
                except Exception as e:
                    log.info("%s时间 配置格式错误：%s" % (func_desc, str(e)))
                    hours = 0
                if hours:
                    scheduler.add_job(func,
                                      "interval",
                                      hours=hours,
                                      next_run_time=next_run_time)
                    log.info("%s服务启动" % func_desc)

    @staticmethod
    def start_range_job(scheduler, func, func_desc, hour, minute, next_run_time=None):
        year = datetime.datetime.now().year
        month = datetime.datetime.now().month
        day = datetime.datetime.now().day
        # 随机数从1秒开始，不在整点签到
        second = random.randint(1, 59)
        log.info("%s到时间 即将在%s-%s-%s,%s:%s:%s签到" % (
            func_desc, str(year), str(month), str(day), str(hour), str(minute), str(second)))
        if hour < 0 or hour > 24:
            hour = -1
        if minute < 0 or minute > 60:
            minute = -1
        if hour < 0 or minute < 0:
            log.warn("%s时间 配置格式错误：不启动任务" % func_desc)
            return
        scheduler.add_job(func,
                          "date",
                          run_date=datetime.datetime(year, month, day, hour, minute, second),
                          next_run_time=next_run_time)
