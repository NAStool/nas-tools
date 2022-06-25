import logging
import os
import threading
import time
from collections import deque
from html import escape
from logging.handlers import RotatingFileHandler
from config import Config
from utils.sqls import insert_system_message

lock = threading.Lock()
LOG_QUEUE = deque(maxlen=200)
LOG_INDEX = 0


class Logger:
    logger = None
    __instance = None
    __config = None

    __loglevels = {
        "info": logging.INFO,
        "debug": logging.DEBUG,
        "error": logging.ERROR
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.__config = Config()
        logtype = self.__config.get_config('app').get('logtype') or "file"
        loglevel = self.__config.get_config('app').get('loglevel') or "info"
        self.logger.setLevel(level=self.__loglevels.get(loglevel))
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
            logpath = self.__config.get_config('app').get('logpath') or ""
            if not os.path.exists(logpath):
                os.makedirs(logpath)
            log_file_handler = RotatingFileHandler(filename=os.path.join(logpath, __name__ + ".txt"),
                                                   maxBytes=5 * 1024 * 1024,
                                                   backupCount=3,
                                                   encoding='utf-8')
            log_file_handler.setFormatter(logging.Formatter('%(asctime)s\t%(levelname)s: %(message)s'))
            self.logger.addHandler(log_file_handler)
        # 记录日志到终端
        log_console_handler = logging.StreamHandler()
        log_console_handler.setFormatter(logging.Formatter('%(asctime)s\t%(levelname)s: %(message)s'))
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
    return Logger.get_instance().logger.debug(text)


def info(text):
    global LOG_INDEX, LOG_QUEUE
    with lock:
        LOG_QUEUE.append(f"{time.strftime('%H:%M:%S', time.localtime(time.time()))} INFO - {escape(text)}")
        LOG_INDEX += 1
    return Logger.get_instance().logger.info(text)


def error(text):
    global LOG_INDEX, LOG_QUEUE
    with lock:
        LOG_QUEUE.append(f"{time.strftime('%H:%M:%S', time.localtime(time.time()))} ERROR - {escape(text)}")
        LOG_INDEX += 1
    try:
        if text.strip().find("：") != -1:
            title = text.split("：")[0]
            content = text.split("：")[1]
        else:
            title = text.strip()
            content = ""
        insert_system_message(level="ERROR", title=title, content=content)
    except Exception as e:
        print(str(e))
    return Logger.get_instance().logger.error(text)


def warn(text):
    global LOG_INDEX, LOG_QUEUE
    with lock:
        LOG_QUEUE.append(f"{time.strftime('%H:%M:%S', time.localtime(time.time()))} WARN - {escape(text)}")
        LOG_INDEX += 1
    return Logger.get_instance().logger.warning(text)


def console(text):
    global LOG_INDEX, LOG_QUEUE
    with lock:
        LOG_QUEUE.append(f"{time.strftime('%H:%M:%S', time.localtime(time.time()))} - {escape(text)}")
        LOG_INDEX += 1
    print(text)
