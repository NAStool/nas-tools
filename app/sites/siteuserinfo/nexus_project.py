# -*- coding: utf-8 -*-
import re

from app.sites.siteuserinfo._base import SITE_BASE_ORDER
from app.sites.siteuserinfo.nexus_php import NexusPhpSiteUserInfo
from app.utils.types import SiteSchema


class NexusProjectSiteUserInfo(NexusPhpSiteUserInfo):
    schema = SiteSchema.NexusProject
    order = SITE_BASE_ORDER + 25

    @classmethod
    def match(cls, html_text):
        return 'Nexus Project' in html_text

    def _parse_site_page(self, html_text):
        html_text = self._prepare_html_text(html_text)

        user_detail = re.search(r"userdetails.php\?id=(\d+)", html_text)
        if user_detail and user_detail.group().strip():
            self._user_detail_page = user_detail.group().strip().lstrip('/')
            self.userid = user_detail.group(1)

        self._torrent_seeding_page = f"viewusertorrents.php?id={self.userid}&show=seeding"
