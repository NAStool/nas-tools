import re
from functools import lru_cache
from urllib import parse
import cn2an
from lxml import etree
from config import GRAP_FREE_SITES
from utils.http_utils import RequestUtils
from utils.types import MediaType
import bencode


class Torrent:

    @staticmethod
    def is_torrent_match_rss(media_info, movie_keys, tv_keys, site_name):
        """
        判断种子是否命中订阅
        :param media_info: 已识别的种子媒体信息
        :param movie_keys: 电影订阅清单
        :param tv_keys: 电视剧订阅清单
        :param site_name: 站点名称
        :return: 命中状态
        """
        if media_info.type == MediaType.MOVIE:
            for key_info in movie_keys:
                if not key_info:
                    continue
                name = key_info[0]
                year = key_info[1]
                tmdbid = key_info[2]
                sites = key_info[4]
                # 未订阅站点不匹配
                if sites and sites.find('|') != -1 and site_name not in sites.split('|'):
                    continue
                # 有tmdbid时精确匹配
                if tmdbid:
                    # 匹配名称、年份，年份可以没有
                    if name == media_info.title and (not year or str(year) == str(media_info.year)) \
                            or str(media_info.tmdb_id) == str(tmdbid):
                        return True
                # 模糊匹配
                else:
                    # 匹配年份
                    if year and str(year) != str(media_info.year):
                        continue
                    # 匹配关键字，可能是正则表达式
                    if re.search(r"%s" % name,
                                 "%s %s %s" % (media_info.org_string, media_info.title, media_info.year),
                                 re.IGNORECASE):
                        return True
        else:
            # 匹配种子标题
            for key_info in tv_keys:
                if not key_info:
                    continue
                name = key_info[0]
                year = key_info[1]
                season = key_info[2]
                tmdbid = key_info[3]
                sites = key_info[5]
                # 未订阅站点不匹配
                if sites and sites.find('|') != -1 and site_name not in sites:
                    continue
                # 有tmdbid时精确匹配
                if tmdbid:
                    # 匹配季，季可以为空
                    if season and season != media_info.get_season_string():
                        continue
                    # 匹配年份，年份可以为空
                    if year and str(year) != str(media_info.year):
                        continue
                    # 匹配名称
                    if name == media_info.title or str(media_info.tmdb_id) == str(tmdbid):
                        return True
                # 模糊匹配
                else:
                    # 匹配季
                    if season and season != "S00" and season != media_info.get_season_string():
                        continue
                    # 匹配年份
                    if year and str(year) != str(media_info.year):
                        continue
                    # 匹配关键字，可能是正则表达式
                    if re.search(r"%s" % name,
                                 "%s %s %s" % (media_info.org_string, media_info.title, media_info.year),
                                 re.IGNORECASE):
                        return True
        return False

    @staticmethod
    def is_torrent_match_size(media_info, types, t_size):
        """
        判断种子大子是否与配置匹配，只针对电影
        :param media_info: 已识别好的种子媒体信息
        :param types: 配置中的过滤规则
        :param t_size: 种子大小
        :return: 是否命中
        """
        if media_info.type != MediaType.MOVIE:
            return True
        if not isinstance(types, dict):
            return True
        # 大小
        if t_size:
            sizes = types.get('size')
            if sizes:
                if sizes.find(',') != -1:
                    sizes = sizes.split(',')
                    if sizes[0].isdigit():
                        begin_size = int(sizes[0].strip())
                    else:
                        begin_size = 0
                    if sizes[1].isdigit():
                        end_size = int(sizes[1].strip())
                    else:
                        end_size = 0
                else:
                    begin_size = 0
                    if sizes.isdigit():
                        end_size = int(sizes.strip())
                    else:
                        end_size = 0
                if not begin_size * 1024 * 1024 * 1024 <= int(t_size) <= end_size * 1024 * 1024 * 1024:
                    return False
        return True

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

    @classmethod
    def check_resouce_types(cls, title, subtitle, types):
        """
        检查种子是否匹配过滤规则：排除规则、包含规则，优先规则
        :param title: 种子标题
        :param subtitle: 种子副标题
        :param types: 配置文件中的配置规则
        :return: 是否匹配，匹配的优先值，值越大越优先
        """
        if not types:
            # 未配置默认不过滤
            return True, 0
        if not isinstance(types, dict):
            return True, 0
        if not title:
            return False, 0
        # 必须包括的项
        includes = types.get('include')
        if includes:
            if isinstance(includes, str):
                includes = [includes]
            include_flag = True
            for include in includes:
                if not include:
                    continue
                re_res = re.search(r'%s' % include.strip(), title, re.IGNORECASE)
                if not re_res:
                    include_flag = False
            if not include_flag:
                return False, 0

        # 不能包含的项
        excludes = types.get('exclude')
        if excludes:
            if isinstance(excludes, str):
                excludes = [excludes]
            exclude_flag = False
            exclude_count = 0
            for exclude in excludes:
                if not exclude:
                    continue
                exclude_count += 1
                re_res = re.search(r'%s' % exclude.strip(), title, re.IGNORECASE)
                if not re_res:
                    exclude_flag = True
            if exclude_count != 0 and not exclude_flag:
                return False, 0

        return True, cls.check_res_order(title, subtitle, types)

    @staticmethod
    def check_res_order(title, subtitle, types):
        """
        检查种子是否匹配优先规则
        :param title: 种子标题
        :param subtitle: 种子副标题
        :param types: 配置文件中的配置规则
        :return: 匹配的优先顺序
        """
        res_order = 0
        if not types:
            return res_order
        notes = types.get('note')
        if notes:
            res_seq = 100
            for note in notes:
                res_seq = res_seq - 1
                if re.search(r"%s" % note, "%s%s" % (title, subtitle), re.IGNORECASE):
                    res_order = res_seq
                    break
        return res_order

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
    def get_download_list(media_list):
        """
        对媒体信息进行排序、去重
        """
        if not media_list:
            return []

        # 排序函数，标题、PT站、资源类型、做种数量
        def get_sort_str(x):
            season_len = str(len(x.get_season_list())).rjust(2, '0')
            episode_len = str(len(x.get_episode_list())).rjust(4, '0')
            # 排序：标题、资源类型、站点、做种、季集
            return "%s%s%s%s%s" % (str(x.title).ljust(100, ' '),
                                   str(x.res_order).rjust(3, '0'),
                                   str(x.site_order).rjust(3, '0'),
                                   str(x.seeders).rjust(10, '0'),
                                   "%s%s" % (season_len, episode_len))

        # 匹配的资源中排序分组选最好的一个下载
        # 按站点顺序、资源匹配顺序、做种人数下载数逆序排序
        media_list = sorted(media_list, key=lambda x: get_sort_str(x), reverse=True)
        # 控重
        can_download_list_item = []
        can_download_list = []
        # 排序后重新加入数组，按真实名称控重，即只取每个名称的第一个
        for t_item in media_list:
            # 控重的主链是名称、年份、季、集
            if t_item.type != MediaType.MOVIE:
                media_name = "%s%s" % (t_item.get_title_string(),
                                       t_item.get_season_episode_string())
            else:
                media_name = t_item.get_title_string()
            if media_name not in can_download_list:
                can_download_list.append(media_name)
                can_download_list_item.append(t_item)
        return can_download_list_item

    @staticmethod
    @lru_cache(maxsize=128)
    def check_torrent_free(torrent_url, cookie):
        """
        检验种子是否免费
        :param torrent_url: 种子的详情页面
        :param cookie: 站点的Cookie
        :return: 促销类型 FREE 2XFREE
        """
        if not torrent_url:
            return None
        url_host = parse.urlparse(torrent_url).netloc
        if not url_host:
            return None
        xpath_strs = GRAP_FREE_SITES.get(url_host)
        if not xpath_strs:
            return None
        res = RequestUtils(cookies=cookie).get_res(url=torrent_url)
        if res and res.status_code == 200:
            res.encoding = res.apparent_encoding
            html_text = res.text
            if not html_text:
                return None
            try:
                html = etree.HTML(html_text)
                # 检测2XFREE
                for xpath_str in xpath_strs.get("2XFREE"):
                    if html.xpath(xpath_str):
                        return "2XFREE"
                # 检测FREE
                for xpath_str in xpath_strs.get("FREE"):
                    if html.xpath(xpath_str):
                        return "FREE"
            except Exception as err:
                print(err)
        return None

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
                return None, "无法打开链接"
            else:
                return None, "状态码：%s" % req.status_code
        except Exception as err:
            return None, "%s" % str(err)
