# -*- coding: utf-8 -*-
import re
from abc import ABCMeta, abstractmethod
from urllib.parse import urljoin, urlsplit

import requests

from utils.http_utils import RequestUtils


class ISiteUserInfo(metaclass=ABCMeta):
    # 用户信息
    username = None
    userid = None

    # 流量信息
    upload = 0
    download = 0
    ratio = 0

    # 种子信息
    seeding = 0
    leeching = 0
    uploaded = 0
    completed = 0
    incomplete = 0
    seeding_size = 0
    leeching_size = 0
    uploaded_size = 0
    completed_size = 0
    incomplete_size = 0

    # 用户详细信息
    user_level = None
    join_at = None
    bonus = 0.0

    # 内部数据
    _base_url = None
    _site_cookie = None
    _index_html = None

    # 站点模版
    _site_schema = None
    # 站点页面
    _brief_page = "index.php"
    _user_detail_page = "userdetails.php?id="
    _user_traffic_page = "index.php"
    _torrent_seeding_page = "getusertorrentlistajax.php?userid="
    _session = requests.Session()

    def __init__(self, url, site_cookie, index_html):
        super().__init__()
        split_url = urlsplit(url)
        self._base_url = f"{split_url.scheme}://{split_url.netloc}"
        self._site_cookie = site_cookie
        self._index_html = index_html

    def site_schema(self):
        """
        站点解析模型
        :return:
        """
        return self._site_schema

    def parse(self):
        """
        解析站点信息
        :return:
        """
        self._parse_site_page(self._index_html)
        if self._brief_page:
            self._parse_user_base_info(self._get_page_content(urljoin(self._base_url, self._brief_page)))
        if self._user_traffic_page:
            self._parse_user_traffic_info(self._get_page_content(urljoin(self._base_url, self._user_traffic_page)))
        if self._user_detail_page:
            self._parse_user_detail_info(self._get_page_content(urljoin(self._base_url, self._user_detail_page)))

        if self._torrent_seeding_page:
            # 第一页
            next_page = self._parse_user_torrent_seeding_info(
                self._get_page_content(urljoin(self._base_url, self._torrent_seeding_page)))

            # 其他页处理
            while next_page:
                next_page = self._parse_user_torrent_seeding_info(
                    self._get_page_content(urljoin(urljoin(self._base_url, self._torrent_seeding_page), next_page)),
                    multi_page=True)

    @staticmethod
    def _prepare_html_text(html_text):
        """
        处理掉HTML中的干扰部分
        """
        return re.sub(r"#\d+", "", re.sub(r"\d+px", "", html_text))

    def _get_page_content(self, url):
        """
        :param url:
        :return:
        """
        res = RequestUtils(cookies=self._site_cookie, session=self._session).get_res(url=url)
        if res and res.status_code == 200:
            if "charset=utf-8" in res.text or "charset=UTF-8" in res.text:
                res.encoding = "UTF-8"
            else:
                res.encoding = res.apparent_encoding
            return res.text

        return ""

    @abstractmethod
    def _parse_site_page(self, html_text):
        """
        解析站点相关信息页面
        :param html_text:
        :return:
        """
        pass

    @abstractmethod
    def _parse_user_base_info(self, html_text):
        """
        解析用户基础信息
        :param html_text:
        :return:
        """
        pass

    @abstractmethod
    def _parse_user_traffic_info(self, html_text):
        """
        解析用户的上传，下载，分享率等信息
        :param html_text:
        :return:
        """
        pass

    @abstractmethod
    def _parse_user_torrent_seeding_info(self, html_text, multi_page=False):
        """
        解析用户的做种相关信息
        :param html_text:
        :param multi_page: 是否多页数据
        :return: 下页地址
        """
        pass

    @abstractmethod
    def _parse_user_detail_info(self, html_text):
        """
        解析用户的详细信息
        加入时间/等级/魔力值等
        :param html_text:
        :return:
        """
        pass
