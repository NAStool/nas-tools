import re
import anitopy
import cn2an
import requests
from requests import RequestException

import log
from config import FANART_TV_API_URL, FANART_MOVIE_API_URL, RMT_MEDIAEXT, ANIME_GENREIDS, Config
from rmt.category import Category
from utils.functions import is_chinese
from utils.tokens import Tokens
from utils.types import MediaType


class MetaInfo(object):
    config = None
    category_handler = None
    # 原字符串
    org_string = None
    # 副标题
    subtitle = None
    # 类型 电影、电视剧
    type = None
    # 识别的中文名
    cn_name = None
    # 识别的英文名
    en_name = None
    # 总季数
    total_seasons = 0
    # 识别的开始季 数字
    begin_season = None
    # 识别的结束季 数字
    end_season = None
    # 总集数
    total_episodes = 0
    # 识别的开始集
    begin_episode = None
    # 识别的结束集
    end_episode = None
    # Partx Cd Dvd Disk Disc
    part = None
    # 识别的资源类型
    resource_type = None
    # 识别的分辨率
    resource_pix = None
    # 二级分类
    category = None
    # TMDB ID
    tmdb_id = 0
    # 媒体标题
    title = None
    # 媒体年份
    year = None
    # 封面图片
    backdrop_path = None
    poster_path = None
    fanart_image = None
    # 评分
    vote_average = 0
    # 描述
    overview = None
    # TMDB 的其它信息
    tmdb_info = {}
    # 种子附加信息
    site = None
    site_order = 0
    enclosure = None
    res_order = 0
    size = 0
    seeders = 0
    peers = 0
    description = None
    # 控制标位区
    _stop_name_flag = False
    _last_token = ""
    _last_token_type = ""
    _continue_flag = True
    _unknown_name_str = ""
    _subtitle_flag = False
    # 正则式区
    _season_re = r"S(\d{2})|^S(\d{1,2})"
    _episode_re = r"EP?(\d{2,4})|^EP?(\d{1,4})"
    _part_re = r"(^PART[1-9]?$|^CD[1-9]?$|^DVD[1-9]?$|^DISK[1-9]?$|^DISC[1-9]?$)"
    _resources_type_re = r"^BLURAY|^REMUX|^HDTV|^HDDVD|^WEBRIP|^DVDRIP|^BDRIP|^UHD|^SDR|^HDR|^DOLBY|^BLU|^WEB|^BD"
    _name_no_begin_re = r"^\[.+?]"
    _name_se_words = ['共', '第', '季', '集', '话', '話']
    _name_nostring_re = r"^JADE|^AOD|^[A-Z]{1,4}TV[\-0-9UVHDK]*|HBO|\d{1,2}th|NETFLIX|IMAX|^CHC|^3D|\s+3D|^BBC|DISNEY\+" \
                        r"|[第\s共]+[0-9一二三四五六七八九十\-\s]+季" \
                        r"|[第\s共]+[0-9一二三四五六七八九十\-\s]+[集话話]" \
                        r"|S\d{2}\s*-\s*S\d{2}|S\d{2}|\s+S\d{1,2}|EP?\d{2,4}\s*-\s*EP?\d{2,4}|EP?\d{2,4}|\s+EP?\d{1,4}" \
                        r"|BLU-?RAY|REMUX|HDTV|HDDVD|WEBRIP|DVDRIP|UHD|WEB|SDR|HDR|DOLBY|TRUEHD|BDRIP|BD" \
                        r"|[HX]264|[HX]265|AVC|AAC|DTS\d.\d|HEVC|\d{3,4}[PI]" \
                        r"|TV|Series|Movie|Animations|XXX" \
                        r"|连载|日剧|美剧|电视剧|电影|动画片|动漫|欧美|西德|日韩|超高清|高清|蓝光|翡翠台" \
                        r"|最终季|合集|[中国英葡法俄日韩德意西印泰台港粤双文语简繁体特效内封官译外挂]+字幕" \
                        r"|未删减版|UNCUT|UNRATE|WITH EXTRAS|RERIP|SUBBED|PROPER|REPACK|SEASON|EPISODE" \
                        r"|PART[\s.]*[1-9]|CD[\s.]*[1-9]|DVD[\s.]*[1-9]|DISK[\s.]*[1-9]|DISC[\s.]*[1-9]" \
                        r"|[248]K|\d{3,4}[PIX]+"
    _resources_pix_re = r"^[SBUHD]*(\d{3,4}[PIX]+)"
    _resources_pix_re2 = r"(^[248]+K)"
    _subtitle_season_re = r"[第\s]+([0-9一二三四五六七八九十\-]+)\s*季"
    _subtitle_season_all_re = r"全\s*([0-9一二三四五六七八九十]+)\s*季|([0-9一二三四五六七八九十]+)\s*季全"
    _subtitle_episode_re = r"[第\s]+([0-9一二三四五六七八九十\-]+)\s*[集话話]"
    _subtitle_episode_all_re = r"([0-9一二三四五六七八九十]+)\s*集全|全\s*([0-9一二三四五六七八九十]+)\s*集"
    _anime_no_words = ['CHS&CHT']

    def __init__(self, title, subtitle=None, anime=False):
        if not title:
            return
        self.config = Config()
        self.category_handler = Category()
        self.org_string = title
        self.subtitle = subtitle
        if not anime:
            # 去掉名称中第1个[]的内容
            title = re.sub(r'%s' % self._name_no_begin_re, "", title, count=1)
            # 把xxxx-xxxx年份换成前一个年份，常出现在季集上
            title = re.sub(r'[\s.]+(\d{4})-(\d{4})', r'\1', title)
            # 拆分tokens
            tokens = Tokens(title)
            # 解析名称、年份、季、集、资源类型、分辨率等
            token = tokens.get_next()
            while token:
                # 标题
                self.__init_name(token)
                # Part
                if self._continue_flag:
                    self.__init_part(token)
                # 年份
                if self._continue_flag:
                    self.__init_year(token)
                # 分辨率
                if self._continue_flag:
                    self.__init_resource_pix(token)
                # 季
                if self._continue_flag:
                    self.__init_seasion(token)
                # 集
                if self._continue_flag:
                    self.__init_episode(token)
                # 资源类型
                if self._continue_flag:
                    self.__init_resource_type(token)
                # 取下一个，直到没有为卡
                token = tokens.get_next()
                self._continue_flag = True
            # 解析副标题，只要季和集
            self.__init_subtitle(title)
            if not self._subtitle_flag and subtitle:
                self.__init_subtitle(subtitle)
            # 没有识别出类型时默认为电影
            if not self.type:
                self.type = MediaType.MOVIE
            # 去掉名字中不需要的干扰字符，过短的纯数字不要
            if self.cn_name:
                self.cn_name = re.sub(r'%s' % self._name_nostring_re, '', self.cn_name,
                                      flags=re.IGNORECASE).strip()
                self.cn_name = re.sub(r'\s+', ' ', self.cn_name)
                if self.cn_name.isdigit() and int(self.cn_name) < 1800:
                    if self.begin_episode is None:
                        self.begin_episode = int(self.cn_name)
                        self.cn_name = None
                    elif self.is_in_episode(int(self.cn_name)):
                        self.cn_name = None
            if self.en_name:
                self.en_name = re.sub(r'%s' % self._name_nostring_re, '', self.en_name,
                                      flags=re.IGNORECASE).strip()
                self.en_name = re.sub(r'\s+', ' ', self.en_name)
                if self.en_name.isdigit() and int(self.en_name) < 1800:
                    if self.begin_episode is None:
                        self.begin_episode = int(self.en_name)
                        self.en_name = None
                    elif self.is_in_episode(int(self.en_name)):
                        self.en_name = None
        else:
            # 调用第三方模块识别动漫
            try:
                self.type = MediaType.UNKNOWN
                anitopy_info = anitopy.parse(title)
                if anitopy_info:
                    # 名称
                    name = anitopy_info.get("anime_title")
                    if not name or name in self._anime_no_words or (len(name) < 5 and not is_chinese(name)):
                        anitopy_info = anitopy.parse("[ANIME]" + title)
                        if anitopy_info:
                            name = anitopy_info.get("anime_title")
                    if not name or name in self._anime_no_words or (len(name) < 5 and not is_chinese(name)):
                        return
                    # 名称
                    if is_chinese(name):
                        self.cn_name = name
                    else:
                        self.en_name = name
                    # 年份
                    year = anitopy_info.get("anime_year")
                    if str(year).isdigit():
                        self.year = str(year)
                    # 季号
                    anime_season = anitopy_info.get("anime_season")
                    if isinstance(anime_season, list):
                        if len(anime_season) == 1:
                            begin_season = anime_season[0]
                            end_season = 0
                        else:
                            begin_season = anime_season[0]
                            end_season = anime_season[-1]
                    else:
                        begin_season = anime_season
                        end_season = 0
                    if isinstance(begin_season, str) and begin_season.isdigit():
                        self.begin_season = int(begin_season)
                        self.type = MediaType.ANIME
                    if isinstance(end_season, str) and end_season.isdigit():
                        if self.begin_season is not None and end_season != self.begin_season:
                            self.end_season = int(end_season)
                            self.type = MediaType.ANIME
                    # 集号
                    episode_number = anitopy_info.get("episode_number")
                    if isinstance(episode_number, list):
                        if len(episode_number) == 1:
                            begin_episode = episode_number[0]
                            end_episode = 0
                        else:
                            begin_episode = episode_number[0]
                            end_episode = episode_number[-1]
                    else:
                        begin_episode = episode_number
                        end_episode = 0
                    if isinstance(begin_episode, str) and begin_episode.isdigit():
                        self.begin_episode = int(begin_episode)
                        self.type = MediaType.ANIME
                    if isinstance(end_episode, str) and end_episode.isdigit():
                        if self.end_episode is not None and end_episode != self.end_episode:
                            self.end_season = int(end_episode)
                            self.type = MediaType.ANIME
                    # 类型
                    if not self.type:
                        anime_type = anitopy_info.get('anime_type')
                        if isinstance(anime_type, list):
                            anime_type = anime_type[0]
                        if isinstance(anime_type, str):
                            if anime_type.upper() == "TV":
                                self.type = MediaType.ANIME
                            else:
                                self.type = MediaType.MOVIE
                    # 分辨率
                    self.resource_pix = anitopy_info.get("video_resolution")
            except Exception as e:
                log.console(str(e))

    def __init_name(self, token):
        if not token:
            return
        # 回收标题
        if self._unknown_name_str and not self.get_name():
            self.en_name = self._unknown_name_str
            self._unknown_name_str = ""
        if self._stop_name_flag:
            if self._unknown_name_str and self._unknown_name_str != self.year:
                if self.en_name:
                    self.en_name = "%s %s" % (self.en_name, self._unknown_name_str)
                else:
                    self.cn_name = "%s %s" % (self.cn_name, self._unknown_name_str)
                self._unknown_name_str = ""
            return
        if token in self._name_se_words:
            self._last_token_type = 'name_se_words'
            return
        if is_chinese(token):
            # 含有中文，直接做为标题（连着的数字或者英文会保留），且不再取用后面出现的中文
            if not self.cn_name and token:
                self.cn_name = token
                self._last_token_type = "cnname"
        else:
            # 数字
            if token.isdigit():
                # 第季集后面的不要
                if self._last_token_type == 'name_se_words':
                    return
                if self.get_name():
                    # 名字后面以 0 开头的不要，极有可能是集
                    if token.startswith('0'):
                        return
                    # 名称后面跟着的数字，停止查找名称
                    self._stop_name_flag = True
                    if len(token) < 4:
                        # 4位以下的数字，拼装到已有标题中
                        if self._last_token_type == "cnname":
                            self.cn_name = "%s %s" % (self.cn_name, token)
                        elif self._last_token_type == "enname":
                            self.en_name = "%s %s" % (self.en_name, token)
                    elif len(token) == 4:
                        # 4位数字，可能是年份，也可能真的是标题的一部分，也有可能是集
                        if token.startswith('0') or not 1900 < int(token) < 2050:
                            return
                        if not self._unknown_name_str:
                            self._unknown_name_str = token
                else:
                    # 名字未出现前的第一个数字，记下来
                    if not self._unknown_name_str:
                        self._unknown_name_str = token
            else:
                # 后缀名不要
                if ".%s".lower() % token in RMT_MEDIAEXT:
                    return
                # 英文或者英文+数字，拼装起来
                if self.en_name:
                    self.en_name = "%s %s" % (self.en_name, token)
                else:
                    self.en_name = token
                self._last_token_type = "enname"

    def __init_part(self, token):
        if not self.get_name():
            return
        re_res = re.search(r"%s" % self._part_re, token, re.IGNORECASE)
        if re_res:
            self._last_token_type = "part"
            self._continue_flag = False
            self._stop_name_flag = True
            if not self.part:
                self.part = re_res.group(1)
        else:
            # 单个数字加入part
            if self._last_token_type == "part" and token.isdigit() and len(token) == 1:
                self._last_token_type = "part"
                self.part = "%s%s" % (self.part, token)
                self._continue_flag = False
                self._stop_name_flag = True

    def __init_year(self, token):
        if not self.get_name():
            return
        if not token.isdigit():
            return
        if len(token) != 4:
            return
        if not 1900 < int(token) < 2050:
            return
        self.year = token
        self._last_token_type = "year"
        self._continue_flag = False
        self._stop_name_flag = True

    def __init_resource_pix(self, token):
        if not self.get_name():
            return
        re_res = re.search(r"%s" % self._resources_pix_re, token, re.IGNORECASE)
        if re_res:
            self._last_token_type = "pix"
            self._continue_flag = False
            self._stop_name_flag = True
            if not self.resource_pix:
                self.resource_pix = re_res.group(1).lower()
            elif self.resource_pix == "3D":
                self.resource_pix = "%s 3D" % re_res.group(1).lower()
        else:
            re_res = re.search(r"%s" % self._resources_pix_re2, token, re.IGNORECASE)
            if re_res:
                self._last_token_type = "pix"
                self._continue_flag = False
                self._stop_name_flag = True
                if not self.resource_pix:
                    self.resource_pix = re_res.group(1).lower()
                elif self.resource_pix == "3D":
                    self.resource_pix = "%s 3D" % re_res.group(1).lower()
            elif token.upper() == "3D":
                self._last_token_type = "pix"
                self._continue_flag = False
                self._stop_name_flag = True
                if not self.resource_pix:
                    self.resource_pix = "3D"
                else:
                    self.resource_pix = "%s 3D" % self.resource_pix

    def __init_seasion(self, token):
        if not self.get_name():
            return
        re_res = re.findall(r"%s" % self._season_re, token, re.IGNORECASE)
        if re_res:
            self._last_token_type = "season"
            self.type = MediaType.TV
            self._stop_name_flag = True
            self._continue_flag = True
            for se in re_res:
                if isinstance(se, tuple):
                    if se[0]:
                        se = se[0]
                    else:
                        se = se[1]
                if not se:
                    continue
                if not se.isdigit():
                    continue
                else:
                    se = int(se)
                if self.begin_season is None:
                    self.begin_season = se
                    self.total_seasons = 1
                else:
                    if self.begin_season != se:
                        self.end_season = se
                        self.total_seasons = (self.end_season - self.begin_season) + 1
        elif token.isdigit():
            if self.begin_season is not None \
                    and self.end_season is None \
                    and len(token) < 3 \
                    and int(token) > self.begin_season \
                    and self._last_token_type == "season":
                self.end_season = int(token)
                self.total_seasons = (self.end_season - self.begin_season) + 1
                self._last_token_type = "season"
                self._continue_flag = False
            elif self._last_token_type == "SEASON" \
                    and self.begin_season is None \
                    and len(token) < 3:
                self.begin_season = int(token)
                self.total_seasons = 1
                self._last_token_type = "season"
                self._stop_name_flag = True
                self._continue_flag = False
                self.type = MediaType.TV
        elif token.upper() == "SEASON" and self.begin_season is None:
            self._last_token_type = "SEASON"

    def __init_episode(self, token):
        if not self.get_name():
            return
        re_res = re.findall(r"%s" % self._episode_re, token, re.IGNORECASE)
        if re_res:
            self._last_token_type = "episode"
            self._continue_flag = False
            self._stop_name_flag = True
            self.type = MediaType.TV
            for se in re_res:
                if isinstance(se, tuple):
                    if se[0]:
                        se = se[0]
                    else:
                        se = se[1]
                if not se:
                    continue
                if not se.isdigit():
                    continue
                else:
                    se = int(se)
                if self.begin_episode is None:
                    self.begin_episode = se
                    self.total_episodes = 1
                else:
                    if self.begin_episode != se:
                        self.end_episode = se
                        self.total_episodes = (self.end_episode - self.begin_episode) + 1
        elif token.isdigit():
            if self.begin_episode is not None \
                    and self.end_episode is None \
                    and len(token) < 5 \
                    and int(token) > self.begin_episode \
                    and self._last_token_type == "episode":
                self.end_episode = int(token)
                self.total_episodes = (self.end_episode - self.begin_episode) + 1
                self._last_token_type = "episode"
                self._continue_flag = False
            elif self.begin_episode is None \
                    and 1 < len(token) < 5 \
                    and token.startswith('0'):
                self.begin_episode = int(token)
                self.total_episodes = 1
                self._last_token_type = "episode"
                self._continue_flag = False
                self._stop_name_flag = True
                self.type = MediaType.TV
            elif self._last_token_type == "EPISODE" \
                    and self.begin_episode is None \
                    and len(token) < 5:
                self.begin_episode = int(token)
                self.total_episodes = 1
                self._last_token_type = "episode"
                self._continue_flag = False
                self._stop_name_flag = True
                self.type = MediaType.TV
        elif token.upper() == "EPISODE":
            self._last_token_type = "EPISODE"

    def __init_resource_type(self, token):
        if not self.get_name():
            return
        re_res = re.search(r"(%s)" % self._resources_type_re, token, re.IGNORECASE)
        if re_res:
            self._last_token_type = "restype"
            self._continue_flag = False
            self._stop_name_flag = True
            if not self.resource_type:
                self.resource_type = re_res.group(1)
                self._last_token = self.resource_type.upper()

        else:
            if token.upper() == "DL" \
                    and self._last_token_type == "restype" \
                    and self._last_token == "WEB":
                self.resource_type = "WEB-DL"
                self._last_token_type = "restype"
                self._continue_flag = False
            if token.upper() == "RAY" \
                    and self._last_token_type == "restype" \
                    and self._last_token == "BLU":
                self.resource_type = "BluRay"
                self._last_token_type = "restype"
                self._continue_flag = False

    def __init_subtitle(self, title_text):
        if not title_text:
            return
        if re.search(r'[全第季集话話]', title_text, re.IGNORECASE):
            # 第x季
            season_str = re.search(r'%s' % self._subtitle_season_re, title_text, re.IGNORECASE)
            if season_str:
                seasons = season_str.group(1)
                if seasons:
                    seasons = seasons.strip()
                else:
                    return
                end_season = None
                if seasons.find('-') != -1:
                    seasons = seasons.split('-')
                    begin_season = int(cn2an.cn2an(seasons[0].strip(), mode='smart'))
                    if len(seasons) > 1:
                        end_season = int(cn2an.cn2an(seasons[1].strip(), mode='smart'))
                else:
                    begin_season = int(cn2an.cn2an(seasons, mode='smart'))
                if self.begin_season is None and isinstance(begin_season, int):
                    self.begin_season = begin_season
                    self.total_seasons = 1
                if self.begin_season is not None and self.end_season is None and isinstance(end_season, int):
                    self.end_season = end_season
                    self.total_seasons = (self.end_season - self.begin_season) + 1
                self.type = MediaType.TV
                self._subtitle_flag = True
            # 第x集
            episode_str = re.search(r'%s' % self._subtitle_episode_re, title_text, re.IGNORECASE)
            if episode_str:
                episodes = episode_str.group(1)
                if episodes:
                    episodes = episodes.strip()
                else:
                    return
                end_episode = None
                if episodes.find('-') != -1:
                    episodes = episodes.split('-')
                    begin_episode = int(cn2an.cn2an(episodes[0].strip(), mode='smart'))
                    if len(episodes) > 1:
                        end_episode = int(cn2an.cn2an(episodes[1].strip(), mode='smart'))
                else:
                    begin_episode = int(cn2an.cn2an(episodes, mode='smart'))
                if self.begin_episode is None and isinstance(begin_episode, int):
                    self.begin_episode = begin_episode
                    self.total_episodes = 1
                if self.begin_episode is not None and self.end_episode is None and isinstance(end_episode, int):
                    self.end_episode = end_episode
                    self.total_episodes = (self.end_episode - self.begin_episode) + 1
                self.type = MediaType.TV
                self._subtitle_flag = True
            # x集全
            episode_all_str = re.search(r'%s' % self._subtitle_episode_all_re, title_text, re.IGNORECASE)
            if episode_all_str:
                self.begin_episode = None
                self.end_episode = None
                self.total_episodes = 0
            # 全x季 x季全
            season_all_str = re.search(r"%s" % self._subtitle_season_all_re, title_text, re.IGNORECASE)
            if season_all_str:
                season_all = season_all_str.group(1)
                if not season_all:
                    season_all = season_all_str.group(2)
                if season_all and self.begin_season is None and self.begin_episode is None:
                    self.total_seasons = int(cn2an.cn2an(season_all.strip(), mode='smart'))
                    self.begin_season = 1
                    self.end_season = self.total_seasons
                    self._subtitle_flag = True

    def get_name(self):
        if self.cn_name:
            return self.cn_name
        if self.en_name:
            return self.en_name
        return ""

    def get_title_string(self):
        return "%s (%s)" % (self.title, self.year) if self.year else self.title

    def get_vote_string(self):
        if self.vote_average:
            return "评分：%s" % self.vote_average
        else:
            return ""

    def get_title_vote_string(self):
        if not self.vote_average:
            return self.get_title_string()
        else:
            return "%s %s" % (self.get_title_string(), self.get_vote_string())

    # 返回季字符串
    def get_season_string(self):
        if self.begin_season is not None:
            return "S%s" % str(self.begin_season).rjust(2, "0") \
                if self.end_season is None \
                else "S%s-S%s" % \
                     (str(self.begin_season).rjust(2, "0"),
                      str(self.end_season).rjust(2, "0"))
        else:
            if self.type == MediaType.MOVIE:
                return ""
            else:
                return "S01"

    # 返回begin_season 的Sxx
    def get_season_item(self):
        if self.begin_season is not None:
            return "S%s" % str(self.begin_season).rjust(2, "0")
        else:
            if self.type == MediaType.MOVIE:
                return ""
            else:
                return "S01"

    # 返回季的数组
    def get_season_list(self):
        if self.begin_season is None:
            if self.type == MediaType.MOVIE:
                return []
            else:
                return [1]
        elif self.end_season is not None:
            return [season for season in range(self.begin_season, self.end_season + 1)]
        else:
            return [self.begin_season]

    # 返回集字符串
    def get_episode_string(self):
        if self.begin_episode is not None:
            return "E%s" % str(self.begin_episode).rjust(2, "0") \
                if self.end_episode is None \
                else "E%s-E%s" % \
                     (
                         str(self.begin_episode).rjust(2, "0"),
                         str(self.end_episode).rjust(2, "0"))
        else:
            return ""

    # 返回集的数组
    def get_episode_list(self):
        if self.begin_episode is None:
            return []
        elif self.end_episode is not None:
            return [episode for episode in range(self.begin_episode, self.end_episode + 1)]
        else:
            return [self.begin_episode]

    # 返回集的并列表达方式，用于支持单文件多集
    def get_episode_items(self):
        return "E%s" % "E".join(str(episode).rjust(2, '0') for episode in self.get_episode_list())

    # 返回季集字符串
    def get_season_episode_string(self):
        if self.type == MediaType.MOVIE:
            return ""
        else:
            seaion = self.get_season_string()
            episode = self.get_episode_string()
            if seaion and episode:
                return "%s %s" % (seaion, episode)
            elif seaion:
                return "%s" % seaion
            elif episode:
                return "%s" % episode
        return ""

    # 返回资源类型字符串
    def get_resource_type_string(self):
        if self.resource_type and self.resource_pix:
            return "%s %s" % (self.resource_type, self.resource_pix)
        elif self.resource_type:
            return self.resource_type
        elif self.resource_pix:
            return self.resource_pix
        else:
            return ""

    # 返回背景图片地址
    def get_backdrop_path(self):
        return self.fanart_image if self.fanart_image else self.backdrop_path

    # 返回消息图片地址
    def get_message_image(self):
        return self.fanart_image if self.fanart_image else self.poster_path

    # 是否包含季
    def is_in_seasion(self, season):
        if isinstance(season, list):
            if self.end_season is not None:
                meta_season = list(range(self.begin_season, self.end_season + 1))
            else:
                if self.begin_season is not None:
                    meta_season = [self.begin_season]
                else:
                    meta_season = [1]

            return set(meta_season).issuperset(set(season))
        else:
            if self.end_season is not None:
                return self.begin_season <= int(season) <= self.end_season
            else:
                if self.begin_season is not None:
                    return int(season) == self.begin_season
                else:
                    return int(season) == 1

    # 是否包含集
    def is_in_episode(self, episode):
        if isinstance(episode, list):
            if self.end_episode is not None:
                meta_episode = list(range(self.begin_episode, self.end_episode + 1))
            else:
                meta_episode = [self.begin_episode]
            return set(meta_episode).issuperset(set(episode))
        else:
            if self.end_episode is not None:
                return self.begin_episode <= int(episode) <= self.end_episode
            else:
                return int(episode) == self.begin_episode

    # 整合TMDB识别的信息
    def set_tmdb_info(self, info):
        if not info:
            return
        self.type = self.__get_tmdb_type(info)
        if not self.type:
            return
        self.tmdb_id = info.get('id')
        if not self.tmdb_id:
            return
        self.tmdb_info = info
        self.vote_average = info.get('vote_average')
        self.overview = info.get('overview')
        if self.type == MediaType.MOVIE:
            self.title = info.get('title')
            release_date = info.get('release_date')
            if release_date:
                self.year = release_date[0:4]
            self.category = self.category_handler.get_movie_category(info)
        else:
            self.title = info.get('name')
            first_air_date = info.get('first_air_date')
            if first_air_date:
                self.year = first_air_date[0:4]
            if self.type == MediaType.TV:
                self.category = self.category_handler.get_tv_category(info)
            else:
                self.category = self.category_handler.get_anime_category(info)
        self.poster_path = "https://image.tmdb.org/t/p/w500%s" % info.get('poster_path')
        self.fanart_image = self.get_fanart_image(self.type, tmdbid=info.get('id'))
        self.backdrop_path = "https://image.tmdb.org/t/p/w500%s" % info.get('backdrop_path')

    # 整合种了信息
    def set_torrent_info(self,
                         site=None,
                         site_order=0,
                         enclosure=None,
                         res_order=0,
                         size=0,
                         seeders=0,
                         peers=0,
                         description=None):
        self.site = site
        self.site_order = site_order
        self.enclosure = enclosure
        self.res_order = res_order
        self.size = size
        self.seeders = seeders
        self.peers = peers
        self.description = description

    # 获取消息媒体图片
    def get_fanart_image(self, search_type, tmdbid, default=None):
        if not search_type:
            return ""
        if tmdbid:
            if search_type == MediaType.MOVIE:
                image_url = FANART_MOVIE_API_URL % tmdbid
            else:
                image_url = FANART_TV_API_URL % tmdbid
            try:
                ret = requests.get(image_url, timeout=10, proxies=self.config.get_proxies())
                if ret:
                    moviethumbs = ret.json().get('moviethumb')
                    if moviethumbs:
                        moviethumb = moviethumbs[0].get('url')
                        if moviethumb:
                            # 有则返回FanArt的图片
                            return moviethumb
            except RequestException as e1:
                log.console(str(e1))
            except Exception as e2:
                log.console(str(e2))
        if default:
            # 返回一个默认图片
            return default
        return ""

    # 判断电视剧是否为动漫
    def __get_tmdb_type(self, info):
        if not info:
            return self.type
        if not info.get('media_type'):
            return self.type
        if info.get('media_type') == MediaType.TV:
            genre_ids = info.get("genre_ids")
            if not genre_ids:
                return MediaType.TV
            if isinstance(genre_ids, list):
                genre_ids = [str(val).upper() for val in genre_ids]
            else:
                genre_ids = [str(genre_ids).upper()]
            if set(genre_ids).intersection(set(ANIME_GENREIDS)):
                return MediaType.ANIME
            else:
                return MediaType.TV
        else:
            return info.get('media_type')
