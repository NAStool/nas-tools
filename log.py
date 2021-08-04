import logging
import os
import settings


class Logger:
    def __init__(self, logname):
        self.logger = logging.Logger(logname.upper())
        self.logger.setLevel(level=logging.DEBUG)
        logpath = settings.get("root.logpath")
        if not os.path.exists(logpath):
            os.makedirs(logpath)
        handler = logging.FileHandler(logpath + "/" + logname + ".txt")
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        self.logger.addHandler(handler)
        self.logger.addHandler(console)
