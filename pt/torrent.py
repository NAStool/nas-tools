import re
from utils.types import MediaType


class Torrent:

    # 种子大小匹配
    @staticmethod
    def is_torrent_match_size(media_info, types, t_size):
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

    # 种子名称关键字匹配
    @staticmethod
    def is_torrent_match_sey(media_info, s_num, e_num, year_str):
        if s_num:
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
            if str(media_info.year) != year_str:
                return False
        return True

    # 检查种子是否匹配资源类型
    # 返回：是否匹配，匹配的优先值
    @staticmethod
    def check_resouce_types(title, subtitle, types):
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

        # 优先包含的项
        notes = types.get('note')
        res_order = 0
        if notes:
            res_seq = 100
            for note in notes:
                res_seq = res_seq - 1
                if re.search(r"%s" % note, "%s%s" % (title, subtitle), re.IGNORECASE):
                    res_order = res_seq
                    break

        return True, res_order
