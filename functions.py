import ctypes
import os
import socket
import subprocess
import time
import platform
import requests
import bisect


# 根据IP地址获取位置
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
        return "timeout", ''
    except Exception as err2:
        return str(err2), ''


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


def crate_number_list(start, end):
    if start is None:
        start = 1
    if end is None:
        return [start]
    arr = []
    i = start
    while i <= end:
        arr.append(i)
        i = i + 1
    return arr