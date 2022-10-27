import datetime
from functools import wraps

import jwt
from flask import request

from app.utils import TokenCache
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
            if auth == Config().get_config("security").get("api_key"):
                return func(*args, **kwargs)
        return {
            "code": 401,
            "success": False,
            "message": "安全认证未通过，请检查ApiKey"
        }

    return wrapper


def generate_access_token(username: str, algorithm: str = 'HS256', exp: float = 2):
    """
    生成access_token
    :param username: 用户名(自定义部分)
    :param algorithm: 加密算法
    :param exp: 过期时间，默认2小时
    :return:token
    """

    now = datetime.datetime.utcnow()
    exp_datetime = now + datetime.timedelta(hours=exp)
    access_payload = {
        'exp': exp_datetime,
        'iat': now,
        'username': username
    }
    access_token = jwt.encode(access_payload,
                              Config().get_config("security").get("api_key"),
                              algorithm=algorithm)
    return access_token


def __decode_auth_token(token: str, algorithms='HS256'):
    """
    解密token
    :param token:token字符串
    :return: 是否有效，playload
    """
    key = Config().get_config("security").get("api_key")
    try:
        payload = jwt.decode(token,
                             key=key,
                             algorithms=algorithms)
    except jwt.ExpiredSignatureError:
        return False, jwt.decode(token,
                                 key=key,
                                 algorithms=algorithms,
                                 options={'verify_exp': False})
    except (jwt.DecodeError, jwt.InvalidTokenError, jwt.ImmatureSignatureError):
        return False, {}
    else:
        return True, payload


def identify(auth_header: str):
    """
    用户鉴权，返回是否有效、用户名
    """
    flag = False
    if auth_header:
        flag, payload = __decode_auth_token(auth_header)
        if payload:
            return flag, payload.get("username") or ""
    return flag, ""


def login_required(func):
    """
    登录保护，验证用户是否登录
    :param func:
    :return:
    """

    @wraps(func)
    def wrapper(*args, **kwargs):

        def auth_failed():
            return {
                "code": 403,
                "success": False,
                "message": "安全认证未通过，请检查Token"
            }

        token = request.headers.get("Authorization", default=None)
        if not token:
            return auth_failed()
        latest_token = TokenCache.get(token)
        if not latest_token:
            return auth_failed()
        flag, username = identify(latest_token)
        if not username:
            return auth_failed()
        if not flag and username:
            TokenCache.set(token, generate_access_token(username))
        return func(*args, **kwargs)

    return wrapper
