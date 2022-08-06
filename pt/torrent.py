import random
import re
from functools import lru_cache
from time import sleep
from urllib import parse
import cn2an
from lxml import etree

import log
from config import TORRENT_SEARCH_PARAMS
from pt.filterrules import FilterRule
from pt.siteconf import RSS_SITE_GRAP_CONF
from rmt.meta.metabase import MetaBase
from utils.functions import str_filesize
from utils.http_utils import RequestUtils
from utils.types import MediaType
import bencode


class Torrent:

    def is_torrent_match_rss(self,
                             media_info: MetaBase,
                             movie_keys,
                             tv_keys,
                             site_rule,
                             site_cookie):
        """
        判断种子是否命中订阅
        :param media_info: 已识别的种子媒体信息
        :param movie_keys: 电影订阅清单
        :param tv_keys: 电视剧订阅清单
        :param site_rule: 站点过滤规则
        :param site_cookie: 站点的Cookie
        :return: 匹配到的订阅ID、是否洗版、总集数、匹配规则的资源顺序、上传因子、下载因子
        """
        # 默认值
        match_flag = False
        res_order = 0
        rssid = None
        over_edition = None
        upload_volume_factor = 1.0
        download_volume_factor = 1.0
        rulegroup = site_rule
        total_episodes = 0

        # 匹配电影
        if media_info.type == MediaType.MOVIE:
            for key_info in movie_keys:
                if not key_info:
                    continue
                name = key_info[0]
                year = key_info[1]
                tmdbid = key_info[2]
                rssid = key_info[6]
                # 订阅站点，是否洗板，过滤字典
                sites, _, over_edition, filter_map = self.get_rss_note_item(key_info[4])
                # 订阅有指定过滤规则时优先使用订阅的
                if filter_map and filter_map.get("rule"):
                    rulegroup = filter_map.get("rule")
                # 过滤订阅站点
                if sites and media_info.site not in sites:
                    continue
                # 过滤字典
                if filter_map and not Torrent.check_torrent_filter(media_info, filter_map):
                    continue
                # 有tmdbid时使用TMDBID匹配
                if tmdbid:
                    if not tmdbid.startswith("DB:"):
                        if str(media_info.tmdb_id) != str(tmdbid):
                            continue
                    else:
                        if year and str(year) != str(media_info.year):
                            continue
                        if str(name) != str(media_info.title):
                            continue
                # 模糊匹配
                else:
                    # 模糊匹配时的默认值
                    rssid = 0
                    # 匹配年份
                    if year and str(year) != str(media_info.year):
                        continue
                    # 匹配关键字，可能是正则表达式
                    if not re.search(r"%s" % name,
                                     "%s %s %s" % (media_info.org_string, media_info.title, media_info.year),
                                     re.IGNORECASE):
                        continue
                # 媒体匹配成功
                match_flag = True
                break
        # 匹配电视剧
        else:
            # 匹配种子标题
            for key_info in tv_keys:
                if not key_info:
                    continue
                name = key_info[0]
                year = key_info[1]
                season = key_info[2]
                tmdbid = key_info[3]
                rssid = key_info[10]
                total_episodes = key_info[6]
                # 订阅站点
                sites, _, over_edition, filter_map = self.get_rss_note_item(key_info[5])
                # 订阅有指定过滤规则时优先使用订阅的
                if filter_map and filter_map.get("rule"):
                    rulegroup = filter_map.get("rule")
                # 过滤订阅站点
                if sites and media_info.site not in sites:
                    continue
                # 过滤字典
                if filter_map and not Torrent.check_torrent_filter(media_info, filter_map):
                    continue
                # 有tmdbid时精确匹配
                if tmdbid:
                    if not tmdbid.startswith("DB:"):
                        if str(media_info.tmdb_id) != str(tmdbid):
                            continue
                    else:
                        # 匹配季，季可以为空
                        if season and season != media_info.get_season_string():
                            continue
                        # 匹配年份，年份可以为空
                        if year and str(year) != str(media_info.year):
                            continue
                        # 匹配名称
                        if str(name) != str(media_info.title):
                            continue
                # 模糊匹配
                else:
                    # 模糊匹配时的默认值
                    rssid = 0
                    # 匹配季
                    if season and season != "S00" and season != media_info.get_season_string():
                        continue
                    # 匹配年份
                    if year and str(year) != str(media_info.year):
                        continue
                    # 匹配关键字，可能是正则表达式
                    if not re.search(r"%s" % name,
                                     "%s %s %s" % (media_info.org_string, media_info.title, media_info.year),
                                     re.IGNORECASE):
                        continue
                # 媒体匹配成功
                match_flag = True
                break
        # 名称匹配成功，开始匹配规则
        if match_flag:
            # 检测Free
            attr_type = Torrent.check_torrent_attr(torrent_url=media_info.page_url, cookie=site_cookie)
            if "2XFREE" in attr_type:
                download_volume_factor = 0.0
                upload_volume_factor = 2.0
            elif "FREE" in attr_type:
                download_volume_factor = 0.0
                upload_volume_factor = 1.0
            # 设置属性
            media_info.set_torrent_info(upload_volume_factor=upload_volume_factor,
                                        download_volume_factor=download_volume_factor)
            match_flag, res_order, _ = FilterRule().check_rules(meta_info=media_info,
                                                                rolegroup=rulegroup)
            if not match_flag:
                log.info(f"【RSS】{media_info.org_string} 大小：{str_filesize(media_info.size)} 促销：{media_info.get_volume_factor_string()} 不符合过滤规则")
        if match_flag:
            return rssid, over_edition, total_episodes, res_order, upload_volume_factor, download_volume_factor
        else:
            return None, None, total_episodes, res_order, upload_volume_factor, download_volume_factor

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
