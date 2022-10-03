import random
import re
from functools import lru_cache
from time import sleep
from urllib.parse import quote

import bencode
from lxml import etree

from config import TORRENT_SEARCH_PARAMS
from app.sites import SiteConf
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
    @lru_cache(maxsize=128)
    def check_torrent_attr(torrent_url, cookie, ua=None) -> TorrentAttr:
        """
        检验种子是否免费，当前做种人数
        :param torrent_url: 种子的详情页面
        :param cookie: 站点的Cookie
        :param ua: 站点的ua
        :return: 种子属性，包含FREE 2XFREE HR PEER_COUNT等属性
        """
        ret_attr = TorrentAttr()
        if not torrent_url:
            return ret_attr
        xpath_strs = SiteConf().get_grapsite_conf(torrent_url)
        if not xpath_strs:
            return ret_attr
        res = RequestUtils(cookies=cookie, headers=ua).get_res(url=torrent_url)
        if res and res.status_code == 200:
            res.encoding = res.apparent_encoding
            html_text = res.text
            if not html_text:
                return ret_attr
            try:
                html = etree.HTML(html_text)
                # 检测2XFREE
                for xpath_str in xpath_strs.get("2XFREE"):
                    if html.xpath(xpath_str):
                        ret_attr.free2x = True
                # 检测FREE
                for xpath_str in xpath_strs.get("FREE"):
                    if html.xpath(xpath_str):
                        ret_attr.free = True
                # 检测HR
                for xpath_str in xpath_strs.get("HR"):
                    if html.xpath(xpath_str):
                        ret_attr.hr = True
                # 检测PEER_COUNT当前做种人数
                for xpath_str in xpath_strs.get("PEER_COUNT"):
                    peer_count_dom = html.xpath(xpath_str)
                    if peer_count_dom:
                        peer_count_str = peer_count_dom[0].text
                        peer_count_str_re = re.search(r'^(\d+)', peer_count_str)
                        ret_attr.peer_count = int(peer_count_str_re.group(1)) if peer_count_str_re else 0
            except Exception as err:
                print(err)
        # 随机休眼后再返回
        sleep(round(random.uniform(1, 5), 1))
        return ret_attr

    @staticmethod
    def get_torrent_content(url, cookie=None, ua=None):
        """
        把种子下载到本地，返回种子内容
        :param url: 种子链接
        :param cookie: 站点Cookie
        :param ua: 站点UserAgent
        """
        if not url:
            return None, "URL为空"
        if url.startswith("magnet:"):
            return url, "磁力链接"
        try:
            req = RequestUtils(headers=ua, cookies=cookie).get_res(url=url)
            if req and req.status_code == 200:
                if not req.content:
                    return None, "未下载到种子数据"
                metadata = bencode.bdecode(req.content)
                if not metadata or not isinstance(metadata, dict):
                    return None, "不正确的种子文件"
                return req.content, ""
            elif not req:
                return url, "无法打开链接：%s" % url
            else:
                return None, "下载种子出错，状态码：%s" % req.status_code
        except Exception as err:
            return None, "下载种子文件出现异常：%s，可能站点Cookie已过期或触发了站点首次种子下载" % str(err)

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
        :return: 订阅站点、搜索站点、是否洗版、过滤字典
        """
        if not desc:
            return [], [], False, {}
        rss_sites = []
        search_sites = []
        over_edition = False
        rss_restype = None
        rss_pix = None
        rss_team = None
        rss_rule = None
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

        return rss_sites, search_sites, over_edition, {"restype": rss_restype,
                                                       "pix": rss_pix,
                                                       "rule": rss_rule,
                                                       "team": rss_team}

    @staticmethod
    def parse_download_url(page_url, xpath, cookie=None, ua=None):
        """
        从详情页面中解析中下载链接
        :param page_url: 详情页面地址
        :param xpath: 解析XPATH
        :param cookie: 站点Cookie
        :param ua: 站点User-Agent
        """
        if not page_url or not xpath:
            return ""
        try:
            req = RequestUtils(headers=ua, cookies=cookie).get_res(url=page_url)
            if req and req.status_code == 200:
                if not req.text:
                    return None
                html = etree.HTML(req.text)
                urls = html.xpath(xpath)
                if urls:
                    return str(urls[0])
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
