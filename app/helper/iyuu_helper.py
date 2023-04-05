import json

from app.utils import RequestUtils
from app.utils.commons import singleton


@singleton
class IyuuHelper(object):
    _api_base = "https://api.iyuu.cn/index.php?s=%s&version=2.0.0"
    _sites = []
    _token = None

    def __init__(self, token):
        self._token = token
        self.init_config()

    def init_config(self):
        self._sites = self.__get_sites()

    def __request_iyuu(self, url, method="get", params=None):
        """
        向IYUUApi发送请求
        """
        if params:
            params.update({"sign": self._token})
        else:
            params = {"sign": self._token}
        # 开始请求
        if method == "get":
            ret = RequestUtils(
                accept_type="application/json"
            ).get_res(f"{url}", params=params)
        else:
            ret = RequestUtils(
                accept_type="application/json"
            ).post_res(f"{url}", data=json.dumps(params))
        if ret:
            result = ret.json()
            if result.get('ret') == 200:
                return result.get('data'), ""
            else:
                return None, f"请求IYUU失败，状态码：{result.get('ret')}，返回信息：{result.get('msg')}"
        elif ret is not None:
            return None, f"请求IYUU失败，状态码：{ret.status_code}，错误原因：{ret.reason}"
        else:
            return None, f"请求IYUU失败，未获取到返回信息"

    def get_torrent_url(self, sid):
        if not self._sites:
            return None, None
        if not sid:
            return None, None
        for site in self._sites:
            if site.get('id') == sid:
                return site.get('base_url'), site.get('download_page')
        return None, None

    def __get_sites(self):
        """
        返回支持辅种的全部站点
        :return: 站点列表、错误信息
        {
            "ret": 200,
            "data": {
                "sites": [
                    {
                        "id": 1,
                        "site": "keepfrds",
                        "nickname": "朋友",
                        "base_url": "pt.keepfrds.com",
                        "download_page": "download.php?id={}&passkey={passkey}",
                        "reseed_check": "passkey",
                        "is_https": 2
                    },
                ]
            }
        }
        """
        result, msg = self.__request_iyuu(url=self._api_base % 'App.Api.Sites')
        if result:
            return result.get('sites')
        else:
            print(msg)
            return []

    def get_seed_info(self, info_hash):
        """
        返回info_hash对应的站点id、种子id
        {
            "ret": 200,
            "data": [
                {
                    "sid": 3,
                    "torrent_id": 377467,
                    "info_hash": "a444850638e7a6f6220e2efdde94099c53358159"
                },
                {
                    "sid": 7,
                    "torrent_id": 35538,
                    "info_hash": "cf7d88fd656d10fe5130d13567aec27068b96676"
                }
            ],
            "msg": "",
            "version": "1.0.0"
        }
        """
        result, msg = self.__request_iyuu(url=self._api_base % 'App.Api.GetTorrentInfo',
                                          method="post",
                                          params={"hash": [info_hash]})
        if result and not result[0].get('errmsg'):
            return result, ""
        elif result:
            return [], result.get('errmsg') or msg
        return [], msg
