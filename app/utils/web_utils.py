import datetime
import os
from functools import lru_cache

from app.utils import RequestUtils
from version import APP_VERSION


class WebUtils:

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def get_current_version():
        """
        获取当前版本号
        """
        commit_id = os.popen('git rev-parse --short HEAD').readline().strip()
        return "%s %s" % (APP_VERSION, commit_id)
