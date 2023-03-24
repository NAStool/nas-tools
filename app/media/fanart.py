from functools import lru_cache

from app.utils import RequestUtils, ExceptionUtils
from app.utils.types import MediaType
from config import Config, FANART_MOVIE_API_URL, FANART_TV_API_URL


class Fanart:
    _proxies = Config().get_proxies()
    _movie_image_types = ['movieposter',
                          'hdmovielogo',
                          'moviebackground',
                          'moviedisc',
                          'moviebanner',
                          'moviethumb']
    _tv_image_types = ['hdtvlogo',
                       'tvthumb',
                       'showbackground',
                       'tvbanner',
                       'seasonposter',
                       'seasonbanner',
                       'seasonthumb',
                       'tvposter',
                       'hdclearart']
    _season_types = ['seasonposter',
                     'seasonthumb',
                     'seasonbanner']
    _images = {}

    def __init__(self):
        self.init_config()

    def init_config(self):
        self._images = {}

    def __get_fanart_images(self, media_type, queryid):
        if not media_type or not queryid:
            return
        try:
            ret = self.__request_fanart(media_type=media_type, queryid=queryid)
            if ret and ret.status_code == 200:
                if media_type == MediaType.MOVIE:
                    for image_type in self._movie_image_types:
                        images = ret.json().get(image_type)
                        if isinstance(images, list):
                            self._images[image_type] = images[0].get('url') if isinstance(images[0], dict) else ""
                        else:
                            self._images[image_type] = ""
                else:
                    for image_type in self._tv_image_types:
                        images = ret.json().get(image_type)
                        if isinstance(images, list):
                            if image_type in self._season_types:
                                if not self._images.get(image_type):
                                    self._images[image_type] = {}
                                for image in images:
                                    if image.get("season") not in self._images[image_type].keys():
                                        self._images[image_type][image.get("season")] = image.get("url")
                            else:
                                self._images[image_type] = images[0].get('url') if isinstance(images[0], dict) else ""
                        else:
                            if image_type in self._season_types:
                                self._images[image_type] = {}
                            else:
                                self._images[image_type] = ""
        except Exception as e2:
            ExceptionUtils.exception_traceback(e2)

    @classmethod
    @lru_cache(maxsize=256)
    def __request_fanart(cls, media_type, queryid):
        if media_type == MediaType.MOVIE:
            image_url = FANART_MOVIE_API_URL % queryid
        else:
            image_url = FANART_TV_API_URL % queryid
        try:
            return RequestUtils(proxies=cls._proxies, timeout=5).get_res(image_url)
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
        return None

    def get_backdrop(self, media_type, queryid, default=""):
        """
        获取横幅背景图
        """
        if not media_type or not queryid:
            return ""
        if not self._images:
            self.__get_fanart_images(media_type=media_type, queryid=queryid)
        if media_type == MediaType.MOVIE:
            return self._images.get("moviethumb", default)
        else:
            return self._images.get("tvthumb", default)

    def get_poster(self, media_type, queryid, default=None):
        """
        获取海报
        """
        if not media_type or not queryid:
            return None
        if not self._images:
            self.__get_fanart_images(media_type=media_type, queryid=queryid)
        if media_type == MediaType.MOVIE:
            return self._images.get("movieposter", default)
        else:
            return self._images.get("tvposter", default)

    def get_background(self, media_type, queryid, default=None):
        """
        获取海报
        """
        if not media_type or not queryid:
            return None
        if not self._images:
            self.__get_fanart_images(media_type=media_type, queryid=queryid)
        if media_type == MediaType.MOVIE:
            return self._images.get("moviebackground", default)
        else:
            return self._images.get("showbackground", default)

    def get_banner(self, media_type, queryid, default=None):
        """
        获取海报
        """
        if not media_type or not queryid:
            return None
        if not self._images:
            self.__get_fanart_images(media_type=media_type, queryid=queryid)
        if media_type == MediaType.MOVIE:
            return self._images.get("moviebanner", default)
        else:
            return self._images.get("tvbanner", default)

    def get_disc(self, media_type, queryid, default=None):
        """
        获取光盘封面
        """
        if not media_type or not queryid:
            return None
        if not self._images:
            self.__get_fanart_images(media_type=media_type, queryid=queryid)
        if media_type == MediaType.MOVIE:
            return self._images.get("moviedisc", default)
        else:
            return None

    def get_logo(self, media_type, queryid, default=None):
        """
        获取海报
        """
        if not media_type or not queryid:
            return None
        if not self._images:
            self.__get_fanart_images(media_type=media_type, queryid=queryid)
        if media_type == MediaType.MOVIE:
            return self._images.get("hdmovielogo", default)
        else:
            return self._images.get("hdtvlogo", default)

    def get_thumb(self, media_type, queryid, default=None):
        """
        获取缩略图
        """
        if not media_type or not queryid:
            return None
        if not self._images:
            self.__get_fanart_images(media_type=media_type, queryid=queryid)
        if media_type == MediaType.MOVIE:
            return self._images.get("moviethumb", default)
        else:
            return self._images.get("tvthumb", default)

    def get_clearart(self, media_type, queryid, default=None):
        """
        获取clearart
        """
        if not media_type or not queryid:
            return None
        if not self._images:
            self.__get_fanart_images(media_type=media_type, queryid=queryid)
        if media_type == MediaType.TV:
            return self._images.get("hdclearart", default)
        else:
            return None

    def get_seasonposter(self, media_type, queryid, season, default=None):
        """
        获取seasonposter
        """
        if not media_type or not queryid:
            return None
        if not self._images:
            self.__get_fanart_images(media_type=media_type, queryid=queryid)
        if media_type != MediaType.TV:
            return None
        return self._images.get("seasonposter", {}).get(season, "") or default

    def get_seasonthumb(self, media_type, queryid, season, default=None):
        """
        获取seasonposter
        """
        if not media_type or not queryid:
            return None
        if not self._images:
            self.__get_fanart_images(media_type=media_type, queryid=queryid)
        if media_type != MediaType.TV:
            return None
        return self._images.get("seasonthumb", {}).get(season, "") or default

    def get_seasonbanner(self, media_type, queryid, season, default=None):
        """
        获取seasonbanner
        """
        if not media_type or not queryid:
            return None
        if not self._images:
            self.__get_fanart_images(media_type=media_type, queryid=queryid)
        if media_type != MediaType.TV:
            return None
        return self._images.get("seasonbanner", {}).get(season, "") or default
