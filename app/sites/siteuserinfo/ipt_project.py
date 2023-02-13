# -*- coding: utf-8 -*-
import re

from lxml import etree

from app.sites.siteuserinfo._base import _ISiteUserInfo, SITE_BASE_ORDER
from app.utils import StringUtils
from app.utils.types import SiteSchema


class IptSiteUserInfo(_ISiteUserInfo):
    schema = SiteSchema.Ipt
    order = SITE_BASE_ORDER + 35

    @classmethod
    def match(cls, html_text):
        return 'IPTorrents' in html_text

    def _parse_user_base_info(self, html_text):
        html_text = self._prepare_html_text(html_text)
        html = etree.HTML(html_text)
        tmps = html.xpath('//a[contains(@href, "/u/")]//text()')
        tmps_id = html.xpath('//a[contains(@href, "/u/")]/@href')
        if tmps:
            self.username = str(tmps[-1])
        if tmps_id:
            user_id_match = re.search(r"/u/(\d+)", tmps_id[0])
            if user_id_match and user_id_match.group().strip():
                self.userid = user_id_match.group(1)
                self._user_detail_page = f"user.php?u={self.userid}"
                self._torrent_seeding_page = f"peers?u={self.userid}"

        tmps = html.xpath('//div[@class = "stats"]/div/div')
        if tmps:
            self.upload = StringUtils.num_filesize(str(tmps[0].xpath('span/text()')[1]).strip())
            self.download = StringUtils.num_filesize(str(tmps[0].xpath('span/text()')[2]).strip())
            self.seeding = StringUtils.str_int(tmps[0].xpath('a')[2].xpath('text()')[0])
            self.leeching = StringUtils.str_int(tmps[0].xpath('a')[2].xpath('text()')[1])
            self.ratio = StringUtils.str_float(str(tmps[0].xpath('span/text()')[0]).strip().replace('-', '0'))
            self.bonus = StringUtils.str_float(tmps[0].xpath('a')[3].xpath('text()')[0])

    def _parse_site_page(self, html_text):
        # TODO
        pass

    def _parse_user_detail_info(self, html_text):
        html = etree.HTML(html_text)
        if not html:
            return

        user_levels_text = html.xpath('//tr/th[text()="Class"]/following-sibling::td[1]/text()')
        if user_levels_text:
            self.user_level = user_levels_text[0].strip()

        # 加入日期
        join_at_text = html.xpath('//tr/th[text()="Join date"]/following-sibling::td[1]/text()')
        if join_at_text:
            self.join_at = StringUtils.unify_datetime_str(join_at_text[0].split(' (')[0])

    def _parse_user_torrent_seeding_info(self, html_text, multi_page=False):
        html = etree.HTML(html_text)
        if not html:
            return
        # seeding start
        seeding_end_pos = 3
        if html.xpath('//tr/td[text() = "Leechers"]'):
            seeding_end_pos = len(html.xpath('//tr/td[text() = "Leechers"]/../preceding-sibling::tr')) + 1
            seeding_end_pos = seeding_end_pos - 3

        page_seeding = 0
        page_seeding_size = 0
        seeding_torrents = html.xpath('//tr/td[text() = "Seeders"]/../following-sibling::tr/td[position()=6]/text()')
        if seeding_torrents:
            page_seeding = seeding_end_pos
            for per_size in seeding_torrents[:seeding_end_pos]:
                if '(' in per_size and ')' in per_size:
                    per_size = per_size.split('(')[-1]
                    per_size = per_size.split(')')[0]

                page_seeding_size += StringUtils.num_filesize(per_size)

        self.seeding = page_seeding
        self.seeding_size = page_seeding_size

    def _parse_user_traffic_info(self, html_text):
        # TODO
        pass

    def _parse_message_unread_links(self, html_text, msg_links):
        return None

    def _parse_message_content(self, html_text):
        return None, None, None
