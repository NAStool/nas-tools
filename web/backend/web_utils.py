import base64
import datetime
import random
from functools import lru_cache

from config import TMDB_IMAGE_ORIGINAL_URL
from rmt.media import Media
from utils.http_utils import RequestUtils
from utils.indexer_helper import IndexerHelper


@lru_cache(maxsize=1)
def get_login_wallpaper(today=datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')):
    print("当前日期：%s" % today)
    img_url = get_random_discover_backdrop()
    if img_url:
        res = RequestUtils().get_res(img_url)
        if res:
            return base64.b64encode(res.content).decode()
    return ""


def get_random_discover_backdrop():
    """
    获取TMDB热门电影随机一张背景图
    """
    movies = Media().get_movie_discover()
    if movies:
        backdrops = [movie.get("backdrop_path") for movie in movies.get("results")]
        return TMDB_IMAGE_ORIGINAL_URL % backdrops[round(random.uniform(0, len(backdrops) - 1))]
    return ""


@lru_cache(maxsize=7)
def get_bing_wallpaper(today=datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')):
    """
    获取Bing每日避纸
    """
    url = "http://cn.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&today=%s" % today
    try:
        resp = RequestUtils().get_res(url)
    except Exception as err:
        print(str(err))
        return ""
    if resp and resp.status_code == 200:
        for image in resp.json()['images']:
            return f"https://cn.bing.com{image['url']}"
    return ""


def get_location(ip):
    """
    根据IP址查询真实地址
    """
    url = 'https://sp0.baidu.com/8aQDcjqpAAV3otqbppnN2DJv/api.php?co=&resource_id=6006&t=1529895387942&ie=utf8' \
          '&oe=gbk&cb=op_aladdin_callback&format=json&tn=baidu&' \
          'cb=jQuery110203920624944751099_1529894588086&_=1529894588088&query=%s' % ip
    r = RequestUtils().get_res(url)
    r.encoding = 'gbk'
    html = r.text
    try:
        c1 = html.split('location":"')[1]
        c2 = c1.split('","')[0]
        return c2
    except Exception as err:
        print(str(err))
        return ""


def init_features():
    """
    启动时完成一些预加载操作
    """
    # 更新壁纸
    get_login_wallpaper()
    # 加载索引器配置
    IndexerHelper()
