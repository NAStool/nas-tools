import ctypes
import os
import re
import socket
import subprocess
import time
import platform
import requests
import bisect
from xml.dom.minidom import parse
import xml.dom.minidom

# 根据IP地址获取位置
from requests import RequestException

from config import RMT_MEDIAEXT


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
                    title = item.getElementsByTagName("title")[0].firstChild.data
                    enclosure = item.getElementsByTagName("enclosure")[0].getAttribute("url")
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
                    title = item.getElementsByTagName("title")[0].firstChild.data
                    description = item.getElementsByTagName("description")[0].firstChild.data
                    size = item.getElementsByTagName("size")[0].firstChild.data
                    enclosure = item.getElementsByTagName("enclosure")[0].getAttribute("url")
                    seeders = None
                    peers = None
                    torznab_attrs = item.getElementsByTagName("torznab:attr")
                    for torznab_attr in torznab_attrs:
                        name = torznab_attr.getAttribute('name')
                        value = torznab_attr.getAttribute('value')
                        if name == "seeders":
                            seeders = value
                        if name == "peers":
                            peers = value

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


# 获得媒体名称，用于API检索
def get_pt_media_name(in_name):
    if not in_name:
        return ""
    # 如果有后缀则去掉，避免干扰
    tmp_ext = os.path.splitext(in_name)[-1]
    if tmp_ext in RMT_MEDIAEXT:
        out_name = os.path.splitext(in_name)[0]
    else:
        out_name = in_name
    # 干掉一些固定的前缀 JADE AOD XXTV-X
    out_name = re.sub(r'^JADE[\s.]+|^AOD[\s.]+|^[A-Z]{2,4}TV[\-0-9UVHD]*[\s.]+', '', out_name,
                      flags=re.IGNORECASE).strip()
    # 查找关键字并切分
    num_pos1 = num_pos2 = len(out_name)
    # 查找年份/分辨率的位置
    re_res1 = re.search(r"[\s.]+\d{3,4}[PI]?[\s.]+|[\s.]+\d+K[\s.]+", out_name, re.IGNORECASE)
    if not re_res1:
        # 查询BluRay/REMUX/HDTV/WEB-DL/WEBRip/DVDRip/UHD的位置
        if not re_res1:
            re_res1 = re.search(
                r"[\s.]+BLU-?RAY[\s.]+|[\s.]+REMUX[\s.]+|[\s.]+HDTV[\s.]+|[\s.]+WEB-DL[\s.]+|[\s.]+WEBRIP[\s.]+|[\s.]+DVDRIP[\s.]+|[\s.]+UHD[\s.]+",
                out_name, re.IGNORECASE)
    if re_res1:
        num_pos1 = re_res1.span()[0]
    # 查找Sxx或Exx的位置
    re_res2 = re.search(r"[\s.]+[SE]P?\d{1,3}", out_name, re.IGNORECASE)
    if re_res2:
        num_pos2 = re_res2.span()[0]
    # 取三者最小
    num_pos = min(num_pos1, num_pos2, len(out_name))
    # 截取Year或Sxx或Exx前面的字符
    out_name = out_name[0:num_pos]
    # 如果带有Sxx-Sxx、Exx-Exx这类的要处理掉
    out_name = re.sub(r'[SsEePp]+\d{1,3}-?[SsEePp]*\d{0,3}', '', out_name).strip()
    if is_chinese(out_name):
        # 有中文的，把中文外的英文、字符、数字等全部去掉
        out_name = re.sub(r'[0-9a-zA-Z【】\-_.\[\]()\s]+', '', out_name).strip()
    else:
        # 不包括中文，则是英文名称
        out_name = out_name.replace(".", " ")
    return out_name


# 获得媒体文件的集数S00
def get_media_file_season(in_name):
    if in_name:
        # 查找Sxx
        re_res = re.search(r"[\s.]*(S\d{1,2})", in_name, re.IGNORECASE)
        if re_res:
            return re_res.group(1).upper()
    return "S01"


# 获得媒体文件的集数E00
def get_media_file_seq(in_name):
    ret_str = ""
    if in_name:
        # 查找Sxx
        re_res = re.search(r"[\s.]*S?\d{0,2}(EP?\d{1,3})[\s.]*", in_name, re.IGNORECASE)
        if re_res:
            ret_str = re_res.group(1).upper()
        else:
            # 可能数字就是全名，或者是第xx集
            ret_str = ""
            num_pos = in_name.find(".")
            if num_pos != -1:
                split_char = "."
            else:
                split_char = " "
            split_ary = in_name.split(split_char)
            for split_str in split_ary:
                split_str = split_str.replace("第", "").replace("集", "").strip()
                if split_str.isdigit() and (0 < int(split_str) < 1000):
                    ret_str = "E" + split_str
                    break
        if not ret_str:
            ret_str = ""
    return ret_str


# 获得媒体文件的分辨率
def __get_media_file_pix(in_name):
    if in_name:
        # 查找Sxx
        re_res = re.search(r"[\s.]+[SBUHD]*(\d{3,4}[PI]+)[\s.]+", in_name, re.IGNORECASE)
        if re_res:
            return re_res.group(1).upper()
        else:
            re_res = re.search(r"[\s.]+(\d+K)[\s.]+", in_name, re.IGNORECASE)
            if re_res:
                return re_res.group(1).upper()
    return ""


# 获得媒体文件的Year
def get_media_file_year(in_name):
    if in_name:
        # 查找Sxx
        re_res = re.search(r"[\s.(]+(\d{4})[\s.)]+", in_name, re.IGNORECASE)
        if re_res:
            return re_res.group(1).upper()
    return ""


# 从种子名称中获取季和集的数字
def get_sestring_from_name(name):
    # 不知道怎么写，最傻的办法，穷举！
    re_res = re.search(r'([SsEePp]+\d{1,3}-?[SsEePp]*\d{0,3})', name, re.IGNORECASE)
    if re_res:
        return re_res.group(1).upper()
    else:
        return None
