import re

import cn2an
import requests
from requests import RequestException
from config import RMT_COUNTRY_EA, RMT_COUNTRY_AS, FANART_TV_API_URL, FANART_MOVIE_API_URL
from utils.functions import is_chinese
from utils.tokens import Tokens
from utils.types import MediaType, MediaCatagory


class MetaInfo(object):
    # 原字符串
    org_string = None
    # 类型 电影、电视剧
    type = None
    # 识别的中文名
    cn_name = None
    # 识别的英文名
    en_name = None
    # 总季数
    total_seasons = 0
    # 识别的开始季 数字
    begin_season = 0
    # 识别的结束季 数字
    end_season = 0
    # 总集数
    total_episodes = 0
    # 识别的开始集
    begin_episode = None
    # 识别的结束季
    end_episode = None
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
    # 评分
    vote_average = 0
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
    res_type = None
    # 控制标位区
    _stop_name_flag = False

    def __init__(self, title, subtitle=None):
        if not title:
            return
        self.__clear()
        self.org_string = title
        # 拆分tokens
        tokens = Tokens(title)
        # 解析名称、年份、季、集、资源类型、分辨率等
        token = tokens.get_next()
        while token:
            # 标题
            self.__init_name(token)
            # 年份
            self.__init_year(token)
            # 分辨率
            self.__init_resource_pix(token)
            # 季
            self.__init_seasion(token)
            # 集
            self.__init_episode(token)
            # 资源类型
            self.__init_resource_type(token)
            # 取下一个，直到没有为卡
            token = tokens.get_next()
        # 解析副标题，只要季和集
        if subtitle:
            self.__init_subtitle(subtitle)
        if not self.type:
            self.type = MediaType.MOVIE

    def __clear(self):
        self.org_string = None
        self.type = None
        self.cn_name = None
        self.en_name = None
        self.begin_season = 0
        self.end_season = 0
        self.begin_episode = None
        self.end_episode = None
        self.resource_type = None
        self.resource_pix = None
        self.category = None
        self.tmdb_id = 0
        self.title = None
        self.year = None
        self.backdrop_path = None
        self.vote_average = 0
        self.tmdb_info = {}
        self._stop_name_flag = False

    def __init_name(self, token):
        # 中文或者英文单词都记为名称
        # 干掉一些固定的前缀 JADE AOD XXTV-X
        token = re.sub(r'^JADE[\s.]+|^AOD[\s.]+|^[A-Z]{2,4}TV[\-0-9UVHD]*[\s.]+', '', token, flags=re.IGNORECASE).strip()
        # 如果带有Sxx-Sxx、Exx-Exx这类的要处理掉
        token = re.sub(r'[SsEePp]+\d{1,3}-?[SsEePp]*\d{0,3}', '', token).strip()
        if not token:
            return
        if self._stop_name_flag:
            return
        if is_chinese(token):
            # 中文标题，处理下看是不是有季和集的信息
            self.__init_subtitle(token)
            # 名㝋里如果有第X季，第X集的干掉
            token = re.sub(r'第\s*[0-9一二三四五六七八九十]+\s*季|第\s*[0-9一二三四五六七八九十]+\s*集', '', token, flags=re.IGNORECASE).strip()
            # 有中文的，把中文外的英文、字符、等全部去掉，连在一起的数字会保留
            token = re.sub(r'[a-zA-Z【】\-_.\[\]()\s]+', '', token).strip()
            # 标题
            if not self.cn_name and token:
                self.cn_name = token
        else:
            # 2位以上的数字不要
            if token.isdigit() and len(token) > 2:
                return
            # 不是全英文的不要
            if not token.isalpha():
                return
            if self.en_name:
                self.en_name = "%s %s" % (self.en_name, token)
            else:
                self.en_name = token

    def __init_year(self, token):
        if not token.isdigit():
            return
        if len(token) != 4:
            return
        if not 1900 < int(token) < 2100:
            return
        self.year = token
        self._stop_name_flag = True

    def __init_resource_pix(self, token):
        re_res = re.search(r"[SBUHD]*(\d{3,4}[PI]+)", token, re.IGNORECASE)
        if re_res:
            self.resource_pix = re_res.group(1).lower()
            self._stop_name_flag = True
        else:
            re_res = re.search(r"([248]+K)", token, re.IGNORECASE)
            if re_res:
                self.resource_pix = re_res.group(1).lower()
                self._stop_name_flag = True

    def __init_seasion(self, token):
        re_res = re.search(r"^S(\d{1,2})", token, re.IGNORECASE)
        if re_res:
            se = int(re_res.group(1).upper())
            if not self.begin_season:
                self.begin_season = se
            else:
                if self.begin_season != se:
                    self.end_season = se
            self.type = MediaType.TV
            self._stop_name_flag = True

    def __init_episode(self, token):
        re_res = re.search(r"[\s0-9.\[]+EP?(\d{1,3})", token, re.IGNORECASE)
        if re_res:
            se = int(re_res.group(1).upper())
            if not self.begin_episode:
                self.begin_episode = se
            else:
                if self.begin_episode != se:
                    self.end_episode = se
            self.type = MediaType.TV
            self._stop_name_flag = True

    def __init_resource_type(self, token):
        re_res = re.search(r"(BLU-?RAY|REMUX|HDTV|WEB|WEBRIP|DVDRIP|UHD)", token, re.IGNORECASE)
        if re_res:
            self.resource_type = re_res.group(1)
            self._stop_name_flag = True

    def __init_subtitle(self, title_text):
        if re.search(r'[第季集]', title_text, re.IGNORECASE):
            # 季
            season_str = re.search(r'第\s*([0-9一二三四五六七八九十\-]+)\s*季', title_text, re.IGNORECASE)
            if season_str:
                seasons = season_str.group(1).strip()
                end_season = None
                if seasons.find('-') != -1:
                    seasons = seasons.split('-')
                    begin_season = int(cn2an.cn2an(seasons[0], mode='smart'))
                    if len(seasons) > 1:
                        end_season = int(cn2an.cn2an(seasons[1], mode='smart'))
                else:
                    begin_season = int(cn2an.cn2an(seasons, mode='smart'))
                if not self.begin_season and isinstance(begin_season, int):
                    self.begin_season = begin_season
                if self.begin_season and not self.end_season and isinstance(end_season, int):
                    self.end_season = end_season
                self.type = MediaType.TV
            # 集
            episode_str = re.search(r'第\s*([0-9一二三四五六七八九十\-]+)\s*集', title_text, re.IGNORECASE)
            if episode_str:
                episodes = episode_str.group(1).strip()
                end_episode = None
                if episodes.find('-') != -1:
                    episodes = episodes.split('-')
                    begin_episode = int(cn2an.cn2an(episodes[0], mode='smart'))
                    if len(episodes) > 1:
                        end_episode = int(cn2an.cn2an(episodes[1], mode='smart'))
                else:
                    begin_episode = int(cn2an.cn2an(episodes, mode='smart'))
                if not self.begin_episode and isinstance(begin_episode, int):
                    self.begin_episode = begin_episode
                if self.begin_episode and not self.end_episode and isinstance(end_episode, int):
                    self.end_episode = end_episode
                self.type = MediaType.TV

    def get_name(self):
        return self.cn_name if self.cn_name else self.en_name

    def get_title_string(self):
        return "%s (%s)" % (self.title, self.year) if self.year else self.title

    # 返回季字符串
    def get_season_string(self):
        if self.begin_season:
            return "S%s" % str(self.begin_season).rjust(2, "0") \
                if not self.end_season else "S%s-S%s" %\
                                            (str(self.begin_season).rjust(2, "0"), str(self.end_season).rjust(2, "0"))
        else:
            if self.type == MediaType.TV:
                return "S01"
            else:
                return ""

    # 返回季的数组
    def get_season_list(self):
        if not self.begin_season:
            if self.type == MediaType.TV:
                return [1]
            else:
                return []
        elif self.end_season:
            return [season for season in range(self.begin_season, self.end_season + 1)]
        else:
            return [self.begin_season]

    # 返回集字符串
    def get_episode_string(self):
        if self.begin_episode:
            return "E%s" % str(self.begin_episode).rjust(2, "0") \
                if not self.end_episode else "E%s-E%s" % \
                                             (str(self.begin_episode).rjust(2, "0"), str(self.end_episode).rjust(2, "0"))
        else:
            return ""

    # 返回集的数组
    def get_episode_list(self):
        if not self.begin_episode:
            return []
        elif self.end_episode:
            return [episode for episode in range(self.begin_episode, self.end_episode + 1)]
        else:
            return [self.begin_episode]

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

    # 是否包含季
    def is_in_seasion(self, season):
        if self.end_season:
            return self.begin_season <= int(season) <= self.end_season
        else:
            if self.begin_season:
                return int(season) == self.begin_season
            else:
                return int(season) == 1

    # 是否包含集
    def is_in_episode(self, episode):
        if self.end_episode:
            return self.begin_episode <= int(episode) <= self.end_episode
        else:
            return int(episode) == self.begin_episode

    # 整合TMDB识别的信息
    def set_tmdb_info(self, info):
        if not info:
            return
        if info.get('media_type'):
            self.type = info.get('media_type')
        if not self.type:
            return
        self.tmdb_id = info.get('id')
        if not self.tmdb_id:
            return
        self.tmdb_info = info
        self.vote_average = info.get('vote_average')
        if self.type == MediaType.MOVIE:
            self.title = info.get('title')
            release_date = info.get('release_date')
            if release_date:
                self.year = info.release_date[0:4]
        else:
            self.title = info.get('name')
            first_air_date = info.get('first_air_date')
            if first_air_date:
                self.year = info.first_air_date[0:4]
        self.poster_path = "https://image.tmdb.org/t/p/w500%s" % info.get('poster_path')
        self.backdrop_path = self.get_backdrop_image(self.type, info.get('backdrop_path'), info.get('id'))
        self.category = self.__set_category(info)

    # 整合种了信息
    def set_torrent_info(self, site=None, site_order=0, enclosure=None, res_type=None, res_order=0, size=0, seeders=0, peers=0, description=None):
        self.site = site
        self.site_order = site_order
        self.enclosure = enclosure
        self.res_type = res_type
        self.res_order = res_order
        self.size = size
        self.seeders = seeders
        self.peers = peers
        self.description = description

    # 获取消息媒体图片
    @staticmethod
    def get_backdrop_image(search_type, backdrop_path, tmdbid, default=None):
        if not search_type:
            return ""
        if tmdbid:
            if search_type == MediaType.TV:
                image_url = FANART_TV_API_URL % tmdbid
            else:
                image_url = FANART_MOVIE_API_URL % tmdbid
            try:
                ret = requests.get(image_url)
                if ret:
                    moviethumbs = ret.json().get('moviethumb')
                    if moviethumbs:
                        moviethumb = moviethumbs[0].get('url')
                        if moviethumb:
                            # 有则返回FanArt的图片
                            return moviethumb
            except RequestException as e1:
                print(str(e1))
            except Exception as e2:
                print(str(e2))
        if backdrop_path:
            return "https://image.tmdb.org/t/p/w500%s" % backdrop_path
        if default:
            # 返回一个默认图片
            return default
        return ""

    # 分类
    def __set_category(self, info):
        if not self.type:
            return None
        if self.type == MediaType.TV:
            # 类型 动漫、纪录片、儿童、综艺
            media_genre_ids = info.get('genre_ids')
            if 16 in media_genre_ids:
                # 动漫
                catagory = MediaCatagory.DM
            elif 99 in media_genre_ids:
                # 纪录片
                catagory = MediaCatagory.JLP
            elif 10762 in media_genre_ids:
                # 儿童
                catagory = MediaCatagory.RT
            elif 10764 in media_genre_ids or 10767 in media_genre_ids:
                # 综艺
                catagory = MediaCatagory.ZY
            else:
                # 国家
                media_country = info.get('origin_country')
                if 'CN' in media_country or 'TW' in media_country:
                    catagory = MediaCatagory.GCJ
                elif set(RMT_COUNTRY_EA).intersection(set(media_country)):
                    catagory = MediaCatagory.OMJ
                elif set(RMT_COUNTRY_AS).intersection(set(media_country)):
                    catagory = MediaCatagory.RHJ
                else:
                    catagory = MediaCatagory.QTJ
        else:
            media_language = info.original_language
            if 'zh' in media_language or \
                    'bo' in media_language or \
                    'za' in media_language or \
                    'cn' in media_language:
                catagory = MediaCatagory.HYDY
            else:
                catagory = MediaCatagory.WYDY

        return catagory


if __name__ == "__main__":
    text = "Westworld.S01E01.1080p.BluRay.x265-10bit.DTS5.1-Chingyun"
    meta_info = MetaInfo(text)
    print(meta_info.__dict__)
    print(meta_info.is_in_seasion(7))
