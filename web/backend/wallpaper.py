import base64
import datetime
from functools import lru_cache

from app.media import Media
from app.utils import RequestUtils


@lru_cache(maxsize=1)
def get_login_wallpaper(today=datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')):
    print("当前日期：%s" % today)
    img_url = Media().get_random_discover_backdrop()
    if img_url:
        res = RequestUtils().get_res(img_url)
        if res:
            return base64.b64encode(res.content).decode()
    return ""
