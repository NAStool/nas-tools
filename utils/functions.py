import ctypes
import os
import re
import socket
import subprocess
import time
import platform
import requests
import bisect
import datetime

# 全局对象
INSTANCES = {}


# 单例模式注解
def singleton(cls):
    # 单下划线的作用是这个变量只能在当前模块里访问,仅仅是一种提示作用
    # 创建字典用来保存类的实例对象
    global INSTANCES

    def _singleton(*args, **kwargs):
        # 先判断这个类有没有对象
        if cls not in INSTANCES:
            INSTANCES[cls] = cls(*args, **kwargs)  # 创建一个对象,并保存到字典当中
        # 将实例对象返回
        return INSTANCES[cls]

    return _singleton


def get_location(ip):
    url = 'https://sp0.baidu.com/8aQDcjqpAAV3otqbppnN2DJv/api.php?co=&resource_id=6006&t=1529895387942&ie=utf8' \
          '&oe=gbk&cb=op_aladdin_callback&format=json&tn=baidu&' \
          'cb=jQuery110203920624944751099_1529894588086&_=1529894588088&query=%s' % ip
    try:
        r = requests.get(url, timeout=10)
        r.encoding = 'gbk'
        html = r.text
        c1 = html.split('location":"')[1]
        c2 = c1.split('","')[0]
        return c2
    except requests.exceptions:
        return ''


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


# 计算时间
def str_timelong(time_sec):
    d = [(0, '秒'), (60 - 1, '分'), (3600 - 1, '小时'), (86400 - 1, '天')]
    s = [x[0] for x in d]
    index = bisect.bisect_left(s, time_sec) - 1
    if index == -1:
        return str(time_sec)
    else:
        b, u = d[index]
    return str(round(time_sec / (b + 1))) + u


# 判断是否为中文
def is_chinese(word):
    for ch in word:
        if '\u4e00' <= ch <= '\u9fff':
            return True
    return False


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
def get_dir_files_by_ext(in_path, exts="", filesize=0):
    ret_list = []
    if not os.path.exists(in_path):
        return []
    if os.path.isdir(in_path):
        for root, dirs, files in os.walk(in_path):
            for file in files:
                ext = os.path.splitext(file)[-1]
                if ext.lower() in exts:
                    cur_path = os.path.join(root, file)
                    file_size = os.path.getsize(cur_path)
                    if cur_path not in ret_list and file_size > filesize:
                        ret_list.append(cur_path)
    else:
        ext = os.path.splitext(in_path)[-1]
        file_size = os.path.getsize(in_path)
        if ext.lower() in exts and file_size > filesize:
            if in_path not in ret_list:
                ret_list.append(in_path)
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
                if os.path.splitext(file)[-1].lower() in exts:
                    ret_list.append(path)
            else:
                ret_list.append(path)
    else:
        ret_list.append(in_path)
    return ret_list


# 计算目录剩余空间大小
def get_free_space_gb(folder):
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value / 1024 / 1024 / 1024
    else:
        st = os.statvfs(folder)
        return st.f_bavail * st.f_frsize / 1024 / 1024 / 1024


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
    try:
        sv = os.statvfs(path)
        total = (sv.f_blocks * sv.f_frsize)
        used = (sv.f_blocks - sv.f_bfree) * sv.f_frsize
        return used, total
    except Exception as e:
        print(str(e))
        return 0, 0


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


# 根据名称判断是不是动漫
def is_anime(name):
    if not name:
        return False
    if re.search(r'\[[0-9XPI-]+]', name, re.IGNORECASE):
        return True
    if re.search(r'\s+-\s+\d{1,3}\s+', name, re.IGNORECASE):
        return True
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
