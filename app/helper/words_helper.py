import regex as re

from app.helper import DbHelper
from app.utils.commons import singleton
from app.utils.exception_utils import ExceptionUtils


@singleton
class WordsHelper:
    dbhelper = None
    ignored_words_info = []
    ignored_words_noregex_info = []
    replaced_words_info = []
    replaced_words_noregex_info = []
    replaced_offset_words_info = []
    offset_words_info = []

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()
        self.ignored_words_info = self.dbhelper.get_custom_words(enabled=1, wtype=1, regex=1)
        self.ignored_words_noregex_info = self.dbhelper.get_custom_words(enabled=1, wtype=1, regex=0)
        self.replaced_words_info = self.dbhelper.get_custom_words(enabled=1, wtype=2, regex=1)
        self.replaced_words_noregex_info = self.dbhelper.get_custom_words(enabled=1, wtype=2, regex=0)
        self.replaced_offset_words_info = self.dbhelper.get_custom_words(enabled=1, wtype=3, regex=1)
        self.offset_words_info = self.dbhelper.get_custom_words(enabled=1, wtype=4, regex=1)

    def process(self, title):
        # 错误信息
        msg = []
        # 应用自定义识别
        used_ignored_words = []
        # 应用替换
        used_replaced_words = []
        # 应用集偏移
        used_offset_words = []
        # 屏蔽
        if self.ignored_words_info:
            for ignored_word_info in self.ignored_words_info:
                ignored = ignored_word_info.REPLACED
                ignored_word = ignored
                title, ignore_msg, ignore_flag = self.replace_regex(replaced=ignored,
                                                                    replace="",
                                                                    title=title)
                if ignore_flag:
                    used_ignored_words.append(ignored_word)
                elif ignore_msg:
                    msg.append(f"自定义屏蔽词 {ignored_word} 设置有误：{ignore_msg}")
        if self.ignored_words_noregex_info:
            for ignored_word_noregex_info in self.ignored_words_noregex_info:
                ignored = ignored_word_noregex_info.REPLACED
                ignored_word = ignored
                title, ignore_msg, ignore_flag = self.replace_noregex(replaced=ignored,
                                                                      replace="",
                                                                      title=title)
                if ignore_flag:
                    used_ignored_words.append(ignored_word)
                elif ignore_msg:
                    msg.append(f"自定义屏蔽词 {ignored_word} 设置有误：{ignore_msg}")
        # 替换
        if self.replaced_words_info:
            for replaced_word_info in self.replaced_words_info:
                replaced = replaced_word_info.REPLACED
                replace = replaced_word_info.REPLACE
                replaced_word = f"{replaced}@{replace}"
                title, replace_msg, replace_flag = self.replace_regex(replaced=replaced,
                                                                      replace=replace,
                                                                      title=title)
                if replace_flag:
                    used_replaced_words.append(replaced_word)
                elif replace_msg:
                    msg.append(f"自定义替换词 {replaced_word} 格式有误：{replace_msg}")
        if self.replaced_words_noregex_info:
            for replaced_word_noregex_info in self.replaced_words_noregex_info:
                replaced = replaced_word_noregex_info.REPLACED
                replace = replaced_word_noregex_info.REPLACE
                replaced_word = f"{replaced}@{replace}"
                title, replace_msg, replace_flag = self.replace_noregex(replaced=replaced,
                                                                        replace=replace,
                                                                        title=title)
                if replace_flag:
                    used_replaced_words.append(replaced_word)
                elif replace_msg:
                    msg.append(f"自定义替换词 {replaced_word} 格式有误：{replace_msg}")
        # 替换+集偏移
        if self.replaced_offset_words_info:
            for replaced_offset_word_info in self.replaced_offset_words_info:
                replaced = replaced_offset_word_info.REPLACED
                replace = replaced_offset_word_info.REPLACE
                front = replaced_offset_word_info.FRONT
                back = replaced_offset_word_info.BACK
                offset = replaced_offset_word_info.OFFSET
                replaced_word = f"{replaced}@{replace}"
                offset_word = f"{front}@{back}@{offset}"
                replaced_offset_word = f"{replaced}@{replace}@{front}@{back}@{offset}"
                # 替换
                title_replace, replace_msg, replace_flag = self.replace_regex(replaced=replaced,
                                                                              replace=replace,
                                                                              title=title)
                # 替换应用成功进行集数偏移
                if replace_flag:
                    title_offset, offset_msg, offset_flag = self.episode_offset(front=front,
                                                                                back=back,
                                                                                offset=offset,
                                                                                title=title_replace)
                    # 集数偏移应用成功
                    if offset_flag:
                        used_replaced_words.append(replaced_word)
                        used_offset_words.append(offset_word)
                        title = title_offset
                    elif offset_msg:
                        msg.append(f"自定义替换+集偏移词 {replaced_offset_word} 集偏移部分格式有误：{offset_msg}")
                elif replace_msg:
                    msg.append(f"自定义替换+集偏移词 {replaced_offset_word} 替换部分格式有误：{replace_msg}")
        # 集数偏移
        if self.offset_words_info:
            for offset_word_info in self.offset_words_info:
                front = offset_word_info.FRONT
                back = offset_word_info.BACK
                offset = offset_word_info.OFFSET
                offset_word = f"{front}@{back}@{offset}"
                title, offset_msg, offset_flag = self.episode_offset(front, back, offset, title)
                if offset_flag:
                    used_offset_words.append(offset_word)
                elif offset_msg:
                    msg.append(f"自定义集偏移词 {offset_word} 格式有误：{offset_msg}")

        return title, msg, {"ignored": used_ignored_words,
                            "replaced": used_replaced_words,
                            "offset": used_offset_words}

    @staticmethod
    def replace_regex(replaced, replace, title):
        msg = ""
        try:
            if not re.findall(r'%s' % replaced, title):
                return title, msg, False
            else:
                title = re.sub(r'%s' % replaced, r'%s' % replace, title)
                return title, msg, True
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            msg = str(err)
            return title, msg, False

    @staticmethod
    def replace_noregex(replaced, replace, title):
        msg = ""
        try:
            if title.find(replaced) == -1:
                return title, msg, False
            else:
                title = title.replace(replaced, replace)
                return title, msg, True
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            msg = str(err)
            return title, msg, False

    @staticmethod
    def episode_offset(front, back, offset, title):
        msg = ""
        try:
            if back and not re.findall(r'%s' % back, title):
                return title, msg, False
            if front and not re.findall(r'%s' % front, title):
                return title, msg, False
            offset_word_info_re = re.compile(r'(?<=%s.*?)[0-9]+(?=.*?%s)' % (front, back))
            episode_nums_str = re.findall(offset_word_info_re, title)
            if not episode_nums_str:
                return title, msg, False
            episode_nums_offset_int = []
            offset_order_flag = False
            for episode_num_str in episode_nums_str:
                episode_num_int = int(episode_num_str)
                offset_caculate = offset.replace("EP", str(episode_num_int))
                episode_num_offset_int = eval(offset_caculate)
                # 向前偏移
                if episode_num_int > episode_num_offset_int:
                    offset_order_flag = True
                # 向后偏移
                else:
                    offset_order_flag = False
                episode_nums_offset_int.append(episode_num_offset_int)
            episode_nums_dict = dict(zip(episode_nums_str, episode_nums_offset_int))
            # 集数向前偏移，集数按升序处理
            if offset_order_flag:
                episode_nums_list = sorted(episode_nums_dict.items(), key=lambda x: x[1])
            # 集数向后偏移，集数按降序处理
            else:
                episode_nums_list = sorted(episode_nums_dict.items(), key=lambda x: x[1], reverse=True)
            for episode_num in episode_nums_list:
                episode_offset_re = re.compile(
                    r'(?<=%s.*?)%s(?=.*?%s)' % (front, episode_num[0], back))
                title = re.sub(episode_offset_re, r'%s' % str(episode_num[1]).zfill(2), title)
            return title, msg, True
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            msg = str(err)
            return title, msg, False
