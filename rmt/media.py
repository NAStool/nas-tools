import os
import re
import requests
from requests import RequestException
import log
from tmdbv3api import TMDb, Search
from config import get_config, RMT_MEDIAEXT, RMT_COUNTRY_EA, RMT_COUNTRY_AS, FANART_API_URL
from utils.functions import is_chinese
from message.send import Message
from utils.types import MediaType


class Media:
    # TheMovieDB
    tmdb = None
    search = None

    def __init__(self):
        config = get_config()
        if config.get('app'):
            self.tmdb = TMDb()
            self.tmdb.api_key = config['app'].get('rmt_tmdbkey')
            self.tmdb.language = 'zh'
            self.tmdb.debug = True
        self.message = Message()
        self.search = Search()

    @staticmethod
    def is_media_files_tv(file_list):
        flag = False
        # 不是list的转为list，避免发生字符级的拆分
        if not isinstance(file_list, list):
            file_list = [file_list]
        for tmp_file in file_list:
            tmp_name = os.path.basename(tmp_file)
            re_res = re.search(r"[\s.]*[SE]P?\d{1,3}", tmp_name, re.IGNORECASE)
            if re_res:
                flag = True
                break
        return flag

    # 获得媒体名称，用于API检索
    @staticmethod
    def get_pt_media_name(in_name):
        if not in_name:
            return ""
        # 如果有后缀则去掉，避免干扰
        tmp_ext = os.path.splitext(in_name)[-1]
        if tmp_ext in RMT_MEDIAEXT:
            out_name = os.path.splitext(in_name)[0]
        else:
            out_name = in_name
        # 干掉一些固定的前缀 JADE AOD XXTV-X
        out_name = re.sub(r'^JADE[\s.]+|^AOD[\s.]+|^[A-Z]{2,4}TV[\-0-9UVHD]*[\s.]+', '', out_name,
                          flags=re.IGNORECASE).strip()
        # 查找关键字并切分
        num_pos1 = num_pos2 = len(out_name)
        # 查找年份/分辨率的位置
        re_res1 = re.search(r"[\s.]+\d{3,4}[PI]?[\s.]+|[\s.]+\d+K[\s.]+", out_name, re.IGNORECASE)
        if not re_res1:
            # 查询BluRay/REMUX/HDTV/WEB-DL/WEBRip/DVDRip/UHD的位置
            if not re_res1:
                re_res1 = re.search(
                    r"[\s.]+BLU-?RAY[\s.]+|[\s.]+REMUX[\s.]+|[\s.]+HDTV[\s.]+|[\s.]+WEB-DL[\s.]+|[\s.]+WEBRIP[\s.]+|[\s.]+DVDRIP[\s.]+|[\s.]+UHD[\s.]+",
                    out_name, re.IGNORECASE)
        if re_res1:
            num_pos1 = re_res1.span()[0]
        # 查找Sxx或Exx的位置
        re_res2 = re.search(r"[\s.]+[SE]P?\d{1,3}", out_name, re.IGNORECASE)
        if re_res2:
            num_pos2 = re_res2.span()[0]
        # 取三者最小
        num_pos = min(num_pos1, num_pos2, len(out_name))
        # 截取Year或Sxx或Exx前面的字符
        out_name = out_name[0:num_pos]
        # 如果带有Sxx-Sxx、Exx-Exx这类的要处理掉
        out_name = re.sub(r'[SsEePp]+\d{1,3}-?[SsEePp]*\d{0,3}', '', out_name).strip()
        if is_chinese(out_name):
            # 有中文的，把中文外的英文、字符、数字等全部去掉
            out_name = re.sub(r'[0-9a-zA-Z【】\-_.\[\]()\s]+', '', out_name).strip()
        else:
            # 不包括中文，则是英文名称
            out_name = out_name.replace(".", " ")
        return out_name

    # 获得媒体文件的集数S00
    @staticmethod
    def get_media_file_season(in_name):
        if in_name:
            # 查找Sxx
            re_res = re.search(r"[\s.]*(S\d{1,2})", in_name, re.IGNORECASE)
            if re_res:
                return re_res.group(1).upper()
        return "S01"

    # 获得媒体文件的集数E00
    @staticmethod
    def get_media_file_seq(in_name):
        ret_str = ""
        if in_name:
            # 查找Sxx
            re_res = re.search(r"[\s.]*S?\d{0,2}(EP?\d{1,3})[\s.]*", in_name, re.IGNORECASE)
            if re_res:
                ret_str = re_res.group(1).upper()
            else:
                # 可能数字就是全名，或者是第xx集
                ret_str = ""
                num_pos = in_name.find(".")
                if num_pos != -1:
                    split_char = "."
                else:
                    split_char = " "
                split_ary = in_name.split(split_char)
                for split_str in split_ary:
                    split_str = split_str.replace("第", "").replace("集", "").strip()
                    if split_str.isdigit() and (0 < int(split_str) < 1000):
                        ret_str = "E" + split_str
                        break
            if not ret_str:
                ret_str = ""
        return ret_str

    # 获得媒体文件的分辨率
    @staticmethod
    def __get_media_file_pix(in_name):
        if in_name:
            # 查找Sxx
            re_res = re.search(r"[\s.]+[SBUHD]*(\d{3,4}[PI]+)[\s.]+", in_name, re.IGNORECASE)
            if re_res:
                return re_res.group(1).upper()
            else:
                re_res = re.search(r"[\s.]+(\d+K)[\s.]+", in_name, re.IGNORECASE)
                if re_res:
                    return re_res.group(1).upper()
        return ""

    # 获得媒体文件的Year
    @staticmethod
    def get_media_file_year(in_name):
        if in_name:
            # 查找Sxx
            re_res = re.search(r"[\s.(]+(\d{4})[\s.)]+", in_name, re.IGNORECASE)
            if re_res:
                return re_res.group(1).upper()
        return ""

    # 检索tmdb中的媒体信息，传入名字、年份、类型
    # 返回媒体信息对象
    def __search_tmdb(self, file_media_name, media_year, search_type, language=None):
        if not file_media_name:
            log.error("【RMT】检索关键字有误！")
            return None
        if language:
            self.tmdb.language = language
        else:
            self.tmdb.language = 'zh'
        # TMDB检索
        if search_type == MediaType.MOVIE:
            # 先按年份查，不行再不用年份查
            log.info("【RMT】正在检索电影：%s, 年份=%s ..." % (file_media_name, media_year))
            if media_year:
                movies = self.search.movies({"query": file_media_name, "year": media_year})
                if len(movies) == 0:
                    movies = self.search.movies({"query": file_media_name})
            else:
                movies = self.search.movies({"query": file_media_name})

            log.debug("【RMT】API返回：%s" % str(self.search.total_results))
            if len(movies) == 0:
                log.warn("【RMT】%s 未找到媒体信息!" % file_media_name)
                return None
            else:
                info = movies[0]
                for movie in movies:
                    if movie.title == file_media_name or movie.release_date[0:4] == media_year:
                        # 优先使用名称或者年份完全匹配的，匹配不到则取第一个
                        info = movie
                        break
                media_id = info.id
                media_title = info.title
                log.info(">电影ID：%s, 上映日期：%s, 电影名称：%s" % (str(info.id), info.release_date, info.title))
                if info.get('release_date'):
                    media_year = info.release_date[0:4]
                backdrop_path = info.backdrop_path
                vote_average = str(info.vote_average)
                # 国家
                media_language = info.original_language
                if 'zh' in media_language or \
                        'bo' in media_language or \
                        'za' in media_language or \
                        'cn' in media_language:
                    media_type = "华语电影"
                else:
                    media_type = "外语电影"
        else:
            # 先按年份查，不行再不用年份查
            log.info("【RMT】正在检索剧集：%s, 年份=%s ..." % (file_media_name, media_year))
            if media_year:
                tvs = self.search.tv_shows({"query": file_media_name, "first_air_date_year": media_year})
                if len(tvs) == 0:
                    tvs = self.search.tv_shows({"query": file_media_name})
            else:
                tvs = self.search.tv_shows({"query": file_media_name})

            log.debug("【RMT】API返回：%s" % str(self.search.total_results))
            if len(tvs) == 0:
                log.warn("【RMT】%s 未找到媒体信息!" % file_media_name)
                return None
            else:
                info = tvs[0]
                for tv in tvs:
                    if tv.get('first_air_date'):
                        if tv.name == file_media_name and tv.first_air_date[0:4] == media_year:
                            # 优先使用名称或者年份完全匹配的，匹配不到则取第一个
                            info = tv
                            break
                    elif tv.name == file_media_name:
                        info = tv
                        break

                media_id = info.id
                media_title = info.name
                log.info(">剧集ID：%s, 剧集名称：%s, 上映日期：%s" % (str(info.id), info.name, info.get('first_air_date')))
                if info.get('first_air_date'):
                    media_year = info.first_air_date[0:4]
                backdrop_path = info.backdrop_path
                vote_average = str(info.vote_average)

                # 类型 动漫、纪录片、儿童、综艺
                media_genre_ids = info.genre_ids
                if 16 in media_genre_ids:
                    # 动漫
                    media_type = "动漫"
                elif 99 in media_genre_ids:
                    # 纪录片
                    media_type = "纪录片"
                elif 10762 in media_genre_ids:
                    # 儿童
                    media_type = "儿童"
                elif 10764 in media_genre_ids or 10767 in media_genre_ids:
                    # 综艺
                    media_type = "综艺"
                else:
                    # 国家
                    media_country = info.origin_country
                    if 'CN' in media_country or 'TW' in media_country:
                        media_type = "国产剧"
                    elif set(RMT_COUNTRY_EA).intersection(set(media_country)):
                        media_type = "欧美剧"
                    elif set(RMT_COUNTRY_AS).intersection(set(media_country)):
                        media_type = "日韩剧"
                    else:
                        media_type = "其它剧"
        return {"name": file_media_name,
                "search_type": search_type,
                "type": media_type,
                "id": str(media_id),
                "title": media_title,
                "year": str(media_year),
                "info": info,
                "backdrop_path": backdrop_path,
                "vote_average": vote_average}

    # 只有名称信息，判别是电影还是电视剧并TMDB信息
    def get_media_info_on_name(self, in_name, media_name=None, media_year=None, in_type=None):
        if not media_name:
            media_name = self.get_pt_media_name(in_name)
        if not media_year:
            media_year = self.get_media_file_year(in_name)
        if not in_type:
            if self.is_media_files_tv(in_name):
                # 肯定是电视剧
                file_media_info = self.__search_tmdb(media_name, media_year, MediaType.TV)
            else:
                # 不能确定是电视剧，先按电影查
                file_media_info = self.__search_tmdb(media_name, media_year, MediaType.MOVIE)
                if not file_media_info:
                    # 查不到再按电视剧查
                    file_media_info = self.__search_tmdb(media_name, media_year, MediaType.TV)
        else:
            file_media_info = self.__search_tmdb(media_name, media_year, in_type)

        if file_media_info:
            file_media_info['media_pix'] = self.__get_media_file_pix(in_name)

        return file_media_info

    # 搜刮媒体信息和类型，返回每个文件对应的媒体信息
    '''
    输入：file_list：文件路径清单, 可能是一个目录，也可能是一个文件清单
    输出：类型，文件路径：媒体信息的List
    '''

    def get_media_info_on_files(self, file_list):
        # 存储文件路径与媒体的对应关系
        return_media_infos = {}

        # 不是list的转为list
        if not isinstance(file_list, list):
            file_list = [file_list]

        # 存储所有识别的名称与媒体信息的对应关系
        media_names = {}

        # 遍历每个文件，看得出来的名称是不是不一样，不一样的先搜索媒体信息
        for file_path in file_list:
            if not os.path.exists(file_path):
                log.error("【RMT】%s 不存在！" % file_path)
                continue
            # 解析媒体名称
            if os.path.isfile(file_path):
                # 如要是文件，则先用上级文件夹的名称
                parent_dir = os.path.dirname(file_path)
                file_name = os.path.basename(parent_dir)
                file_media_name = self.get_pt_media_name(file_name)
                # 如果上一级文件夹不对，则拿文件名称
                if not file_media_name or file_media_name == file_name:
                    file_name = os.path.basename(file_path)
                    file_media_name = self.get_pt_media_name(file_name)
                    # 如果文件名不行，则拿上上级文件夹的名称
                    if not file_media_name or file_media_name == file_name:
                        p2_dir_name = os.path.dirname(parent_dir)
                        file_name = os.path.basename(p2_dir_name)
                        file_media_name = self.get_pt_media_name(file_name)

            else:
                # 如果是文件夹，先用自己的名称，不行再用上级的
                file_name = os.path.basename(file_path)
                file_media_name = self.get_pt_media_name(file_name)
                if not file_media_name or file_media_name == file_name:
                    parent_dir = os.path.dirname(file_path)
                    file_name = os.path.basename(parent_dir)
                    file_media_name = self.get_pt_media_name(file_name)

            if not file_media_name:
                continue

            # 确定是电影还是电视剧
            search_type = MediaType.MOVIE
            if self.is_media_files_tv(file_path):
                search_type = MediaType.TV

            # 是否处理过
            if not media_names.get(file_media_name):

                media_year = self.get_media_file_year(file_name)
                if not media_year:
                    # 没有文件的则使用目录里的
                    media_year = self.get_media_file_year(file_path)

                # 解析分辨率
                media_pix = self.__get_media_file_pix(file_name)
                if not media_pix:
                    media_pix = self.get_media_file_year(file_path)

                # 调用TMDB API
                file_media_info = self.__search_tmdb(file_media_name, media_year, search_type)
                if file_media_info:
                    file_media_info['media_pix'] = media_pix
                    # 记录为已检索
                    media_names[file_media_name] = file_media_info
            if not media_names.get(file_media_name):
                media_names[file_media_name] = {'search_type': search_type}
            # 存入结果清单返回
            return_media_infos[file_path] = media_names.get(file_media_name)

        return return_media_infos

    # 检查标题中是否匹配资源类型
    # 返回：是否匹配，匹配的序号，匹配的值
    @staticmethod
    def check_resouce_types(t_title, t_types):
        if t_types is None:
            return False, 0, ""
        c_seq = 100
        for t_type in t_types:
            c_seq = c_seq - 1
            t_type = str(t_type)
            if t_type.upper() == "BLURAY":
                match_str = r'blu-?ray'
                no_match_str = None
            elif t_type.upper() == "4K":
                match_str = r'4k|2160p'
                no_match_str = r'blu-?ray'
            else:
                match_str = t_type
                no_match_str = None
            re_res = re.search(match_str, t_title, re.IGNORECASE)
            if re_res:
                # 命中
                if no_match_str:
                    re_res = re.search(no_match_str, t_title, re.IGNORECASE)
                    if re_res:
                        # 不该命中的命中
                        return False, 0, ""
                return True, c_seq, t_type

        return False, 0, ""

    # 获取消息媒体图片
    @staticmethod
    def get_backdrop_image(backdrop_path, tmdbid):
        if tmdbid:
            try:
                ret = requests.get(FANART_API_URL % tmdbid)
                if ret:
                    moviethumbs = ret.json().get('moviethumb')
                    if moviethumbs:
                        moviethumb = moviethumbs[0].get('url')
                        if moviethumb:
                            # 有则返回FanArt的图片
                            return moviethumb
            except RequestException as e:
                log.debug("【RMT】拉取FanArt图片出错：%s" % str(e))
            except Exception as e:
                log.debug("【RMT】拉取FanArt图片出错：%s" % str(e))
        if not backdrop_path:
            return ""
        return "https://image.tmdb.org/t/p/w500%s" % backdrop_path

    # 从种子名称中获取季和集的数字
    @staticmethod
    def get_sestring_from_name(name):
        # 不知道怎么写，最傻的办法，穷举！
        re_res = re.search(r'([SsEePp]+\d{1,3}-?[SsEePp]*\d{0,3})', name, re.IGNORECASE)
        if re_res:
            return re_res.group(1).upper()
        else:
            return None
