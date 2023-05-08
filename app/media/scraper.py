import os.path
import time
from xml.dom import minidom

from requests.exceptions import RequestException

import log
from app.conf import SystemConfig, ModuleConf
from app.helper import FfmpegHelper
from app.media.douban import DouBan
from app.media.meta import MetaInfo
from app.utils.commons import retry
from config import Config, RMT_MEDIAEXT
from app.utils import DomUtils, RequestUtils, ExceptionUtils, NfoReader, SystemUtils
from app.utils.types import MediaType, SystemConfigKey, RmtMode
from app.media import Media


class Scraper:
    media = None
    _scraper_flag = False
    _scraper_nfo = {}
    _scraper_pic = {}
    _rmt_mode = None
    _temp_path = None

    def __init__(self):
        self.media = Media()
        self.douban = DouBan()
        self._scraper_flag = Config().get_config('media').get("nfo_poster")
        scraper_conf = SystemConfig().get(SystemConfigKey.UserScraperConf)
        if scraper_conf:
            self._scraper_nfo = scraper_conf.get('scraper_nfo') or {}
            self._scraper_pic = scraper_conf.get('scraper_pic') or {}
        self._rmt_mode = None
        self._temp_path = os.path.join(Config().get_temp_path(), "scraper")
        if not os.path.exists(self._temp_path):
            os.makedirs(self._temp_path)

    def folder_scraper(self, path, exclude_path=None, mode=None):
        """
        刮削指定文件夹或文件
        :param path: 文件夹或文件路径
        :param exclude_path: 排除路径
        :param mode: 刮削模式，可选值：force_nfo, force_all
        :return:
        """
        # 模式
        force_nfo = True if mode in ["force_nfo", "force_all"] else False
        force_pic = True if mode in ["force_all"] else False
        # 每个媒体库下的所有文件
        for file in self.__get_library_files(path, exclude_path):
            if not file:
                continue
            log.info(f"【Scraper】开始刮削媒体库文件：{file} ...")
            # 识别媒体文件
            meta_info = MetaInfo(os.path.basename(file))
            # 优先读取本地文件
            tmdbid = None
            if meta_info.type == MediaType.MOVIE:
                # 电影
                movie_nfo = os.path.join(os.path.dirname(file), "movie.nfo")
                if os.path.exists(movie_nfo):
                    tmdbid = self.__get_tmdbid_from_nfo(movie_nfo)
                file_nfo = os.path.join(os.path.splitext(file)[0] + ".nfo")
                if not tmdbid and os.path.exists(file_nfo):
                    tmdbid = self.__get_tmdbid_from_nfo(file_nfo)
            else:
                # 电视剧
                tv_nfo = os.path.join(os.path.dirname(os.path.dirname(file)), "tvshow.nfo")
                if os.path.exists(tv_nfo):
                    tmdbid = self.__get_tmdbid_from_nfo(tv_nfo)
            if tmdbid and not force_nfo:
                log.info(f"【Scraper】读取到本地nfo文件的tmdbid：{tmdbid}")
                meta_info.set_tmdb_info(self.media.get_tmdb_info(mtype=meta_info.type,
                                                                 tmdbid=tmdbid,
                                                                 append_to_response='all'))
                media_info = meta_info
            else:
                medias = self.media.get_media_info_on_files(file_list=[file],
                                                            append_to_response="all")
                if not medias:
                    continue
                media_info = None
                for _, media in medias.items():
                    media_info = media
                    break
            if not media_info or not media_info.tmdb_info:
                continue
            self.gen_scraper_files(media=media_info,
                                   dir_path=os.path.dirname(file),
                                   file_name=os.path.splitext(os.path.basename(file))[0],
                                   file_ext=os.path.splitext(file)[-1],
                                   force=True,
                                   force_nfo=force_nfo,
                                   force_pic=force_pic)
            log.info(f"【Scraper】{file} 刮削完成")

    @staticmethod
    def __get_library_files(in_path, exclude_path=None):
        """
        获取媒体库文件列表
        """
        if not os.path.isdir(in_path):
            yield in_path
            return

        for root, dirs, files in os.walk(in_path):
            if exclude_path and any(os.path.abspath(root).startswith(os.path.abspath(path))
                                    for path in exclude_path.split(",")):
                continue

            for file in files:
                cur_path = os.path.join(root, file)
                # 检查后缀
                if os.path.splitext(file)[-1].lower() in RMT_MEDIAEXT:
                    yield cur_path

    @staticmethod
    def __get_tmdbid_from_nfo(file_path):
        """
        从nfo文件中获取信息
        :param file_path:
        :return: tmdbid
        """
        if not file_path:
            return None
        xpaths = [
            "uniqueid[@type='Tmdb']",
            "uniqueid[@type='tmdb']",
            "uniqueid[@type='TMDB']",
            "tmdbid"
        ]
        reader = NfoReader(file_path)
        for xpath in xpaths:
            try:
                tmdbid = reader.get_element_value(xpath)
                if tmdbid:
                    return tmdbid
            except Exception as err:
                print(str(err))
        return None

    def __gen_common_nfo(self,
                         tmdbinfo: dict,
                         doubaninfo: dict,
                         doc,
                         root,
                         scraper_nfo: dict):
        if scraper_nfo.get("basic"):
            # 添加时间
            DomUtils.add_node(doc, root, "dateadded", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
            # TMDB
            DomUtils.add_node(doc, root, "tmdbid", tmdbinfo.get("id") or "")
            uniqueid_tmdb = DomUtils.add_node(doc, root, "uniqueid", tmdbinfo.get("id") or "")
            uniqueid_tmdb.setAttribute("type", "tmdb")
            uniqueid_tmdb.setAttribute("default", "true")
            # TVDB IMDB
            if tmdbinfo.get("external_ids"):
                tvdbid = tmdbinfo.get("external_ids", {}).get("tvdb_id", 0)
                if tvdbid:
                    DomUtils.add_node(doc, root, "tvdbid", tvdbid)
                    uniqueid_tvdb = DomUtils.add_node(doc, root, "uniqueid", tvdbid)
                    uniqueid_tvdb.setAttribute("type", "tvdb")
                imdbid = tmdbinfo.get("external_ids", {}).get("imdb_id", "")
                if imdbid:
                    DomUtils.add_node(doc, root, "imdbid", imdbid)
                    uniqueid_imdb = DomUtils.add_node(doc, root, "uniqueid", imdbid)
                    uniqueid_imdb.setAttribute("type", "imdb")
                    uniqueid_imdb.setAttribute("default", "true")
                    uniqueid_tmdb.setAttribute("default", "false")

            # 简介
            xplot = DomUtils.add_node(doc, root, "plot")
            xplot.appendChild(doc.createCDATASection(tmdbinfo.get("overview") or ""))
            xoutline = DomUtils.add_node(doc, root, "outline")
            xoutline.appendChild(doc.createCDATASection(tmdbinfo.get("overview") or ""))
        if scraper_nfo.get("credits"):
            # 导演
            directors, actors = self.media.get_tmdb_directors_actors(tmdbinfo=tmdbinfo)
            if scraper_nfo.get("credits_chinese"):
                directors, actors = self.__gen_people_chinese_info(directors, actors, doubaninfo)
            for director in directors:
                xdirector = DomUtils.add_node(doc, root, "director", director.get("name") or "")
                xdirector.setAttribute("tmdbid", str(director.get("id") or ""))
            # 演员
            for actor in actors:
                xactor = DomUtils.add_node(doc, root, "actor")
                DomUtils.add_node(doc, xactor, "name", actor.get("name") or "")
                DomUtils.add_node(doc, xactor, "type", "Actor")
                DomUtils.add_node(doc, xactor, "role", actor.get("role") or "")
                DomUtils.add_node(doc, xactor, "order", actor.get("order") if actor.get("order") is not None else "")
                DomUtils.add_node(doc, xactor, "tmdbid", actor.get("id") or "")
                DomUtils.add_node(doc, xactor, "thumb", actor.get('image'))
                DomUtils.add_node(doc, xactor, "profile", actor.get('profile'))
        if scraper_nfo.get("basic"):
            # 风格
            genres = tmdbinfo.get("genres") or []
            for genre in genres:
                DomUtils.add_node(doc, root, "genre", genre.get("name") or "")
            # 评分
            DomUtils.add_node(doc, root, "rating", tmdbinfo.get("vote_average") or "0")
        return doc

    def __gen_movie_nfo_file(self,
                             tmdbinfo: dict,
                             doubaninfo: dict,
                             scraper_movie_nfo: dict,
                             out_path,
                             file_name):
        """
        生成电影的NFO描述文件
        :param tmdbinfo: TMDB元数据
        :param doubaninfo: 豆瓣元数据
        :param scraper_movie_nfo: 刮削配置
        :param out_path: 电影根目录
        :param file_name: 电影文件名，不含后缀
        """
        # 开始生成XML
        log.info("【Scraper】正在生成电影NFO文件：%s" % file_name)
        doc = minidom.Document()
        root = DomUtils.add_node(doc, doc, "movie")
        # 公共部分
        doc = self.__gen_common_nfo(tmdbinfo=tmdbinfo,
                                    doubaninfo=doubaninfo,
                                    doc=doc,
                                    root=root,
                                    scraper_nfo=scraper_movie_nfo)
        # 基础部分
        if scraper_movie_nfo.get("basic"):
            # 标题
            DomUtils.add_node(doc, root, "title", tmdbinfo.get("title") or "")
            DomUtils.add_node(doc, root, "originaltitle", tmdbinfo.get("original_title") or "")
            # 发布日期
            DomUtils.add_node(doc, root, "premiered", tmdbinfo.get("release_date") or "")
            # 年份
            DomUtils.add_node(doc, root, "year",
                              tmdbinfo.get("release_date")[:4] if tmdbinfo.get("release_date") else "")
        # 保存
        self.__save_nfo(doc, os.path.join(out_path, "%s.nfo" % file_name))

    def __gen_tv_nfo_file(self,
                          tmdbinfo: dict,
                          doubaninfo: dict,
                          scraper_tv_nfo: dict,
                          out_path):
        """
        生成电视剧的NFO描述文件
        :param tmdbinfo: TMDB元数据
        :param doubaninfo: 豆瓣元数据
        :param scraper_tv_nfo: 刮削配置
        :param out_path: 电视剧根目录
        """
        # 开始生成XML
        log.info("【Scraper】正在生成电视剧NFO文件：%s" % out_path)
        doc = minidom.Document()
        root = DomUtils.add_node(doc, doc, "tvshow")
        # 公共部分
        doc = self.__gen_common_nfo(tmdbinfo=tmdbinfo,
                                    doubaninfo=doubaninfo,
                                    doc=doc,
                                    root=root,
                                    scraper_nfo=scraper_tv_nfo)
        if scraper_tv_nfo.get("basic"):
            # 标题
            DomUtils.add_node(doc, root, "title", tmdbinfo.get("name") or "")
            DomUtils.add_node(doc, root, "originaltitle", tmdbinfo.get("original_name") or "")
            # 发布日期
            DomUtils.add_node(doc, root, "premiered", tmdbinfo.get("first_air_date") or "")
            # 年份
            DomUtils.add_node(doc, root, "year",
                              tmdbinfo.get("first_air_date")[:4] if tmdbinfo.get("first_air_date") else "")
            DomUtils.add_node(doc, root, "season", "-1")
            DomUtils.add_node(doc, root, "episode", "-1")
        # 保存
        self.__save_nfo(doc, os.path.join(out_path, "tvshow.nfo"))

    def __gen_tv_season_nfo_file(self, seasoninfo: dict, season, out_path):
        """
        生成电视剧季的NFO描述文件
        :param seasoninfo: TMDB季媒体信息
        :param season: 季号
        :param out_path: 电视剧季的目录
        """
        log.info("【Scraper】正在生成季NFO文件：%s" % out_path)
        doc = minidom.Document()
        root = DomUtils.add_node(doc, doc, "season")
        # 添加时间
        DomUtils.add_node(doc, root, "dateadded", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
        # 简介
        xplot = DomUtils.add_node(doc, root, "plot")
        xplot.appendChild(doc.createCDATASection(seasoninfo.get("overview") or ""))
        xoutline = DomUtils.add_node(doc, root, "outline")
        xoutline.appendChild(doc.createCDATASection(seasoninfo.get("overview") or ""))
        # 标题
        DomUtils.add_node(doc, root, "title", "季 %s" % season)
        # 发行日期
        DomUtils.add_node(doc, root, "premiered", seasoninfo.get("air_date") or "")
        DomUtils.add_node(doc, root, "releasedate", seasoninfo.get("air_date") or "")
        # 发行年份
        DomUtils.add_node(doc, root, "year", seasoninfo.get("air_date")[:4] if seasoninfo.get("air_date") else "")
        # seasonnumber
        DomUtils.add_node(doc, root, "seasonnumber", season)
        # 保存
        self.__save_nfo(doc, os.path.join(out_path, "season.nfo"))

    def __gen_tv_episode_nfo_file(self,
                                  seasoninfo: dict,
                                  scraper_tv_nfo,
                                  season: int,
                                  episode: int,
                                  out_path,
                                  file_name):
        """
        生成电视剧集的NFO描述文件
        :param seasoninfo: TMDB元数据
        :param scraper_tv_nfo: 刮削配置
        :param season: 季号
        :param episode: 集号
        :param out_path: 电视剧季的目录
        :param file_name: 电视剧文件名，不含后缀
        """
        # 开始生成集的信息
        log.info("【Scraper】正在生成剧集NFO文件：%s" % file_name)
        # 集的信息
        episode_detail = {}
        for episode_info in seasoninfo.get("episodes") or []:
            if int(episode_info.get("episode_number")) == int(episode):
                episode_detail = episode_info
        if not episode_detail:
            return
        doc = minidom.Document()
        root = DomUtils.add_node(doc, doc, "episodedetails")
        if scraper_tv_nfo.get("episode_basic"):
            # 添加时间
            DomUtils.add_node(doc, root, "dateadded", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
            # TMDBID
            uniqueid = DomUtils.add_node(doc, root, "uniqueid", episode_detail.get("id") or "")
            uniqueid.setAttribute("type", "tmdb")
            uniqueid.setAttribute("default", "true")
            # tmdbid
            DomUtils.add_node(doc, root, "tmdbid", episode_detail.get("id") or "")
            # 标题
            DomUtils.add_node(doc, root, "title", episode_detail.get("name") or "第 %s 集" % episode)
            # 简介
            xplot = DomUtils.add_node(doc, root, "plot")
            xplot.appendChild(doc.createCDATASection(episode_detail.get("overview") or ""))
            xoutline = DomUtils.add_node(doc, root, "outline")
            xoutline.appendChild(doc.createCDATASection(episode_detail.get("overview") or ""))
            # 发布日期
            DomUtils.add_node(doc, root, "aired", episode_detail.get("air_date") or "")
            # 年份
            DomUtils.add_node(doc, root, "year",
                              episode_detail.get("air_date")[:4] if episode_detail.get("air_date") else "")
            # 季
            DomUtils.add_node(doc, root, "season", season)
            # 集
            DomUtils.add_node(doc, root, "episode", episode)
            # 评分
            DomUtils.add_node(doc, root, "rating", episode_detail.get("vote_average") or "0")
        if scraper_tv_nfo.get("episode_credits"):
            # 导演
            directors = episode_detail.get("crew") or []
            for director in directors:
                if director.get("known_for_department") == "Directing":
                    xdirector = DomUtils.add_node(doc, root, "director", director.get("name") or "")
                    xdirector.setAttribute("tmdbid", str(director.get("id") or ""))
            # 演员
            actors = episode_detail.get("guest_stars") or []
            for actor in actors:
                if actor.get("known_for_department") == "Acting":
                    xactor = DomUtils.add_node(doc, root, "actor")
                    DomUtils.add_node(doc, xactor, "name", actor.get("name") or "")
                    DomUtils.add_node(doc, xactor, "type", "Actor")
                    DomUtils.add_node(doc, xactor, "tmdbid", actor.get("id") or "")
        # 保存文件
        self.__save_nfo(doc, os.path.join(out_path, os.path.join(out_path, "%s.nfo" % file_name)))

    def __save_remove_file(self, out_file, content):
        """
        保存文件到远端
        """
        temp_file = os.path.join(self._temp_path, out_file[1:])
        temp_file_dir = os.path.dirname(temp_file)
        if not os.path.exists(temp_file_dir):
            os.makedirs(temp_file_dir)
        with open(temp_file, "wb") as f:
            f.write(content)
        if self._rmt_mode in [RmtMode.RCLONE, RmtMode.RCLONECOPY]:
            SystemUtils.rclone_move(temp_file, out_file)
        elif self._rmt_mode in [RmtMode.MINIO, RmtMode.MINIOCOPY]:
            SystemUtils.minio_move(temp_file, out_file)
        else:
            SystemUtils.move(temp_file, out_file)

    @retry(RequestException, logger=log)
    def __save_image(self, url, out_path, itype='', force=False):
        """
        下载poster.jpg并保存
        """
        if not url or not out_path:
            return
        if itype:
            image_path = os.path.join(out_path, "%s.%s" % (itype, str(url).split('.')[-1]))
        else:
            image_path = out_path
        if not force and os.path.exists(image_path):
            return
        try:
            log.info(f"【Scraper】正在下载{itype}图片：{url} ...")
            r = RequestUtils().get_res(url=url, raise_exception=True)
            if r:
                # 下载到temp目录，远程则先存到temp再远程移动，本地则直接保存
                if self._rmt_mode in ModuleConf.REMOTE_RMT_MODES:
                    self.__save_remove_file(image_path, r.content)
                else:
                    with open(file=image_path, mode="wb") as img:
                        img.write(r.content)
                log.info(f"【Scraper】{itype}图片已保存：{image_path}")
            else:
                log.info(f"【Scraper】{itype}图片下载失败，请检查网络连通性")
        except RequestException:
            raise RequestException
        except Exception as err:
            ExceptionUtils.exception_traceback(err)

    def __save_nfo(self, doc, out_file):
        log.info("【Scraper】正在保存NFO文件：%s" % out_file)
        xml_str = doc.toprettyxml(indent="  ", encoding="utf-8")
        # 下载到temp目录，远程则先存到temp再远程移动，本地则直接保存
        if self._rmt_mode in ModuleConf.REMOTE_RMT_MODES:
            self.__save_remove_file(out_file, xml_str)
        else:
            with open(out_file, "wb") as xml_file:
                xml_file.write(xml_str)
        log.info("【Scraper】NFO文件已保存：%s" % out_file)

    def gen_scraper_files(self,
                          media,
                          dir_path,
                          file_name,
                          file_ext,
                          force=False,
                          force_nfo=False,
                          force_pic=False,
                          rmt_mode=None):
        """
        刮削元数据入口
        :param media: 已识别的媒体信息
        :param dir_path: 文件路径
        :param file_name: 文件名，不含后缀
        :param file_ext: 文件后缀
        :param force: 是否强制刮削
        :param force_nfo: 是否强制刮削NFO
        :param force_pic: 是否强制刮削图片
        :param rmt_mode: 转移方式
        """
        if not force and not self._scraper_flag:
            return
        if not self._scraper_nfo and not self._scraper_pic:
            return

        if not self._scraper_nfo:
            self._scraper_nfo = {}
        if not self._scraper_pic:
            self._scraper_pic = {}

        self._rmt_mode = rmt_mode

        try:
            # 电影
            if media.type == MediaType.MOVIE:
                scraper_movie_nfo = self._scraper_nfo.get("movie")
                scraper_movie_pic = self._scraper_pic.get("movie")
                #  movie nfo
                if scraper_movie_nfo.get("basic") or scraper_movie_nfo.get("credits"):
                    # 已存在时不处理
                    if force_nfo \
                            or (not os.path.exists(os.path.join(dir_path, "movie.nfo"))
                                and not os.path.exists(os.path.join(dir_path, "%s.nfo" % file_name))):
                        # 查询Douban信息
                        if scraper_movie_nfo.get("credits") and scraper_movie_nfo.get("credits_chinese"):
                            doubaninfo = self.douban.get_douban_info(media)
                        else:
                            doubaninfo = None
                        #  生成电影描述文件
                        self.__gen_movie_nfo_file(tmdbinfo=media.tmdb_info,
                                                  doubaninfo=doubaninfo,
                                                  scraper_movie_nfo=scraper_movie_nfo,
                                                  out_path=dir_path,
                                                  file_name=file_name)
                # poster
                if scraper_movie_pic.get("poster"):
                    poster_image = media.get_poster_image(original=True)
                    if poster_image:
                        self.__save_image(poster_image, dir_path, "poster", force_pic)
                # backdrop
                if scraper_movie_pic.get("backdrop"):
                    backdrop_image = media.get_backdrop_image(default=False, original=True)
                    if backdrop_image:
                        self.__save_image(backdrop_image, dir_path, "fanart", force_pic)
                # background
                if scraper_movie_pic.get("background"):
                    background_image = media.fanart.get_background(media_type=media.type, queryid=media.tmdb_id)
                    if background_image:
                        self.__save_image(background_image, dir_path, "background", force_pic)
                # logo
                if scraper_movie_pic.get("logo"):
                    logo_image = media.fanart.get_logo(media_type=media.type, queryid=media.tmdb_id)
                    if logo_image:
                        self.__save_image(logo_image, dir_path, "logo", force_pic)
                # disc
                if scraper_movie_pic.get("disc"):
                    disc_image = media.fanart.get_disc(media_type=media.type, queryid=media.tmdb_id)
                    if disc_image:
                        self.__save_image(disc_image, dir_path, "disc", force_pic)
                # banner
                if scraper_movie_pic.get("banner"):
                    banner_image = media.fanart.get_banner(media_type=media.type, queryid=media.tmdb_id)
                    if banner_image:
                        self.__save_image(banner_image, dir_path, "banner", force_pic)
                # thumb
                if scraper_movie_pic.get("thumb"):
                    thumb_image = media.fanart.get_thumb(media_type=media.type, queryid=media.tmdb_id)
                    if thumb_image:
                        self.__save_image(thumb_image, dir_path, "thumb", force_pic)
            # 电视剧
            else:
                scraper_tv_nfo = self._scraper_nfo.get("tv")
                scraper_tv_pic = self._scraper_pic.get("tv")
                # tv nfo
                if force_nfo \
                        or not os.path.exists(os.path.join(os.path.dirname(dir_path), "tvshow.nfo")):
                    if scraper_tv_nfo.get("basic") or scraper_tv_nfo.get("credits"):
                        # 查询Douban信息
                        if scraper_tv_nfo.get("credits") and scraper_tv_nfo.get("credits_chinese"):
                            doubaninfo = self.douban.get_douban_info(media)
                        else:
                            doubaninfo = None
                        # 根目录描述文件
                        self.__gen_tv_nfo_file(tmdbinfo=media.tmdb_info,
                                               doubaninfo=doubaninfo,
                                               scraper_tv_nfo=scraper_tv_nfo,
                                               out_path=os.path.dirname(dir_path))
                # poster
                if scraper_tv_pic.get("poster"):
                    poster_image = media.get_poster_image(original=True)
                    if poster_image:
                        self.__save_image(poster_image, os.path.dirname(dir_path), "poster", force_pic)
                # backdrop
                if scraper_tv_pic.get("backdrop"):
                    backdrop_image = media.get_backdrop_image(default=False, original=True)
                    if backdrop_image:
                        self.__save_image(backdrop_image, os.path.dirname(dir_path), "fanart", force_pic)
                # background
                if scraper_tv_pic.get("background"):
                    background_image = media.fanart.get_background(media_type=media.type, queryid=media.tvdb_id)
                    if background_image:
                        self.__save_image(background_image, os.path.dirname(dir_path), "background", force_pic)
                # logo
                if scraper_tv_pic.get("logo"):
                    logo_image = media.fanart.get_logo(media_type=media.type, queryid=media.tvdb_id)
                    if logo_image:
                        self.__save_image(logo_image, os.path.dirname(dir_path), "logo", force_pic)
                # clearart
                if scraper_tv_pic.get("clearart"):
                    clearart_image = media.fanart.get_disc(media_type=media.type, queryid=media.tvdb_id)
                    if clearart_image:
                        self.__save_image(clearart_image, os.path.dirname(dir_path), "clearart", force_pic)
                # banner
                if scraper_tv_pic.get("banner"):
                    banner_image = media.fanart.get_banner(media_type=media.type, queryid=media.tvdb_id)
                    if banner_image:
                        self.__save_image(banner_image, os.path.dirname(dir_path), "banner", force_pic)
                # thumb
                if scraper_tv_pic.get("thumb"):
                    thumb_image = media.fanart.get_thumb(media_type=media.type, queryid=media.tvdb_id)
                    if thumb_image:
                        self.__save_image(thumb_image, os.path.dirname(dir_path), "thumb", force_pic)
                # season nfo
                if scraper_tv_nfo.get("season_basic"):
                    if force_nfo \
                            or not os.path.exists(os.path.join(dir_path, "season.nfo")):
                        # season nfo
                        seasoninfo = self.media.get_tmdb_tv_season_detail(tmdbid=media.tmdb_id,
                                                                          season=int(media.get_season_seq()))
                        if seasoninfo:
                            self.__gen_tv_season_nfo_file(seasoninfo=seasoninfo,
                                                          season=int(media.get_season_seq()),
                                                          out_path=dir_path)
                # episode nfo
                if scraper_tv_nfo.get("episode_basic") \
                        or scraper_tv_nfo.get("episode_credits"):
                    if force_nfo \
                            or not os.path.exists(os.path.join(dir_path, "%s.nfo" % file_name)):
                        seasoninfo = self.media.get_tmdb_tv_season_detail(tmdbid=media.tmdb_id,
                                                                          season=int(media.get_season_seq()))
                        if seasoninfo:
                            self.__gen_tv_episode_nfo_file(seasoninfo=seasoninfo,
                                                           scraper_tv_nfo=scraper_tv_nfo,
                                                           season=int(media.get_season_seq()),
                                                           episode=int(media.get_episode_seq()),
                                                           out_path=dir_path,
                                                           file_name=file_name)
                # season poster
                if scraper_tv_pic.get("season_poster"):
                    season_poster = "season%s-poster" % media.get_season_seq().rjust(2, '0')
                    seasonposter = media.fanart.get_seasonposter(media_type=media.type,
                                                                 queryid=media.tvdb_id,
                                                                 season=media.get_season_seq())
                    if seasonposter:
                        self.__save_image(seasonposter,
                                          os.path.dirname(dir_path),
                                          season_poster,
                                          force_pic)
                    else:
                        seasoninfo = self.media.get_tmdb_tv_season_detail(tmdbid=media.tmdb_id,
                                                                          season=int(media.get_season_seq()))
                        if seasoninfo:
                            self.__save_image(Config().get_tmdbimage_url(seasoninfo.get("poster_path"),
                                                                         prefix="original"),
                                              os.path.dirname(dir_path),
                                              season_poster,
                                              force_pic)
                # season banner
                if scraper_tv_pic.get("season_banner"):
                    seasonbanner = media.fanart.get_seasonbanner(media_type=media.type,
                                                                 queryid=media.tvdb_id,
                                                                 season=media.get_season_seq())
                    if seasonbanner:
                        self.__save_image(seasonbanner,
                                          os.path.dirname(dir_path),
                                          "season%s-banner" % media.get_season_seq().rjust(2, '0'),
                                          force_pic)
                # season thumb
                if scraper_tv_pic.get("season_thumb"):
                    seasonthumb = media.fanart.get_seasonthumb(media_type=media.type,
                                                               queryid=media.tvdb_id,
                                                               season=media.get_season_seq())
                    if seasonthumb:
                        self.__save_image(seasonthumb,
                                          os.path.dirname(dir_path),
                                          "season%s-landscape" % media.get_season_seq().rjust(2, '0'),
                                          force_pic)
                # episode thumb
                if scraper_tv_pic.get("episode_thumb"):
                    episode_thumb = os.path.join(dir_path, file_name + "-thumb.jpg")
                    if not force_pic \
                            and not os.path.exists(episode_thumb):
                        # 优先从TMDB查询
                        episode_image = self.media.get_episode_images(tv_id=media.tmdb_id,
                                                                      season_id=media.get_season_seq(),
                                                                      episode_id=media.get_episode_seq(),
                                                                      orginal=True)
                        if episode_image:
                            self.__save_image(episode_image, episode_thumb, '', force_pic)
                        else:
                            # 开启ffmpeg，则从视频文件生成缩略图
                            if scraper_tv_pic.get("episode_thumb_ffmpeg"):
                                video_path = os.path.join(dir_path, file_name + file_ext)
                                log.info(f"【Scraper】正在生成缩略图：{video_path} ...")
                                FfmpegHelper().get_thumb_image_from_video(video_path=video_path,
                                                                          image_path=episode_thumb)
                                log.info(f"【Scraper】缩略图生成完成：{episode_thumb}")

        except Exception as e:
            ExceptionUtils.exception_traceback(e)

    def __gen_people_chinese_info(self, directors, actors, doubaninfo):
        """
        匹配豆瓣演职人员中文名
        """
        if doubaninfo:
            # 导演
            if directors:
                douban_directors = doubaninfo.get("directors") or []
                # douban英文名姓和名分开匹配，（豆瓣中名前姓后，TMDB中不确定）
                for director in douban_directors:
                    if director.get("latin_name"):
                        director["names"] = director.get("latin_name", "").lower().split(" ")
                    else:
                        director["names"] = director.get("name", "").lower().split(" ")
                for director in directors:
                    douban_director = self.__match_people_in_douban(director, douban_directors)
                    if douban_director:
                        director["name"] = douban_director.get("name")
                    else:
                        log.info("【Scraper】豆瓣该影片或剧集无导演 %s 信息" % director.get("name"))
            # 演员
            if actors:
                douban_actors = doubaninfo.get("actors") or []
                # douban英文名姓和名分开匹配，（豆瓣中名前姓后，TMDB中不确定）
                for actor in douban_actors:
                    if actor.get("latin_name"):
                        actor["names"] = actor.get("latin_name", "").lower().split(" ")
                    else:
                        actor["names"] = actor.get("name", "").lower().split(" ")
                for actor in actors:
                    douban_actor = self.__match_people_in_douban(actor, douban_actors)
                    if douban_actor:
                        actor["name"] = douban_actor.get("name")
                        if douban_actor.get("character") != "演员":
                            actor["character"] = douban_actor.get("character")[2:]
                    else:
                        log.info("【Scraper】豆瓣该影片或剧集无演员 %s 信息" % actor.get("name"))
        else:
            log.info("【Scraper】豆瓣无该影片或剧集信息")
        return directors, actors

    def __match_people_in_douban(self, people, peoples_douban):
        """
        名字加又名构成匹配列表
        """
        people_aka_names = self.media.get_tmdbperson_aka_names(people.get("id")) or []
        people_aka_names.append(people.get("name"))
        for people_aka_name in people_aka_names:
            for people_douban in peoples_douban:
                latin_match_res = True
                #  姓和名分开匹配
                for latin_name in people_douban.get("names"):
                    latin_match_res = latin_match_res and (latin_name in people_aka_name.lower())
                if latin_match_res or (people_douban.get("name") == people_aka_name):
                    return people_douban
        return None
