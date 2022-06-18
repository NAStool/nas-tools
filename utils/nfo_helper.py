import os.path

import requests

from config import Config
from rmt.meta.metabase import MetaBase
from utils.types import MediaType


class NfoHelper:
    __nfo_poster = False

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        self.__nfo_poster = config.get_config("media").get("nfo_poster")

    def gen_movie_nfo_file(self, media: MetaBase, out_path, file_name):
        """
        生成电影的NFO描述文件
        :param media: 媒体信息
        :param out_path: 电影根目录
        :param file_name: 电影文件名，不含后缀
        """
        pass

    def gen_tv_nfo_file(self, media: MetaBase, out_path):
        """
        生成电视剧的NFO描述文件
        :param media: 媒体信息
        :param out_path: 电视剧根目录
        """
        pass

    def gen_tv_season_nfo_file(self, media: MetaBase, out_path):
        """
        生成电视剧季的NFO描述文件
        :param media: 媒体信息
        :param out_path: 电视剧季的目录
        """
        pass

    def gen_tv_episode_nfo_file(self, media: MetaBase, out_path, file_name):
        """
        生成电视剧集的NFO描述文件
        :param media: 媒体信息
        :param out_path: 电视剧季的目录
        :param file_name: 电视剧文件名，不含后缀
        """
        pass

    @staticmethod
    def save_image(url, out_path, itype="poster"):
        """
        下载poster.jpg并保存
        """
        if not url or not out_path:
            return
        if os.path.exists(os.path.join(out_path, "%s.%s" % (itype, str(url).split('.')[-1]))):
            return
        try:
            r = requests.get(url)
            with open(file=os.path.join(out_path, "%s.%s" % (itype, str(url).split('.')[-1])),
                      mode="wb",
                      encoding="utf-8") as img:
                img.write(r.content)
        except Exception as err:
            print(str(err))

    def gen_nfo_files(self, media: MetaBase, dir_path, file_name):
        if not self.__nfo_poster:
            return
        # 电影
        if media.type == MediaType.MOVIE:
            # 生成电影描述文件
            self.gen_movie_nfo_file(media, dir_path, file_name)
            # 保存海报
            if media.poster_path:
                self.save_image(media.poster_path, dir_path)
            if media.fanart_image:
                self.save_image(media.fanart_image, dir_path, "fanart")
        # 电视剧
        else:
            # 根目录描述文件
            self.gen_tv_nfo_file(media, os.path.dirname(dir_path))
            # 季的描述文件
            self.gen_tv_season_nfo_file(media, dir_path)
            # 集的描述文件
            self.gen_tv_episode_nfo_file(media, dir_path, file_name)
            # 保存海报
            if media.poster_path:
                self.save_image(media.poster_path, os.path.dirname(dir_path))
            if media.fanart_image:
                self.save_image(media.fanart_image, os.path.dirname(dir_path), "fanart")
