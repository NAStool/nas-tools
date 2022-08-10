import os.path
import time
from xml.dom import minidom

import log
from rmt.media import Media
from rmt.meta.metabase import MetaBase
from utils.functions import add_node
from utils.http_utils import RequestUtils
from utils.types import MediaType


class NfoHelper:
    media = None

    def __init__(self):
        self.media = Media()

    def __gen_common_nfo(self, tmdbinfo: dict, doc, root):
        # 添加时间
        add_node(doc, root, "dateadded", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
        # TMDBID
        uniqueid = add_node(doc, root, "uniqueid", tmdbinfo.get("id") or "")
        uniqueid.setAttribute("type", "tmdb")
        uniqueid.setAttribute("default", "true")
        # tmdbid
        add_node(doc, root, "tmdbid", tmdbinfo.get("id") or "")
        # 简介
        xplot = add_node(doc, root, "plot")
        xplot.appendChild(doc.createCDATASection(tmdbinfo.get("overview") or ""))
        xoutline = add_node(doc, root, "outline")
        xoutline.appendChild(doc.createCDATASection(tmdbinfo.get("overview") or ""))
        # 导演
        directors, actors = self.media.get_tmdbinfo_directors_actors(tmdbinfo.get("credits"))
        for director in directors:
            xdirector = add_node(doc, root, "director", director.get("name") or "")
            xdirector.setAttribute("tmdbid", str(director.get("id") or ""))
        # 演员
        for actor in actors:
            xactor = add_node(doc, root, "actor")
            add_node(doc, xactor, "name", actor.get("name") or "")
            add_node(doc, xactor, "type", "Actor")
            add_node(doc, xactor, "tmdbid", actor.get("id") or "")
        # 风格
        genres = tmdbinfo.get("genres") or []
        for genre in genres:
            add_node(doc, root, "genre", genre.get("name") or "")
        # 评分
        add_node(doc, root, "rating", tmdbinfo.get("vote_average") or "0")
        return doc

    def gen_movie_nfo_file(self, tmdbinfo: dict, out_path, file_name):
        """
        生成电影的NFO描述文件
        :param tmdbinfo: TMDB元数据
        :param out_path: 电影根目录
        :param file_name: 电影文件名，不含后缀
        """
        # 开始生成XML
        log.info("【NFO】正在生成电影NFO文件：%s" % file_name)
        doc = minidom.Document()
        root = add_node(doc, doc, "movie")
        # 公共部分
        doc = self.__gen_common_nfo(tmdbinfo, doc, root)
        # 标题
        add_node(doc, root, "title", tmdbinfo.get("title") or "")
        add_node(doc, root, "originaltitle", tmdbinfo.get("original_title") or "")
        # 发布日期
        add_node(doc, root, "premiered", tmdbinfo.get("release_date") or "")
        # 年份
        add_node(doc, root, "year", tmdbinfo.get("release_date")[:4] if tmdbinfo.get("release_date") else "")
        # 保存
        self.__save_nfo(doc, os.path.join(out_path, "%s.nfo" % file_name))

    def gen_tv_nfo_file(self, tmdbinfo: dict, out_path):
        """
        生成电视剧的NFO描述文件
        :param tmdbinfo: TMDB元数据
        :param out_path: 电视剧根目录
        """
        # 开始生成XML
        log.info("【NFO】正在生成电视剧NFO文件：%s" % out_path)
        doc = minidom.Document()
        root = add_node(doc, doc, "tvshow")
        # 公共部分
        doc = self.__gen_common_nfo(tmdbinfo, doc, root)
        # 标题
        add_node(doc, root, "title", tmdbinfo.get("name") or "")
        add_node(doc, root, "originaltitle", tmdbinfo.get("original_name") or "")
        # 发布日期
        add_node(doc, root, "premiered", tmdbinfo.get("first_air_date") or "")
        # 年份
        add_node(doc, root, "year", tmdbinfo.get("first_air_date")[:4] if tmdbinfo.get("first_air_date") else "")
        add_node(doc, root, "season", "-1")
        add_node(doc, root, "episode", "-1")
        # 保存
        self.__save_nfo(doc, os.path.join(out_path, "tvshow.nfo"))

    def gen_tv_season_nfo_file(self, tmdbinfo: dict, season, out_path):
        """
        生成电视剧季的NFO描述文件
        :param tmdbinfo: TMDB季媒体信息
        :param season: 季号
        :param out_path: 电视剧季的目录
        """
        log.info("【NFO】正在生成季NFO文件：%s" % out_path)
        doc = minidom.Document()
        root = add_node(doc, doc, "season")
        # 添加时间
        add_node(doc, root, "dateadded", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
        # 简介
        xplot = add_node(doc, root, "plot")
        xplot.appendChild(doc.createCDATASection(tmdbinfo.get("overview") or ""))
        xoutline = add_node(doc, root, "outline")
        xoutline.appendChild(doc.createCDATASection(tmdbinfo.get("overview") or ""))
        # 标题
        add_node(doc, root, "title", "季 %s" % season)
        # 发行日期
        add_node(doc, root, "premiered", tmdbinfo.get("air_date") or "")
        add_node(doc, root, "releasedate", tmdbinfo.get("air_date") or "")
        # 发行年份
        add_node(doc, root, "year", tmdbinfo.get("air_date")[:4] if tmdbinfo.get("air_date") else "")
        # seasonnumber
        add_node(doc, root, "seasonnumber", season)
        # 保存
        self.__save_nfo(doc, os.path.join(out_path, "season.nfo"))

    def gen_tv_episode_nfo_file(self, tmdbinfo: dict, season: int, episode: int, out_path, file_name):
        """
        生成电视剧集的NFO描述文件
        :param tmdbinfo: TMDB元数据
        :param season: 季号
        :param episode: 集号
        :param out_path: 电视剧季的目录
        :param file_name: 电视剧文件名，不含后缀
        """
        # 开始生成集的信息
        log.info("【NFO】正在生成剧集NFO文件：%s" % file_name)
        doc = minidom.Document()
        root = add_node(doc, doc, "episodedetails")
        # 添加时间
        add_node(doc, root, "dateadded", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
        # TMDBID
        uniqueid = add_node(doc, root, "uniqueid", tmdbinfo.get("id") or "")
        uniqueid.setAttribute("type", "tmdb")
        uniqueid.setAttribute("default", "true")
        # tmdbid
        add_node(doc, root, "tmdbid", tmdbinfo.get("id") or "")
        # 集的信息
        episode_detail = {}
        for episode_info in tmdbinfo.get("episodes") or []:
            if int(episode_info.get("episode_number")) == int(episode):
                episode_detail = episode_info
        if not episode_detail:
            return
        # 标题
        add_node(doc, root, "title", episode_detail.get("name") or "第 %s 集" % episode)
        # 简介
        xplot = add_node(doc, root, "plot")
        xplot.appendChild(doc.createCDATASection(episode_detail.get("overview") or ""))
        xoutline = add_node(doc, root, "outline")
        xoutline.appendChild(doc.createCDATASection(episode_detail.get("overview") or ""))
        # 导演
        directors = episode_detail.get("crew") or []
        for director in directors:
            if director.get("known_for_department") == "Directing":
                xdirector = add_node(doc, root, "director", director.get("name") or "")
                xdirector.setAttribute("tmdbid", str(director.get("id") or ""))
        # 演员
        actors = episode_detail.get("guest_stars") or []
        for actor in actors:
            if actor.get("known_for_department") == "Acting":
                xactor = add_node(doc, root, "actor")
                add_node(doc, xactor, "name", actor.get("name") or "")
                add_node(doc, xactor, "type", "Actor")
                add_node(doc, xactor, "tmdbid", actor.get("id") or "")
        # 发布日期
        add_node(doc, root, "aired", episode_detail.get("air_date") or "")
        # 年份
        add_node(doc, root, "year", episode_detail.get("air_date")[:4] if episode_detail.get("air_date") else "")
        # 季
        add_node(doc, root, "season", season)
        # 集
        add_node(doc, root, "episode", episode)
        # 评分
        add_node(doc, root, "rating", episode_detail.get("vote_average") or "0")
        self.__save_nfo(doc, os.path.join(out_path, os.path.join(out_path, "%s.nfo" % file_name)))

    @staticmethod
    def __save_image(url, out_path, itype="poster"):
        """
        下载poster.jpg并保存
        """
        if not url or not out_path:
            return
        if os.path.exists(os.path.join(out_path, "%s.%s" % (itype, str(url).split('.')[-1]))):
            return
        try:
            log.info("【NFO】正在保存 %s 图片：%s" % (itype, out_path))
            r = RequestUtils().get_res(url)
            if r:
                with open(file=os.path.join(out_path, "%s.%s" % (itype, str(url).split('.')[-1])),
                          mode="wb") as img:
                    img.write(r.content)
        except Exception as err:
            print(str(err))

    @staticmethod
    def __save_nfo(doc, out_file):
        xml_str = doc.toprettyxml(indent="  ", encoding="utf-8")
        with open(out_file, "wb") as xml_file:
            xml_file.write(xml_str)

    def gen_nfo_files(self, media: MetaBase, dir_path, file_name):
        try:
            # 电影
            if media.type == MediaType.MOVIE:
                # 已存在时不处理
                if os.path.exists(os.path.join(dir_path, "movie.nfo")):
                    return
                if os.path.exists(os.path.join(dir_path, "%s.nfo" % file_name)):
                    return
                # 查询TMDB信息
                tmdbinfo = self.media.get_tmdb_info(mtype=MediaType.MOVIE, tmdbid=media.tmdb_id)
                # 生成电影描述文件
                self.gen_movie_nfo_file(tmdbinfo, dir_path, file_name)
                # 保存海报
                if media.get_poster_image():
                    self.__save_image(media.get_poster_image(), dir_path)
                fanart_image = media.get_fanart_image()
                if fanart_image:
                    self.__save_image(fanart_image, dir_path, "fanart")
            # 电视剧
            else:
                # 处理根目录
                if not os.path.exists(os.path.join(dir_path, "tvshow.nfo")):
                    # 查询TMDB信息
                    tmdbinfo = self.media.get_tmdb_info(mtype=MediaType.TV, tmdbid=media.tmdb_id)
                    # 根目录描述文件
                    self.gen_tv_nfo_file(tmdbinfo, os.path.dirname(dir_path))
                    # 根目录海报
                    if media.get_poster_image():
                        self.__save_image(media.get_poster_image(), os.path.dirname(dir_path))
                    fanart_image = media.get_fanart_image()
                    if fanart_image:
                        self.__save_image(fanart_image, os.path.dirname(dir_path), "fanart")
                # 处理集
                if not os.path.exists(os.path.join(dir_path, "%s.nfo" % file_name)):
                    # 查询TMDB信息
                    tmdbinfo = self.media.get_tmdb_tv_season_detail(tmdbid=media.tmdb_id, season=int(media.get_season_seq()))
                    self.gen_tv_episode_nfo_file(tmdbinfo, int(media.get_season_seq()), int(media.get_episode_seq()), dir_path, file_name)
                    # 处理季
                    if not os.path.exists(os.path.join(dir_path, "season.nfo")):
                        # 生成季的信息
                        self.gen_tv_season_nfo_file(tmdbinfo, int(media.get_season_seq()), dir_path)
                        # 季的海报
                        self.__save_image("https://image.tmdb.org/t/p/w500%s" % tmdbinfo.get("poster_path"),
                                          os.path.dirname(dir_path),
                                          "season%s-poster" % media.get_season_seq().rjust(2, '0'))
        except Exception as e:
            print(str(e))
