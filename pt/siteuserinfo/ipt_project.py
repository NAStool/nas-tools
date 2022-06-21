# -*- coding: utf-8 -*-

from pt.siteuserinfo.site_user_info import ISiteUserInfo
from utils.functions import num_filesize
from lxml import etree


class IptSiteUserInfo(ISiteUserInfo):

    _site_schema = "IPTorrents"
    _brief_page = "/"
    _user_traffic_page = None
    _user_detail_page = None
    _torrent_seeding_page = None

    def _parse_user_base_info(self, html_text):
        html_text = self._prepare_html_text(html_text)
        html = etree.HTML(html_text)
        tmps = html.xpath('//a[contains(@href, "/u/")]//text()')
        if tmps:
            self.username = str(tmps[-1])
        tmps = html.xpath('//div[@class = "stats"]/div/div')
        if tmps:
            self.upload = num_filesize(str(tmps[0].xpath('span/text()')[1]).strip())
            self.download = num_filesize(str(tmps[0].xpath('span/text()')[2]).strip())
            self.seeding = int(tmps[0].xpath('a')[2].xpath('text()')[0].strip())
            self.leeching = int(tmps[0].xpath('a')[2].xpath('text()')[1].strip())
            self.ratio = float(str(tmps[0].xpath('span/text()')[0]).strip())
            self.bonus = float(tmps[0].xpath('a')[3].xpath('text()')[0])

    def _parse_site_page(self, html_text):
        # TODO
        pass

    def _parse_user_detail_info(self, html_text):
        # TODO
        pass

    def _parse_user_torrent_seeding_info(self, html_text):
        # TODO
        pass

    def _parse_user_traffic_info(self, html_text):
        # TODO
        pass
