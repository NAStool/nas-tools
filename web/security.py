import base64
import datetime
import hashlib
import hmac
import json
import os
import log
from functools import wraps, partial

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from cryptography.fernet import Fernet
from base64 import b64encode
import jwt
from flask import request

from app.utils import TokenCache
from config import Config


def require_auth(func=None, force=True):
    """
    API安全认证
    force 是否强制检查apikey，为False时，会检查 check_apikey 配置值
    """
    if func is None:
        return partial(require_auth, force=force)

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not force and \
                not Config().get_config("security").get("check_apikey"):
            return func(*args, **kwargs)
        log.debug(f"【Security】{func.__name__} 认证检查")
        # 允许在请求头Authorization中添加apikey
        auth = request.headers.get("Authorization")
        if auth:
            auth = str(auth).split()[-1]
            if auth == Config().get_config("security").get("api_key"):
                return func(*args, **kwargs)
        # 允许使用在api后面拼接 ?apikey=xxx 的方式进行验证
        # 从query中获取apikey
        auth = request.args.get("apikey")
        if auth:
            if auth == Config().get_config("security").get("api_key"):
                return func(*args, **kwargs)
        log.warn(f"【Security】{func.__name__} 认证未通过，请检查API Key")
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


def encrypt_message(message, key):
    """
    使用给定的key对消息进行加密，并返回加密后的字符串
    """
    f = Fernet(key)
    encrypted_message = f.encrypt(message.encode())
    return encrypted_message.decode()


def hash_sha256(message):
    """
    对字符串做hash运算
    """
    return hashlib.sha256(message.encode()).hexdigest()


def aes_decrypt(data, key):
    """
    AES解密
    """
    if not data:
        return ""
    data = base64.b64decode(data)
    iv = data[:16]
    encrypted = data[16:]
    # 使用AES-256-CBC解密
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv)
    result = cipher.decrypt(encrypted)
    # 去除填充
    padding = result[-1]
    if padding < 1 or padding > AES.block_size:
        return ""
    result = result[:-padding]
    return result.decode('utf-8')


def aes_encrypt(data, key):
    """
    AES加密
    """
    if not data:
        return ""
    # 使用AES-256-CBC加密
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC)
    # 填充
    padding = AES.block_size - len(data) % AES.block_size
    data += chr(padding) * padding
    result = cipher.encrypt(data.encode('utf-8'))
    # 使用base64编码
    return b64encode(cipher.iv + result).decode('utf-8')


def nexusphp_encrypt(data_str: str, key):
    """
    NexusPHP加密
    """
    # 生成16字节长的随机字符串
    iv = os.urandom(16)
    # 对向量进行 Base64 编码
    iv_base64 = base64.b64encode(iv)
    # 加密数据
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(data_str.encode(), AES.block_size))
    ciphertext_base64 = base64.b64encode(ciphertext)
    # 对向量的字符串表示进行签名
    mac = hmac.new(key, msg=iv_base64 + ciphertext_base64, digestmod=hashlib.sha256).hexdigest()
    # 构造 JSON 字符串
    json_str = json.dumps({
        'iv': iv_base64.decode(),
        'value': ciphertext_base64.decode(),
        'mac': mac,
        'tag': ''
    })

    # 对 JSON 字符串进行 Base64 编码
    return base64.b64encode(json_str.encode()).decode()
