import ctypes
import os
import re
import socket
import subprocess
import time
import platform

import cn2an
import requests
import bisect
import datetime
from xml.dom.minidom import parse
import xml.dom.minidom


def get_location(ip):
    url = 'https://sp0.baidu.com/8aQDcjqpAAV3otqbppnN2DJv/api.php?co=&resource_id=6006&t=1529895387942&ie=utf8' \
          '&oe=gbk&cb=op_aladdin_callback&format=json&tn=baidu&' \
          'cb=jQuery110203920624944751099_1529894588086&_=1529894588088&query=%s' % ip
    try:
        r = requests.get(url)
        r.encoding = 'gbk'
        html = r.text
        c1 = html.split('location":"')[1]
        c2 = c1.split('","')[0]
        return c2
    except requests.exceptions:
        return ''


# 计算文件大小
def str_filesize(size):
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
def get_dir_files_by_ext(in_path, exts=""):
    ret_list = []
    if not os.path.exists(in_path):
        return []
    if os.path.isdir(in_path):
        for root, dirs, files in os.walk(in_path):
            for file in files:
                ext = os.path.splitext(file)[-1]
                if ext in exts:
                    cur_path = os.path.join(root, file)
                    if cur_path not in ret_list:
                        ret_list.append(cur_path)
    else:
        ext = os.path.splitext(in_path)[-1]
        if ext in exts:
            if in_path not in ret_list:
                ret_list.append(in_path)
    return ret_list


# 获得目录下的媒体文件列表List，按文件名过滤
def get_dir_files_by_name(in_path, namestr=""):
    ret_list = []
    if not os.path.exists(in_path):
        return []
    if os.path.isdir(in_path):
        for root, dirs, files in os.walk(in_path):
            for file in files:
                file_name = os.path.basename(file)
                if namestr in file_name:
                    cur_path = os.path.join(root, file)
                    if cur_path not in ret_list:
                        ret_list.append(cur_path)
    else:
        file_name = os.path.basename(in_path)
        if namestr in file_name:
            if in_path not in ret_list:
                ret_list.append(in_path)
    return ret_list


# cookie字符串解析成字典
def cookieParse(cookies_str):
    cookie_dict = {}
    cookies = cookies_str.split(';')

    for cookie in cookies:
        cstr = cookie.split('=')
        cookie_dict[cstr[0]] = cstr[1]

    return cookie_dict


# 生成HTTP请求头
def generateHeader(url):
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:61.0) Gecko/20100101 Firefox/61.0',
        'Accept-Language': 'zh-CN',
        'Referer': url
    }
    return header


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


# 解析RSS的XML，返回标题及URL
def parse_rssxml(url):
    ret_array = []
    if not url:
        return []
    try:
        ret = requests.get(url)
    except Exception as e2:
        print(str(e2))
        return []
    if ret:
        ret_xml = ret.text
        try:
            # 解析XML
            dom_tree = xml.dom.minidom.parseString(ret_xml)
            rootNode = dom_tree.documentElement
            items = rootNode.getElementsByTagName("item")
            for item in items:
                try:
                    # 获取XML值
                    firstChild = item.getElementsByTagName("title")[0].firstChild
                    if not firstChild:
                        continue
                    else:
                        title = firstChild.data
                    tagName = item.getElementsByTagName("enclosure")[0]
                    if not tagName:
                        continue
                    else:
                        enclosure = tagName.getAttribute("url")
                    tmp_dict = {'title': title, 'enclosure': enclosure}
                    ret_array.append(tmp_dict)
                except Exception as e1:
                    print(str(e1))
                    continue
        except Exception as e2:
            print(str(e2))
            return ret_array
    return ret_array


# 解析Jackett的XML，返回标题及URL等
def parse_jackettxml(url):
    ret_array = []
    if not url:
        return ret_array
    try:
        ret = requests.get(url)
    except Exception as e2:
        print(str(e2))
        return []
    if ret:
        ret_xml = ret.text
        try:
            # 解析XML
            dom_tree = xml.dom.minidom.parseString(ret_xml)
            rootNode = dom_tree.documentElement
            items = rootNode.getElementsByTagName("item")
            for item in items:
                try:
                    # 获取XML值
                    firstChild = item.getElementsByTagName("title")[0].firstChild
                    if firstChild:
                        title = firstChild.data
                    else:
                        continue
                    firstChild = item.getElementsByTagName("description")[0].firstChild
                    if firstChild:
                        description = firstChild.data
                    else:
                        description = ""
                    firstChild = item.getElementsByTagName("size")[0].firstChild
                    if firstChild:
                        size = firstChild.data
                    else:
                        size = 0
                    tagName = item.getElementsByTagName("enclosure")[0]
                    if tagName:
                        enclosure = tagName.getAttribute("url")
                    else:
                        continue

                    seeders = 0
                    peers = 0
                    torznab_attrs = item.getElementsByTagName("torznab:attr")
                    for torznab_attr in torznab_attrs:
                        name = torznab_attr.getAttribute('name')
                        value = torznab_attr.getAttribute('value')
                        if name == "seeders":
                            seeders = value
                        if name == "peers":
                            peers = value

                    # 做种为0的跳过
                    if seeders == 0:
                        continue

                    tmp_dict = {'title': title, 'enclosure': enclosure, 'description': description, 'size': size,
                                'seeders': seeders, 'peers': peers}
                    ret_array.append(tmp_dict)
                except Exception as e:
                    print(str(e))
                    continue
        except Exception as e2:
            print(str(e2))
            return ret_array
    return ret_array


def is_media_files_tv(file_list):
    flag = False
    # 不是list的转为list，避免发生字符级的拆分
    if not isinstance(file_list, list):
        file_list = [file_list]
    for tmp_file in file_list:
        tmp_name = os.path.basename(tmp_file)
        re_res = re.search(r"[\s.]*[SE]P?\d{1,3}", tmp_name, re.IGNORECASE)
        if re_res:
            flag = True
            break
    return flag


# 从检索关键字中拆分中年份、季、集
def get_keyword_from_string(content):
    # 稍微切一下剧集吧
    season_num = None
    episode_num = None
    year = None
    season_re = re.search(r"第\s*([0-9一二三四五六七八九十]+)\s*季", content, re.IGNORECASE)
    episode_re = re.search(r"第\s*([0-9一二三四五六七八九十]+)\s*集", content, re.IGNORECASE)
    year_re = re.search(r"[\s(]+(\d{4})[\s)]*", content)
    if season_re:
        season_num = int(cn2an.cn2an(season_re.group(1), mode='smart'))
    if episode_re:
        episode_num = int(cn2an.cn2an(episode_re.group(1), mode='smart'))
    if year_re:
        year = year_re.group(1)
    key_word = re.sub(r'第\s*[0-9一二三四五六七八九十]+\s*季|第\s*[0-9一二三四五六七八九十]+\s*集|[\s(]+(\d{4})[\s)]*', '', content, flags=re.IGNORECASE).strip()
    if not key_word:
        key_word = year
    return key_word, season_num, episode_num, year


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


# 从TMDB的季集信息中获得季的组
def get_tmdb_seasons_info(seasons):
    if not seasons:
        return []
    total_seasons = []
    for season in seasons:
        if season.get("season_number") != 0:
            total_seasons.append({"season_number": season.get("season_number"), "episode_count": season.get("episode_count")})
    return total_seasons


# 从TMDB的季信息中获得具体季有多少集
def get_tmdb_season_episodes_num(seasons, sea):
    if not seasons:
        return 0
    for season in seasons:
        if season.get("season_number") == sea:
            return season.get("episode_count")
    return 0
