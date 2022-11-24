import logging
import os
import threading
import time
from collections import deque
from html import escape
from logging.handlers import RotatingFileHandler

from config import CONFIG

logging.getLogger('werkzeug').setLevel(logging.ERROR)
lock = threading.Lock()
LOG_QUEUE = deque(maxlen=200)
LOG_INDEX = 0


class Logger:
    logger = None
    __instance = {}
    __config = None

    __loglevels = {
        "info": logging.INFO,
        "debug": logging.DEBUG,
        "error": logging.ERROR
    }

    def __init__(self, module):
        self.logger = logging.getLogger(module)
        self.__config = CONFIG
        logtype = self.__config.get_config('app').get('logtype') or "console"
        loglevel = self.__config.get_config('app').get('loglevel') or "info"
        self.logger.setLevel(level=self.__loglevels.get(loglevel))
        if logtype == "server":
            logserver = self.__config.get_config('app').get('logserver', '').split(':')
            if logserver:
                logip = logserver[0]
                if len(logserver) > 1:
                    logport = int(logserver[1] or '514')
                else:
                    logport = 514
                log_server_handler = logging.handlers.SysLogHandler((logip, logport),
                                                                    logging.handlers.SysLogHandler.LOG_USER)
                log_server_handler.setFormatter(logging.Formatter('%(filename)s: %(message)s'))
                self.logger.addHandler(log_server_handler)
        elif logtype == "file":
            # 记录日志到文件
            logpath = os.environ.get('NASTOOL_LOG') or self.__config.get_config('app').get('logpath') or ""
            if logpath:
                if not os.path.exists(logpath):
                    os.makedirs(logpath)
                log_file_handler = RotatingFileHandler(filename=os.path.join(logpath, module + ".txt"),
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
    def get_instance(module):
        if not module:
            module = "run"
        if Logger.__instance.get(module):
            return Logger.__instance.get(module)
        with lock:
            Logger.__instance[module] = Logger(module)
        return Logger.__instance.get(module)


def __append_log_queue(level, text):
    global LOG_INDEX, LOG_QUEUE
    with lock:
        LOG_QUEUE.append(f"{time.strftime('%H:%M:%S', time.localtime(time.time()))} {level} - {escape(text)}")
        LOG_INDEX += 1


def debug(text, module=None):
    return Logger.get_instance(module).logger.debug(text)


def info(text, module=None):
    __append_log_queue("INFO", text)
    return Logger.get_instance(module).logger.info(text)


def error(text, module=None):
    __append_log_queue("ERROR", text)
    return Logger.get_instance(module).logger.error(text)


def warn(text, module=None):
    __append_log_queue("WARN", text)
    return Logger.get_instance(module).logger.warning(text)


def console(text):
    __append_log_queue("INFO", text)
    print(text)
