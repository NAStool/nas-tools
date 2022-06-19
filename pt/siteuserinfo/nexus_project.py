# -*- coding: utf-8 -*-
import re

from pt.siteuserinfo.nexus_php import NexusPhpSiteUserInfo


class NexusProjectSiteUserInfo(NexusPhpSiteUserInfo):
    _site_schema = "NexusProject"

    _brief_page = "/index.php"
    _user_traffic_page = "/index.php"
    _user_detail_page = "/userdetails.php?id="
    _torrent_seeding_page = "getusertorrentlistajax.php?userid="

    def _parse_site_page(self, html_text):
        html_text = self._prepare_html_text(html_text)

        user_detail = re.search(r"userdetails.php\?id=(\d+)", html_text)
        if user_detail and user_detail.group().strip():
            self._user_detail_page = user_detail.group().strip().lstrip('/')
            self.userid = user_detail.group(1)

        self._torrent_seeding_page = f"viewusertorrents.php?id={self.userid}&show=seeding"
