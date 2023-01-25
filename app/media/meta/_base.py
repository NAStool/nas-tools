import re
import cn2an
from app.media.fanart import Fanart
from config import ANIME_GENREIDS, DEFAULT_TMDB_IMAGE, TMDB_IMAGE_W500_URL
from app.media.category import Category
from app.utils import StringUtils, ExceptionUtils
from app.utils.types import MediaType


class MetaBase(object):
    """
    媒体信息基类
    """
    proxies = None
    category_handler = None
    # 是否处理的文件
    fileflag = False
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
    # 识别的效果
    resource_effect = None
    # 识别的分辨率
    resource_pix = None
    # 识别的制作组/字幕组
    resource_team = None
    # 视频编码
    video_encode = None
    # 音频编码
    audio_encode = None
    # 二级分类
    category = None
    # TMDB ID
    tmdb_id = 0
    # IMDB ID
    imdb_id = ""
    # TVDB ID
    tvdb_id = 0
    # 豆瓣 ID
    douban_id = 0
    # 自定义搜索词
    keyword = None
    # 媒体标题
    title = None
    # 媒体原语种
    original_language = None
    # 媒体原发行标题
    original_title = None
    # 媒体发行日期
    release_date = None
    # 播放时长
    runtime = 0
    # 媒体年份
    year = None
    # 封面图片
    backdrop_path = None
    poster_path = None
    fanart_backdrop = None
    fanart_poster = None
    # 评分
    vote_average = 0
    # 描述
    overview = None
    # TMDB 的其它信息
    tmdb_info = {}
    # 本地状态 1-已订阅 2-已存在
    fav = "0"
    # 站点列表
    rss_sites = []
    search_sites = []
    # 种子附加信息
    # 站点名称
    site = None
    # 站点优先级
    site_order = 0
    # 操作用户
    user_name = None
    # 种子链接
    enclosure = None
    # 资源优先级
    res_order = 0
    # 使用的过滤规则
    filter_rule = None
    # 是否洗版
    over_edition = None
    # 种子大小
    size = 0
    # 做种者
    seeders = 0
    # 下载者
    peers = 0
    # 种子描述
    description = None
    # 详情页面
    page_url = None
    # 上传因子
    upload_volume_factor = None
    # 下载因子
    download_volume_factor = None
    # HR
    hit_and_run = None
    # 订阅ID
    rssid = None
    # 保存目录
    save_path = None
    # 下载设置
    download_setting = None
    # 识别辅助
    ignored_words = None
    replaced_words = None
    offset_words = None
    # 备注字典
    note = {}
    # 副标题解析
    _subtitle_flag = False
    _subtitle_season_re = r"[第\s]+([0-9一二三四五六七八九十S\-]+)\s*季"
    _subtitle_season_all_re = r"全\s*([0-9一二三四五六七八九十]+)\s*季|([0-9一二三四五六七八九十]+)\s*季全"
    _subtitle_episode_re = r"[第\s]+([0-9一二三四五六七八九十EP\-]+)\s*[集话話期]"
    _subtitle_episode_all_re = r"([0-9一二三四五六七八九十]+)\s*集全|全\s*([0-9一二三四五六七八九十]+)\s*[集话話期]"

    def __init__(self, title, subtitle=None, fileflag=False):
        self.category_handler = Category()
        self.fanart = Fanart()
        if not title:
            return
        self.org_string = title
        self.subtitle = subtitle
        self.fileflag = fileflag

    def get_name(self):
        if self.cn_name and StringUtils.is_all_chinese(self.cn_name):
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

    def get_star_string(self):
        if self.vote_average:
            return "评分：%s" % self.get_stars()
        else:
            return ""

    def get_vote_string(self):
        if self.vote_average:
            return "评分：%s" % round(float(self.vote_average), 1)
        else:
            return ""

    def get_type_string(self):
        if not self.type:
            return ""
        return "类型：%s" % self.type.value

    def get_title_vote_string(self):
        if not self.vote_average:
            return self.get_title_string()
        else:
            return "%s\n%s" % (self.get_title_string(), self.get_star_string())

    def get_title_ep_string(self):
        string = self.get_title_string()
        if self.get_episode_list():
            string = "%s %s" % (string, self.get_season_episode_string())
        else:
            if self.get_season_list():
                string = "%s %s" % (string, self.get_season_string())
        return string

    def get_overview_string(self, max_len=140):
        """
        返回带限定长度的简介信息
        :param max_len: 内容长度
        :return:
        """
        if not hasattr(self, "overview"):
            return ""

        overview = str(self.overview).strip()
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

    # 返回资源类型字符串，含分辨率
    def get_resource_type_string(self):
        ret_string = ""
        if self.resource_type:
            ret_string = f"{ret_string} {self.resource_type}"
        if self.resource_effect:
            ret_string = f"{ret_string} {self.resource_effect}"
        if self.resource_pix:
            ret_string = f"{ret_string} {self.resource_pix}"
        return ret_string

    # 返回资源类型字符串，不含分辨率
    def get_edtion_string(self):
        ret_string = ""
        if self.resource_type:
            ret_string = f"{ret_string} {self.resource_type}"
        if self.resource_effect:
            ret_string = f"{ret_string} {self.resource_effect}"
        return ret_string.strip()
    
    # 返回发布组/字幕组字符串
    def get_resource_team_string(self):
        if self.resource_team:
            return self.resource_team
        else:
            return ""

    # 返回视频编码
    def get_video_encode_string(self):
        return self.video_encode or ""

    # 返回音频编码
    def get_audio_encode_string(self):
        return self.audio_encode or ""

    # 返回背景图片地址
    def get_backdrop_image(self, default=True, original=False):
        if self.fanart_backdrop:
            return self.fanart_backdrop
        else:
            self.fanart_backdrop = self.fanart.get_backdrop(media_type=self.type,
                                                            queryid=self.tmdb_id if self.type == MediaType.MOVIE else self.tvdb_id)
        if self.fanart_backdrop:
            return self.fanart_backdrop
        elif self.backdrop_path:
            if original:
                return self.backdrop_path.replace("/w500", "/original")
            else:
                return self.backdrop_path
        else:
            return "../static/img/tmdb.webp" if default else ""

    # 返回消息图片地址
    def get_message_image(self):
        if self.fanart_backdrop:
            return self.fanart_backdrop
        else:
            self.fanart_backdrop = self.fanart.get_backdrop(media_type=self.type,
                                                            queryid=self.tmdb_id if self.type == MediaType.MOVIE else self.tvdb_id)
        if self.fanart_backdrop:
            return self.fanart_backdrop
        elif self.backdrop_path:
            return self.backdrop_path
        elif self.poster_path:
            return self.poster_path
        else:
            return DEFAULT_TMDB_IMAGE

    # 返回海报图片地址
    def get_poster_image(self, original=False):
        if self.poster_path:
            if original:
                return self.poster_path.replace("/w500", "/original")
            else:
                return self.poster_path
        if not self.fanart_poster:
            self.fanart_poster = self.fanart.get_poster(media_type=self.type,
                                                        queryid=self.tmdb_id if self.type == MediaType.MOVIE else self.tvdb_id)
        return self.fanart_poster or ""

    # 查询TMDB详情页URL
    def get_detail_url(self):
        if self.tmdb_id:
            if str(self.tmdb_id).startswith("DB:"):
                return "https://movie.douban.com/subject/%s" % str(self.tmdb_id).replace("DB:", "")
            elif self.type == MediaType.MOVIE:
                return "https://www.themoviedb.org/movie/%s" % self.tmdb_id
            else:
                return "https://www.themoviedb.org/tv/%s" % self.tmdb_id
        elif self.douban_id:
            return "https://movie.douban.com/subject/%s" % self.douban_id
        return ""

    # 返回评分星星个数
    def get_stars(self):
        if not self.vote_average:
            return ""
        return "".rjust(int(self.vote_average), "★")

    # 返回促销信息
    def get_volume_factor_string(self):
        return self.get_free_string(self.upload_volume_factor, self.download_volume_factor)

    @staticmethod
    def get_free_string(upload_volume_factor, download_volume_factor):
        if upload_volume_factor is None or download_volume_factor is None:
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
        return free_strs.get('%.1f %.1f' % (upload_volume_factor, download_volume_factor), "未知")

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
        if info.get("external_ids"):
            self.tvdb_id = info.get("external_ids", {}).get("tvdb_id", 0)
            self.imdb_id = info.get("external_ids", {}).get("imdb_id", "")
        self.tmdb_info = info
        self.vote_average = round(float(info.get('vote_average')), 1) if info.get('vote_average') else 0
        self.overview = info.get('overview')
        if self.type == MediaType.MOVIE:
            self.title = info.get('title')
            self.original_title = info.get('original_title')
            self.original_language = info.get('original_language')
            self.runtime = info.get("runtime")
            self.release_date = info.get('release_date')
            if self.release_date:
                self.year = self.release_date[0:4]
            self.category = self.category_handler.get_movie_category(info)
        else:
            self.title = info.get('name')
            self.original_title = info.get('original_name')
            self.original_language = info.get('original_language')
            self.runtime = info.get("episode_run_time")[0] if info.get("episode_run_time") else None
            self.release_date = info.get('first_air_date')
            if self.release_date:
                self.year = self.release_date[0:4]
            if self.type == MediaType.TV:
                self.category = self.category_handler.get_tv_category(info)
            else:
                self.category = self.category_handler.get_anime_category(info)
        self.poster_path = TMDB_IMAGE_W500_URL % info.get('poster_path') if info.get(
            'poster_path') else ""
        self.backdrop_path = TMDB_IMAGE_W500_URL % info.get('backdrop_path') if info.get(
            'backdrop_path') else ""

    # 整合种了信息
    def set_torrent_info(self,
                         site=None,
                         site_order=0,
                         enclosure=None,
                         res_order=0,
                         filter_rule=None,
                         size=0,
                         seeders=0,
                         peers=0,
                         description=None,
                         page_url=None,
                         upload_volume_factor=None,
                         download_volume_factor=None,
                         rssid=None,
                         hit_and_run=None,
                         imdbid=None,
                         over_edition=None):
        if site:
            self.site = site
        if site_order:
            self.site_order = site_order
        if enclosure:
            self.enclosure = enclosure
        if res_order:
            self.res_order = res_order
        if filter_rule:
            self.filter_rule = filter_rule
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
        if imdbid is not None:
            self.imdb_id = imdbid
        if over_edition is not None:
            self.over_edition = over_edition

    # 整合下载参数
    def set_download_info(self, download_setting=None, save_path=None):
        if download_setting:
            self.download_setting = download_setting
        if save_path:
            self.save_path = save_path

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
        if re.search(r'[全第季集话話期]', title_text, re.IGNORECASE):
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
                    ExceptionUtils.exception_traceback(err)
                    return
                if self.begin_season is None and isinstance(begin_season, int):
                    self.begin_season = begin_season
                    self.total_seasons = 1
                if self.begin_season is not None \
                        and self.end_season is None \
                        and isinstance(end_season, int) \
                        and end_season != self.begin_season:
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
                    ExceptionUtils.exception_traceback(err)
                    return
                if self.begin_episode is None and isinstance(begin_episode, int):
                    self.begin_episode = begin_episode
                    self.total_episodes = 1
                if self.begin_episode is not None \
                        and self.end_episode is None \
                        and isinstance(end_episode, int) \
                        and end_episode != self.begin_episode:
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
                self.type = MediaType.TV
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
                        ExceptionUtils.exception_traceback(err)
                        return
                    self.begin_season = 1
                    self.end_season = self.total_seasons
                    self.type = MediaType.TV
                    self._subtitle_flag = True

    def to_dict(self):
        """
        转化为字典
        """
        return {
            "id": self.tmdb_id,
            'orgid': self.tmdb_id,
            "title": self.title,
            "year": self.year,
            "type": self.type.value if self.type else "",
            'vote': self.vote_average,
            'image': self.poster_path,
            "imdb_id": self.imdb_id,
            "tmdb_id": self.tmdb_id,
            "overview": str(self.overview).strip() if self.overview else '',
            "link": self.get_detail_url()
        }
