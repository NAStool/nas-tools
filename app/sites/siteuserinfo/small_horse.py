# -*- coding: utf-8 -*-
import re

from lxml import etree

from app.sites.siteuserinfo.site_user_info import ISiteUserInfo
from app.utils import StringUtils


class SmallHorseSiteUserInfo(ISiteUserInfo):
    _site_schema = "Small Horse"

    def _parse_site_page(self, html_text):
        html_text = self._prepare_html_text(html_text)

        user_detail = re.search(r"user.php\?id=(\d+)", html_text)
        if user_detail and user_detail.group().strip():
            self._user_detail_page = user_detail.group().strip().lstrip('/')
            self.userid = user_detail.group(1)
        self._user_traffic_page = f"user.php?id={self.userid}"

        if not self.userid:
            self.err_msg = "获取不到用户信息，请检查cookies是否过期"

    def _parse_user_base_info(self, html_text):
        html_text = self._prepare_html_text(html_text)
        html = etree.HTML(html_text)
        ret = html.xpath('//a[contains(@href, "user.php")]//text()')
        if ret:
            self.username = str(ret[0])

    def _parse_user_traffic_info(self, html_text):
        """
        上传/下载/分享率 [做种数/魔力值]
        :param html_text:
        :return:
        """
        html_text = self._prepare_html_text(html_text)
        html = etree.HTML(html_text)
        tmps = html.xpath('//ul[@class = "stats nobullet"]')
        if tmps:
            if tmps[1].xpath("li") and tmps[1].xpath("li")[0].xpath("span//text()"):
                self.join_at = str(tmps[1].xpath("li")[0].xpath("span//text()")[0])
            self.upload = StringUtils.num_filesize(str(tmps[1].xpath("li")[2].xpath("text()")[0]).split(":")[1].strip())
            self.download = StringUtils.num_filesize(
                str(tmps[1].xpath("li")[3].xpath("text()")[0]).split(":")[1].strip())
            self.ratio = StringUtils.str_float(str(tmps[1].xpath("li")[4].xpath("span//text()")[0]))
            self.bonus = StringUtils.str_float(str(tmps[1].xpath("li")[5].xpath("text()")[0]).split(":")[1])
            self.user_level = str(tmps[3].xpath("li")[0].xpath("text()")[0]).split(":")[1].strip()
            self.seeding = StringUtils.str_int(
                (tmps[4].xpath("li")[5].xpath("text()")[0]).split(":")[1].replace("[", ""))
            self.leeching = StringUtils.str_int(
                (tmps[4].xpath("li")[6].xpath("text()")[0]).split(":")[1].replace("[", ""))

    def _parse_user_detail_info(self, html_text):
        pass

    def _parse_user_torrent_seeding_info(self, html_text, multi_page=False):
        pass

    def _parse_message_unread_links(self, html_text, msg_links):
        return None

    def _parse_message_content(self, html_text):
        return None, None, None
