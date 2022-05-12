import logging
import os
import threading
import time
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
        logtype = self.__config.get_config('app').get('logtype')
        if logtype:
            logtype = logtype.lower()
        if logtype == "server":
            logserver = self.__config.get_config('app').get('logserver')
            logip = logserver.split(':')[0]
            logport = int(logserver.split(':')[1])
            log_server_handler = logging.handlers.SysLogHandler((logip, logport),
                                                                logging.handlers.SysLogHandler.LOG_USER)
            log_server_handler.setFormatter(logging.Formatter('%(filename)s: %(message)s'))
            self.logger.addHandler(log_server_handler)
        else:
            # 记录日志到文件
            logpath = self.__config.get_config('app').get('logpath') or "/config/logs"
            if not os.path.exists(logpath):
                os.makedirs(logpath)
            log_file_handler = TimedRotatingFileHandler(filename=os.path.join(logpath, __name__ + ".txt"),
                                                        when='D',
                                                        backupCount=3,
                                                        encoding='utf-8')
            log_file_handler.setFormatter(logging.Formatter('%(asctime)s\t%(levelname)s: %(message)s'))
            self.logger.addHandler(log_file_handler)

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
    return Logger.get_instance().logger.debug(text)


def info(text):
    LOG_QUEUE.append(f"{time.strftime('%H:%M:%S',time.localtime(time.time()))} INFO - {text}")
    return Logger.get_instance().logger.info(text)


def error(text):
    LOG_QUEUE.append(f"{time.strftime('%H:%M:%S',time.localtime(time.time()))} ERROR - {text}")
    return Logger.get_instance().logger.error(text)


def warn(text):
    LOG_QUEUE.append(f"{time.strftime('%H:%M:%S',time.localtime(time.time()))} WARN - {text}")
    return Logger.get_instance().logger.warning(text)


def console(text):
    LOG_QUEUE.append(f"{time.strftime('%H:%M:%S', time.localtime(time.time()))} - {text}")
    print(text)
