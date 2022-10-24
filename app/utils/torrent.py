import os.path
import re
from urllib.parse import quote
import bencode

from app.utils.torrentParser import TorrentParser
from config import TORRENT_SEARCH_PARAMS
from app.utils import RequestUtils


class TorrentAttr:
    def __init__(self):
        self.free = None
        self.free2x = None
        self.peer_count = 0
        self.hr = None

    def __str__(self):
        return "free: {}, free2x: {}, peer_count: {}, hr: {}".format(self.free, self.free2x, self.peer_count, self.hr)

    def is_free(self):
        return True if self.free or self.free2x else False

    def is_free2x(self):
        return True if self.free2x else False

    def is_hr(self):
        return True if self.hr else False


class Torrent:

    @staticmethod
    def is_torrent_match_sey(media_info, s_num, e_num, year_str):
        """
        种子名称关键字匹配
        :param media_info: 已识别的种子信息
        :param s_num: 要匹配的季号，为空则不匹配
        :param e_num: 要匹配的集号，为空则不匹配
        :param year_str: 要匹配的年份，为空则不匹配
        :return: 是否命中
        """
        if s_num:
            if not media_info.get_season_list():
                return False
            if not isinstance(s_num, list):
                s_num = [s_num]
            if not set(s_num).issuperset(set(media_info.get_season_list())):
                return False
        if e_num:
            if not isinstance(e_num, list):
                e_num = [e_num]
            if not set(e_num).issuperset(set(media_info.get_episode_list())):
                return False
        if year_str:
            if str(media_info.year) != str(year_str):
                return False
        return True

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
            req = RequestUtils(headers=ua, cookies=cookie, referer=referer).get_res(url=url)
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
        ret = RequestUtils(cookies=cookie, headers=ua, referer=referer).get_res(url)
        if ret and ret.status_code == 200:
            file_name = re.findall(r"filename=\"(.+)\"", ret.headers.get('content-disposition'))[0]
            file_path = os.path.join(path, file_name)
            with open(file_path, 'wb') as f:
                f.write(ret.content)
        elif not ret:
            return None
        else:
            return None
        return file_path

    @staticmethod
    def check_torrent_filter(meta_info, filter_args, uploadvolumefactor=None, downloadvolumefactor=None):
        """
        对种子进行过滤
        :param meta_info: 名称识别后的MetaBase对象
        :param filter_args: 过滤条件的字典
        :param uploadvolumefactor: 种子的上传因子 传空不过滤
        :param downloadvolumefactor: 种子的下载因子 传空不过滤
        """
        if filter_args.get("restype"):
            restype_re = TORRENT_SEARCH_PARAMS["restype"].get(filter_args.get("restype"))
            if not meta_info.resource_type:
                return False
            if restype_re and not re.search(r"%s" % restype_re, meta_info.resource_type, re.IGNORECASE):
                return False
        if filter_args.get("pix"):
            restype_re = TORRENT_SEARCH_PARAMS["pix"].get(filter_args.get("pix"))
            if not meta_info.resource_pix:
                return False
            if restype_re and not re.search(r"%s" % restype_re, meta_info.resource_pix, re.IGNORECASE):
                return False
        if filter_args.get("team"):
            restype_re = filter_args.get("team")
            if not meta_info.resource_team:
                return False
            if restype_re and not re.search(r"%s" % restype_re, meta_info.resource_team, re.IGNORECASE):
                return False
        if filter_args.get("sp_state"):
            ul_factor, dl_factor = filter_args.get("sp_state").split()
            if uploadvolumefactor and ul_factor not in ("*", str(uploadvolumefactor)):
                return False
            if downloadvolumefactor and dl_factor not in ("*", str(downloadvolumefactor)):
                return False
        if filter_args.get("key") and not re.search(r"%s" % filter_args.get("key"),
                                                    meta_info.org_string,
                                                    re.IGNORECASE):
            return False
        return True

    @staticmethod
    def get_rss_note_item(desc):
        """
        解析订阅的NOTE字段，从中获取订阅站点、搜索站点、是否洗版、订阅质量、订阅分辨率、订阅制作组/字幕组、过滤规则等信息
        DESC字段组成：RSS站点#搜索站点#是否洗版(Y/N)#过滤条件，站点用|分隔多个站点，过滤条件用@分隔多个条件
        :param desc: RSS订阅DESC字段的值
        :return: 订阅站点、搜索站点、是否洗版、过滤字典、总集数，当前集数
        """
        if not desc:
            return {}
        rss_sites = []
        search_sites = []
        over_edition = False
        rss_restype = None
        rss_pix = None
        rss_team = None
        rss_rule = None
        total_episode = None
        current_episode = None
        notes = str(desc).split('#')
        # 订阅站点
        if len(notes) > 0:
            if notes[0]:
                rss_sites = [site for site in notes[0].split('|') if site and len(site) < 20]
        # 搜索站点
        if len(notes) > 1:
            if notes[1]:
                search_sites = [site for site in notes[1].split('|') if site]
        # 洗版
        if len(notes) > 2:
            if notes[2] == 'Y':
                over_edition = True
            else:
                over_edition = False
        # 过滤条件
        if len(notes) > 3:
            if notes[3]:
                filters = notes[3].split('@')
                if len(filters) > 0:
                    rss_restype = filters[0]
                if len(filters) > 1:
                    rss_pix = filters[1]
                if len(filters) > 2:
                    rss_rule = filters[2]
                if len(filters) > 3:
                    rss_team = filters[3]
        # 总集数及当前集数
        if len(notes) > 4:
            if notes[4]:
                episode_info = notes[4].split('@')
                if len(episode_info) > 0:
                    total_episode = episode_info[0]
                if len(episode_info) > 1:
                    current_episode = episode_info[1]
        return {
            "rss_sites": rss_sites,
            "search_sites": search_sites,
            "over_edition": over_edition,
            "filter_map": {"restype": rss_restype,
                           "pix": rss_pix,
                           "rule": rss_rule,
                           "team": rss_team},
            "episode_info": {"total": total_episode,
                             "current": current_episode}
        }

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
