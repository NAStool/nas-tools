import re
from functools import lru_cache

import cn2an

import log
from config import FANART_TV_API_URL, FANART_MOVIE_API_URL, ANIME_GENREIDS, Config, DEFAULT_TMDB_IMAGE
from rmt.category import Category
from utils.functions import is_all_chinese
from utils.http_utils import RequestUtils
from utils.types import MediaType


class MetaBase(object):
    """
    媒体信息基类
    """
    proxies = None
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
    # 视频编码
    video_encode = None
    # 音频编码
    audio_encode = None
    # 二级分类
    category = None
    # TMDB ID
    tmdb_id = 0
    # 豆瓣 ID
    douban_id = 0
    # 媒体标题
    title = None
    # 媒体原语种
    original_language = None
    # 媒体原发行标题
    original_title = None
    # 媒体年份
    year = None
    # 封面图片
    backdrop_path = None
    poster_path = None
    fanart_image = None
    fanart_flag = False
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
    page_url = None
    upload_volume_factor = None
    download_volume_factor = None
    hit_and_run = None
    rssid = None
    # 副标题解析
    _subtitle_flag = False
    _subtitle_season_re = r"[第\s]+([0-9一二三四五六七八九十S\-]+)\s*季"
    _subtitle_season_all_re = r"全\s*([0-9一二三四五六七八九十]+)\s*季|([0-9一二三四五六七八九十]+)\s*季全"
    _subtitle_episode_re = r"[第\s]+([0-9一二三四五六七八九十EP\-]+)\s*[集话話]"
    _subtitle_episode_all_re = r"([0-9一二三四五六七八九十]+)\s*集全|全\s*([0-9一二三四五六七八九十]+)\s*集"

    def __init__(self, title, subtitle=None):
        if not title:
            return
        config = Config()
        self.proxies = config.get_proxies()
        self.category_handler = Category()
        self.org_string = title
        self.subtitle = subtitle

    def get_name(self):
        if self.cn_name and is_all_chinese(self.cn_name):
            return self.cn_name
        elif self.en_name:
            return self.en_name
        elif self.cn_name:
            return self.cn_name
        return ""

    def get_title_string(self):
        if self.title:
            return "%s (%s)" % (self.title, self.year) if self.year else self.title
        elif self.get_name():
            return "%s (%s)" % (self.get_name(), self.year) if self.year else self.get_name()
        else:
            return ""

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

    def get_title_ep_vote_string(self):
        string = self.get_title_string()
        if self.get_episode_list():
            string = "%s %s" % (string, self.get_season_episode_string())
        else:
            if self.get_season_list():
                string = "%s %s" % (string, self.get_season_string())
            if self.vote_average:
                string = "%s %s" % (string, self.get_vote_string())
        return string

    def get_overview_string(self, max_len=140):
        """
        返回带限定长度的简介信息
        :param max_len: 内容长度
        :return:
        """
        if not hasattr(self, "overview"):
            return ""

        overview = self.overview
        placeholder = ' ...'
        max_len = max(len(placeholder), max_len - len(placeholder))
        overview = (overview[:max_len] + placeholder) if len(overview) > max_len else overview
        return overview

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

    # 返回begin_season 的数字
    def get_season_seq(self):
        if self.begin_season is not None:
            return str(self.begin_season)
        else:
            if self.type == MediaType.MOVIE:
                return ""
            else:
                return "1"

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

    # 返回单文件多集的集数表达方式，用于支持单文件多集
    def get_episode_seqs(self):
        episodes = self.get_episode_list()
        if episodes:
            # 集 xx
            if len(episodes) == 1:
                return str(episodes[0])
            else:
                return "%s-%s" % (episodes[0], episodes[-1])
        else:
            return ""

    # 返回begin_episode 的数字
    def get_episode_seq(self):
        episodes = self.get_episode_list()
        if episodes:
            return str(episodes[0])
        else:
            return ""

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

    # 返回视频编码
    def get_video_encode_string(self):
        return self.video_encode or ""

    # 返回音频编码
    def get_audio_encode_string(self):
        return self.audio_encode or ""

    # 返回背景图片地址
    def get_backdrop_path(self, default=True):
        if not self.fanart_image:
            self.__refresh_fanart_image()
        if self.fanart_image:
            return self.fanart_image
        elif self.backdrop_path:
            return self.backdrop_path
        else:
            return "../static/img/tmdb.webp" if default else ""

    # 返回消息图片地址
    def get_message_image(self):
        if not self.fanart_image:
            self.__refresh_fanart_image()
        if self.fanart_image:
            return self.fanart_image
        elif self.backdrop_path:
            return self.backdrop_path
        elif self.poster_path:
            return self.poster_path
        else:
            return DEFAULT_TMDB_IMAGE

    # 返回海报图片地址
    def get_poster_image(self):
        return self.poster_path if self.poster_path else ""

    # 返回促销信息
    def get_volume_factor_string(self):
        if self.upload_volume_factor is None or self.download_volume_factor is None:
            return "未知"
        free_strs = {
            "1.0 1.0": "普通",
            "1.0 0.0": "免费",
            "2.0 1.0": "2X",
            "2.0 0.0": "2X免费",
            "1.0 0.5": "50%",
            "2.0 0.5": "2X 50%",
            "1.0 0.7": "70%",
            "1.0 0.3": "30%"
        }
        return free_strs.get('%.1f %.1f' % (self.upload_volume_factor, self.download_volume_factor), "未知")

    # 是否包含季
    def is_in_season(self, season):
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
            self.original_title = info.get('original_title')
            self.original_language = info.get('original_language')
            release_date = info.get('release_date')
            if release_date:
                self.year = release_date[0:4]
            self.category = self.category_handler.get_movie_category(info)
        else:
            self.title = info.get('name')
            self.original_title = info.get('original_name')
            self.original_language = info.get('original_language')
            first_air_date = info.get('first_air_date')
            if first_air_date:
                self.year = first_air_date[0:4]
            if self.type == MediaType.TV:
                self.category = self.category_handler.get_tv_category(info)
            else:
                self.category = self.category_handler.get_anime_category(info)
        self.poster_path = "https://image.tmdb.org/t/p/w500%s" % info.get('poster_path') if info.get(
            'poster_path') else ""
        self.backdrop_path = "https://image.tmdb.org/t/p/w500%s" % info.get('backdrop_path') if info.get(
            'backdrop_path') else ""

    # 刷新Fanart图片
    def __refresh_fanart_image(self):
        if not self.tmdb_id:
            return
        if self.fanart_image or self.fanart_flag:
            return
        self.fanart_image = self.__get_fanart_image(search_type=self.type, tmdbid=self.tmdb_id)
        self.fanart_flag = True

    # 获取Fanart图片
    def get_fanart_image(self):
        self.__refresh_fanart_image()
        return self.fanart_image

    # 整合种了信息
    def set_torrent_info(self,
                         site=None,
                         site_order=0,
                         enclosure=None,
                         res_order=0,
                         size=0,
                         seeders=0,
                         peers=0,
                         description=None,
                         page_url=None,
                         upload_volume_factor=None,
                         download_volume_factor=None,
                         rssid=None,
                         hit_and_run=None):
        if site:
            self.site = site
        if site_order:
            self.site_order = site_order
        if enclosure:
            self.enclosure = enclosure
        if res_order:
            self.res_order = res_order
        if size:
            self.size = size
        if seeders:
            self.seeders = seeders
        if peers:
            self.peers = peers
        if description:
            self.description = description
        if page_url:
            self.page_url = page_url
        if upload_volume_factor is not None:
            self.upload_volume_factor = upload_volume_factor
        if download_volume_factor is not None:
            self.download_volume_factor = download_volume_factor
        if rssid:
            self.rssid = rssid
        if hit_and_run is not None:
            self.hit_and_run = hit_and_run

    # 获取消息媒体图片
    # 增加cache，优化资源检索时性能
    @classmethod
    @lru_cache(maxsize=128)
    def __get_fanart_image(cls, search_type, tmdbid, default=None):
        if not search_type:
            return ""
        if tmdbid:
            if search_type == MediaType.MOVIE:
                image_url = FANART_MOVIE_API_URL % tmdbid
            else:
                image_url = FANART_TV_API_URL % tmdbid
            try:
                ret = RequestUtils(proxies=cls.proxies, timeout=5).get_res(image_url)
                if ret:
                    moviethumbs = ret.json().get('moviethumb')
                    if moviethumbs:
                        moviethumb = moviethumbs[0].get('url')
                        if moviethumb:
                            # 有则返回FanArt的图片
                            return moviethumb
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

    def init_subtitle(self, title_text):
        if not title_text:
            return
        if re.search(r'[全第季集话話]', title_text, re.IGNORECASE):
            # 第x季
            season_str = re.search(r'%s' % self._subtitle_season_re, title_text, re.IGNORECASE)
            if season_str:
                seasons = season_str.group(1)
                if seasons:
                    seasons = seasons.upper().replace("S", "").strip()
                else:
                    return
                try:
                    end_season = None
                    if seasons.find('-') != -1:
                        seasons = seasons.split('-')
                        begin_season = int(cn2an.cn2an(seasons[0].strip(), mode='smart'))
                        if len(seasons) > 1:
                            end_season = int(cn2an.cn2an(seasons[1].strip(), mode='smart'))
                    else:
                        begin_season = int(cn2an.cn2an(seasons, mode='smart'))
                except Exception as err:
                    print(str(err))
                    return
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
                    episodes = episodes.upper().replace("E", "").replace("P", "").strip()
                else:
                    return
                try:
                    end_episode = None
                    if episodes.find('-') != -1:
                        episodes = episodes.split('-')
                        begin_episode = int(cn2an.cn2an(episodes[0].strip(), mode='smart'))
                        if len(episodes) > 1:
                            end_episode = int(cn2an.cn2an(episodes[1].strip(), mode='smart'))
                    else:
                        begin_episode = int(cn2an.cn2an(episodes, mode='smart'))
                except Exception as err:
                    print(str(err))
                    return
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
                    try:
                        self.total_seasons = int(cn2an.cn2an(season_all.strip(), mode='smart'))
                    except Exception as err:
                        print(str(err))
                        return
                    self.begin_season = 1
                    self.end_season = self.total_seasons
                    self._subtitle_flag = True
