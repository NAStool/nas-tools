import regex as re

from app.helper import DbHelper
from app.utils.commons import singleton
from app.utils.exception_utils import ExceptionUtils


@singleton
class WordsHelper:
    dbhelper = None
    # 识别词
    words_info = []
    # 标题
    title = ""
    # 错误信息
    msg = []
    # 应用自定义识别
    used_ignored_words = []
    # 应用替换
    used_replaced_words = []
    # 应用集偏移
    used_offset_words = []

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.reset()
        self.dbhelper = DbHelper()
        self.words_info = self.dbhelper.get_custom_words(enabled=1)

    def process(self, title):
        # 初始化
        self.reset()
        self.title = title
        # 应用识别词
        for word_info in self.words_info:
            match word_info.TYPE:
                case 1:
                    # 屏蔽
                    self.check_ignore(word_info.REPLACED, word_info.REGEX)
                case 2:
                    # 替换
                    self.check_replace(word_info.REPLACED, word_info.REPLACE, word_info.REGEX)
                case 3:
                    # 替换+集偏移
                    self.check_replace_offset(word_info.REPLACED,
                                              word_info.REPLACE,
                                              word_info.FRONT,
                                              word_info.BACK,
                                              word_info.OFFSET)
                case 4:
                    # 集数偏移
                    self.check_offset(word_info.FRONT, word_info.BACK, word_info.OFFSET)
                case _:
                    pass
        # # 应用识别词信息
        used_info = {
            "ignored": self.used_ignored_words,
            "replaced": self.used_replaced_words,
            "offset": self.used_offset_words}
        return self.title, self.msg, used_info

    def check_ignore(self, ignored, regex=0):
        ignored_word = ignored
        ignore_msg, ignore_flag = self.replace_regex(ignored, "") \
            if regex else self.replace_noregex(ignored, "")
        if ignore_flag:
            self.used_ignored_words.append(ignored_word)
        elif ignore_msg:
            self.msg.append(f"自定义屏蔽词 {ignored_word} 设置有误：{ignore_msg}")

    def check_replace(self, replaced, replace, regex=0):
        replaced_word = f"{replaced} ⇒ {replace}"
        replace_msg, replace_flag = self.replace_regex(replaced, replace) \
            if regex else self.replace_noregex(replaced, replace)
        if replace_flag:
            self.used_replaced_words.append(replaced_word)
        elif replace_msg:
            self.msg.append(f"自定义替换词 {replaced_word} 格式有误：{replace_msg}")

    def check_replace_offset(self, replaced, replace, front, back, offset):
        replaced_word = f"{replaced} ⇒ {replace}"
        offset_word = f"{front} + {back} >> {offset}"
        replaced_offset_word = f"{replaced_word} @@@ {offset_word}"
        # 记录替换前title
        title_cache = self.title
        # 替换
        replace_msg, replace_flag = self.replace_regex(replaced, replace)
        # 替换应用成功进行集数偏移
        if replace_flag:
            offset_msg, offset_flag = self.episode_offset(front, back, offset)
            # 集数偏移应用成功
            if offset_flag:
                self.used_replaced_words.append(replaced_word)
                self.used_offset_words.append(offset_word)
            elif offset_msg:
                # 还原title
                self.title = title_cache
                self.msg.append(f"自定义替换+集偏移词 {replaced_offset_word} 集偏移部分格式有误：{offset_msg}")
        elif replace_msg:
            self.msg.append(f"自定义替换+集偏移词 {replaced_offset_word} 替换部分格式有误：{replace_msg}")

    def check_offset(self, front, back, offset):
        offset_word = f"{front} + {back} >> {offset}"
        offset_msg, offset_flag = self.episode_offset(front, back, offset)
        if offset_flag:
            self.used_offset_words.append(offset_word)
        elif offset_msg:
            self.msg.append(f"自定义集偏移词 {offset_word} 格式有误：{offset_msg}")

    def replace_regex(self, replaced, replace) -> (str, bool):
        title = self.title
        try:
            if not re.findall(r'%s' % replaced, title):
                return "", False
            else:
                self.title = re.sub(r'%s' % replaced, r'%s' % replace, title)
                return "", True
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return str(err), False

    def replace_noregex(self, replaced, replace) -> (str, bool):
        title = self.title
        try:
            if title.find(replaced) == -1:
                return "", False
            else:
                self.title = title.replace(replaced, replace)
                return "", True
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return str(err), False

    def episode_offset(self, front, back, offset) -> (str, bool):
        title = self.title
        try:
            if back and not re.findall(r'%s' % back, title):
                return "", False
            if front and not re.findall(r'%s' % front, title):
                return "", False
            offset_word_info_re = re.compile(r'(?<=%s.*?)[0-9]+(?=.*?%s)' % (front, back))
            episode_nums_str = re.findall(offset_word_info_re, title)
            if not episode_nums_str:
                return "", False
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
                self.title = re.sub(episode_offset_re, r'%s' % str(episode_num[1]).zfill(2), title)
            return "", True
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return str(err), False

    def reset(self):
        self.title = ""
        self.msg = []
        self.used_ignored_words = []
        self.used_replaced_words = []
        self.used_offset_words = []
