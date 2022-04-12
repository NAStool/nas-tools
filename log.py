import logging
import os
import threading
from logging.handlers import TimedRotatingFileHandler
from config import LOG_LEVEL, Config, LOG_QUEUE

lock = threading.Lock()


class Logger:
    __instance = None
    __config = None

    def __init__(self):
        self.logger = logging.Logger(__name__)
        self.logger.setLevel(level=LOG_LEVEL)
        self.__config = Config()
        app = self.__config.get_config('app')
        if app:
            logtype = app.get('logtype')
            if logtype:
                logtype = logtype.upper()
            else:
                logtype = "CONSOLE"
        else:
            logtype = 'CONSOLE'
        if logtype == "FILE":
            # 记录日志到文件
            logpath = app.get('logpath')
            if not os.path.exists(logpath):
                os.makedirs(logpath)
            log_file_handler = TimedRotatingFileHandler(filename=logpath + "/" + __name__ + ".txt", when="D",
                                                        interval=1,
                                                        backupCount=2)
            formatter = logging.Formatter(
                '%(asctime)s\tFile \"%(filename)s\",line %(lineno)s\t%(levelname)s: %(message)s')
            log_file_handler.setFormatter(formatter)
            self.logger.addHandler(log_file_handler)
        elif logtype == "SERVER":
            logserver = app.get('logserver')
            logip = logserver.split(':')[0]
            logport = int(logserver.split(':')[1])
            log_server_handler = logging.handlers.SysLogHandler((logip, logport),
                                                                logging.handlers.SysLogHandler.LOG_USER)
            formatter = logging.Formatter('%(filename)s: %(message)s')
            log_server_handler.setFormatter(formatter)
            self.logger.addHandler(log_server_handler)
        else:
            # 记录日志到终端
            formatter = logging.Formatter('%(asctime)s\t%(levelname)s: %(message)s')
            log_console_handler = logging.StreamHandler()
            log_console_handler.setFormatter(formatter)
            self.logger.addHandler(log_console_handler)

    @staticmethod
    def get_instance():
        if Logger.__instance:
            return Logger.__instance
        try:
            lock.acquire()
            if not Logger.__instance:
                Logger.__instance = Logger()
        finally:
            lock.release()
        return Logger.__instance


def debug(text):
    LOG_QUEUE.append("DEBUG - %s" % text)
    return Logger.get_instance().logger.debug(text)


def info(text):
    LOG_QUEUE.append("INFO - %s" % text)
    return Logger.get_instance().logger.info(text)


def error(text):
    LOG_QUEUE.append("ERROR - %s" % text)
    return Logger.get_instance().logger.error(text)


def warn(text):
    LOG_QUEUE.append("WARN - %s" % text)
    return Logger.get_instance().logger.warning(text)
