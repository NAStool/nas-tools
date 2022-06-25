# -*- coding: utf-8 -*-
import re

from lxml import etree

from pt.siteuserinfo.site_user_info import ISiteUserInfo
from utils.functions import num_filesize


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
                bonus_match = re.search(r"[魔力值|\]][\[\]:：<>/a-zA-Z_\-=\"'\s#;]+\s*([\d,.]+)[<()&\s]", html_text,
                                        flags=re.S)
                if bonus_match and bonus_match.group(1).strip():
                    self.bonus = float(bonus_match.group(1).strip().replace(',', ''))
            except Exception as err:
                print(str(err))

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

        page_seeding = 0
        page_seeding_size = 0
        seeding_torrents = html.xpath('//tr[position()>1]/td[3]')
        if seeding_torrents:
            page_seeding = len(seeding_torrents)

            for per_size in seeding_torrents:
                page_seeding_size += num_filesize(per_size.xpath("string(.)").strip())

        if multi_page:
            self.seeding += page_seeding
            self.seeding_size += page_seeding_size
        else:
            if not self.seeding:
                self.seeding = page_seeding
            if not self.seeding_size:
                self.seeding_size = page_seeding_size

        # 是否存在下页数据
        next_page = None
        next_page_text = html.xpath('//a[contains(.//text(), "下一页") or contains(.//text(), "下一頁")]/@href')
        if next_page_text:
            next_page = next_page_text[-1].strip()

        return next_page

    def _parse_user_detail_info(self, html_text):
        """
        解析用户额外信息，加入时间，等级
        :param html_text:
        :return:
        """
        html = etree.HTML(html_text)
        if not html:
            return
        # 等级 获取同一行等级数据，图片格式等级，取title信息，否则取文本信息
        user_levels_text = html.xpath('//tr/td[text()="等級" or text()="等级" or *[text()="等级"]]/'
                                      'following-sibling::td[1]/img[1]/@title'
                                      '|//tr/td[text()="等級" or text()="等级"]/'
                                      'following-sibling::td[1 and img[not(@title)]]/text()'
                                      '|//tr/td[text()="等級" or text()="等级"]/'
                                      'following-sibling::td[1 and not(img)]/text()')
        if user_levels_text:
            self.user_level = user_levels_text[0].strip()

        # 加入日期
        join_at_text = html.xpath('//tr/td[text()="加入日期" or text()="注册日期"]/following-sibling::td[1]/text()')
        if join_at_text:
            self.join_at = join_at_text[0].strip()

        # 做种体积
        # seeding 页面获取不到的话，此处再获取一次
        if not self.seeding_size:
            self.seeding_size = 0
            seeding_sizes = html.xpath('//tr/td[text()="当前上传"]/following-sibling::td[1]//'
                                       'table[tr[1][td[4 and text()="尺寸"]]]//tr[position()>1]/td[4]')
            for per_size in seeding_sizes:
                self.seeding_size += num_filesize(per_size.xpath("string(.)").strip())

        # 存在链接跳转新页面，代表较多数据量，需要使用跳转链接查询
        seeding_url_text = html.xpath('//tr/td[text()="目前做種"]/following-sibling::td[1]/'
                                      'a[1 and @target = "_blank"]/@href')
        if seeding_url_text:
            self._torrent_seeding_page = seeding_url_text[0].strip()
