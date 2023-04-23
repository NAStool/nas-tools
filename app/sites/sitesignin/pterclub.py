import json

from app.sites.sitesignin._base import _ISiteSigninHandler
from app.utils import StringUtils, RequestUtils
from config import Config


class PTerClub(_ISiteSigninHandler):
    """
    猫签到
    """
    # 匹配的站点Url，每一个实现类都需要设置为自己的站点Url
    site_url = "pterclub.com"

    # 已签到
    _sign_regex = ['签到已得\\d+']

    @classmethod
    def match(cls, url):
        """
        根据站点Url判断是否匹配当前站点签到类，大部分情况使用默认实现即可
        :param url: 站点Url
        :return: 是否匹配，如匹配则会调用该类的signin方法
        """
        return True if StringUtils.url_equal(url, cls.site_url) else False

    def signin(self, site_info: dict):
        """
        执行签到操作
        :param site_info: 站点信息，含有站点Url、站点Cookie、UA等信息
        :return: 签到结果信息
        """
        site = site_info.get("name")
        site_cookie = site_info.get("cookie")
        ua = site_info.get("ua")
        proxy = Config().get_proxies() if site_info.get("proxy") else None

        # 签到
        sign_res = RequestUtils(cookies=site_cookie,
                                headers=ua,
                                proxies=proxy
                                ).get_res(url="https://pterclub.com/attendance-ajax.php")
        if not sign_res or sign_res.status_code != 200:
            self.error(f"签到失败，签到接口请求失败")
            return False, f'【{site}】签到失败，请检查cookie是否失效'

        sign_dict = json.loads(sign_res.text)
        self.debug(f"签到返回 {sign_dict}")
        if sign_dict['status'] == 1:
            # {"status":"1","data":" (签到已成功300)","message":"<p>这是您的第<b>237</b>次签到，
            # 已连续签到<b>237</b>天。</p><p>本次签到获得<b>300</b>克猫粮。</p>"}
            self.info(f"签到成功")
            return True, f'【{site}】签到成功'
        else:
            # {"status":"0","data":"抱歉","message":"您今天已经签到过了，请勿重复刷新。"}
            self.error(f"今日已签到")
            return True, f'【{site}】今日已签到'
