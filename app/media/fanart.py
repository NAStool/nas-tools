from functools import lru_cache

from app.utils.http_utils import RequestUtils
from app.utils.types import MediaType
from config import Config, FANART_MOVIE_API_URL, FANART_TV_API_URL


class Fanart:
    _proxies = None
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
    _images = {}

    def __init__(self):
        self.init_config()

    def init_config(self):
        self._images = {}
        self._proxies = Config().get_proxies()

    def __get_fanart_images(self, media_type, queryid):
        if not media_type or not queryid:
            return ""
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
                            self._images[image_type] = images[0].get('url') if isinstance(images[0], dict) else ""
                        else:
                            self._images[image_type] = ""
        except Exception as e2:
            print(str(e2))

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
            print(str(err))
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
            return ""
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
            return ""
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
            return ""
        if not self._images:
            self.__get_fanart_images(media_type=media_type, queryid=queryid)
        if media_type == MediaType.MOVIE:
            return self._images.get("moviebanner", default)
        else:
            return self._images.get("tvbanner", default)

    def get_logo(self, media_type, queryid, default=None):
        """
        获取海报
        """
        if not media_type or not queryid:
            return ""
        if not self._images:
            self.__get_fanart_images(media_type=media_type, queryid=queryid)
        if media_type == MediaType.MOVIE:
            return self._images.get("hdmovielogo", default)
        else:
            return self._images.get("hdtvlogo", default)
