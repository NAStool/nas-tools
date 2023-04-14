import regex as re

from app.helper import DbHelper
from app.utils.commons import singleton
from app.utils.exception_utils import ExceptionUtils


@singleton
class WordsHelper:
    dbhelper = None
    # 识别词
    words_info = []

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()
        self.words_info = self.dbhelper.get_custom_words(enabled=1)

    def process(self, title):
        # 错误信息
        msg = []
        # 应用自定义识别
        used_ignored_words = []
        # 应用替换
        used_replaced_words = []
        # 应用集偏移
        used_offset_words = []
        # 应用识别词
        for word_info in self.words_info:
            match word_info.TYPE:
                case 1:
                    # 屏蔽
                    ignored = word_info.REPLACED
                    ignored_word = ignored
                    title, ignore_msg, ignore_flag = self.replace_regex(title, ignored, "") \
                        if word_info.REGEX else self.replace_noregex(title, ignored, "")
                    if ignore_flag:
                        used_ignored_words.append(ignored_word)
                    elif ignore_msg:
                        msg.append(f"自定义屏蔽词 {ignored_word} 设置有误：{ignore_msg}")
                case 2:
                    # 替换
                    replaced, replace = word_info.REPLACED, word_info.REPLACE
                    replaced_word = f"{replaced} ⇒ {replace}"
                    title, replace_msg, replace_flag = self.replace_regex(title, replaced, replace) \
                        if word_info.REGEX else self.replace_noregex(title, replaced, replace)
                    if replace_flag:
                        used_replaced_words.append(replaced_word)
                    elif replace_msg:
                        msg.append(f"自定义替换词 {replaced_word} 格式有误：{replace_msg}")

                case 3:
                    # 替换+集偏移
                    replaced, replace, front, back, offset = \
                        word_info.REPLACED, word_info.REPLACE, word_info.FRONT, word_info.BACK, word_info.OFFSET
                    replaced_word = f"{replaced} ⇒ {replace}"
                    offset_word = f"{front} + {back} >> {offset}"
                    replaced_offset_word = f"{replaced_word} @@@ {offset_word}"
                    # 记录替换前title
                    title_cache = title
                    # 替换
                    title, replace_msg, replace_flag = self.replace_regex(title, replaced, replace)
                    # 替换应用成功进行集数偏移
                    if replace_flag:
                        title, offset_msg, offset_flag = self.episode_offset(title, front, back, offset)
                        # 集数偏移应用成功
                        if offset_flag:
                            used_replaced_words.append(replaced_word)
                            used_offset_words.append(offset_word)
                        elif offset_msg:
                            # 还原title
                            title = title_cache
                            msg.append(
                                f"自定义替换+集偏移词 {replaced_offset_word} 集偏移部分格式有误：{offset_msg}")
                    elif replace_msg:
                        msg.append(f"自定义替换+集偏移词 {replaced_offset_word} 替换部分格式有误：{replace_msg}")
                case 4:
                    # 集数偏移
                    front, back, offset = word_info.FRONT, word_info.BACK, word_info.OFFSET
                    offset_word = f"{front} + {back} >> {offset}"
                    title, offset_msg, offset_flag = self.episode_offset(title, front, back, offset)
                    if offset_flag:
                        used_offset_words.append(offset_word)
                    elif offset_msg:
                        msg.append(f"自定义集偏移词 {offset_word} 格式有误：{offset_msg}")
                case _:
                    pass
        return title, msg, {"ignored": used_ignored_words, "replaced": used_replaced_words, "offset": used_offset_words}

    @staticmethod
    def replace_regex(title, replaced, replace) -> (str, str, bool):
        try:
            if not re.findall(r'%s' % replaced, title):
                return title, "", False
            else:
                return re.sub(r'%s' % replaced, r'%s' % replace, title), "", True
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return title, str(err), False

    @staticmethod
    def replace_noregex(title, replaced, replace) -> (str, str, bool):
        try:
            if title.find(replaced) == -1:
                return title, "", False
            else:
                return title.replace(replaced, replace), "", True
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return title, str(err), False

    @staticmethod
    def episode_offset(title, front, back, offset) -> (str, str, bool):
        try:
            if back and not re.findall(r'%s' % back, title):
                return title, "", False
            if front and not re.findall(r'%s' % front, title):
                return title, "", False
            offset_word_info_re = re.compile(r'(?<=%s.*?)[0-9]+(?=.*?%s)' % (front, back))
            episode_nums_str = re.findall(offset_word_info_re, title)
            if not episode_nums_str:
                return title, "", False
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
            return title, "", True
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return title, str(err), False
