import anitopy
import log
from rmt.meta.metabase import MetaBase
from utils.functions import is_chinese
from utils.types import MediaType


class MetaAnime(MetaBase):
    """
    识别动漫
    """
    _anime_no_words = ['CHS&CHT']

    def __init__(self, title, subtitle=None):
        super().__init__(title, subtitle)
        if not title:
            return
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
                # 拆份中英文名称
                lastword_type = ""
                for word in name:
                    if not word:
                        continue
                    if word.isspace() or word.isdigit():
                        if lastword_type == "cn":
                            self.cn_name = "%s%s" % (self.cn_name or "", word)
                        elif lastword_type == "en":
                            self.en_name = "%s%s" % (self.en_name or "", word)
                    elif is_chinese(word):
                        self.cn_name = "%s%s" % (self.cn_name or "", word)
                        lastword_type = "cn"
                    else:
                        self.en_name = "%s%s" % (self.en_name or "", word)
                        lastword_type = "en"
                if self.cn_name:
                    self.cn_name = self.cn_name.strip()
                if self.en_name:
                    self.en_name = self.en_name.strip()
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
                if isinstance(self.resource_pix, list):
                    self.resource_pix = self.resource_pix[0]
        except Exception as e:
            log.console(str(e))
