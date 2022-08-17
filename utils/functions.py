import json
import os
import re
import shutil
import socket
import threading
import subprocess
import time
import platform
import bisect
import datetime
from enum import Enum

from utils.types import OsType

INSTANCES = {}
lock = threading.RLock()


# 单例模式注解
def singleton(cls):
    # 创建字典用来保存类的实例对象
    global INSTANCES

    def _singleton(*args, **kwargs):
        # 先判断这个类有没有对象
        if cls not in INSTANCES:
            with lock:
                if cls not in INSTANCES:
                    INSTANCES[cls] = cls(*args, **kwargs)
                    pass
        # 将实例对象返回
        return INSTANCES[cls]

    return _singleton


# 计算文件大小
def str_filesize(size):
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


# 将文件大小文本转化为字节
def num_filesize(text):
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


# 计算时间
def str_timelong(time_sec):
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


# 判断是否含有中文
def is_chinese(word):
    for ch in word:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False


# 判断是否全是中文
def is_all_chinese(word):
    for ch in word:
        if ch == ' ':
            continue
        if '\u4e00' <= ch <= '\u9fff':
            continue
        else:
            return False
    return True


# 执地本地命令，返回信息
def system_exec_command(cmd, timeout=60):
    try:
        p = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
        t_beginning = time.time()
        while True:
            if p.poll() is not None:
                break
            seconds_passed = time.time() - t_beginning
            if timeout and seconds_passed > timeout:
                p.terminate()
                raise TimeoutError(cmd, timeout)
            time.sleep(0.1)
        result_out = p.stdout.read().decode(encoding='utf8')
        return '', str(result_out)
    except TimeoutError as err1:
        return "timeout", str(err1)
    except Exception as err2:
        return str(err2), str(err2)


# 获得目录下的媒体文件列表List，按后缀过滤
def get_dir_files(in_path, exts="", filesize=0, episode_format=None):
    if not in_path:
        return []
    if not os.path.exists(in_path):
        return []
    ret_list = []
    if os.path.isdir(in_path):
        for root, dirs, files in os.walk(in_path):
            for file in files:
                cur_path = os.path.join(root, file)
                # 检查路径是否合法
                if is_invalid_path(cur_path):
                    continue
                # 检查格式匹配
                if episode_format and not episode_format.match(file):
                    continue
                # 检查后缀
                if exts and os.path.splitext(file)[-1].lower() not in exts:
                    continue
                # 检查文件大小
                if filesize and os.path.getsize(cur_path) < filesize:
                    continue
                # 命中
                if cur_path not in ret_list:
                    ret_list.append(cur_path)
    else:
        # 检查路径是否合法
        if is_invalid_path(in_path):
            return []
        # 检查后缀
        if exts and os.path.splitext(in_path)[-1].lower() not in exts:
            return []
        # 检查格式
        if episode_format and not episode_format.match(os.path.basename(in_path)):
            return []
        # 检查文件大小
        if filesize and os.path.getsize(in_path) < filesize:
            return []
        ret_list.append(in_path)
    return ret_list


# 查询目录下的文件（只查询一级）
def get_dir_level1_files(in_path, exts=""):
    ret_list = []
    if not os.path.exists(in_path):
        return []
    for file in os.listdir(in_path):
        path = os.path.join(in_path, file)
        if os.path.isfile(path):
            if not exts or os.path.splitext(file)[-1].lower() in exts:
                ret_list.append(path)
    return ret_list


# 根据后缀，返回目录下所有的文件及文件夹列表（只查询一级）
def get_dir_level1_medias(in_path, exts=""):
    ret_list = []
    if not os.path.exists(in_path):
        return []
    if os.path.isdir(in_path):
        for file in os.listdir(in_path):
            path = os.path.join(in_path, file)
            if os.path.isfile(path):
                if not exts or os.path.splitext(file)[-1].lower() in exts:
                    ret_list.append(path)
            else:
                ret_list.append(path)
    else:
        ret_list.append(in_path)
    return ret_list


# 获取主机名
def get_host_name():
    return socket.gethostname()


# 获取当前IP地址
def get_host_ip():
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('223.5.5.5', 80))
        ip = s.getsockname()[0]
    finally:
        if s:
            s.close()
    if ip:
        return ip
    else:
        return ''


def is_media_files_tv(file_list):
    flag = False
    # 不是list的转为list，避免发生字符级的拆分
    if not isinstance(file_list, list):
        file_list = [file_list]
    for tmp_file in file_list:
        tmp_name = os.path.basename(tmp_file)
        re_res = re.search(r"[\s.]*[SE]P?\d{2}", tmp_name, re.IGNORECASE)
        if re_res:
            flag = True
            break
    return flag


# 获取系统存储空间占用信息
def get_used_of_partition(path):
    if not path:
        return 0, 0
    if not os.path.exists(path):
        return 0, 0
    try:
        total_b, used_b, free_b = shutil.disk_usage(path)
        return used_b, total_b
    except Exception as e:
        print(str(e))
        return 0, 0


# 获取操作系统类型
def get_system():
    if platform.system() == 'Windows':
        return OsType.WINDOWS
    else:
        return OsType.LINUX


# 计算目录剩余空间大小
def get_free_space_gb(folder):
    total_b, used_b, free_b = shutil.disk_usage(folder)
    return free_b / 1024 / 1024 / 1024


