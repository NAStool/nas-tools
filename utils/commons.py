# -*- coding: utf-8 -*-
import parse
import re
from config import SPLIT_CHARS


class EpisodeFormat(object):

    __key = ""

    def __init__(self, format, details: str = None, offset = None, key = "ep"):
        self.__format = format
        self.__start_ep = None
        self.__end_ep = None
        if details:
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
        if self.__format is None:
            return False
        ret = parse.parse(self.__format, file)
        if not ret:
            return False
        if self.__start_ep is None:
            return True
        s, e = self.__handle_single(ret)
        if self.__start_ep <= s <= self.__end_ep:
            return True
        return False

    def split_episode(self, file_name):
        # 指定的具体集数，直接返回
        if self.__start_ep and self.__start_ep == self.__end_ep:
            return self.__start_ep + self.__offset, None
        if not self.__format:
            return None, None
        ret = parse.parse(self.__format, file_name)
        if ret:
            s, e = self.__handle_single(ret)
            return s + self.__offset, e + self.__offset if e else None
        else:
            return None, None

    def __handle_single(self, parse_ret):
        episodes = parse_ret.__getitem__(self.__key)
        episode_splits = list(filter(lambda x: re.compile(r'[a-zA-Z]*\d{1,4}', re.IGNORECASE).match(x),
                                     re.split(r'%s' % SPLIT_CHARS, episodes)))
        if len(episode_splits) == 1:
            return int(re.compile(r'[a-zA-Z]*', re.IGNORECASE).sub("", episode_splits[0])), None
        else:
            return int(re.compile(r'[a-zA-Z]*', re.IGNORECASE).sub("", episode_splits[0])), int(
                re.compile(r'[a-zA-Z]*', re.IGNORECASE).sub("", episode_splits[1]))
