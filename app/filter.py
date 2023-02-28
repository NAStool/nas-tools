import re

from app.conf import ModuleConf
from app.helper import DbHelper
from app.media.meta import ReleaseGroupsMatcher
from app.utils import StringUtils
from app.utils.commons import singleton
from app.utils.types import MediaType


@singleton
class Filter:
    rg_matcher = None
    dbhelper = None
    _groups = []
    _rules = []

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()
        self.rg_matcher = ReleaseGroupsMatcher()
        self._groups = self.dbhelper.get_config_filter_group()
        self._rules = self.dbhelper.get_config_filter_rule()

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
            if (groupid and str(groupid) == str(group.ID)) \
                    or (default and group.IS_DEFAULT == "Y"):
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

    def get_rule_first_order(self, rulegroup):
        """
        获取规则的最高优先级
        """
        if not rulegroup:
            rulegroup = self.get_rule_groups(default=True)
        first_order = min([int(rule_info.get("pri")) for rule_info in self.get_rules(groupid=rulegroup)] or [0])
        return 100 - first_order

    def check_rules(self, meta_info, rulegroup=None):
        """
        检查种子是否匹配站点过滤规则：排除规则、包含规则，优先规则
        :param meta_info: 识别的信息
        :param rulegroup: 规则组ID
        :return: 是否匹配，匹配的优先值，规则名称，值越大越优先
        """
        if not meta_info:
            return False, 0, ""
        # 为-1时不使用过滤规则
        if rulegroup and int(rulegroup) == -1:
            return True, 0, "不过滤"
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
                meta_info.size = StringUtils.num_filesize(meta_info.size)
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
                            and not begin_size * 1024 ** 3 <= int(meta_info.size) / int(meta_info.total_episodes) <= end_size * 1024 ** 3:
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

    def check_torrent_filter(self,
                             meta_info,
                             filter_args,
                             uploadvolumefactor=None,
                             downloadvolumefactor=None):
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
            restype_re = ModuleConf.TORRENT_SEARCH_PARAMS["restype"].get(filter_args.get("restype"))
            if not meta_info.get_edtion_string():
                return False, 0, f"{meta_info.org_string} 不符合质量 {filter_args.get('restype')} 要求"
            if restype_re and not re.search(r"%s" % restype_re, meta_info.get_edtion_string(), re.I):
                return False, 0, f"{meta_info.org_string} 不符合质量 {filter_args.get('restype')} 要求"
        # 过滤分辨率
        if filter_args.get("pix"):
            pix_re = ModuleConf.TORRENT_SEARCH_PARAMS["pix"].get(filter_args.get("pix"))
            if not meta_info.resource_pix:
                return False, 0, f"{meta_info.org_string} 不符合分辨率 {filter_args.get('pix')} 要求"
            if pix_re and not re.search(r"%s" % pix_re, meta_info.resource_pix, re.I):
                return False, 0, f"{meta_info.org_string} 不符合分辨率 {filter_args.get('pix')} 要求"
        # 过滤制作组/字幕组
        if filter_args.get("team"):
            team = filter_args.get("team")
            if not meta_info.resource_team:
                resource_team = self.rg_matcher.match(
                    title=meta_info.org_string,
                    groups=team)
                if not resource_team:
                    return False, 0, f"{meta_info.org_string} 不符合制作组/字幕组 {team} 要求"
                else:
                    meta_info.resource_team = resource_team
            elif not re.search(r"%s" % team, meta_info.resource_team, re.I):
                return False, 0, f"{meta_info.org_string} 不符合制作组/字幕组 {team} 要求"
        # 过滤促销
        if filter_args.get("sp_state"):
            ul_factor, dl_factor = filter_args.get("sp_state").split()
            if uploadvolumefactor and ul_factor not in ("*", str(uploadvolumefactor)):
                return False, 0, f"{meta_info.org_string} 不符合促销要求"
            if downloadvolumefactor and dl_factor not in ("*", str(downloadvolumefactor)):
                return False, 0, f"{meta_info.org_string} 不符合促销要求"
        # 过滤包含
        if filter_args.get("include"):
            include = filter_args.get("include")
            if not re.search(r"%s" % include, meta_info.org_string, re.I):
                return False, 0, f"{meta_info.org_string} 不符合包含 {include} 要求"
        # 过滤排除
        if filter_args.get("exclude"):
            exclude = filter_args.get("exclude")
            if re.search(r"%s" % exclude, meta_info.org_string, re.I):
                return False, 0, f"{meta_info.org_string} 不符合排除 {exclude} 要求"
        # 过滤关键字
        if filter_args.get("key"):
            key = filter_args.get("key")
            if not re.search(r"%s" % key, meta_info.org_string, re.I):
                return False, 0, f"{meta_info.org_string} 不符合 {key} 要求"
        # 过滤过滤规则，-1表示不使用过滤规则，空则使用默认过滤规则
        if filter_args.get("rule"):
            # 已设置默认规则
            match_flag, order_seq, rule_name = self.check_rules(meta_info, filter_args.get("rule"))
            match_msg = "%s 大小：%s 促销：%s 不符合订阅/站点过滤规则 %s 要求" % (
                meta_info.org_string,
                StringUtils.str_filesize(meta_info.size),
                meta_info.get_volume_factor_string(),
                rule_name
            )
            return match_flag, order_seq, match_msg
        else:
            # 默认过滤规则
            match_flag, order_seq, rule_name = self.check_rules(meta_info)
            match_msg = "%s 大小：%s 促销：%s 不符合默认过滤规则 %s 要求" % (
                meta_info.org_string,
                StringUtils.str_filesize(meta_info.size),
                meta_info.get_volume_factor_string(),
                rule_name
            )
            return match_flag, order_seq, match_msg
