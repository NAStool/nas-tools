import regex as re

from app.helper import SqlHelper
from app.utils.commons import singleton


@singleton
class WordsHelper:
    ignored_words_info = []
    ignored_words_noregex_info = []
    replaced_words_info = []
    replaced_words_noregex_info = []
    replaced_offset_words_info = []
    offset_words_info = []

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.ignored_words_info = SqlHelper.get_custom_words(enabled=1, wtype=1, regex=1)
        self.ignored_words_noregex_info = SqlHelper.get_custom_words(enabled=1, wtype=1, regex=0)
        self.replaced_words_info = SqlHelper.get_custom_words(enabled=1, wtype=2, regex=1)
        self.replaced_words_noregex_info = SqlHelper.get_custom_words(enabled=1, wtype=2, regex=0)
        self.replaced_offset_words_info = SqlHelper.get_custom_words(enabled=1, wtype=3, regex=1)
        self.offset_words_info = SqlHelper.get_custom_words(enabled=1, wtype=4, regex=1)

    def process(self, title):
        # 错误信息
        msg = ""
        # 应用自定义识别
        used_ignored_words = []
        # 应用替换
        used_replaced_words = []
        # 应用集偏移
        used_offset_words = []
        # 屏蔽
        if self.ignored_words_info:
            try:
                ignored_words = []
                for ignored_word_info in self.ignored_words_info:
                    ignored_words.append(ignored_word_info[1])
                ignored_words = "|".join(ignored_words)
                ignored_words = re.compile(r'%s' % ignored_words)
                # 去重
                used_ignored_words = list(set(re.findall(ignored_words, title)))
                if used_ignored_words:
                    title = re.sub(ignored_words, '', title)
            except Exception as err:
                msg = "【Meta】自定义屏蔽词设置有误：%s" % str(err)
        if self.ignored_words_noregex_info:
            try:
                for ignored_word_noregex_info in self.ignored_words_noregex_info:
                    ignored_word = ignored_word_noregex_info[1]
                    if title.find(ignored_word) != -1:
                        title = title.replace(ignored_word, '')
                        used_ignored_words.append(ignored_word)
            except Exception as err:
                msg = "【Meta】自定义屏蔽词设置有误：%s" % str(err)
        # 替换
        if self.replaced_words_info:
            for replaced_word_info in self.replaced_words_info:
                try:
                    replaced = replaced_word_info[1]
                    replace = replaced_word_info[2]
                    replaced_word = "%s@%s" % (replaced, replace)
                    if re.findall(r'%s' % replaced, title):
                        used_replaced_words.append(replaced_word)
                        title = re.sub(r'%s' % replaced, r'%s' % replace, title)
                except Exception as err:
                    msg = "【Meta】自定义替换词 %s 格式有误：%s" % (replaced_word_info, str(err))
        if self.replaced_words_noregex_info:
            for replaced_word_noregex_info in self.replaced_words_noregex_info:
                try:
                    replaced = replaced_word_noregex_info[1]
                    replace = replaced_word_noregex_info[2]
                    replaced_word = "%s@%s" % (replaced, replace)
                    if title.find(replaced) != -1:
                        used_replaced_words.append(replaced_word)
                        title = title.replace(replaced, replace)
                except Exception as err:
                    msg = "【Meta】自定义替换词 %s 格式有误：%s" % (replaced_word_noregex_info, str(err))
        # 替换+集偏移
        if self.replaced_offset_words_info:
            for replaced_offset_word_info in self.replaced_offset_words_info:
                try:
                    replaced = replaced_offset_word_info[1]
                    replace = replaced_offset_word_info[2]
                    front = replaced_offset_word_info[3]
                    back = replaced_offset_word_info[4]
                    offset = replaced_offset_word_info[5]
                    replaced_word = "%s@%s" % (replaced, replace)
                    if re.findall(r'%s' % replaced, title):
                        used_replaced_words.append(replaced_word)
                        title = re.sub(r'%s' % replaced, r'%s' % replace, title)
                        title, msg = self.episode_offset(front, back, offset, used_offset_words, title)
                except Exception as err:
                    msg = "【Meta】自定义替换+集偏移词 %s 格式有误：%s" % (replaced_offset_word_info, str(err))
        # 集数偏移
        if self.offset_words_info:
            for offset_word_info in self.offset_words_info:
                front = offset_word_info[3]
                back = offset_word_info[4]
                offset = offset_word_info[5]
                title, msg = self.episode_offset(front, back, offset, used_offset_words, title)

        return title, msg, {"ignored": used_ignored_words,
                            "replaced": used_replaced_words,
                            "offset": used_offset_words}

    @staticmethod
    def episode_offset(front, back, offset, used_offset_words, title):
        msg = ""
        offset_num = int(offset)
        offset_word = "%s@%s@%s" % (front, back, offset)
        try:
            if back and not re.findall(r'%s' % back, title):
                return title, msg
            if front and not re.findall(r'%s' % front, title):
                return title, msg
            offset_word_info_re = re.compile(r'(?<=%s[\W\w]*)[0-9]+(?=[\W\w]*%s)' % (front, back))
            episode_nums_str = re.findall(offset_word_info_re, title)
            if not episode_nums_str:
                return title, msg
            episode_nums_int = [int(x) for x in episode_nums_str]
            episode_nums_dict = dict(zip(episode_nums_str, episode_nums_int))
            used_offset_words.append(offset_word)
            # 集数向前偏移，集数按升序处理
            if offset_num < 0:
                episode_nums_list = sorted(episode_nums_dict.items(), key=lambda x: x[1])
            # 集数向后偏移，集数按降序处理
            else:
                episode_nums_list = sorted(episode_nums_dict.items(), key=lambda x: x[1], reverse=True)
            for episode_num in episode_nums_list:
                episode_offset_re = re.compile(
                    r'(?<=%s[\W\w]*)%s(?=[\W\w]*%s)' % (front, episode_num[0], back))
                title = re.sub(episode_offset_re, r'%s' % str(episode_num[1] + offset_num).zfill(2), title)
            return title, msg
        except Exception as err:
            msg = "自定义集数偏移 %s 格式有误：%s" % (offset_word, str(err))
            return title, msg
