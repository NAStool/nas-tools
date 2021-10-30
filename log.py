import logging
import os
from logging.handlers import TimedRotatingFileHandler

import settings


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
        self.logger.addHandler(log_file_handler)
        self.logger.addHandler(log_console_handler)
