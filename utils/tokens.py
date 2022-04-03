import re


class Tokens:
    __text = ""
    __index = 0
    __tokens = []

    def __init__(self, text):
        self.__text = text
        self.__tokens = []
        self.load_text(text)

    def load_text(self, text):
        splited_text = re.split(r'\.|\s+|\(|\)|\[|]|-|\+|【|】|/|～|;|&|\||#|_|「|」|（|）', text)
        for sub_text in splited_text:
            if sub_text:
                self.__tokens.append(sub_text)

    def get_next(self):
        if self.__index >= len(self.__tokens):
            return None
        else:
            token = self.__tokens[self.__index]
            self.__index = self.__index + 1
            return token
