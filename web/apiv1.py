import flask_restx
from flask_restx import Api, reqparse
from flask import Blueprint, make_response, request, jsonify

from app.media import Media
from app.sites import Sites
from web.action import WebAction
from web.security import require_auth

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


class Resource(flask_restx.Resource):
    method_decorators = [require_auth]


@site.route('/statistics')
class GetSiteStatistic(Resource):
    @staticmethod
    def post():
        """
        获取站点数据明细
        """
        # 返回站点信息
        return make_response(jsonify(
            {
                "code": 0,
                "data": {
                    "user_statistics": Sites().get_site_user_statistics(encoding="DICT")
                }
            }
        ), 200)


@site.route('/sites')
class GetSiteConf(Resource):
    @staticmethod
    def post():
        """
        获取站点配置
        """
        return make_response(jsonify(
            {
                "code": 0,
                "data": {
                    "user_sites": Sites().get_sites()
                }
            }
        ), 200)


@service.route('/mediainfo')
class GetMediaInfo(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('name', type=str, help='名称')

    @staticmethod
    @service.doc(parser=parser)
    def post():
        """
        识别媒体信息
        """
        name = request.form.get("name")
        if not name:
            return make_response(jsonify(
                {
                    "code": -1,
                    "msg": "名称不能为空"
                }
            ), 200)
        media_info = Media().get_media_info(title=name)
        if not media_info:
            return make_response(jsonify(
                {
                    "code": 1,
                    "msg": "无法识别",
                    "data": {}
                }
            ), 200)
        mediainfo_dict = WebAction.mediainfo_dict(media_info)
        return make_response(jsonify(
            {
                "code": 0,
                "data": mediainfo_dict
            }
        ), 200)
