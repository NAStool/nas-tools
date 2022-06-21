import datetime
import random
from functools import lru_cache

import requests

from rmt.media import Media


@lru_cache(maxsize=1)
def get_random_discover_backdrop(today=datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')):
    """
    获取TMDB热门电影随机一张背景图
    """
    movies = Media().get_movie_discover()
    if movies:
        backdrops = [movie.get("backdrop_path") for movie in movies.get("results")]
        return "https://www.themoviedb.org/t/p/original%s" % backdrops[round(random.uniform(0, len(backdrops)-1))]
    return ""


@lru_cache(maxsize=7)
def get_bing_wallpaper(today=datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')):
    """
    获取Bing每日避纸
    """
    url = "http://cn.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&today=%s" % today
    try:
        resp = requests.get(url, timeout=5)
    except Exception as err:
        print(str(err))
        return ""
    if resp and resp.status_code == 200:
        for image in resp.json()['images']:
            return f"https://cn.bing.com{image['url']}"
    return ""
