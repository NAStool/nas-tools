from app.media import Media
from app.media.bangumi import Bangumi
from app.media.douban import DouBan
from app.media.meta import MetaInfo
from app.utils.http_utils import RequestUtils
from app.utils.system_utils import SystemUtils
from app.utils.exception_utils import ExceptionUtils
from app.utils.types import MediaType
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

    @staticmethod
    def get_mediainfo_from_id(mtype, mediaid):
        """
        根据TMDB/豆瓣/BANGUMI获取媒体信息
        """
        if not mediaid:
            return None
        media_info = None
        if str(mediaid).startswith("DB:"):
            # 豆瓣
            doubanid = mediaid[3:]
            info = DouBan().get_douban_detail(doubanid=doubanid, mtype=mtype)
            if not info:
                return {
                    "code": 1,
                    "msg": "无法查询到豆瓣信息"
                }
            title = info.get("title")
            original_title = info.get("original_title")
            year = info.get("year")
            if original_title:
                media_info = Media().get_media_info(title=f"{original_title} {year}",
                                                    mtype=mtype,
                                                    append_to_response="all")
            if not media_info or not media_info.tmdb_info:
                media_info = Media().get_media_info(title=f"{title} {year}",
                                                    mtype=mtype,
                                                    append_to_response="all")
        elif str(mediaid).startswith("BG:"):
            # BANGUMI
            bangumiid = str(mediaid)[3:]
            info = Bangumi().detail(bid=bangumiid)
            if not info:
                return {
                    "code": 1,
                    "msg": "无法查询Bangumi信息"
                }
            title = info.get("name")
            title_cn = info.get("name_cn")
            year = info.get("date")[:4] if info.get("date") else ""
            media_info = Media().get_media_info(title=f"{title} {year}", mtype=MediaType.TV)
            if not media_info or not media_info.tmdb_info:
                media_info = Media().get_media_info(title=f"{title_cn} {year}", mtype=MediaType.TV)
        else:
            # TMDB
            info = Media().get_tmdb_info(tmdbid=mediaid,
                                         mtype=mtype,
                                         append_to_response="all")
            if not info:
                return {
                    "code": 1,
                    "msg": "无法查询TMDB信息"
                }
            media_info = MetaInfo(title=info.get("title") if mtype == MediaType.MOVIE else info.get("name"))
            media_info.set_tmdb_info(info)

        return media_info
