from flask_restx import Api, reqparse, Resource
from flask import Blueprint, request, jsonify

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
site = Apiv1.namespace('site', description='站点')
service = Apiv1.namespace('service', description='服务')
user = Apiv1.namespace('user', description='用户')


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

    @staticmethod
    @user.doc(parser=parser)
    def post():
        """
        用户登录
        """
        username = request.form.get('username')
        password = request.form.get('password')
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
class UseInfo(ClientResource):
    parser = reqparse.RequestParser()
    parser.add_argument('username', type=str, help='用户名', location='form')

    @staticmethod
    @user.doc(parser=parser)
    def post():
        """
        获取用户信息
        """
        username = request.form.get('username')
        user_info = User().get_user(username)
        if not user_info:
            return {"code": 1, "message": "用户名不正确"}
        return jsonify({
                "userid": user_info.id,
                "username": user_info.username,
                "userpris": str(user_info.pris).split(",")
            })
