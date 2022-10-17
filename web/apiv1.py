from flask import Blueprint, make_response, request, jsonify

from app.media import Media
from app.sites import Sites
from config import Config
from web.action import WebAction

apiv1 = Blueprint("apiv1", __name__)


@apiv1.route('/site/statistics', methods=['POST', 'GET'])
def site_statistic():
    """
    站点信息查询接口
    """
    if not authorization():
        return make_response(jsonify({"code": 400, "msg": "认证失败！"}), 400)
    # 返回站点信息
    return make_response(jsonify({"code": 0,
                                  "data": {
                                      "user_statistics": Sites().get_site_user_statistics(encoding="DICT")}}),
                         200)


@apiv1.route('/site/sites', methods=['POST', 'GET'])
def site_get_sites():
    """
    所有站点的详细信息接口
    """
    if not authorization():
        return make_response(jsonify({"code": 400, "msg": "认证失败！"}), 400)
    # 返回所有站点信息
    return make_response(jsonify({"code": 0, "data": {"user_sites": Sites().get_sites()}}), 200)


@apiv1.route('/service/name_test', methods=['POST', 'GET'],)
def name_test():
    """
    名称识别测试
    """
    name = request.args.get("name")
    if not name:
        return {"code": -1}
    media_info = Media().get_media_info(title=name)
    if not media_info:
        return {"code": 0, "data": {"name": "无法识别"}}
    mediainfo_dict = WebAction.mediainfo_dict(media_info)
    return {"code": 0, "data": mediainfo_dict}


def authorization():
    """
    安全认证
    """
    auth = request.headers.get("Authorization")
    if not auth or auth != Config().get_config("security").get("subscribe_token"):
        return False
    return True
