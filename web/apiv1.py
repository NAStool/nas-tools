from flask_restx import Api, reqparse, Resource
from flask import Blueprint, jsonify

from app.media import Media
from app.sites import Sites
from config import Config
from web.action import WebAction
from web.backend.user import User
from web.security import require_auth, login_required, generate_access_token

apiv1_bp = Blueprint("apiv1",
                     __name__,
                     static_url_path='',
                     static_folder='./frontend/static/',
                     template_folder='./frontend/', )
Apiv1 = Api(apiv1_bp,
            version="1.0",
            title="NAStool Api",
            description="",
            doc="/",
            security='Bearer Auth',
            authorizations={"Bearer Auth": {"type": "apiKey", "name": "Authorization", "in": "header"}},
            )
# API分组
system = Apiv1.namespace('system', description='系统')
user = Apiv1.namespace('user', description='用户')
config = Apiv1.namespace('config', description='设置')
site = Apiv1.namespace('site', description='站点')
service = Apiv1.namespace('service', description='服务')
subscribe = Apiv1.namespace('subscribe', description='订阅')
rss = Apiv1.namespace('rss', description='RSS')
recommend = Apiv1.namespace('recommend', description='推荐')
search = Apiv1.namespace('search', description='搜索')
download = Apiv1.namespace('download', description='下载')
organization = Apiv1.namespace('organization', description='整理')
brushtask = Apiv1.namespace('brushtask', description='刷流')
media = Apiv1.namespace('media', description='媒体')
filterrule = Apiv1.namespace('filterrule', description='过滤规则')
words = Apiv1.namespace('words', description='识别词')


class ApiResource(Resource):
    """
    API 认证
    """
    method_decorators = [require_auth]


class ClientResource(Resource):
    """
    登录认证
    """
    method_decorators = [login_required]


@site.route('/statistics')
class GetSiteStatistic(ApiResource):
    @staticmethod
    def get():
        """
        获取站点数据明细
        """
        # 返回站点信息
        return jsonify(
            {
                "code": 0,
                "data": {
                    "user_statistics": Sites().get_site_user_statistics(encoding="DICT")
                }
            }
        )


@site.route('/sites')
class GetSiteConf(ApiResource):
    @staticmethod
    def get():
        """
        获取站点配置
        """
        return jsonify(
            {
                "code": 0,
                "data": {
                    "user_sites": Sites().get_sites()
                }
            }
        )


@service.route('/mediainfo')
class GetMediaInfo(ApiResource):
    parser = reqparse.RequestParser()
    parser.add_argument('name', type=str, help='名称', location='args')

    @service.doc(parser=parser)
    def get(self):
        """
        识别媒体信息
        """
        args = self.parser.parse_args()
        name = args.get('name')
        if not name:
            return jsonify(
                {
                    "code": -1,
                    "msg": "名称不能为空"
                }
            )
        media_info = Media().get_media_info(title=name)
        if not media_info:
            return jsonify(
                {
                    "code": 1,
                    "msg": "无法识别",
                    "data": {}
                }
            )
        mediainfo_dict = WebAction().mediainfo_dict(media_info)
        return jsonify(
            {
                "code": 0,
                "data": mediainfo_dict
            }
        )


