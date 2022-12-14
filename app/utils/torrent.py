import os.path
import re
import datetime
from urllib.parse import quote

from app.utils.exception_util import ExceptionUtils
from app.utils.torrentParser import TorrentParser
from app.utils import RequestUtils
from config import Config


class Torrent:

    _torrent_path = None

    def __init__(self):
        self._torrent_path = os.path.join(Config().get_config_path(), "temp")
        if not os.path.exists(self._torrent_path):
            os.makedirs(self._torrent_path)

    def get_torrent_info(self, url, cookie=None, ua=None, referer=None):
        """
        把种子下载到本地，返回种子内容
        :param url: 种子链接
        :param cookie: 站点Cookie
        :param ua: 站点UserAgent
        :param referer: 关联地址，有的网站需要这个否则无法下载
        :return: 种子保存路径、种子内容、种子文件列表主目录、种子文件列表、错误信息
        """
        if not url:
            return None, None, "", [], "URL为空"
        if url.startswith("magnet:"):
            return None, url, "", [], f"{url} 为磁力链接"
        try:
            req = RequestUtils(headers=ua, cookies=cookie, referer=referer).get_res(url=url, allow_redirects=False)
            while req and req.status_code in [301, 302]:
                url = req.headers['Location']
                if url and url.startswith("magnet:"):
                    return None, url, "", [], f"获取到磁力链接：{url}"
                req = RequestUtils(headers=ua, cookies=cookie, referer=referer).get_res(url=url, allow_redirects=False)
            if req and req.status_code == 200:
                if not req.content:
                    return None, None, "", [], "未下载到种子数据"
                # 读取种子文件名
                file_name = self.__get_url_torrent_name(req.headers.get('content-disposition'), url)
                # 种子文件路径
                file_path = os.path.join(self._torrent_path, file_name)
                with open(file_path, 'wb') as f:
                    f.write(req.content)
                # 解析种子文件
                files_folder, files, retmsg = self.__get_torrent_files(file_path)
                # 种子文件路径、种子内容、种子文件列表主目录、种子文件列表、错误信息
                return file_path, req.content, files_folder, files, retmsg
            elif req is None:
                return None, None, "", [], "无法打开链接：%s" % url
            else:
                return None, None, "", [], "下载种子出错，状态码：%s" % req.status_code
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return None, None, "", [], "下载种子文件出现异常：%s，请检查是否站点Cookie已过期，或触发了站点首次种子下载" % str(err)

    @staticmethod
    def convert_hash_to_magnet(hash_text, title):
        """
        根据hash值，转换为磁力链，自动添加tracker
        :param hash_text: 种子Hash值
        :param title: 种子标题
        """
        if not hash_text or not title:
            return None
        hash_text = re.search(r'[0-9a-z]+', hash_text, re.IGNORECASE)
        if not hash_text:
            return None
        hash_text = hash_text.group(0)
        return f'magnet:?xt=urn:btih:{hash_text}&dn={quote(title)}&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80' \
               '&tr=udp%3A%2F%2Fopentor.org%3A2710' \
               '&tr=udp%3A%2F%2Ftracker.ccc.de%3A80' \
               '&tr=udp%3A%2F%2Ftracker.blackunicorn.xyz%3A6969' \
               '&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969' \
               '&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969'

    @staticmethod
    def __get_torrent_files(path):
        """
        解析Torrent文件，获取文件清单
        :return: 种子文件列表主目录、种子文件列表、错误信息
        """
        if not path or not os.path.exists(path):
            return "", [], f"种子文件不存在：{path}"
        file_names = []
        file_folder = ""
        try:
            torrent = TorrentParser().readFile(path=path)
            if torrent.get("torrent"):
                file_folder = torrent.get("torrent").get("info", {}).get("name") or ""
                files = torrent.get("torrent").get("info", {}).get("files") or []
                if not files and file_folder:
                    file_names.append(file_folder)
                else:
                    for item in files:
                        if item.get("path"):
                            file_names.append(item["path"][0])
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return file_folder, file_names, "解析种子文件异常：%s" % str(err)
        return file_folder, file_names, ""

    def read_torrent_file(self, path):
        """
        读取本地种子文件的内容
        :return: 种子内容、种子文件列表主目录、种子文件列表、错误信息
        """
        if not path or not os.path.exists(path):
            return None, "", "种子文件不存在：%s" % path
        content, retmsg, file_folder, files = None, "", "", []
        try:
            # 读取种子文件内容
            with open(path, 'rb') as f:
                content = f.read()
            # 解析种子文件
            file_folder, files, retmsg = self.__get_torrent_files(path)
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            retmsg = "读取种子文件出错：%s" % str(e)
        return content, file_folder, files, retmsg

    @staticmethod
    def __get_url_torrent_name(disposition, url):
        """
        从下载请求中获取种子文件名
        """
        file_name = re.findall(r"filename=\"?(.+)\"?", disposition or "")
        if file_name:
            file_name = str(file_name[0].encode('ISO-8859-1').decode()).split(";")[0].strip()
            if file_name.endswith('"'):
                file_name = file_name[:-1]
        elif url and url.endswith(".torrent"):
            file_name = url.split("/")[-1]
        else:
            file_name = str(datetime.datetime.now())
        return file_name
