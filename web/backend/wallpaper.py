import base64
import datetime
from functools import lru_cache

from app.media import Media
from app.utils import RequestUtils, ExceptionUtils
from config import Config


def get_login_wallpaper(time_now=None):
    """
    获取Base64编码的壁纸图片
    """
    if not time_now:
        time_now = datetime.datetime.now()
    wallpaper = Config().get_config('app').get('wallpaper')
    tmdbkey = Config().get_config('app').get('rmt_tmdbkey')
    if (not wallpaper or wallpaper == "themoviedb") and tmdbkey:
        # 每小时更新
        curr_time = datetime.datetime.strftime(time_now, '%Y%m%d%H')
        img_url, img_title, img_link = __get_themoviedb_wallpaper(curr_time)
    else:
        # 每天更新
        today = datetime.datetime.strftime(time_now, '%Y%m%d')
        img_url, img_title, img_link = __get_bing_wallpaper(today)
    img_enc = __get_image_b64(img_url)
    if img_enc:
        return img_enc, img_title, img_link
    return "", "", ""


@lru_cache(maxsize=1)
def __get_image_b64(img_url, cache_tag=None):
    """
    根据图片URL缓存
    如果遇到同一地址返回随机图片的情况, 需要视情况传递cache_tag参数
    """
    if img_url:
        res = RequestUtils().get_res(img_url)
        if res and res.status_code == 200:
            return base64.b64encode(res.content).decode()
    return ""


@lru_cache(maxsize=1)
def __get_themoviedb_wallpaper(cache_tag):
    """
    获取TheMovieDb的随机背景图
    cache_tag 缓存标记, 相同时会命中缓存
    """
    return Media().get_random_discover_backdrop()


@lru_cache(maxsize=1)
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
                img_url = f"https://cn.bing.com{image.get('url')}" if 'url' in image else ''
                img_title = image.get('title', '')
                img_link = image.get('copyrightlink', '')
                return img_url, img_title, img_link
    return '', '', ''