@user.route('/login')
class UserLogin(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('username', type=str, help='用户名', location='form')
    parser.add_argument('password', type=str, help='密码', location='form')

    @user.doc(parser=parser)
    def post(self):
        """
        用户登录
        """
        args = self.parser.parse_args()
        username = args.get('username')
        password = args.get('password')
        if not username or not password:
            return {"code": 1, "message": "用户名或密码错误"}
        user_info = User().get_user(username)
        if not user_info:
            return {"code": 1, "message": "用户名或密码错误"}
        # 校验密码
        if not user_info.verify_password(password):
            return {"code": 1, "message": "用户名或密码错误"}
        return jsonify({
            "code": 0,
            "token": generate_access_token(username),
            "apikey": Config().get_config("security").get("api_key"),
            "userinfo": {
                "userid": user_info.id,
                "username": user_info.username,
                "userpris": str(user_info.pris).split(",")
            }
        })


@user.route('/info')
class UserInfo(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('username', type=str, help='用户名', location='form')

    @user.doc(parser=parser)
    def post(self):
        """
        获取用户信息
        """
        args = self.parser.parse_args()
        username = args.get('username')
        user_info = User().get_user(username)
        if not user_info:
            return {"code": 1, "message": "用户名不正确"}
        return jsonify({
            "userid": user_info.id,
            "username": user_info.username,
            "userpris": str(user_info.pris).split(",")
        })


@user.route('/manage')
class UserManage(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('oper', type=str, help='操作类型（add 新增、del删除）', location='form')
    parser.add_argument('name', type=str, help='用户名', location='form')
    parser.add_argument('pris', type=str, help='权限', location='form')

    @user.doc(parser=parser)
    def post(self):
        """
        管理用户
        """
        return WebAction().action(cmd='user_manager', data=self.parser.parse_args())


"""
# search
"search": self.__search,

# download
"download": self.__download,
"download_link": self.__download_link,
"pt_start": self.__pt_start,
"pt_stop": self.__pt_stop,
"pt_remove": self.__pt_remove,
"pt_info": self.__pt_info,
"get_downloaded": self.get_downloaded,


# organization
"del_unknown_path": self.__del_unknown_path,
"rename": self.__rename,
"rename_udf": self.__rename_udf,
"re_identification": self.__re_identification,
"delete_history": self.__delete_history,
"start_mediasync": self.__start_mediasync,
"mediasync_state": self.__mediasync_state,
"truncate_blacklist": self.__truncate_blacklist,


# system
"logging": self.__logging,
"version": self.__version,
"restart": self.__restart,
"update_system": self.__update_system,
"logout": self.__logout,
"refresh_message": self.__refresh_message,
"refresh_process": self.__refresh_process,


# site
"update_site": self.__update_site,
"get_site": self.__get_site,
"del_site": self.__del_site,


# config
"update_config": self.__update_config,
"update_directory": self.__update_directory,
"test_connection": self.__test_connection,
"restory_backup": self.__restory_backup,


# subscribe
"remove_rss_media": self.__remove_rss_media,
"add_rss_media": self.__add_rss_media,
"movie_calendar_data": self.__movie_calendar_data,
"tv_calendar_data": self.__tv_calendar_data,


# user
"user_manager": self.__user_manager,

# rss
"refresh_rss": self.__refresh_rss,
"rss_detail": self.__rss_detail,
"get_userrss_task": self.__get_userrss_task,
"delete_userrss_task": self.__delete_userrss_task,
"update_userrss_task": self.__update_userrss_task,
"get_rssparser": self.__get_rssparser,
"delete_rssparser": self.__delete_rssparser,
"update_rssparser": self.__update_rssparser,
"run_userrss": self.__run_userrss,
"list_rss_articles": self.__list_rss_articles,
"rss_article_test": self.__rss_article_test,
"list_rss_history": self.__list_rss_history,
"re_rss_history": self.__re_rss_history,
"rss_articles_check": self.__rss_articles_check,
"rss_articles_download": self.__rss_articles_download,
"delete_rss_history": self.__delete_rss_history,
"truncate_rsshistory": self.__truncate_rsshistory,

# media
"modify_tmdb_cache": self.__modify_tmdb_cache,
"clear_tmdb_cache": self.__clear_tmdb_cache,
"get_tvseason_list": self.__get_tvseason_list,
"get_categories": self.__get_categories,
"media_info": self.__media_info,
"delete_tmdb_cache": self.__delete_tmdb_cache,

# brushtask
"add_brushtask": self.__add_brushtask,
"del_brushtask": self.__del_brushtask,
"brushtask_detail": self.__brushtask_detail,
"add_downloader": self.__add_downloader,
"delete_downloader": self.__delete_downloader,
"get_downloader": self.__get_downloader,
"run_brushtask": self.__run_brushtask,

# service
"name_test": self.__name_test,
"rule_test": self.__rule_test,
"net_test": self.__net_test,
"sch": self.__sch,

# filterrule
"add_filtergroup": self.__add_filtergroup,
"restore_filtergroup": self.__restore_filtergroup,
"set_default_filtergroup": self.__set_default_filtergroup,
"del_filtergroup": self.__del_filtergroup,
"add_filterrule": self.__add_filterrule,
"del_filterrule": self.__del_filterrule,
"filterrule_detail": self.__filterrule_detail,
"share_filtergroup": self.__share_filtergroup,
"import_filtergroup": self.__import_filtergroup

#site
"get_site_activity": self.__get_site_activity,
"get_site_history": self.__get_site_history,
"check_site_attr": self.__check_site_attr,
"get_site_seeding_info": self.__get_site_seeding_info,
"list_site_resources": self.__list_site_resources,

#recommend
"get_recommend": self.get_recommend,

# words
"add_custom_word_group": self.__add_custom_word_group,
"delete_custom_word_group": self.__delete_custom_word_group,
"add_or_edit_custom_word": self.__add_or_edit_custom_word,
"get_custom_word": self.__get_custom_word,
"delete_custom_word": self.__delete_custom_word,
"check_custom_words": self.__check_custom_words,
"export_custom_words": self.__export_custom_words,
"analyse_import_custom_words_code": self.__analyse_import_custom_words_code,
"import_custom_words": self.__import_custom_words,

"""
