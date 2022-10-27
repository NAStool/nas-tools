import requests
import urllib3

from config import Config


class RequestUtils:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    __headers = None
    __cookies = None
    __proxies = None
    __timeout = 20
    __session = None

    def __init__(self,
                 headers=None,
                 cookies=None,
                 proxies=False,
                 session=None,
                 timeout=None,
                 referer=None):
        if headers:
            if isinstance(headers, str):
                self.__headers = {
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "User-Agent": f"{headers}"
                }
            else:
                self.__headers = headers
        else:
            self.__headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "User-Agent": Config().get_ua()
            }
        if referer:
            self.__headers.update({
                "referer": referer
            })
        if cookies:
            if isinstance(cookies, str):
                self.__cookies = self.cookie_parse(cookies)
            else:
                self.__cookies = cookies
        if proxies:
            self.__proxies = proxies
        if session:
            self.__session = session
        if timeout:
            self.__timeout = timeout

    def post(self, url, params=None, json=None):
        if json is None:
            json = {}
        try:
            if self.__session:
                return self.__session.post(url,
                                           data=params,
                                           verify=False,
                                           headers=self.__headers,
                                           proxies=self.__proxies,
                                           json=json)
            else:
                return requests.post(url,
                                     data=params,
                                     verify=False,
                                     headers=self.__headers,
                                     proxies=self.__proxies,
                                     json=json)
        except requests.exceptions.RequestException:
            return None

    def get(self, url, params=None):
        try:
            if self.__session:
                r = self.__session.get(url,
                                       verify=False,
                                       headers=self.__headers,
                                       proxies=self.__proxies,
                                       params=params,
                                       timeout=self.__timeout)
            else:
                r = requests.get(url,
                                 verify=False,
                                 headers=self.__headers,
                                 proxies=self.__proxies,
                                 params=params,
                                 timeout=self.__timeout)
            return str(r.content, 'UTF-8')
        except requests.exceptions.RequestException:
            return None

    def get_res(self, url, params=None, allow_redirects=True):
        try:
            if self.__session:
                return self.__session.get(url,
                                          params=params,
                                          verify=False,
                                          headers=self.__headers,
                                          proxies=self.__proxies,
                                          cookies=self.__cookies,
                                          timeout=self.__timeout,
                                          allow_redirects=allow_redirects)
            else:
                return requests.get(url,
                                    params=params,
                                    verify=False,
                                    headers=self.__headers,
                                    proxies=self.__proxies,
                                    cookies=self.__cookies,
                                    timeout=self.__timeout,
                                    allow_redirects=allow_redirects)
        except requests.exceptions.RequestException:
            return None

    def post_res(self, url, params=None, allow_redirects=True, files=None):
        try:
            if self.__session:
                return self.__session.post(url,
                                           data=params,
                                           verify=False,
                                           headers=self.__headers,
                                           proxies=self.__proxies,
                                           cookies=self.__cookies,
                                           allow_redirects=allow_redirects,
                                           files=files)
            else:
                return requests.post(url,
                                     data=params,
                                     verify=False,
                                     headers=self.__headers,
                                     proxies=self.__proxies,
                                     cookies=self.__cookies,
                                     allow_redirects=allow_redirects,
                                     files=files)
        except requests.exceptions.RequestException:
            return None

    @staticmethod
    def cookie_parse(cookies_str, array=False):
        if not cookies_str:
            return {}
        cookie_dict = {}
        cookies = cookies_str.split(';')
        for cookie in cookies:
            cstr = cookie.split('=')
            if len(cstr) > 1:
                cookie_dict[cstr[0].strip()] = cstr[1].strip()
        if array:
            cookiesList = []
            for cookieName, cookieValue in cookie_dict.items():
                cookies = {'name': cookieName, 'value': cookieValue}
                cookiesList.append(cookies)
            return cookiesList
        return cookie_dict
