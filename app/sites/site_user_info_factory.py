import requests

import log
from app.helper import ChromeHelper, SubmoduleHelper
from app.utils import RequestUtils, ExceptionUtils
from app.utils.commons import singleton
from config import Config


@singleton
class SiteUserInfoFactory(object):

    def __init__(self):
        self.__site_schema = SubmoduleHelper.import_submodules('app.sites.siteuserinfo',
                                                               filter_func=lambda _, obj: hasattr(obj, 'schema'))
        self.__site_schema.sort(key=lambda x: x.order)
        log.debug(f"【Sites】: 已经加载的站点解析 {self.__site_schema}")

    def _build_class(self, html_text):
        for site_schema in self.__site_schema:
            try:
                if site_schema.match(html_text):
                    return site_schema
            except Exception as e:
                ExceptionUtils.exception_traceback(e)

        return None

    def build(self, url, site_name, site_cookie=None, ua=None, emulate=None, proxy=False):
        if not site_cookie:
            return None
        log.debug(f"【Sites】站点 {site_name} url={url} site_cookie={site_cookie} ua={ua}")
        session = requests.Session()
        # 检测环境，有浏览器内核的优先使用仿真签到
        chrome = ChromeHelper()
        if emulate and chrome.get_status():
            if not chrome.visit(url=url, ua=ua, cookie=site_cookie):
                log.error("【Sites】%s 无法打开网站" % site_name)
                return None
            # 循环检测是否过cf
            cloudflare = chrome.pass_cloudflare()
            if not cloudflare:
                log.error("【Sites】%s 跳转站点失败" % site_name)
                return None
            # 判断是否已签到
            html_text = chrome.get_html()
        else:
            proxies = Config().get_proxies() if proxy else None
            res = RequestUtils(cookies=site_cookie,
                               session=session,
                               headers=ua,
                               proxies=proxies
                               ).get_res(url=url)
            if res and res.status_code == 200:
                if "charset=utf-8" in res.text or "charset=UTF-8" in res.text:
                    res.encoding = "UTF-8"
                else:
                    res.encoding = res.apparent_encoding
                html_text = res.text
                # 第一次登录反爬
                if html_text.find("title") == -1:
                    i = html_text.find("window.location")
                    if i == -1:
                        return None
                    tmp_url = url + html_text[i:html_text.find(";")] \
                        .replace("\"", "").replace("+", "").replace(" ", "").replace("window.location=", "")
                    res = RequestUtils(cookies=site_cookie,
                                       session=session,
                                       headers=ua,
                                       proxies=proxies
                                       ).get_res(url=tmp_url)
                    if res and res.status_code == 200:
                        if "charset=utf-8" in res.text or "charset=UTF-8" in res.text:
                            res.encoding = "UTF-8"
                        else:
                            res.encoding = res.apparent_encoding
                        html_text = res.text
                        if not html_text:
                            return None
                    else:
                        log.error("【Sites】站点 %s 被反爬限制：%s, 状态码：%s" % (site_name, url, res.status_code))
                        return None

                # 兼容假首页情况，假首页通常没有 <link rel="search" 属性
                if '"search"' not in html_text and '"csrf-token"' not in html_text:
                    res = RequestUtils(cookies=site_cookie,
                                       session=session,
                                       headers=ua,
                                       proxies=proxies
                                       ).get_res(url=url + "/index.php")
                    if res and res.status_code == 200:
                        if "charset=utf-8" in res.text or "charset=UTF-8" in res.text:
                            res.encoding = "UTF-8"
                        else:
                            res.encoding = res.apparent_encoding
                        html_text = res.text
                        if not html_text:
                            return None
            elif res is not None:
                log.error(f"【Sites】站点 {site_name} 连接失败，状态码：{res.status_code}")
                return None
            else:
                log.error(f"【Sites】站点 {site_name} 无法访问：{url}")
                return None
        # 解析站点类型
        site_schema = self._build_class(html_text)
        if not site_schema:
            log.error("【Sites】站点 %s 无法识别站点类型" % site_name)
            return None
        return site_schema(site_name, url, site_cookie, html_text, session=session, ua=ua)
