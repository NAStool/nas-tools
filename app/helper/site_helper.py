# -*- coding: utf-8 -*-
from lxml import etree


class SiteHelper:
    @classmethod
    def is_logged_in(cls, html_text):
        """
        判断站点是否已经登陆
        :param html_text:
        :return:
        """
        html = etree.HTML(html_text)
        if not html:
            return False
        # 存在明显的密码输入框，说明未登录
        if html.xpath("//input[@type='password']"):
            return False
        # 是否存在登出和用户面板等链接
        logout_or_usercp = html.xpath('//a[contains(@href, "logout") or contains(@data-url, "logout")'
                                      ' or contains(@href, "mybonus") '
                                      ' or contains(@onclick, "logout") or contains(@href, "usercp")]')

        if logout_or_usercp:
            return True

        user_info_div = html.xpath('//div[@class="user-info-side"]')
        if user_info_div:
            return True

        return False
