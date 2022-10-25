# -*- coding: utf-8 -*-
import re

from lxml import etree

from app.sites.siteuserinfo.nexus_php import NexusPhpSiteUserInfo


class NexusProjectSiteUserInfo(NexusPhpSiteUserInfo):
    _site_schema = "NexusProject"

    def _parse_site_page(self, html_text):
        html_text = self._prepare_html_text(html_text)

        user_detail = re.search(r"userdetails.php\?id=(\d+)", html_text)
        if user_detail and user_detail.group().strip():
            self._user_detail_page = user_detail.group().strip().lstrip('/')
            self.userid = user_detail.group(1)

        self._torrent_seeding_page = f"viewusertorrents.php?id={self.userid}&show=seeding"

        html = etree.HTML(html_text)
        if not html:
            self.err_msg = "未检测到已登陆，请检查cookies是否过期"
            return

        logout = html.xpath('//a[contains(@href, "logout") or contains(@data-url, "logout")'
                            ' or contains(@onclick, "logout")]')
        if not logout:
            self.err_msg = "未检测到已登陆，请检查cookies是否过期"
