# -*- coding: utf-8 -*-
import re

from pt.siteuserinfo.site_user_info import ISiteUserInfo
from utils.functions import num_filesize
from lxml import etree


class GazelleUserInfo(ISiteUserInfo):

    _site_schema = "Gazelle"
    _brief_page = "/"
    _user_traffic_page = None
    _user_detail_page = None
    _torrent_seeding_page = None

    def _parse_user_base_info(self, html_text):
        html_text = self._prepare_html_text(html_text)
        html = etree.HTML(html_text)
        tmps = html.xpath('//a[@id="header-username-value"]/@data-value')
        if tmps:
            self.username = str(tmps[0]).strip()

        tmps = html.xpath('//a[contains(@href, "user.php?id=")]/@href')
        if tmps:
            user_id_match = re.search(r"user.php\?id=(\d+)", tmps[0])
            if user_id_match and user_id_match.group().strip():
                self.userid = user_id_match.group(1)
                self._torrent_seeding_page = f"torrents.php?type=seeding&userid={self.userid}"
                self._user_detail_page = f"user.php?id={self.userid}"

        tmps = html.xpath('//*[@id="header-uploaded-value"]/@data-value')
        if tmps:
            self.upload = str(tmps[0]).strip()
        tmps = html.xpath('//*[@id="header-downloaded-value"]/@data-value')
        if tmps:
            self.download = str(tmps[0]).strip()
        tmps = html.xpath('//*[@id="header-ratio-value"]/@data-value')
        if tmps:
            self.ratio = str(tmps[0]).strip()

        tmps = html.xpath('//a[contains(@href, "bonus.php")]/@data-tooltip')
        if tmps:
            bonus_match = re.search(r"\(([\d,.]+)\)", tmps[0])
            if bonus_match and bonus_match.group(1).strip():
                self.bonus = float(bonus_match.group(1).strip().replace(',', ''))

        if not self.username:
            self.err_msg = "获取不到用户信息，请检查cookies是否过期"

    def _parse_site_page(self, html_text):
        # TODO
        pass

    def _parse_user_detail_info(self, html_text):
        """
        解析用户额外信息，加入时间，等级
        :param html_text:
        :return:
        """
        html = etree.HTML(html_text)
        if not html:
            return None

        # 用户等级
        user_levels_text = html.xpath('//*[@id="class-value"]/@data-value')
        if user_levels_text:
            self.user_level = user_levels_text[0].strip()

        # 加入日期
        join_at_text = html.xpath('//*[@id="join-date-value"]/@data-value')
        if join_at_text:
            self.join_at = join_at_text[0].strip()

    def _parse_user_torrent_seeding_info(self, html_text, multi_page=False):
        """
        做种相关信息
        :param html_text:
        :param multi_page: 是否多页数据
        :return: 下页地址
        """
        html = etree.HTML(html_text)
        if not html:
            return None

        size_col = 3
        seeders_col = 5
        page_seeding = 0
        page_seeding_size = 0
        page_seeding_info = []
        seeding_sizes = html.xpath(f'//tr[position()>1]/td[{size_col}]')
        seeding_seeders = html.xpath(f'//tr[position()>1]/td[{seeders_col}]/text()')
        if seeding_sizes and seeding_seeders:
            page_seeding = len(seeding_sizes)

            for i in range(0, len(seeding_sizes)):
                size = num_filesize(seeding_sizes[i].xpath("string(.)").strip())
                seeders = int(seeding_seeders[i])

                page_seeding_size += size
                page_seeding_info.append([seeders, size])

        if multi_page:
            self.seeding += page_seeding
            self.seeding_size += page_seeding_size
            self.seeding_info.extend(page_seeding_info)
        else:
            if not self.seeding:
                self.seeding = page_seeding
            if not self.seeding_size:
                self.seeding_size = page_seeding_size
            if not self.seeding_info:
                self.seeding_info = page_seeding_info

    def _parse_user_traffic_info(self, html_text):
        # TODO
        pass
