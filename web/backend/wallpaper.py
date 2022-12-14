import base64
import datetime
from functools import lru_cache

from app.media import Media
from app.utils import RequestUtils
from app.utils.exception_util import ExceptionUtils
from config import Config


@lru_cache(maxsize=1)
def get_login_wallpaper(today=datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')):
    """
    获取Base64编码的壁纸图片
    """
    wallpaper = Config().get_config('app').get('wallpaper')
    tmdbkey = Config().get_config('app').get('rmt_tmdbkey')
    if (not wallpaper or wallpaper == "themoviedb") and tmdbkey:
        img_url = __get_themoviedb_wallpaper(today)
    else:
        img_url = __get_bing_wallpaper(today)
    if img_url:
        res = RequestUtils().get_res(img_url)
        if res and res.status_code == 200:
            return base64.b64encode(res.content).decode()
    return ""


def __get_themoviedb_wallpaper(today):
    """
    获取TheMovieDb的随机背景图
    """
    return Media().get_random_discover_backdrop()


def __get_bing_wallpaper(today):
    """
    获取Bing每日壁纸
    """
    url = "https://cn.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&today=%s" % today
    try:
        resp = RequestUtils(timeout=5).get_res(url)
    except Exception as err:
        ExceptionUtils.exception_traceback(err)
        return ""
    if resp and resp.status_code == 200:
        if resp.json():
            for image in resp.json().get('images') or []:
                return f"https://cn.bing.com{image.get('url')}"
    return ""
