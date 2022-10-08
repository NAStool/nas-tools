import os
from app.utils import RequestUtils
from version import APP_VERSION


class WebUtils:

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
