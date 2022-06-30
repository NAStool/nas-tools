import re

import anitopy
import log
from rmt.meta.metabase import MetaBase
from utils.functions import is_chinese, is_all_chinese
from utils.types import MediaType


class MetaAnime(MetaBase):
    """
    识别动漫
    """
    _anime_no_words = ['CHS&CHT', 'MP4', 'GB MP4', 'WEB-DL']

    def __init__(self, title, subtitle=None):
        super().__init__(title, subtitle)
        if not title:
            return
        # 调用第三方模块识别动漫
        try:
            title = self.__prepare_title(title)
            anitopy_info = anitopy.parse(title)
            if anitopy_info:
                # 名称
                name = anitopy_info.get("anime_title")
                if not name or name in self._anime_no_words or (len(name) < 5 and not is_chinese(name)):
                    anitopy_info = anitopy.parse("[ANIME]" + title)
                    if anitopy_info:
                        name = anitopy_info.get("anime_title")
                if not name or name in self._anime_no_words or (len(name) < 5 and not is_chinese(name)):
                    name_match = re.search(r'\[(.+?)]', title)
                    if name_match and name_match.group(1):
                        name = name_match.group(1).strip()
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
                    self.type = MediaType.TV
                if isinstance(end_season, str) and end_season.isdigit():
                    if self.begin_season is not None and end_season != self.begin_season:
                        self.end_season = int(end_season)
                        self.type = MediaType.TV
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
                    self.type = MediaType.TV
                if isinstance(end_episode, str) and end_episode.isdigit():
                    if self.end_episode is not None and end_episode != self.end_episode:
                        self.end_season = int(end_episode)
                        self.type = MediaType.TV
                # 类型
                if not self.type:
                    anime_type = anitopy_info.get('anime_type')
                    if isinstance(anime_type, list):
                        anime_type = anime_type[0]
                    if isinstance(anime_type, str):
                        if anime_type.upper() == "TV":
                            self.type = MediaType.TV
                        else:
                            self.type = MediaType.MOVIE
                # 分辨率
                self.resource_pix = anitopy_info.get("video_resolution")
                if isinstance(self.resource_pix, list):
                    self.resource_pix = self.resource_pix[0]
                if self.resource_pix:
                    if re.search(r'x', self.resource_pix, re.IGNORECASE):
                        self.resource_pix = re.split(r'[Xx]', self.resource_pix)[0] + "p"
                # 视频编码
                self.video_encode = anitopy_info.get("video_term")
                if isinstance(self.video_encode, list):
                    self.video_encode = self.video_encode[0]
                # 音频编码
                self.audio_encode = anitopy_info.get("audio_term")
                if isinstance(self.audio_encode, list):
                    self.audio_encode = self.audio_encode[0]
            if not self.type:
                self.type = MediaType.TV
        except Exception as e:
            log.console(str(e))

    @staticmethod
    def __prepare_title(title):
        """
        对命名进行预处理
        """
        if not title:
            return title
        title = title.replace("【", "[").replace("】", "]")
        if re.search(r"新番|月?番", title):
            title = re.sub(".*新番.", "", title)
        else:
            title = re.sub(r"^[^]】]*[]】]", "", title).strip()
        names = title.split("]")
        if len(names) > 1:
            titles = []
            for name in names:
                if not is_all_chinese(name[1:]):
                    name = re.sub(r'[\u4e00-\u9fa5]', '', name)
                if name and name.find("/") != -1:
                    if name.split("/")[-1].strip():
                        titles.append("[%s" % name.split("/")[-1].strip())
                    else:
                        titles.append("[%s" % name.split("/")[0].strip())
                else:
                    titles.append(name.strip())
            return "]".join(titles)
        return title
