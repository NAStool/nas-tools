import json

from lxml import etree

from app.sites.sitesignin._base import _ISiteSigninHandler
from app.utils import StringUtils, RequestUtils
from config import Config


class HDChina(_ISiteSigninHandler):
    """
    瓷器签到
    """
    # 匹配的站点Url，每一个实现类都需要设置为自己的站点Url
    site_url = "hdchina.org"

    # 已签到
    _sign_regex = ['<a class="label label-default" href="#">已签到</a>']

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

        # 获取页面html
        html_res = RequestUtils(cookies=site_cookie,
                                headers=ua,
                                proxies=proxy
                                ).get_res(url="https://hdchina.org/")
        if not html_res or html_res.status_code != 200:
            self.error(f"签到失败，请检查站点连通性")
            return False, f'【{site}】签到失败，请检查站点连通性'

        if "login.php" in html_res.text:
            self.error(f"签到失败，cookie失效")
            return False, f'【{site}】签到失败，cookie失效'

        # 判断是否已签到
        html_res.encoding = "utf-8"
        sign_status = self.sign_in_result(html_res=html_res.text,
                                          regexs=self._sign_regex)
        if sign_status:
            self.info(f"今日已签到")
            return True, f'【{site}】今日已签到'

        # 没有签到则解析html
        html = etree.HTML(html_res.text)

        if not html:
            return False, f'【{site}】签到失败'

        # x_csrf
        x_csrf = html.xpath("//meta[@name='x-csrf']/@content")[0]
        if not x_csrf:
            self.error("签到失败，获取x-csrf失败")
            return False, f'【{site}】签到失败'
        self.debug(f"获取到x-csrf {x_csrf}")

        # 签到
        data = {
            'csrf': x_csrf
        }
        sign_res = RequestUtils(cookies=site_cookie,
                                headers=ua,
                                proxies=proxy
                                ).post_res(url="https://hdchina.org/plugin_sign-in.php?cmd=signin", data=data)
        if not sign_res or sign_res.status_code != 200:
            self.error(f"签到失败，签到接口请求失败")
            return False, f'【{site}】签到失败，签到接口请求失败'

        sign_dict = json.loads(sign_res.text)
        self.debug(f"签到返回结果 {sign_dict}")
        if sign_dict['state']:
            # {'state': 'success', 'signindays': 10, 'integral': 20}
            self.info(f"签到成功")
            return True, f'【{site}】签到成功'
        else:
            # {'state': False, 'msg': '不正确的CSRF / Incorrect CSRF token'}
            self.error(f"签到失败，不正确的CSRF / Incorrect CSRF token")
            return False, f'【{site}】签到失败'
