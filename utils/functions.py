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

from utils.types import MediaType

# 全局对象
INSTANCES = {}


# 单例模式注解
def singleton(cls):
    # 单下划线的作用是这个变量只能在当前模块里访问,仅仅是一种提示作用
    # 创建一个字典用来保存类的实例对象
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
def get_dir_files_by_ext(in_path, exts=""):
    ret_list = []
    if not os.path.exists(in_path):
        return []
    if os.path.isdir(in_path):
        for root, dirs, files in os.walk(in_path):
            for file in files:
                ext = os.path.splitext(file)[-1]
                if ext.lower() in exts:
                    cur_path = os.path.join(root, file)
                    if cur_path not in ret_list:
                        ret_list.append(cur_path)
    else:
        ext = os.path.splitext(in_path)[-1]
        if ext.lower() in exts:
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
        ret = requests.get(url, timeout=30)
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
                    # 标题
                    title = ""
                    tagNames = item.getElementsByTagName("title")
                    if tagNames:
                        firstChild = tagNames[0].firstChild
                        if firstChild:
                            title = firstChild.data
                    if not title:
                        continue
                    # 种子链接
                    enclosure = ""
                    tagNames = item.getElementsByTagName("enclosure")
                    if tagNames:
                        enclosure = tagNames[0].getAttribute("url")
                    if not enclosure:
                        continue
                    # 描述
                    description = ""
                    tagNames = item.getElementsByTagName("description")
                    if tagNames:
                        firstChild = tagNames[0].firstChild
                        if firstChild:
                            description = firstChild.data
                    tmp_dict = {'title': title, 'enclosure': enclosure, 'description': description}
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
        ret = requests.get(url, timeout=30)
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
                    # 标题
                    title = ""
                    tagNames = item.getElementsByTagName("title")
                    if tagNames:
                        firstChild = tagNames[0].firstChild
                        if firstChild:
                            title = firstChild.data
                    if not title:
                        continue
                    # 种子链接
                    enclosure = ""
                    tagNames = item.getElementsByTagName("enclosure")
                    if tagNames:
                        enclosure = tagNames[0].getAttribute("url")
                    if not enclosure:
                        continue
                    # 描述
                    description = ""
                    tagNames = item.getElementsByTagName("description")
                    if tagNames:
                        firstChild = tagNames[0].firstChild
                        if firstChild:
                            description = firstChild.data
                    # 种子大小
                    size = 0
                    tagNames = item.getElementsByTagName("size")
                    if tagNames:
                        firstChild = tagNames[0].firstChild
                        if firstChild:
                            size = firstChild.data
                    # 做种数
                    seeders = 0
                    # 下载数
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
        re_res = re.search(r"[\s.]*[SE]P?\d{2}", tmp_name, re.IGNORECASE)
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
        if episode_num and not season_num:
            season_num = "1"
    if year_re:
        year = year_re.group(1)
    key_word = re.sub(r'第\s*[0-9一二三四五六七八九十]+\s*季|第\s*[0-9一二三四五六七八九十]+\s*集|[\s(]+(\d{4})[\s)]*', '', content,
                      flags=re.IGNORECASE).strip()
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
            total_seasons.append(
                {"season_number": season.get("season_number"), "episode_count": season.get("episode_count")})
    return total_seasons


# 从TMDB的季信息中获得具体季有多少集
def get_tmdb_season_episodes_num(seasons, sea):
    if not seasons:
        return 0
    for season in seasons:
        if season.get("season_number") == sea:
            return season.get("episode_count")
    return 0


# 字符串None输出为空
def xstr(s):
    return s if s else ''


# 种子去重，每一个名称、站点、资源类型 选一个做种人最多的显示
def get_torrents_group_item(media_list):
    if not media_list:
        return []

    # 排序函数
    def get_sort_str(x):
        return "%s%s%s%s" % (str(x.title).ljust(100, ' '),
                             str(x.site).ljust(20, ' '),
                             str(x.res_type).ljust(20, ' '),
                             str(x.seeders).rjust(10, '0'))

    # 匹配的资源中排序分组
    media_list = sorted(media_list, key=lambda x: get_sort_str(x), reverse=True)
    # 控重
    can_download_list_item = []
    can_download_list = []
    # 排序后重新加入数组，按真实名称控重，即只取每个名称的第一个
    for t_item in media_list:
        # 控重的主链是名称、节份、季、集
        if t_item.type == MediaType.TV:
            media_name = "%s%s%s%s" % (t_item.get_title_string(),
                                       t_item.site,
                                       t_item.get_resource_type_string(),
                                       t_item.get_season_episode_string())
        else:
            media_name = "%s%s%s" % (t_item.get_title_string(), t_item.site, t_item.get_resource_type_string())
        if media_name not in can_download_list:
            can_download_list.append(media_name)
            can_download_list_item.append(t_item)
    return can_download_list_item


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
