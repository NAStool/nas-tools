import cn2an

from app.media import Media, Bangumi, DouBan
from app.media.meta import MetaInfo
from app.utils import StringUtils, ExceptionUtils, SystemUtils, RequestUtils
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
            media_info = Media().get_media_info(title=f"{title} {year}",
                                                mtype=MediaType.TV,
                                                append_to_response="all")
            if not media_info or not media_info.tmdb_info:
                media_info = Media().get_media_info(title=f"{title_cn} {year}",
                                                    mtype=MediaType.TV,
                                                    append_to_response="all")
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

    @staticmethod
    def search_media_infos(keyword, source=None, page=1):
        """
        搜索TMDB或豆瓣词条
        :param: keyword 关键字
        :param: source 渠道 tmdb/douban
        :param: season 季号
        :param: episode 集号
        """
        if not keyword:
            return []
        mtype, key_word, season_num, episode_num, _, content = StringUtils.get_keyword_from_string(keyword)
        if source == "tmdb":
            use_douban_titles = False
        else:
            use_douban_titles = Config().get_config("laboratory").get("use_douban_titles")
        if use_douban_titles:
            medias = DouBan().search_douban_medias(keyword=key_word,
                                                   mtype=mtype,
                                                   season=season_num,
                                                   episode=episode_num,
                                                   page=page)
        else:
            meta_info = MetaInfo(title=content)
            tmdbinfos = Media().get_tmdb_infos(title=meta_info.get_name(),
                                               year=meta_info.year,
                                               mtype=mtype,
                                               page=page)
            medias = []
            for tmdbinfo in tmdbinfos:
                tmp_info = MetaInfo(title=keyword)
                tmp_info.set_tmdb_info(tmdbinfo)
                if meta_info.type == MediaType.TV and tmp_info.type != MediaType.TV:
                    continue
                if tmp_info.begin_season:
                    tmp_info.title = "%s 第%s季" % (tmp_info.title, cn2an.an2cn(meta_info.begin_season, mode='low'))
                if tmp_info.begin_episode:
                    tmp_info.title = "%s 第%s集" % (tmp_info.title, meta_info.begin_episode)
                medias.append(tmp_info)
        return medias
