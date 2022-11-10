import re
import time
import random
from lxml import etree

from app.helper import DbHelper
from app.sites.sites import Sites
from app.utils.commons import singleton
from app.utils.types import MediaType
from app.utils import StringUtils
from config import TORRENT_SEARCH_PARAMS


@singleton
class Filter:
    _groups = []
    _rules = []
    sites = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        _dbhelper = DbHelper()
        self.sites = Sites()
        self._groups = _dbhelper.get_config_filter_group()
        self._rules = _dbhelper.get_config_filter_rule()

    def get_rule_groups(self, groupid=None, default=False):
        """
        获取所有规则组
        """
        ret_groups = []
        for group in self._groups:
            group_info = {
                "id": group.ID,
                "name": group.GROUP_NAME,
                "default": group.IS_DEFAULT,
                "note": group.NOTE
            }
            if groupid and str(groupid) == str(group.ID) \
                    or default and group.IS_DEFAULT == "Y":
                return group_info
            ret_groups.append(group_info)
        if groupid or default:
            return {}
        return ret_groups

    def get_rule_infos(self):
        """
        获取所有的规则组及组内的规则
        """
        groups = self.get_rule_groups()
        for group in groups:
            group['rules'] = self.get_rules(group.get("id"))
        return groups

    def get_rules(self, groupid, ruleid=None):
        """
        获取过滤规则
        """
        if not groupid:
            return []
        ret_rules = []
        for rule in self._rules:
            rule_info = {
                "id": rule.ID,
                "group": rule.GROUP_ID,
                "name": rule.ROLE_NAME,
                "pri": rule.PRIORITY or 0,
                "include": rule.INCLUDE.split("\n") if rule.INCLUDE else [],
                "exclude": rule.EXCLUDE.split("\n") if rule.EXCLUDE else [],
                "size": rule.SIZE_LIMIT,
                "free": rule.NOTE,
                "free_text": {
                    "1.0 1.0": "普通",
                    "1.0 0.0": "免费",
                    "2.0 0.0": "2X免费"
                }.get(rule.NOTE, "全部") if rule.NOTE else ""
            }
            if str(rule.GROUP_ID) == str(groupid) \
                    and (not ruleid or int(ruleid) == rule.ID):
                ret_rules.append(rule_info)
        if ruleid:
            return ret_rules[0] if ret_rules else {}
        return ret_rules

    def check_rules(self, meta_info, rulegroup=None):
        """
        检查种子是否匹配站点过滤规则：排除规则、包含规则，优先规则
        :param meta_info: 识别的信息
        :param rulegroup: 规则组ID
        :return: 是否匹配，匹配的优先值，规则名称，值越大越优先
        """
        if not meta_info:
            return False, 0, ""
        if meta_info.subtitle:
            title = "%s %s" % (meta_info.org_string, meta_info.subtitle)
        else:
            title = meta_info.org_string
        if not rulegroup:
            rulegroup = self.get_rule_groups(default=True)
            if not rulegroup:
                return True, 0, "未配置过滤规则"
        else:
            rulegroup = self.get_rule_groups(groupid=rulegroup)
        filters = self.get_rules(groupid=rulegroup.get("id"))
        # 命中优先级
        order_seq = 0
        # 当前规则组是否命中
        group_match = True
        for filter_info in filters:
            # 当前规则是否命中
            rule_match = True
            # 命中规则的序号
            order_seq = 100 - int(filter_info.get('pri'))
            # 必须包括的项
            includes = filter_info.get('include')
            if includes and rule_match:
                include_flag = True
                for include in includes:
                    if not include:
                        continue
                    if not re.search(r'%s' % include.strip(), title, re.IGNORECASE):
                        include_flag = False
                        break
                if not include_flag:
                    rule_match = False

            # 不能包含的项
            excludes = filter_info.get('exclude')
            if excludes and rule_match:
                exclude_flag = False
                exclude_count = 0
                for exclude in excludes:
                    if not exclude:
                        continue
                    exclude_count += 1
                    if not re.search(r'%s' % exclude.strip(), title, re.IGNORECASE):
                        exclude_flag = True
                if exclude_count > 0 and not exclude_flag:
                    rule_match = False
            # 大小
            sizes = filter_info.get('size')
            if sizes and rule_match and meta_info.size:
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
                if meta_info.type == MediaType.MOVIE:
                    if not begin_size * 1024 ** 3 <= int(meta_info.size) <= end_size * 1024 ** 3:
                        rule_match = False
                else:
                    if meta_info.total_episodes \
                            and not begin_size * 1024 ** 3 <= int(meta_info.size)/int(meta_info.total_episodes) <= end_size * 1024 ** 3:
                        rule_match = False

            # 促销
            free = filter_info.get("free")
            if free and meta_info.upload_volume_factor is not None and meta_info.download_volume_factor is not None:
                ul_factor, dl_factor = free.split()
                if float(ul_factor) > meta_info.upload_volume_factor \
                        or float(dl_factor) < meta_info.download_volume_factor:
                    rule_match = False

            if rule_match:
                return True, order_seq, rulegroup.get("name")
            else:
                group_match = False
        if not group_match:
            return False, 0, rulegroup.get("name")
        return True, order_seq, rulegroup.get("name")

    def is_rule_free(self, rulegroup=None):
        """
        判断规则中是否需要Free检测
        """
        if not rulegroup:
            rulegroup = self.get_rule_groups(default=True)
            if not rulegroup:
                return True, 0, ""
        else:
            rulegroup = self.get_rule_groups(groupid=rulegroup)
        filters = self.get_rules(groupid=rulegroup.get("id"))
        for filter_info in filters:
            if filter_info.get("free"):
                return True
        return False

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

    def check_torrent_filter(self, meta_info, filter_args, uploadvolumefactor=None, downloadvolumefactor=None):
        """
        对种子进行过滤
        :param meta_info: 名称识别后的MetaBase对象
        :param filter_args: 过滤条件的字典
        :param uploadvolumefactor: 种子的上传因子 传空不过滤
        :param downloadvolumefactor: 种子的下载因子 传空不过滤
        :return: 是否匹配，匹配的优先值，匹配信息，值越大越优先
        """
        # 过滤质量
        if filter_args.get("restype"):
            restype = TORRENT_SEARCH_PARAMS["restype"].get(str(filter_args.get("restype")))
            restype_re = restype.get("re")
            restype_name = restype.get("name")
            if not meta_info.resource_type:
                return False, 0, f"{meta_info.org_string} 不符合质量 {restype_name}要求"
            if restype_re and not re.search(r"%s" % restype_re, meta_info.resource_type, re.I):
                return False, 0, f"{meta_info.org_string} 不符合质量 {restype_name}要求"
        # 过滤分辨率
        if filter_args.get("pix"):
            pix = TORRENT_SEARCH_PARAMS["pix"].get(str(filter_args.get("pix")))
            pix_name = pix.get("name")
            pix_re = pix.get("re")
            if not meta_info.resource_pix:
                return False, 0, f"{meta_info.org_string} 不符合分辨率 {pix_name}要求"
            if pix_re and not re.search(r"%s" % pix_re, meta_info.resource_pix, re.I):
                return False, 0, f"{meta_info.org_string} 不符合分辨率 {pix_name}要求"
        # 过滤制作组/字幕组
        if filter_args.get("team"):
            team = filter_args.get("team")
            if not meta_info.resource_team:
                return False, 0, f"{meta_info.org_string} 不符合制作组/字幕组 {team}要求"
            if team and not re.search(r"%s" % team, meta_info.resource_team, re.I):
                return False, 0, f"{meta_info.org_string} 不符合制作组/字幕组 {team}要求"
        # 过滤促销
        if filter_args.get("sp_state"):
            ul_factor, dl_factor = filter_args.get("sp_state").split()
            if uploadvolumefactor and ul_factor not in ("*", str(uploadvolumefactor)):
                return False, 0, f"{meta_info.org_string} 不符合促销要求"
            if downloadvolumefactor and dl_factor not in ("*", str(downloadvolumefactor)):
                return False, 0, f"{meta_info.org_string} 不符合促销要求"
        # 过滤关键字
        if filter_args.get("key"):
            key = filter_args.get("key")
            if not re.search(r"%s" % key, meta_info.org_string, re.I):
                return False, 0, f"{meta_info.org_string} 不符合 {key}要求"
        # 过滤过滤规则
        if filter_args.get("rule"):
            rule_group = filter_args.get("rule")
            if rule_group == -1:
                match_flag, order_seq, match_msg = self.check_rules(meta_info)
                match_msg = "%s 大小：%s 促销：%s 不符合订阅/站点过滤规则 %s要求" % (
                    meta_info.org_string,
                    StringUtils.str_filesize(meta_info.size),
                    meta_info.get_volume_factor_string(),
                    match_msg
                )
                return match_flag, order_seq, match_msg
            match_flag, order_seq, match_msg = self.check_rules(meta_info, rule_group)
            match_msg = "%s 大小：%s 促销：%s 不符合默认过滤规则 %s要求" % (
                meta_info.org_string,
                StringUtils.str_filesize(meta_info.size),
                meta_info.get_volume_factor_string(),
                match_msg
            )
            return match_flag, order_seq, match_msg
        return True, 0, ""

    def check_torrent_attr(self, torrent_url, cookie, ua=None):
        """
        检验种子是否免费，当前做种人数
        :param torrent_url: 种子的详情页面
        :param cookie: 站点的Cookie
        :param ua: 站点的ua
        :return: 种子属性，包含FREE 2XFREE HR PEER_COUNT等属性
        """
        ret_attr = {
            "free": False,
            "2xfree": False,
            "hr": False,
            "peer_count": 0
        }
        if not torrent_url:
            return ret_attr
        xpath_strs = self.sites.get_grapsite_conf(torrent_url)
        if not xpath_strs:
            return ret_attr
        html_text = self.sites.__get_site_page_html(url=torrent_url, cookie=cookie, ua=ua)
        if not html_text:
            return ret_attr
        try:
            html = etree.HTML(html_text)
            # 检测2XFREE
            for xpath_str in xpath_strs.get("2XFREE"):
                if html.xpath(xpath_str):
                    ret_attr["free"] = True
                    ret_attr["2xfree"] = True
            # 检测FREE
            for xpath_str in xpath_strs.get("FREE"):
                if html.xpath(xpath_str):
                    ret_attr["free"] = True
            # 检测HR
            for xpath_str in xpath_strs.get("HR"):
                if html.xpath(xpath_str):
                    ret_attr["hr"] = True
            # 检测PEER_COUNT当前做种人数
            for xpath_str in xpath_strs.get("PEER_COUNT"):
                peer_count_dom = html.xpath(xpath_str)
                if peer_count_dom:
                    peer_count_str = peer_count_dom[0].text
                    peer_count_str_re = re.search(r'^(\d+)', peer_count_str)
                    ret_attr["peer_count"] = int(peer_count_str_re.group(1)) if peer_count_str_re else 0
        except Exception as err:
            print(str(err))
        # 随机休眼后再返回
        time.sleep(round(random.uniform(1, 5), 1))
        return ret_attr

    def check_torrent_rss(self,
                          media_info,
                          rss_movies,
                          rss_tvs,
                          site_filter_rule,
                          site_cookie,
                          site_parse,
                          site_ua):
        """
        判断种子是否命中订阅
        :param media_info: 已识别的种子媒体信息
        :param rss_movies: 电影订阅清单
        :param rss_tvs: 电视剧订阅清单
        :param site_filter_rule: 站点过滤规则
        :param site_cookie: 站点的Cookie
        :param site_parse: 是否解析种子详情
        :param site_ua: 站点请求UA
        :return: 匹配到的订阅ID、是否洗版、总集数、匹配规则的资源顺序、上传因子、下载因子，匹配的季（电视剧）
        """
        # 默认值
        # 匹配状态 0不在订阅范围内 -1不符合过滤条件 1匹配
        match_flag = False
        # 匹配的rss信息
        match_msg = []
        match_rss_info = {}
        # 上传因素
        upload_volume_factor = None
        # 下载因素
        download_volume_factor = None
        hit_and_run = False

        # 匹配电影
        if media_info.type == MediaType.MOVIE and rss_movies:
            for id in rss_movies:
                rss_info = rss_movies[id]
                rss_sites = rss_info.get('rss_sites')
                # 过滤订阅站点
                if rss_sites and media_info.site not in rss_sites:
                    continue
                # tmdbid或名称年份匹配
                name = rss_info.get('name')
                year = rss_info.get('year')
                tmdbid = rss_info.get('tmdbid')
                fuzzy_match = rss_info.get('fuzzy_match')
                # 非模糊匹配
                if not fuzzy_match:
                    # 有tmdbid时使用tmdbid匹配
                    if tmdbid and not tmdbid.startswith("DB:"):
                        if str(media_info.tmdb_id) != str(tmdbid):
                            continue
                    else:
                        # 豆瓣年份与tmdb取向不同
                        if year and str(media_info.year) not in [str(year),
                                                                 str(int(year) + 1),
                                                                 str(int(year) - 1)]:
                            continue
                        if name not in [str(media_info.title),
                                        str(media_info.original_title)]:
                            continue
                # 模糊匹配
                else:
                    # 匹配年份
                    if year and str(year) != str(media_info.year):
                        continue
                    # 匹配关键字或正则表达式
                    search_title = f"{media_info.org_string} {media_info.title} {media_info.original_title} {media_info.year}"
                    if not re.search(name, search_title, re.I) and name not in search_title:
                        continue
                # 媒体匹配成功
                match_flag = True
                match_rss_info = rss_info

                break
        # 匹配电视剧
        elif rss_tvs:
            # 匹配种子标题
            for id in rss_tvs:
                rss_info = rss_tvs[id]
                rss_sites = rss_info.get('rss_sites')
                # 过滤订阅站点
                if rss_sites and media_info.site not in rss_sites:
                    continue
                # 有tmdbid时精确匹配
                name = rss_info.get('name')
                year = rss_info.get('year')
                season = rss_info.get('season')
                total = rss_info.get('total')
                current = rss_info.get('current')
                tmdbid = rss_info.get('tmdbid')
                fuzzy_match = rss_info.get('fuzzy_match')
                # 匹配季，季可以为空
                if season and season != media_info.get_season_string():
                    continue
                # 匹配集
                if not media_info.get_episode_list():
                    continue
                for episode in media_info.get_episode_list():
                    if total < episode:
                        continue
                    if current and current > episode:
                        continue
                # 非模糊匹配
                if not fuzzy_match:
                    if tmdbid and not tmdbid.startswith("DB:"):
                        if str(media_info.tmdb_id) != str(tmdbid):
                            continue
                    else:
                        # 匹配年份，年份可以为空
                        if year and str(year) != str(media_info.year):
                            continue
                        # 匹配名称
                        if name not in [str(media_info.title),
                                        str(media_info.original_title)]:
                            continue
                # 模糊匹配
                else:
                    # 匹配年份
                    if year and str(year) != str(media_info.year):
                        continue
                    # 匹配关键字或正则表达式
                    search_title = f"{media_info.org_string} {media_info.title} {media_info.original_title} {media_info.year}"
                    if not re.search(name, search_title, re.I) and name not in search_title:
                        continue
                # 媒体匹配成功
                match_flag = True
                match_rss_info = rss_info
                break
        # 名称匹配成功，开始过滤
        if match_flag:
            # 解析种子详情
            if site_parse:
                # 检测Free
                torrent_attr = self.check_torrent_attr(torrent_url=media_info.page_url,
                                                                  cookie=site_cookie,
                                                                  ua=site_ua)
                if torrent_attr.get('2xfree'):
                    download_volume_factor = 0.0
                    upload_volume_factor = 2.0
                elif torrent_attr.get('free'):
                    download_volume_factor = 0.0
                    upload_volume_factor = 1.0
                else:
                    upload_volume_factor = 1.0
                    download_volume_factor = 1.0
                if torrent_attr.get('hr'):
                    hit_and_run = True
                # 设置属性
                media_info.set_torrent_info(upload_volume_factor=upload_volume_factor,
                                            download_volume_factor=download_volume_factor,
                                            hit_and_run=hit_and_run)
            # 订阅无过滤规则应用站点设置
            # 过滤质
            filter_dict = {
                "restype": match_rss_info.get('filter_restype'),
                "pix": match_rss_info.get('filter_pix'),
                "team": match_rss_info.get('filter_team'),
                "rule": match_rss_info.get('filter_rule') or site_filter_rule or -1
            }
            match_filter_flag, res_order, match_filter_msg = self.check_torrent_filter(meta_info=media_info,
                                                                                       filter_args=filter_dict)
            if not match_filter_flag:
                match_msg.append(match_filter_msg)
                return False, match_msg, match_rss_info
            else:
                match_msg.append("%s 识别为 %s %s 匹配订阅成功" % (
                    media_info.org_string,
                    media_info.get_title_string(),
                    media_info.get_season_episode_string()))
                match_msg.append(f"种子描述：{media_info.subtitle}")
                match_rss_info.update({
                    "res_order": res_order,
                    "upload_volume_factor": upload_volume_factor,
                    "download_volume_factor": download_volume_factor})
                return True, match_msg, match_rss_info
        else:
            match_msg.append("%s 识别为 %s %s 不在订阅范围" % (
                media_info.org_string,
                media_info.get_title_string(),
                media_info.get_season_episode_string()))
            return False, match_msg, match_rss_info
