import re
import cn2an
from config import RMT_MEDIAEXT
from rmt.meta.metabase import MetaBase
from utils.functions import is_chinese
from utils.tokens import Tokens
from utils.types import MediaType


class MetaVideo(MetaBase):
    """
    识别电影、电视剧
    """
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
    _resources_type_re = r"^BLURAY$|^REMUX$|^HDTV$|^UHDTV$|^HDDVD$|^WEBRIP$|^DVDRIP$|^BDRIP$|^UHD$|^SDR$|^HDR$|^DOLBY$|^BLU$|^WEB$|^BD$"
    _name_no_begin_re = r"^\[.+?]"
    _name_se_words = ['共', '第', '季', '集', '话', '話']
    _name_nostring_re = r"^JADE|^AOD|^[A-Z]{1,4}TV[\-0-9UVHDK]*|HBO|\d{1,2}th|NETFLIX|IMAX|^CHC|^3D|\s+3D|^BBC|DISNEY\+|XXX" \
                        r"|[第\s共]+[0-9一二三四五六七八九十\-\s]+季" \
                        r"|[第\s共]+[0-9一二三四五六七八九十\-\s]+[集话話]" \
                        r"|S\d{2}\s*-\s*S\d{2}|S\d{2}|\s+S\d{1,2}|EP?\d{2,4}\s*-\s*EP?\d{2,4}|EP?\d{2,4}|\s+EP?\d{1,4}" \
                        r"|连载|日剧|美剧|电视剧|电影|动画片|动漫|欧美|西德|日韩|超高清|高清|蓝光|翡翠台" \
                        r"|最终季|合集|[中国英葡法俄日韩德意西印泰台港粤双文语简繁体特效内封官译外挂]+字幕" \
                        r"|未删减版|UNCUT|UNRATE|WITH EXTRAS|RERIP|SUBBED|PROPER|REPACK|SEASON[\s.]+|EPISODE[\s.]+" \
                        r"|PART[\s.]*[1-9]|CD[\s.]*[1-9]|DVD[\s.]*[1-9]|DISK[\s.]*[1-9]|DISC[\s.]*[1-9]" \
                        r"|[248]K|\d{3,4}[PIX]+"
    _resources_pix_re = r"^[SBUHD]*(\d{3,4}[PIX]+)"
    _resources_pix_re2 = r"(^[248]+K)"
    _subtitle_season_re = r"[第\s]+([0-9一二三四五六七八九十\-]+)\s*季"
    _subtitle_season_all_re = r"全\s*([0-9一二三四五六七八九十]+)\s*季|([0-9一二三四五六七八九十]+)\s*季全"
    _subtitle_episode_re = r"[第\s]+([0-9一二三四五六七八九十\-]+)\s*[集话話]"
    _subtitle_episode_all_re = r"([0-9一二三四五六七八九十]+)\s*集全|全\s*([0-9一二三四五六七八九十]+)\s*集"

    def __init__(self, title, subtitle=None):
        super().__init__(title, subtitle)
        if not title:
            return
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
