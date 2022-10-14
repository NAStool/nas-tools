import regex as re

from app.helper import SqlHelper
from app.utils.commons import singleton


@singleton
class WordsHelper:

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.ignored_words_info = SqlHelper.get_ignored_words_enable()
        self.replaced_words_info = SqlHelper.get_replaced_words_enable_with_offset()
        self.offset_words_info = SqlHelper.get_offset_words_unrelated_enable()

    def process(self, title):
        # 错误信息
        msg = ""
        # 应用自定义识别词
        used_ignored_words = []
        # 应用替换词
        used_replaced_words = []
        # 应用集数偏移
        used_offset_words = []
        # 屏蔽词
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
        # 替换词
        replaced_words_id = -1
        replaced_words_match_flag = False
        if self.replaced_words_info:
            for replaced_word_info in self.replaced_words_info:
                try:
                    replaced = replaced_word_info[1]
                    replace = replaced_word_info[2]
                    front = replaced_word_info[3]
                    offest_word_enabled = replaced_word_info[6]
                    if replaced_words_id != replaced_word_info[0]:
                        replaced_words_id = replaced_word_info[0]
                        replaced_word = "%s@%s" % (replaced, replace)
                        replaced_words_match_flag = False
                        if re.findall(r'%s' % replaced, title):
                            replaced_words_match_flag = True
                            used_replaced_words.append(replaced_word)
                            title = re.sub(r'%s' % replaced, r'%s' % replace, title)
                    if offest_word_enabled == 1 and replaced_words_match_flag:
                        front = replaced_word_info[3]
                        back = replaced_word_info[4]
                        offset = replaced_word_info[5]
                        title, msg = self.episode_offset(front, back, offset, used_offset_words, title)
                except Exception as err:
                    msg = "【Meta】自定义替换词 %s 格式有误：%s" % (replaced_word_info, str(err))
        # 集数偏移
        if self.offset_words_info:
            for offset_word_info in self.offset_words_info:
                front = offset_word_info[1]
                back = offset_word_info[2]
                offset = offset_word_info[3]
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
