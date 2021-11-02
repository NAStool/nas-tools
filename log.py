import logging
import os
from logging.handlers import TimedRotatingFileHandler
import settings
from functions import mysql_exec_sql


class Logger:
    def __init__(self, logname):
        self.logger = logging.Logger(logname.upper())
        self.logger.setLevel(level=logging.INFO)
        logtype = settings.get("root.logtype")
        if logtype == "FILE":
            # 记录日志到文件
            logpath = settings.get("root.logpath")
            if not os.path.exists(logpath):
                os.makedirs(logpath)
            log_file_handler = TimedRotatingFileHandler(filename=logpath + "/" + logname + ".txt", when="D", interval=1, backupCount=2)
            formatter = logging.Formatter('%(asctime)s\tFile \"%(filename)s\",line %(lineno)s\t%(levelname)s: %(message)s')
            log_file_handler.setFormatter(formatter)
            self.logger.addHandler(log_file_handler)
        elif logtype == "MYSQL":
            # 记录日志到MYSQL
            mysql_filter = LoggerToMysqlFilter()
            self.logger.addFilter(mysql_filter)
        elif logtype == "SERVER":
            logserver = settings.get("root.logserver")
            logip = logserver.split(':')[0]
            logport = int(logserver.split(':')[1])
            log_server_handler = logging.handlers.SysLogHandler((logip, logport), logging.handlers.SysLogHandler.LOG_USER)
            formatter = logging.Formatter('%(filename)s: %(message)s')
            log_server_handler.setFormatter(formatter)
            self.logger.addHandler(log_server_handler)
        else:
            # 记录日志到终端
            log_console_handler = logging.StreamHandler()
            self.logger.addHandler(log_console_handler)


# 记录日志到MYSQL
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
