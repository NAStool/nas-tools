import re
import cn2an

from utils.functions import str_filesize
from utils.types import MediaType


class Torrent:

    @staticmethod
    def is_torrent_match_rss(media_info, movie_keys, tv_keys):
        """
        判断种子是否命中订阅
        :param media_info: 已识别的种子媒体信息
        :param movie_keys: 电影订阅清单
        :param tv_keys: 电视剧订阅清单
        :return: 命中状态
        """
        if media_info.type == MediaType.MOVIE:
            for key_info in movie_keys:
                if not key_info:
                    continue
                name = key_info[0]
                year = key_info[1]
                # 匹配标题和年份
                if name == media_info.title and (not year or str(year) == str(media_info.year)):
                    return True
        else:
            # 匹配种子标题
            for key_info in tv_keys:
                if not key_info:
                    continue
                name = key_info[0]
                year = key_info[1]
                season = key_info[2]
                # 匹配标题和年份和季
                if name == media_info.title and (not year or str(year) == str(media_info.year)) and season == media_info.get_season_string():
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
    def get_torrents_group_item(media_list):
        """
        种子去重，每一个名称、站点、资源类型 选一个做种人最多的显示
        """
        if not media_list:
            return []

        # 排序函数
        def get_sort_str(x):
            # 排序：标题、最优规则、站点、做种
            return "%s%s%s%s" % (str(x.title).ljust(100, ' '),
                                 str(x.res_order).rjust(3, '0'),
                                 str(x.site_order).rjust(3, '0'),
                                 str(x.seeders).rjust(10, '0'))

        # 匹配的资源中排序分组
        media_list = sorted(media_list, key=lambda x: get_sort_str(x), reverse=True)
        # 控重
        can_download_list_item = []
        can_download_list = []
        # 按分组显示
        for t_item in media_list:
            if t_item.type == MediaType.TV:
                media_name = "%s%s%s%s%s" % (t_item.get_title_string(),
                                             t_item.site,
                                             t_item.get_resource_type_string(),
                                             t_item.get_season_episode_string(),
                                             str_filesize(t_item.size))
            else:
                media_name = "%s%s%s%s" % (
                    t_item.get_title_string(), t_item.site, t_item.get_resource_type_string(),
                    str_filesize(t_item.size))
            if media_name not in can_download_list:
                can_download_list.append(media_name)
                can_download_list_item.append(t_item)
        return can_download_list_item

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
            # 排序：标题、季集、资源类型、站点、做种
            return "%s%s%s%s%s" % (str(x.title).ljust(100, ' '),
                                   "%s%s" % (season_len, episode_len),
                                   str(x.res_order).rjust(3, '0'),
                                   str(x.site_order).rjust(3, '0'),
                                   str(x.seeders).rjust(10, '0'))

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
