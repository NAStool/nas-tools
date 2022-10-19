from functools import wraps

from flask import Blueprint, make_response, request, jsonify

from app.media import Media
from app.sites import Sites
from config import Config
from web.action import WebAction

apiv1 = Blueprint("apiv1", __name__)


def authorization(func):
    """
    安全认证
    """
    @wraps(func)
    def auth_check():
        auth = request.headers.get("Authorization")
        if not auth or auth != Config().get_config("security").get("subscribe_token"):
            return make_response(jsonify({"code": 400, "msg": "认证失败！"}), 400)
        return func()

    return auth_check


@apiv1.route('/site/statistics', methods=['POST', 'GET'])
@authorization
def site_statistic():
    """
    站点信息查询接口
    """
    # 返回站点信息
    return make_response(jsonify({"code": 0,
                                  "data": {
                                      "user_statistics": Sites().get_site_user_statistics(encoding="DICT")}}),
                         200)


@apiv1.route('/site/sites', methods=['POST', 'GET'])
@authorization
def site_get_sites():
    """
    所有站点的详细信息接口
    """
    # 返回所有站点信息
    return make_response(jsonify({"code": 0, "data": {"user_sites": Sites().get_sites()}}), 200)


@apiv1.route('/service/mediainfo', methods=['POST', 'GET'], )
@authorization
def mediainfo():
    """
    名称识别测试
    """
    name = request.args.get("name")
    if not name:
        return make_response(jsonify({"code": -1, "msg": "识别名称不能为空"}), 200)
    media_info = Media().get_media_info(title=name)
    if not media_info:
        return make_response(jsonify({"code": 1, "msg": "无法识别", "data": {}}), 200)
    mediainfo_dict = WebAction.mediainfo_dict(media_info)
    return make_response(jsonify({"code": 0, "data": mediainfo_dict}), 200)
