import random
import re

from lxml import etree

from app.sites.sitesignin._base import _ISiteSigninHandler
from app.utils import StringUtils, RequestUtils
from config import Config


class U2(_ISiteSigninHandler):
    """
    U2签到 随机
    """
    # 匹配的站点Url，每一个实现类都需要设置为自己的站点Url
    site_url = "u2.dmhy.org"

    # 已签到
    _sign_regex = ['<a href="showup.php">已签到</a>',
                   '<a href="showup.php">Show Up</a>',
                   '<a href="showup.php">Показать</a>',
                   '<a href="showup.php">已簽到</a>',
                   '<a href="showup.php">已簽到</a>']

    # 签到成功
    _success_text = "window.location.href = 'showup.php';</script>"

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
                                ).get_res(url="https://u2.dmhy.org/showup.php")
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

        # 获取签到参数
        req = html.xpath("//form//td/input[@name='req']/@value")[0]
        hash_str = html.xpath("//form//td/input[@name='hash']/@value")[0]
        form = html.xpath("//form//td/input[@name='form']/@value")[0]
        submit_name = html.xpath("//form//td/input[@type='submit']/@name")
        submit_value = html.xpath("//form//td/input[@type='submit']/@value")
        if not re or not hash_str or not form or not submit_name or not submit_value:
            self.error("签到失败，未获取到相关签到参数")
            return False, f'【{site}】签到失败'

        # 随机一个答案
        answer_num = random.randint(0, 3)
        data = {
            'req': req,
            'hash': hash_str,
            'form': form,
            'message': '一切随缘~',
            submit_name[answer_num]: submit_value[answer_num]
        }
        # 签到
        sign_res = RequestUtils(cookies=site_cookie,
                                headers=ua,
                                proxies=proxy
                                ).post_res(url="https://u2.dmhy.org/showup.php?action=show",
                                           data=data)
        if not sign_res or sign_res.status_code != 200:
            self.error(f"签到失败，签到接口请求失败")
            return False, f'【{site}】签到失败，签到接口请求失败'

        # 判断是否签到成功
        # sign_res.text = "<script type="text/javascript">window.location.href = 'showup.php';</script>"
        if self._success_text in sign_res.text:
            self.info(f"签到成功")
            return True, f'【{site}】签到成功'
        else:
            self.error(f"签到失败，未知原因")
            return False, f'【{site}】签到失败，未知原因'
