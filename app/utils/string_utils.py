import bisect
import random
import re


class StringUtils:

    @staticmethod
    def num_filesize(text):
        """
        将文件大小文本转化为字节
        """
        if not text:
            return 0
        if not isinstance(text, str):
            text = str(text)
        text = text.replace(",", "").replace(" ", "").upper()
        size = re.sub(r"[KMGTPI]*B", "", text, flags=re.IGNORECASE)
        try:
            size = float(size)
        except Exception as e:
            print(str(e))
            return 0
        if text.find("PB") != -1 or text.find("PIB") != -1:
            size *= 1024 ** 5
        elif text.find("TB") != -1 or text.find("TIB") != -1:
            size *= 1024 ** 4
        elif text.find("GB") != -1 or text.find("GIB") != -1:
            size *= 1024 ** 3
        elif text.find("MB") != -1 or text.find("MIB") != -1:
            size *= 1024 ** 2
        elif text.find("KB") != -1 or text.find("KIB") != -1:
            size *= 1024
        return round(size)

    @staticmethod
    def str_timelong(time_sec):
        """
        将数字转换为时间描述
        """
        if not isinstance(time_sec, int) or not isinstance(time_sec, float):
            try:
                time_sec = float(time_sec)
            except Exception as e:
                print(str(e))
                return ""
        d = [(0, '秒'), (60 - 1, '分'), (3600 - 1, '小时'), (86400 - 1, '天')]
        s = [x[0] for x in d]
        index = bisect.bisect_left(s, time_sec) - 1
        if index == -1:
            return str(time_sec)
        else:
            b, u = d[index]
        return str(round(time_sec / (b + 1))) + u

    @staticmethod
    def is_chinese(word):
        """
        判断是否含有中文
        """
        for ch in word:
            if '\u4e00' <= ch <= '\u9fff':
                return True
        return False

    @staticmethod
    def is_all_chinese(word):
        """
        判断是否全是中文
        """
        for ch in word:
            if ch == ' ':
                continue
            if '\u4e00' <= ch <= '\u9fff':
                continue
            else:
                return False
        return True

    @staticmethod
    def xstr(s):
        """
        字符串None输出为空
        """
        return s if s else ''

    @staticmethod
    def str_sql(in_str):
        """
        转化SQL字符
        """
        return "" if not in_str else str(in_str)

    @staticmethod
    def str_int(text):
        """
        web字符串转int
        :param text:
        :return:
        """
        int_val = 0
        try:
            int_val = int(text.strip().replace(',', ''))
        except Exception as e:
            print(str(e))

        return int_val

    @staticmethod
    def str_float(text):
        """
        web字符串转float
        :param text:
        :return:
        """
        float_val = 0.0
        try:
            float_val = float(text.strip().replace(',', ''))
        except Exception as e:
            print(str(e))
        return float_val

    @staticmethod
    def handler_special_chars(text, replace_word="", allow_space=False):
        """
        忽略特殊字符
        """
        # 需要忽略的特殊字符
        CONVERT_EMPTY_CHARS = r"\.|\(|\)|\[|]|-|\+|【|】|/|～|;|&|\||#|_|「|」|（|）|'|’|!|！|,|～|·|:|：|\-"
        if not text:
            return ""
        text = re.sub(r"[\u200B-\u200D\uFEFF]", "", re.sub(r"%s" % CONVERT_EMPTY_CHARS, replace_word, text),
                      flags=re.IGNORECASE)
        if not allow_space:
            return re.sub(r"\s+", "", text)
        else:
            return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def str_filesize(size):
        """
        将字节计算为文件大小描述
        """
        if not isinstance(size, int) or not isinstance(size, float):
            try:
                size = float(size)
            except Exception as e:
                print(str(e))
                return ""
        d = [(1024 - 1, 'K'), (1024 ** 2 - 1, 'M'), (1024 ** 3 - 1, 'G'), (1024 ** 4 - 1, 'T')]
        s = [x[0] for x in d]
        index = bisect.bisect_left(s, size) - 1
        if index == -1:
            return str(size)
        else:
            b, u = d[index]
        return str(round(size / (b + 1), 2)) + u

    @staticmethod
    def generate_random_str(randomlength=16):
        """
        生成一个指定长度的随机字符串
        """
        random_str = ''
        base_str = 'ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789'
        length = len(base_str) - 1
        for i in range(randomlength):
            random_str += base_str[random.randint(0, length)]
        return random_str
