import datetime
from functools import wraps

from flask_jwt import jwt
from flask import request
from flask_restx import abort

from config import Config


def require_auth(func):
    """
    API安全认证
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if auth:
            auth = str(auth).split()[-1]
            if auth == Config().get_config("security").get("subscribe_token"):
                return func(*args, **kwargs)
        return abort(401)
    return wrapper


def generate_access_token(username: str, algorithm: str = 'HS256', exp: float = 2):
    """
    生成access_token
    :param username: 用户名(自定义部分)
    :param algorithm: 加密算法
    :param exp: 过期时间
    :return:token
    """

    now = datetime.datetime.utcnow()
    exp_datetime = now + datetime.timedelta(hours=exp)
    access_payload = {
        'exp': exp_datetime,
        'flag': 0,
        'iat': now,
        'iss': 'leon',
        'username': username
    }
    access_token = jwt.encode(access_payload,
                              Config().get_config("security").get("subscribe_token"),
                              algorithm=algorithm).decode("utf-8")
    return access_token


def __decode_auth_token(token: str):
    """
    解密token
    :param token:token字符串
    :return:
    """
    try:
        payload = jwt.decode(token,
                             key=Config().get_config("security").get("subscribe_token"),
                             algorithms='HS256')
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.ImmatureSignatureError):
        return {}
    else:
        return payload


def identify(auth_header: str):
    """
    用户鉴权
    """
    if auth_header:
        payload = __decode_auth_token(auth_header)
        if not payload:
            return False
        if "username" in payload and "flag" in payload:
            if payload.get("flag") == 0:
                return payload.get("username")
            else:
                return None
    return None


def login_required(func):
    """
    登录保护，验证用户是否登录
    :param func:
    :return:
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization", default=None)
        if not token or not identify(token):
            return abort(403)
        return func(*args, **kwargs)
    return wrapper
