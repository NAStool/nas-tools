import os
import shutil
from functools import lru_cache
from urllib.parse import quote

from pyquery import PyQuery

from app.helper import SiteHelper
from app.helper.chrome_helper import ChromeHelper
from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils import RequestUtils, PathUtils, ExceptionUtils
from app.utils.types import MediaType, EventType
from config import Config, RMT_SUBEXT


class OpenSubtitles(_IPluginModule):
    # 插件名称
    module_name = "OpenSubtitles"
    # 插件描述
    module_desc = "从opensubtitles.org下载中文字幕。"
    # 插件图标
    module_icon = "opensubtitles.png"
    # 主题色
    module_color = "bg-black"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "opensubtitles_"
    # 加载顺序
    module_order = 2
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    sitehelper = None
    _cookie = ""
    _ua = None
    _url_imdbid = "https://www.opensubtitles.org/zh/search/imdbid-%s/sublanguageid-chi"
    _url_keyword = "https://www.opensubtitles.org/zh/search/moviename-%s/sublanguageid-chi"
    _save_tmp_path = None
    _enable = False

    def __init__(self):
        self._ua = Config().get_ua()

    def init_config(self, config: dict = None):
        self.sitehelper = SiteHelper()
        self._save_tmp_path = Config().get_temp_path()
        if not os.path.exists(self._save_tmp_path):
            os.makedirs(self._save_tmp_path)
        if config:
            self._enable = config.get("enable")

    def get_state(self):
        return self._enable

    @staticmethod
    def get_fields():
        return [
            # 同一板块
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '开启opensubtitles.org字幕下载',
                            'required': "",
                            'tooltip': '需要确保网络能正常连通www.opensubtitles.org',
                            'type': 'switch',
                            'id': 'enable',
                        }
                    ]
                ]
            }
        ]

    def stop_service(self):
        pass

    @EventHandler.register(EventType.SubtitleDownload)
    def download(self, event):
        """
        调用OpenSubtitles Api下载字幕
        """
        if not self._enable:
            return
        item = event.event_data
        if not item:
            return
        # 媒体信息
        item_media = item.get("media_info")
        if item_media.get("type") != MediaType.MOVIE.value and not item_media.get("imdb_id"):
            self.warn("电视剧类型需要imdbid才能搜索字幕！")
            return
        # 查询名称
        item_name = item_media.get("en_name") or item_media.get("cn_name")
        # 查询IMDBID
        imdb_id = item_media.get("imdb_id")
        # 查询年份
        item_year = item_media.get("year")
        # 查询季
        item_season = item_media.get("season")
        # 查询集
        item_episode = item_media.get("episode")
        # 文件路径
        item_file = item.get("file")
        # 后缀
        item_file_ext = item.get("file_ext")

        self.info("开始从Opensubtitle.org搜索字幕: %s，imdbid=%s" % (item_name, imdb_id))
        subtitles = self.search_subtitles(imdb_id=imdb_id, name=item_name, year=item_year)
        if not subtitles:
            self.warn("%s 未搜索到字幕" % item_name)
        else:
            self.info("opensubtitles.org返回数据：%s" % len(subtitles))
            # 成功数
            subtitle_count = 0
            for subtitle in subtitles:
                # 标题
                if not imdb_id:
                    if str(subtitle.get('title')) != "%s (%s)" % (item_name, item_year):
                        continue
                # 季
                if item_season \
                        and subtitle.get('season') \
                        and int(subtitle.get('season').replace("Season", "").strip()) not in item_season:
                    continue
                # 集
                if item_episode \
                        and subtitle.get('episode') \
                        and int(subtitle.get('episode')) not in item_episode:
                    continue
                # 字幕文件名
                SubFileName = subtitle.get('description')
                # 下载链接
                Download_Link = subtitle.get('link')
                # 下载后的字幕文件路径
                Media_File = "%s.chi.zh-cn%s" % (item_file, item_file_ext)
                self.info("正在从opensubtitles.org下载字幕 %s 到 %s " % (SubFileName, Media_File))
                # 下载
                ret = RequestUtils(cookies=self._cookie,
                                   headers=self._ua).get_res(Download_Link)
                if ret and ret.status_code == 200:
                    # 保存ZIP
                    file_name = self.sitehelper.get_url_subtitle_name(ret.headers.get('content-disposition'), Download_Link)
                    if not file_name:
                        continue
                    zip_file = os.path.join(self._save_tmp_path, file_name)
                    zip_path = os.path.splitext(zip_file)[0]
                    with open(zip_file, 'wb') as f:
                        f.write(ret.content)
                    # 解压文件
                    shutil.unpack_archive(zip_file, zip_path, format='zip')
                    # 遍历转移文件
                    for sub_file in PathUtils.get_dir_files(in_path=zip_path, exts=RMT_SUBEXT):
                        self.sitehelper.transfer_subtitle(sub_file, Media_File)
                    # 删除临时文件
                    try:
                        shutil.rmtree(zip_path)
                        os.remove(zip_file)
                    except Exception as err:
                        ExceptionUtils.exception_traceback(err)
                else:
                    self.error("下载字幕文件失败：%s" % Download_Link)
                    continue
                # 最多下载3个字幕
                subtitle_count += 1
                if subtitle_count > 2:
                    break
            if not subtitle_count:
                if item_episode:
                    self.info("%s 第%s季 第%s集 未找到符合条件的字幕" % (
                        item_name, item_season, item_episode))
                else:
                    self.info("%s 未找到符合条件的字幕" % item_name)
            else:
                self.info("%s 共下载了 %s 个字幕" % (item_name, subtitle_count))

    def search_subtitles(self, imdb_id, name, year):
        if imdb_id:
            return self.__search_subtitles_by_imdbid(imdb_id)
        else:
            return self.__search_subtitles_by_keyword("%s %s" % (name, year))

    def __search_subtitles_by_imdbid(self, imdbid):
        """
        按TMDBID搜索OpenSubtitles
        """
        return self.__parse_opensubtitles_results(url=self._url_imdbid % str(imdbid).replace("tt", ""))

    def __search_subtitles_by_keyword(self, keyword):
        """
        按关键字搜索OpenSubtitles
        """
        return self.__parse_opensubtitles_results(url=self._url_keyword % quote(keyword))

    @classmethod
    @lru_cache(maxsize=128)
    def __parse_opensubtitles_results(cls, url):
        """
        搜索并解析结果
        """
        chrome = ChromeHelper()
        if not chrome.get_status():
            return []
        # 访问页面
        if not chrome.visit(url):
            return []
        # 源码
        html_text = chrome.get_html()
        # Cookie
        cls._cookie = chrome.get_cookies()
        # 解析列表
        ret_subtitles = []
        html_doc = PyQuery(html_text)
        global_season = ''
        for tr in html_doc('#search_results > tbody > tr:not([style])'):
            tr_doc = PyQuery(tr)
            # 季
            season = tr_doc('span[id^="season-"] > a > b').text()
            if season:
                global_season = season
                continue
            # 集
            episode = tr_doc('span[itemprop="episodeNumber"]').text()
            # 标题
            title = tr_doc('strong > a.bnone').text()
            # 描述 下载链接
            if not global_season:
                description = tr_doc('td:nth-child(1)').text()
                if description and len(description.split("\n")) > 1:
                    description = description.split("\n")[1]
                link = tr_doc('td:nth-child(5) > a').attr("href")
            else:
                description = tr_doc('span[itemprop="name"]').text()
                link = tr_doc('a[href^="/download/"]').attr("href")
            if link:
                link = "https://www.opensubtitles.org%s" % link
            else:
                continue
            ret_subtitles.append({
                "season": global_season,
                "episode": episode,
                "title": title,
                "description": description,
                "link": link
            })
        return ret_subtitles
