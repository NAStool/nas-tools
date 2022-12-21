# -*- coding: utf-8 -*-
"""
Created on 2022/7/26 4:28 下午
---------
@summary:
---------
@author: Boris
@email: boris_liu@foxmail.com
"""

from requests.cookies import RequestsCookieJar

import feapder.setting as setting
import feapder.utils.tools as tools
from feapder.network.downloader.base import RenderDownloader
from feapder.network.response import Response
from feapder.utils.webdriver import WebDriverPool


class SeleniumDownloader(RenderDownloader):
    webdriver_pool: WebDriverPool = None

    @property
    def _webdriver_pool(self):
        if not self.__class__.webdriver_pool:
            self.__class__.webdriver_pool = WebDriverPool(**setting.WEBDRIVER)

        return self.__class__.webdriver_pool

    def download(self, request) -> Response:
        requests_kwargs = request.requests_kwargs

        headers = requests_kwargs.get("headers")
        user_agent = headers.get("User-Agent") or headers.get("user-agent")

        cookies = requests_kwargs.get("cookies")
        if cookies and isinstance(cookies, RequestsCookieJar):
            cookies = cookies.get_dict()

        if not cookies:
            cookie_str = headers.get("Cookie") or headers.get("cookie")
            if cookie_str:
                cookies = tools.get_cookies_from_str(cookie_str)

        proxy = request.proxy()
        browser = self._webdriver_pool.get(user_agent=user_agent, proxy=proxy)

        url = request.url
        if requests_kwargs.get("params"):
            url = tools.joint_url(url, requests_kwargs.get("params"))

        try:
            browser.get(url)
            if cookies:
                browser.delete_all_cookies()
                browser.cookies = cookies
                browser.get(url)
            if request.render_time:
                tools.delay_time(request.render_time)

            html = browser.page_source
            response = Response.from_dict(
                {
                    "url": browser.current_url,
                    "cookies": browser.cookies,
                    "_content": html.encode(),
                    "status_code": 200,
                    "elapsed": 666,
                    "headers": {
                        "User-Agent": browser.execute_script(
                            "return navigator.userAgent"
                        ),
                        "Cookie": tools.cookies2str(browser.cookies),
                    },
                }
            )

            response.browser = browser
            return response
        except Exception as e:
            self._webdriver_pool.remove(browser)
            raise e

    def close(self, response: Response):
        if response is not None and hasattr(response, "browser"):
            self._webdriver_pool.remove(response.browser)

    def put_back(self, driver):
        """
        释放浏览器对象
        """
        self._webdriver_pool.put(driver)

    def close_all(self):
        """
        关闭所有浏览器
        """
        self._webdriver_pool.close()
