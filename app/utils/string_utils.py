import bisect
import random
import re
import time
import datetime
from urllib import parse

import cn2an
from app.utils.types import MediaType


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
        size = re.sub(r"[KMGTPI]*B?", "", text, flags=re.IGNORECASE)
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
        chn = re.compile(r'[\u4e00-\u9fff]')
        if chn.search(word):
            return True
        else:
            return False

    @staticmethod
    def is_japanese(word):
        jap = re.compile(r'[\u3040-\u309F\u30A0-\u30FF]')
        if jap.search(word):
            return True
        else:
            return False

    @staticmethod
    def is_korean(word):
        kor = re.compile(r'[\uAC00-\uD7FF]')
        if kor.search(word):
            return True
        else:
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
        CONVERT_EMPTY_CHARS = r"\.|\(|\)|\[|]|-|\+|【|】|/|～|;|&|\||#|_|「|」|（|）|'|’|!|！|,|～|·|:|：|\-|~"
        if not text:
            return ""
        text = re.sub(r"[\u200B-\u200D\uFEFF]", "", re.sub(r"%s" % CONVERT_EMPTY_CHARS, replace_word, text),
                      flags=re.IGNORECASE)
        if not allow_space:
            return re.sub(r"\s+", "", text)
        else:
            return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def str_filesize(size, pre=2):
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
        return str(round(size / (b + 1), pre)) + u

    @staticmethod
    def url_equal(url1, url2):
        """
        比较两个地址是否为同一个网站
        """
        if not url1 or not url2:
            return False
        if url1.startswith("http"):
            url1 = parse.urlparse(url1).netloc
        if url2.startswith("http"):
            url2 = parse.urlparse(url2).netloc
        if url1.replace("www.", "") == url2.replace("www.", ""):
            return True
        return False

    @staticmethod
    def get_url_netloc(url):
        """
        获取URL的协议和域名部分
        """
        if not url:
            return "", ""
        if not url.startswith("http"):
            return "http", url
        addr = parse.urlparse(url)
        return addr.scheme, addr.netloc

    @staticmethod
    def get_base_url(url):
        """
        获取URL根地址
        """
        scheme, netloc = StringUtils.get_url_netloc(url)
        return f"{scheme}://{netloc}"

    @staticmethod
    def clear_file_name(name):
        if not name:
            return None
        return re.sub(r"[*?\\/\"<>~]", "", name, flags=re.IGNORECASE).replace(":", "：")

    @staticmethod
    def get_keyword_from_string(content):
        """
        从检索关键字中拆分中年份、季、集、类型
        """
        if not content:
            return None, None, None, None, None
        # 去掉查询中的电影或电视剧关键字
        if re.search(r'^电视剧|\s+电视剧|^动漫|\s+动漫', content):
            mtype = MediaType.TV
        else:
            mtype = None
        content = re.sub(r'^电影|^电视剧|^动漫|\s+电影|\s+电视剧|\s+动漫', '', content).strip()
        # 稍微切一下剧集吧
        season_num = None
        episode_num = None
        year = None
        season_re = re.search(r"第\s*([0-9一二三四五六七八九十]+)\s*季", content, re.IGNORECASE)
        if season_re:
            mtype = MediaType.TV
            season_num = int(cn2an.cn2an(season_re.group(1), mode='smart'))
        episode_re = re.search(r"第\s*([0-9一二三四五六七八九十]+)\s*集", content, re.IGNORECASE)
        if episode_re:
            mtype = MediaType.TV
            episode_num = int(cn2an.cn2an(episode_re.group(1), mode='smart'))
            if episode_num and not season_num:
                season_num = 1
        year_re = re.search(r"[\s(]+(\d{4})[\s)]*", content)
        if year_re:
            year = year_re.group(1)
        key_word = re.sub(r'第\s*[0-9一二三四五六七八九十]+\s*季|第\s*[0-9一二三四五六七八九十]+\s*集|[\s(]+(\d{4})[\s)]*', '',
                          content,
                          flags=re.IGNORECASE).strip()
        if key_word:
            key_word = re.sub(r'\s+', ' ', key_word)
        if not key_word:
            key_word = year

        return mtype, key_word, season_num, episode_num, year, content

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

    @staticmethod
    def get_time_stamp(date):
        tempsTime = None
        try:
            result = re.search(r"[\-+]\d+", date)
            if result:
                time_area = result.group()
                utcdatetime = time.strptime(date, '%a, %d %b %Y %H:%M:%S ' + time_area)
                tempsTime = time.mktime(utcdatetime)
                tempsTime = datetime.datetime.fromtimestamp(tempsTime)
        except Exception as err:
            print(str(err))
        return tempsTime

    @staticmethod
    def unify_datetime_str(date_str):
        """
        日期时间格式化 统一转成 2020-10-14 07:48:04 这种格式
        """
        # 传入的参数如果是None 或者空字符串 直接返回
        if not date_str:
            return date_str
        # 判断日期时间是否满足 yyyy-MM-dd hh:MM:ss 格式
        if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", date_str):
            # 如果满足则直接返回
            return date_str

        # 场景1: 带有时区的日期字符串 eg: Sat, 15 Oct 2022 14:02:54 +0800
        try:
            return datetime.datetime.strftime(
                datetime.datetime.strptime(date_str,
                                           '%a, %d %b %Y %H:%M:%S %z'),
                '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass

        # 场景2: 中间带T的日期字符串 eg: 2020-10-14T07:48:04
        try:
            return datetime.datetime.strftime(
                datetime.datetime.strptime(date_str,
                                           '%Y-%m-%dT%H:%M:%S'),
                '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass

        # 场景3: 中间带T的日期字符串 eg: 2020-10-14T07:48:04.208
        try:
            return datetime.datetime.strftime(
                datetime.datetime.strptime(date_str.split(".")[0],
                                           '%Y-%m-%dT%H:%M:%S'),
                '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass

        # 场景4: 日期字符串以GMT结尾 eg: Fri, 14 Oct 2022 07:48:04 GMT
        if date_str.endswith('GMT'):
            try:
                return datetime.datetime.strftime(
                    datetime.datetime.strptime(date_str,
                                               '%a, %d %b %Y %H:%M:%S GMT'),
                    '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        # 其他情况直接返回
        return date_str
