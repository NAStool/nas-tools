import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from config import Config

urllib3.disable_warnings(InsecureRequestWarning)


class RequestUtils:
    _headers = None
    _cookies = None
    _proxies = None
    _timeout = 20
    _session = None

    def __init__(self,
                 headers=None,
                 cookies=None,
                 proxies=False,
                 session=None,
                 timeout=None,
                 referer=None,
                 content_type=None):
        if not content_type:
            content_type = "application/x-www-form-urlencoded; charset=UTF-8"
        if headers:
            if isinstance(headers, str):
                self._headers = {
                    "Content-Type": content_type,
                    "User-Agent": f"{headers}"
                }
            else:
                self._headers = headers
        else:
            self._headers = {
                "Content-Type": content_type,
                "User-Agent": Config().get_ua()
            }
        if referer:
            self._headers.update({
                "referer": referer
            })
        if cookies:
            if isinstance(cookies, str):
                self._cookies = self.cookie_parse(cookies)
            else:
                self._cookies = cookies
        if proxies:
            self._proxies = proxies
        if session:
            self._session = session
        if timeout:
            self._timeout = timeout

    def post(self, url, params=None, json=None):
        if json is None:
            json = {}
        try:
            if self._session:
                return self._session.post(url,
                                          data=params,
                                          verify=False,
                                          headers=self._headers,
                                          proxies=self._proxies,
                                          timeout=self._timeout,
                                          json=json)
            else:
                return requests.post(url,
                                     data=params,
                                     verify=False,
                                     headers=self._headers,
                                     proxies=self._proxies,
                                     timeout=self._timeout,
                                     json=json)
        except requests.exceptions.RequestException:
            return None

    def get(self, url, params=None):
        try:
            if self._session:
                r = self._session.get(url,
                                      verify=False,
                                      headers=self._headers,
                                      proxies=self._proxies,
                                      timeout=self._timeout,
                                      params=params)
            else:
                r = requests.get(url,
                                 verify=False,
                                 headers=self._headers,
                                 proxies=self._proxies,
                                 timeout=self._timeout,
                                 params=params)
            return str(r.content, 'utf-8')
        except requests.exceptions.RequestException:
            return None

    def get_res(self, url, params=None, allow_redirects=True):
        try:
            if self._session:
                return self._session.get(url,
                                         params=params,
                                         verify=False,
                                         headers=self._headers,
                                         proxies=self._proxies,
                                         cookies=self._cookies,
                                         timeout=self._timeout,
                                         allow_redirects=allow_redirects)
            else:
                return requests.get(url,
                                    params=params,
                                    verify=False,
                                    headers=self._headers,
                                    proxies=self._proxies,
                                    cookies=self._cookies,
                                    timeout=self._timeout,
                                    allow_redirects=allow_redirects)
        except requests.exceptions.RequestException:
            return None

    def post_res(self, url, params=None, allow_redirects=True, files=None, json=None):
        try:
            if self._session:
                return self._session.post(url,
                                          data=params,
                                          verify=False,
                                          headers=self._headers,
                                          proxies=self._proxies,
                                          cookies=self._cookies,
                                          timeout=self._timeout,
                                          allow_redirects=allow_redirects,
                                          files=files,
                                          json=json)
            else:
                return requests.post(url,
                                     data=params,
                                     verify=False,
                                     headers=self._headers,
                                     proxies=self._proxies,
                                     cookies=self._cookies,
                                     timeout=self._timeout,
                                     allow_redirects=allow_redirects,
                                     files=files,
                                     json=json)
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
