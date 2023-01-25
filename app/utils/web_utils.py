from app.utils.http_utils import RequestUtils
from app.utils.system_utils import SystemUtils
from app.utils.exception_utils import ExceptionUtils
from config import Config
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
            ExceptionUtils.exception_traceback(err)
            return ""

    @staticmethod
    def get_current_version():
        """
        获取当前版本号
        """
        commit_id = SystemUtils.execute('git rev-parse HEAD')
        if commit_id and len(commit_id) > 7:
            commit_id = commit_id[:7]
        return "%s %s" % (APP_VERSION, commit_id)

    @staticmethod
    def get_latest_version():
        """
        获取最新版本号
        """
        try:
            version_res = RequestUtils(proxies=Config().get_proxies()).get_res(
                "https://api.github.com/repos/jxxghp/nas-tools/releases/latest")
            commit_res = RequestUtils(proxies=Config().get_proxies()).get_res(
                "https://api.github.com/repos/jxxghp/nas-tools/commits/master")
            if version_res and commit_res:
                ver_json = version_res.json()
                commit_json = commit_res.json()
                version = f"{ver_json['tag_name']} {commit_json['sha'][:7]}"
                url = ver_json["html_url"]
                return version, url, True
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
        return None, None, False
