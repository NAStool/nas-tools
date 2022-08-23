# -*- coding: utf-8 -*-
import re
import threading

import parse

# 线程锁
lock = threading.RLock()
# 种子名/文件名要素分隔字符
SPLIT_CHARS = r"\.|\s+|\(|\)|\[|]|-|\+|【|】|/|～|;|&|\||#|_|「|」|（|）"
# 全局实例
INSTANCES = {}


# 单例模式注解
def singleton(cls):
    # 创建字典用来保存类的实例对象
    global INSTANCES

    def _singleton(*args, **kwargs):
        # 先判断这个类有没有对象
        if cls not in INSTANCES:
            with lock:
                if cls not in INSTANCES:
                    INSTANCES[cls] = cls(*args, **kwargs)
                    pass
        # 将实例对象返回
        return INSTANCES[cls]

    return _singleton


class EpisodeFormat(object):
    __key = ""

    def __init__(self, eformat, details: str = None, offset=None, key="ep"):
        self.__format = eformat
        self.__start_ep = None
        self.__end_ep = None
        if details:
            if re.compile("\\d{1,4}-\\d{1,4}").match(details):
                self.__start_ep = details
                self.__end_ep = details
            else:
                tmp = details.split(",")
                if len(tmp) > 1:
                    self.__start_ep = int(tmp[0])
                    self.__end_ep = int(tmp[0]) if int(tmp[0]) > int(tmp[1]) else int(tmp[1])
                else:
                    self.__start_ep = self.__end_ep = int(tmp[0])
        self.__offset = int(offset) if offset else 0
        self.__key = key

    @property
    def format(self):
        return self.__format

    @property
    def start_ep(self):
        return self.__start_ep

    @property
    def end_ep(self):
        return self.__end_ep

    @property
    def offset(self):
        return self.__offset

    def match(self, file: str):
        if not self.__format:
            return True
        s, e = self.__handle_single(file)
        if not s:
            return False
        if self.__start_ep is None:
            return True
        if self.__start_ep <= s <= self.__end_ep:
            return True
        return False

    def split_episode(self, file_name):
        # 指定的具体集数，直接返回
        if self.__start_ep is not None and self.__start_ep == self.__end_ep:
            if isinstance(self.__start_ep, str):
                s, e = self.__start_ep.split("-")
                if int(s) == int(e):
                    return int(s) + self.__offset, None
                return int(s) + self.__offset, int(e) + self.__offset
            return self.__start_ep + self.__offset, None
        if not self.__format:
            return None, None
        s, e = self.__handle_single(file_name)
        return s + self.__offset if s is not None else None, e + self.__offset if e is not None else None

    def __handle_single(self, file: str):
        if not self.__format:
            return None, None
        ret = parse.parse(self.__format, file)
        if not ret or not ret.__contains__(self.__key):
            return None, None
        episodes = ret.__getitem__(self.__key)
        if not re.compile(r"^(EP)?(\d{1,4})(-(EP)?(\d{1,4}))?$", re.IGNORECASE).match(episodes):
            return None, None
        episode_splits = list(filter(lambda x: re.compile(r'[a-zA-Z]*\d{1,4}', re.IGNORECASE).match(x),
                                     re.split(r'%s' % SPLIT_CHARS, episodes)))
        if len(episode_splits) == 1:
            return int(re.compile(r'[a-zA-Z]*', re.IGNORECASE).sub("", episode_splits[0])), None
        else:
            return int(re.compile(r'[a-zA-Z]*', re.IGNORECASE).sub("", episode_splits[0])), int(
                re.compile(r'[a-zA-Z]*', re.IGNORECASE).sub("", episode_splits[1]))


@singleton
class ProcessHandler(object):
    _process_detail = None
    _enable = False

    def __init__(self):
        self.reset()

    def reset(self):
        self._process_detail = {
            "value": 0,
            "text": "请稍候..."
        }

    def start(self):
        self.reset()
        self._enable = True

    def end(self):
        self._enable = False

    def update(self, value=None, text=None):
        if not self._enable:
            return
        if value:
            self._process_detail['value'] = value
        if text:
            self._process_detail['text'] = text

    def get_process(self):
        if self._enable:
            return self._process_detail
        else:
            return None
