from functools import wraps
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
