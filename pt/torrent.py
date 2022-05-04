import re
from utils.types import MediaType


class Torrent:

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

    @staticmethod
    def check_resouce_types(title, subtitle, types):
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
