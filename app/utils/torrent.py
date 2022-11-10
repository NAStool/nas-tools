import os.path
import re
from urllib.parse import quote
import bencode

from app.utils.torrentParser import TorrentParser
from app.utils import RequestUtils


class Torrent:

    @staticmethod
    def get_torrent_content(url, cookie=None, ua=None, referer=None):
        """
        把种子下载到本地，返回种子内容
        :param url: 种子链接
        :param cookie: 站点Cookie
        :param ua: 站点UserAgent
        :param referer: 关联地址，有的网站需要这个否则无法下载
        """
        if not url:
            return None, "URL为空"
        if url.startswith("magnet:"):
            return url, "磁力链接"
        try:
            req = RequestUtils(headers=ua, cookies=cookie, referer=referer).get_res(url=url, allow_redirects=False)
            while req and req.status_code in [301, 302]:
                url = req.headers['Location']
                if url and url.startswith("magnet:"):
                    return url, "磁力链接"
                req = RequestUtils(headers=ua, cookies=cookie, referer=referer).get_res(url=url, allow_redirects=False)
            if req and req.status_code == 200:
                if not req.content:
                    return None, "未下载到种子数据"
                metadata = bencode.bdecode(req.content)
                if not metadata or not isinstance(metadata, dict):
                    return None, "不正确的种子文件"
                return req.content, ""
            elif not req:
                return None, "无法打开链接：%s" % url
            else:
                return None, "下载种子出错，状态码：%s" % req.status_code
        except Exception as err:
            return None, "下载种子文件出现异常：%s，可能站点Cookie已过期或触发了站点首次种子下载" % str(err)

    @staticmethod
    def save_torrent_file(url, path, cookie, ua, referer=None):
        """
        下载种子并保存到文件，返回文件路径
        """
        if not os.path.exists(path):
            os.makedirs(path)
        # 下载种子
        try:
            ret = RequestUtils(cookies=cookie, headers=ua, referer=referer).get_res(url)
            if ret and ret.status_code == 200:
                file_name = re.findall(r"filename=\"?(.+)\"?", ret.headers.get('content-disposition'))
                if not file_name:
                    return None
                file_name = file_name[0]
                if file_name.endswith('"'):
                    file_name = file_name[:-1]
                file_path = os.path.join(path, file_name)
                with open(file_path, 'wb') as f:
                    f.write(ret.content)
            elif not ret:
                return None
            else:
                return None
            return file_path
        except Exception as err:
            print(str(err))
            return None

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
    def get_torrent_files(path):
        """
        解析Torrent文件，获取文件清单
        """
        if not path or not os.path.exists(path):
            return []
        file_names = []
        try:
            torrent = TorrentParser().readFile(path=path)
            if torrent.get("torrent"):
                files = torrent.get("torrent").get("info", {}).get("files") or []
                for item in files:
                    if item.get("path"):
                        file_names.append(item["path"][0])
        except Exception as err:
            print(str(err))
        return file_names
