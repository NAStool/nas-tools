import random
import re
from functools import lru_cache
from time import sleep
from urllib import parse
import cn2an
from lxml import etree
from config import TORRENT_SEARCH_PARAMS
from pt.siteconf import RSS_SITE_GRAP_CONF
from rmt.meta.metabase import MetaBase
from utils.http_utils import RequestUtils
from utils.types import MediaType
import bencode


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
    def get_keyword_from_string(content):
        """
        从检索关键字中拆分中年份、季、集、类型
        """
        if not content:
            return None, None, None, None, None
        # 去掉查询中的电影或电视剧关键字
        if re.search(r'^电视剧|\s+电视剧|^动漫|\s+动漫', content):
            mtype = MediaType.TV
        else:
            mtype = None
        content = re.sub(r'^电影|^电视剧|^动漫|\s+电影|\s+电视剧|\s+动漫', '', content).strip()
        # 稍微切一下剧集吧
        season_num = None
        episode_num = None
        year = None
        season_re = re.search(r"第\s*([0-9一二三四五六七八九十]+)\s*季", content, re.IGNORECASE)
        if season_re:
            mtype = MediaType.TV
            season_num = int(cn2an.cn2an(season_re.group(1), mode='smart'))
        episode_re = re.search(r"第\s*([0-9一二三四五六七八九十]+)\s*集", content, re.IGNORECASE)
        if episode_re:
            mtype = MediaType.TV
            episode_num = int(cn2an.cn2an(episode_re.group(1), mode='smart'))
            if episode_num and not season_num:
                season_num = "1"
        year_re = re.search(r"[\s(]+(\d{4})[\s)]*", content)
        if year_re:
            year = year_re.group(1)
        key_word = re.sub(r'第\s*[0-9一二三四五六七八九十]+\s*季|第\s*[0-9一二三四五六七八九十]+\s*集|[\s(]+(\d{4})[\s)]*', '',
                          content,
                          flags=re.IGNORECASE).strip()
        if key_word:
            key_word = re.sub(r'\s+', ' ', key_word)
        if not key_word:
            key_word = year

        return mtype, key_word, season_num, episode_num, year, content

    @staticmethod
    @lru_cache(maxsize=128)
    def check_torrent_attr(torrent_url, cookie) -> list:
        """
        检验种子是否免费
        :param torrent_url: 种子的详情页面
        :param cookie: 站点的Cookie
        :return: 促销类型 FREE 2XFREE HR 的数组
        """
        ret_attr = []
        if not torrent_url:
            return ret_attr
        url_host = parse.urlparse(torrent_url).netloc
        if not url_host:
            return ret_attr
        xpath_strs = RSS_SITE_GRAP_CONF.get(url_host)
        if not xpath_strs:
            return ret_attr
        res = RequestUtils(cookies=cookie).get_res(url=torrent_url)
        if res and res.status_code == 200:
            res.encoding = res.apparent_encoding
            html_text = res.text
            if not html_text:
                return []
            try:
                html = etree.HTML(html_text)
                # 检测2XFREE
                for xpath_str in xpath_strs.get("2XFREE"):
                    if html.xpath(xpath_str):
                        ret_attr.append("FREE")
                        ret_attr.append("2XFREE")
                # 检测FREE
                for xpath_str in xpath_strs.get("FREE"):
                    if html.xpath(xpath_str):
                        ret_attr.append("FREE")
                # 检测HR
                for xpath_str in xpath_strs.get("HR"):
                    if html.xpath(xpath_str):
                        ret_attr.append("HR")
            except Exception as err:
                print(err)
        # 随机休眼后再返回
        sleep(round(random.uniform(1, 5), 1))
        return ret_attr

    @staticmethod
    def get_torrent_content(url):
        """
        把种子下载到本地，返回种子内容
        :param url: 种子链接
        """
        if not url:
            return None, "URL为空"
        try:
            if url.startswith("magnet:"):
                return url, "磁力链接"
            req = RequestUtils().get_res(url=url)
            if req and req.status_code == 200:
                if not req.content:
                    return None, "未下载到种子数据"
                metadata = bencode.bdecode(req.content)
                if not metadata or not isinstance(metadata, dict):
                    return None, "不正确的种子文件"
                return req.content, ""
            elif not req:
                return url, "无法打开链接"
            else:
                return None, "状态码：%s" % req.status_code
        except Exception as err:
            return None, "%s" % str(err)

    @staticmethod
    def check_torrent_filter(meta_info: MetaBase, filter_args, uploadvolumefactor=None, downloadvolumefactor=None):
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
        解析订阅的NOTE字段，从中获取订阅站点、搜索站点、是否洗版、订阅质量、订阅分辨率、过滤规则等信息
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

        return rss_sites, search_sites, over_edition, {"restype": rss_restype, "pix": rss_pix, "rule": rss_rule}
