import re

from config import SPLIT_CHARS


class Tokens:
    __text = ""
    __index = 0
    __tokens = []

    def __init__(self, text):
        self.__text = text
        self.__tokens = []
        self.load_text(text)

    def load_text(self, text):
        splited_text = re.split(r'%s' % SPLIT_CHARS, text)
        for sub_text in splited_text:
            if sub_text:
                self.__tokens.append(sub_text)

    def cur(self):
        if self.__index >= len(self.__tokens):
            return None
        else:
            token = self.__tokens[self.__index]
            return token

    def get_next(self):
        token = self.cur()
        if token:
            self.__index = self.__index + 1
        return token

    def peek(self):
        index = self.__index + 1
        if index >= len(self.__tokens):
            return None
        else:
            return self.__tokens[index]
