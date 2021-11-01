import logging
import os
from logging.handlers import TimedRotatingFileHandler
import settings
from functions import mysql_exec_sql


class Logger:
    def __init__(self, logname):
        self.logger = logging.Logger(logname.upper())
        self.logger.setLevel(level=logging.INFO)
        logpath = settings.get("root.logpath")
        if not os.path.exists(logpath):
            os.makedirs(logpath)
        log_fmt = '%(asctime)s\tFile \"%(filename)s\",line %(lineno)s\t%(levelname)s: %(message)s'
        formatter = logging.Formatter(log_fmt)
        log_file_handler = TimedRotatingFileHandler(filename=logpath + "/" + logname + ".txt", when="D", interval=1, backupCount=2)
        log_file_handler.setFormatter(formatter)
        log_console_handler = logging.StreamHandler()
        mysql_filter = LoggerToMysqlFilter()
        self.logger.addHandler(log_file_handler)
        self.logger.addHandler(log_console_handler)
        self.logger.addFilter(mysql_filter)


class LoggerToMysqlFilter(logging.Filter):
    def filter(self, record):
        rtext = record.msg
        rname = record.name
        rtype = record.levelname
        if rtype == "INFO" or rtype == "ERROR":
            sql = "INSERT INTO system_log \
                                    (TYPE, NAME, TEXT, TIME) \
                                    VALUES ('%s', '%s', '%s', now())" % \
                  (rtype, rname, rtext)
            # 登记数据库
            mysql_exec_sql(sql)
        return True