# 通过UTC的时间字符串获取时间
def get_local_time(utc_time_str):
    try:
        utc_date = datetime.datetime.strptime(utc_time_str.replace('0000', ''), '%Y-%m-%dT%H:%M:%S.%fZ')
        local_date = utc_date + datetime.timedelta(hours=8)
        local_date_str = datetime.datetime.strftime(local_date, '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f'Could not get local date:{e}')
        return utc_time_str
    return local_date_str


# 字符串None输出为空
def xstr(s):
    return s if s else ''


# 判断是否不能处理的路径
def is_invalid_path(path):
    if not path:
        return True
    if path.find('/@Recycle/') != -1 or path.find('/#recycle/') != -1 or path.find('/.') != -1 or path.find(
            '/@eaDir') != -1:
        return True
    return False


# 判断两个路径是否包含关系 path1 in path2
def is_path_in_path(path1, path2):
    if not path1 or not path2:
        return False
    path1 = os.path.normpath(path1)
    path2 = os.path.normpath(path2)
    if path1 == path2:
        return True
    path = os.path.dirname(path2)
    while True:
        if path == path1:
            return True
        path = os.path.dirname(path)
        if path == os.path.dirname(path):
            break
    return False


# 判断Sxx-Sxx Exx-Exx 是否包含关系
def is_ses_in_ses(sea, epi, season, episode):
    # 季是否匹配
    season_match = False
    # 都没有季，说明对上了
    if not sea and not season:
        season_match = True
    # 一个有季一个没季对不上
    elif sea and not season or not sea and season:
        season_match = False
    else:
        # 输入季拆分为数组
        if sea.find('-') != -1:
            seas = sea.split('-')
            sea_begin = int(seas[0].replace('S', ''))
            sea_end = int(seas[1].replace('S', ''))
        else:
            sea_begin = sea_end = int(sea.replace('S', ''))
        seas = list(range(sea_begin, sea_end + 1))
        # 目的季拆分为数组
        if season.find('-') != -1:
            seasons = season.split('-')
            season_begin = int(seasons[0].replace('S', ''))
            season_end = int(seasons[1].replace('S', ''))
        else:
            season_begin = season_end = int(season.replace('S', ''))
        seasons = list(range(season_begin, season_end + 1))
        # 目标是否包含输入
        if set(seasons).issuperset(set(seas)):
            season_match = True

    # 集是否匹配
    episode_match = False
    # 两个都没有集，则默认为对上
    if not epi and not episode:
        episode_match = True
    # 输入没集，目标有集，说明输入是整季，对不上
    elif not epi and episode:
        episode_match = False
    # 输入有集，目标没集，说明目标是整季，肯定包含
    elif epi and not episode:
        episode_match = True
    else:
        # 输入集拆分为数组
        if epi.find('-') != -1:
            epis = epi.split('-')
            epi_begin = int(epis[0].replace('E', ''))
            epi_end = int(epis[1].replace('E', ''))
        else:
            epi_begin = epi_end = int(epi.replace('E', ''))
        epis = list(range(epi_begin, epi_end + 1))
        # 目的集拆分为数组
        if episode.find('-') != -1:
            episodes = episode.split('-')
            episode_begin = int(episodes[0].replace('E', ''))
            episode_end = int(episodes[1].replace('E', ''))
        else:
            episode_begin = episode_end = int(episode.replace('E', ''))
        episodes = list(range(episode_begin, episode_end + 1))
        # 比较集
        if set(episodes).issuperset(set(epis)):
            episode_match = True
    # 季和集都匹配才算匹配
    if season_match and episode_match:
        return True

    return False


# 判断是否蓝光原盘目录
def is_bluray_dir(path):
    if not path:
        return False
    if os.path.normpath(path).endswith("BDMV"):
        return os.path.exists(os.path.join(path, "index.bdmv"))
    else:
        return os.path.exists(os.path.join(path, "BDMV", "index.bdmv"))


# 转化SQL字符
def str_sql(in_str):
    return "" if not in_str else str(in_str)


# 将普通对象转化为支持json序列化的对象
def json_serializable(obj):
    """
    @param obj: 待转化的对象
    @return: 支持json序列化的对象
    """

    def _try(o):
        if isinstance(o, Enum):
            return o.value
        try:
            return o.__dict__
        except Exception as err:
            print(err)
            return str(o)

    return json.loads(json.dumps(obj, default=lambda o: _try(o)))


# 检查进程序是否存在
def check_process(pname):
    """
    判断进程是否存在
    """
    if not pname:
        return False
    text = subprocess.Popen('ps -ef | grep -v grep | grep %s' % pname, shell=True).communicate()
    return True if text else False


def tag_value(tag_item, tag_name, attname="", default=None):
    """
    解析XML标签值
    """
    tagNames = tag_item.getElementsByTagName(tag_name)
    if tagNames:
        if attname:
            attvalue = tagNames[0].getAttribute(attname)
            if attvalue:
                return attvalue
        else:
            firstChild = tagNames[0].firstChild
            if firstChild:
                return firstChild.data
    return default


def add_node(doc, parent, name, value=None):
    """
    添加一个DOM节点
    """
    node = doc.createElement(name)
    parent.appendChild(node)
    if value is not None:
        text = doc.createTextNode(str(value))
        node.appendChild(text)
    return node


def max_ele(a, b):
    """
    返回非空最大值
    """
    if not a:
        return b
    if not b:
        return a
    return max(a, b)


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


def handler_special_chars(text, replace_word="", allow_space=False):
    """
    忽略特殊字符
    """
    # 需要忽略的特殊字符
    CONVERT_EMPTY_CHARS = r"\.|\(|\)|\[|]|-|\+|【|】|/|～|;|&|\||#|_|「|」|（|）|'|’|!|！|,|～|·|:|："
    if not text:
        return ""
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", re.sub(r"%s" % CONVERT_EMPTY_CHARS, replace_word, text), flags=re.IGNORECASE)
    if not allow_space:
        return re.sub(r"\s+", "", text)
    else:
        return re.sub(r"\s+", " ", text).strip()
