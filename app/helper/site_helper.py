# -*- coding: utf-8 -*-
from lxml import etree

from app.utils.types import SiteSchema


class SiteHelper:

    @classmethod
    def schema(cls, html_text):
        """
        获取当前站点框架
        :param html_text:
        :return:
        """
        # 解析站点代码
        html = etree.HTML(html_text)
        if not html:
            return SiteSchema.NexusPhp

        printable_text = html.xpath("string(.)") if html else ""

        if "Powered by Gazelle" in printable_text:
            return SiteSchema.Gazelle

        if "Style by Rabbit" in printable_text:
            return SiteSchema.NexusRabbit

        if "Powered by Discuz!" in printable_text:
            return SiteSchema.DiscuzX

        if "unit3d.js" in html_text:
            return SiteSchema.Unit3d

        if "NexusPHP" in html_text:
            return SiteSchema.NexusPhp

        if "Nexus Project" in html_text:
            return SiteSchema.NexusProject

        if "Small Horse" in html_text:
            return SiteSchema.SmallHorse

        if "IPTorrents" in html_text:
            return SiteSchema.Ipt
        # 默认NexusPhp
        return SiteSchema.NexusPhp

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

        # 是否存在登出和用户面板等链接
        logout_or_usercp = html.xpath('//a[contains(@href, "logout") or contains(@data-url, "logout")'
                                      ' or contains(@href, "mybonus") '
                                      ' or contains(@onclick, "logout") or contains(@href, "usercp")]')

        if logout_or_usercp:
            return True

        return False
