# -*- coding: utf-8 -*-
import re
from abc import ABCMeta, abstractmethod

import log
from app.utils import StringUtils


class _ISiteSigninHandler(metaclass=ABCMeta):
    """
    实现站点签到的基类，所有站点签到类都需要继承此类，并实现match和signin方法
    实现类放置到sitesignin目录下将会自动加载
    """
    # 匹配的站点Url，每一个实现类都需要设置为自己的站点Url
    site_url = ""

    @abstractmethod
    def match(self, url):
        """
        根据站点Url判断是否匹配当前站点签到类，大部分情况使用默认实现即可
        :param url: 站点Url
        :return: 是否匹配，如匹配则会调用该类的signin方法
        """
        return True if StringUtils.url_equal(url, self.site_url) else False

    @abstractmethod
    def signin(self, site_info: dict):
        """
        执行签到操作
        :param site_info: 站点信息，含有站点Url、站点Cookie、UA等信息
        :return: True|False,签到结果信息
        """
        pass

    @staticmethod
    def sign_in_result(html_res, regexs):
        """
        判断是否签到成功
        """
        html_text = re.sub(r"#\d+", "", re.sub(r"\d+px", "", html_res))
        for regex in regexs:
            if re.search(str(regex), html_text):
                return True
        return False

    def info(self, msg):
        """
        记录INFO日志
        :param msg: 日志信息
        """
        log.info(f"【Sites】{self.__class__.__name__} - {msg}")

    def warn(self, msg):
        """
        记录WARN日志
        :param msg: 日志信息
        """
        log.warn(f"【Sites】{self.__class__.__name__} - {msg}")

    def error(self, msg):
        """
        记录ERROR日志
        :param msg: 日志信息
        """
        log.error(f"【Sites】{self.__class__.__name__} - {msg}")

    def debug(self, msg):
        """
        记录Debug日志
        :param msg: 日志信息
        """
        log.debug(f"【Sites】{self.__class__.__name__} - {msg}")
