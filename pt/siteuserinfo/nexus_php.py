# -*- coding: utf-8 -*-
import re

from bs4 import BeautifulSoup

from pt.siteuserinfo.site_user_info import ISiteUserInfo
from utils.functions import num_filesize
from lxml import etree


class NexusPhpSiteUserInfo(ISiteUserInfo):
    _site_schema = "NexusPhp"
    _brief_page = "index.php"
    _user_traffic_page = "index.php"
    _user_detail_page = "userdetails.php?id="
    _torrent_seeding_page = "getusertorrentlistajax.php?userid="

    def _parse_site_page(self, html_text):
        html_text = self._prepare_html_text(html_text)

        user_detail = re.search(r"userdetails.php\?id=(\d+)", html_text)
        if user_detail and user_detail.group().strip():
            self._user_detail_page = user_detail.group().strip().lstrip('/')
            self.userid = user_detail.group(1)

        self._torrent_seeding_page = f"getusertorrentlistajax.php?userid={self.userid}&type=seeding"

    def _parse_user_base_info(self, html_text):
        html_text = self._prepare_html_text(html_text)
        user_name = re.search(r"userdetails.php\?id=\d+[a-zA-Z\"'=_\-\s]+>[<b>\s]*([^<>]*)[</b>]*</a>", html_text)
        if user_name and user_name.group(1).strip():
            self.username = user_name.group(1).strip()
            return
        html = etree.HTML(html_text)
        ret = html.xpath('//a[contains(@href, "userdetails")]//b//text()')
        if ret:
            self.username = str(ret[-1])
            return
        ret = html.xpath('//a[contains(@href, "userdetails")]//text()')
        if ret:
            self.username = str(ret[-1])

    def _parse_user_traffic_info(self, html_text):
        """
        上传/下载/分享率 [做种数/魔力值]
        :param html_text:
        :return:
        """
        html_text = self._prepare_html_text(html_text)
        upload_match = re.search(r"[^总]上[传傳]量?[:：<>/a-zA-Z-=\"'\s#;]+([0-9,.\s]+[KMGTPI]*B)", html_text, re.IGNORECASE)
        self.upload = num_filesize(upload_match.group(1).strip()) if upload_match else 0

        download_match = re.search(r"[^总]下[载載]量?[:：<>/a-zA-Z-=\"'\s#;]+([0-9,.\s]+[KMGTPI]*B)", html_text,
                                   re.IGNORECASE)
        self.download = num_filesize(download_match.group(1).strip()) if download_match else 0

        ratio_match = re.search(r"分享率[:：<>/a-zA-Z-=\"'\s#;]+([0-9.\s]+)", html_text)
        self.ratio = float(ratio_match.group(1).strip()) if (ratio_match and ratio_match.group(1).strip()) else 0.0

        seeding_match = re.search(r"(Torrents seeding|做种中)[\u4E00-\u9FA5\D\s]+(\d+)[\s\S]+<", html_text)
        self.seeding = int(seeding_match.group(2).strip()) if seeding_match and seeding_match.group(2).strip() else 0

        leeching_match = re.search(r"(Torrents leeching|下载中)[\u4E00-\u9FA5\D\s]+(\d+)[\s\S]+<", html_text)
        self.leeching = int(leeching_match.group(2).strip()) if leeching_match and leeching_match.group(
            2).strip() else 0

        html = etree.HTML(html_text)
        tmps = html.xpath('//span[@class = "ucoin-symbol ucoin-gold"]//text()')
        if tmps:
            self.bonus = float(str(tmps[-1]).strip())
        else:
            bonus_match = re.search(r"mybonus.[\[\]:：<>/a-zA-Z_\-=\"'\s#;.(使用魔力值豆]+\s*([\d,.]+)[<()&\s]", html_text)
            try:
                if bonus_match and bonus_match.group(1).strip():
                    self.bonus = float(bonus_match.group(1).strip().replace(',', ''))
                bonus_match = re.search(r"[魔力值|\]][\[\]:：<>/a-zA-Z_\-=\"'\s#;]+\s*([\d,.]+)[<()&\s]", html_text, flags=re.S)
                if bonus_match and bonus_match.group(1).strip():
                    self.bonus = float(bonus_match.group(1).strip().replace(',', ''))
            except Exception as err:
                print(str(err))

    def _parse_user_torrent_seeding_info(self, html_text):
        """
        做种相关信息
        :param html_text:
        :return:
        """
        soup = BeautifulSoup(html_text, "lxml")

        # 做种体积
        self.seeding_size = 0
        for tr in soup.find_all('tr')[1:]:
            tds = tr.find_all('td')
            self.seeding_size += num_filesize(tds[2].text.strip())

    def _parse_user_detail_info(self, html_text):
        """
        解析用户额外信息，加入时间，等级
        :param html_text:
        :return:
        """
        soup = BeautifulSoup(html_text, "lxml")
        for tr in soup.find_all('tr')[1:]:
            tds = tr.find_all('td')
            if len(tds) == 0:
                continue
            if "当前上传" == tds[0].text.strip():
                # seeding size 获取不到的话，此处再获取一次
                if tds[1].table and self.seeding_size == 0:
                    self.seeding_size = 0
                    inner_tb = tds[1].table
                    for inner_tr in inner_tb.find_all('tr')[1:]:
                        inner_tds = inner_tr.find_all('td')
                        self.seeding_size += num_filesize(inner_tds[3].text.strip())
                continue

            if "加入日期" == tds[0].text.strip() or "注册日期" == tds[0].text.strip():
                self.join_at = tds[1].text
                continue
            if "等级" == tds[0].text.strip() or "等級" == tds[0].text.strip():
                if tds[1].img and 'title' in tds[1].img.attrs:
                    self.user_level = tds[1].img.attrs['title']
                else:
                    self.user_level = tds[1].text.strip()
                continue
