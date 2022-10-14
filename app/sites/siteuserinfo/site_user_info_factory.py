import time

import requests
from lxml import etree

import log
from app.helper import ChromeHelper, CHROME_LOCK
from app.sites.siteuserinfo.discuz import DiscuzUserInfo
from app.sites.siteuserinfo.gazelle import GazelleUserInfo
from app.sites.siteuserinfo.ipt_project import IptSiteUserInfo
from app.sites.siteuserinfo.nexus_php import NexusPhpSiteUserInfo
from app.sites.siteuserinfo.nexus_project import NexusProjectSiteUserInfo
from app.sites.siteuserinfo.small_horse import SmallHorseSiteUserInfo
from app.utils import RequestUtils


class SiteUserInfoFactory(object):
    @staticmethod
    def build(url, site_name, site_cookie=None, ua=None, emulate=None):
        if not site_cookie:
            return None
        log.debug(f"【Sites】站点 {site_name} site_cookie={site_cookie} ua={ua}")
        session = requests.Session()
        # 检测环境，有浏览器内核的优先使用仿真签到
        chrome = ChromeHelper()
        if emulate and chrome.get_status():
            with CHROME_LOCK:
                try:
                    chrome.visit(url=url, ua=ua, cookie=site_cookie)
                except Exception as err:
                    print(str(err))
                    log.error("【Sites】%s 无法打开网站" % site_name)
                    return None
                # 循环检测是否过cf
                cloudflare = False
                for i in range(0, 10):
                    if chrome.get_title() != "Just a moment...":
                        cloudflare = True
                        break
                    time.sleep(1)
                if not cloudflare:
                    log.error("【Sites】%s 跳转站点失败" % site_name)
                    return None
                # 判断是否已签到
                html_text = chrome.get_html()
        else:
            res = RequestUtils(cookies=site_cookie, session=session, headers=ua).get_res(url=url)
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
                    res = RequestUtils(cookies=site_cookie, session=session, headers=ua).get_res(url=tmp_url)
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
                if '"search"' not in html_text:
                    res = RequestUtils(cookies=site_cookie, session=session, headers=ua).get_res(url=url + "/index.php")
                    if res and res.status_code == 200:
                        if "charset=utf-8" in res.text or "charset=UTF-8" in res.text:
                            res.encoding = "UTF-8"
                        else:
                            res.encoding = res.apparent_encoding
                        html_text = res.text
                        if not html_text:
                            return None
            elif not res:
                log.error("【Sites】站点 %s 连接失败：%s" % (site_name, url))
                return None
            else:
                log.error("【Sites】站点 %s 获取流量数据失败，状态码：%s" % (site_name, res.status_code))
                return None

        # 解析站点代码
        html = etree.HTML(html_text)
        printable_text = html.xpath("string(.)") if html else ""

        if "Powered by Gazelle" in printable_text:
            return GazelleUserInfo(site_name, url, site_cookie, html_text, session=session, ua=ua)

        if "Powered by Discuz!" in printable_text:
            return DiscuzUserInfo(site_name, url, site_cookie, html_text, session=session, ua=ua)

        if "NexusPHP" in html_text in html_text:
            return NexusPhpSiteUserInfo(site_name, url, site_cookie, html_text, session=session, ua=ua)

        if "Nexus Project" in html_text:
            return NexusProjectSiteUserInfo(site_name, url, site_cookie, html_text, session=session, ua=ua)

        if "Small Horse" in html_text:
            return SmallHorseSiteUserInfo(site_name, url, site_cookie, html_text, session=session, ua=ua)

        if "IPTorrents" in html_text:
            return IptSiteUserInfo(site_name, url, site_cookie, html_text, session=session, ua=ua)
        # 默认NexusPhp
        return NexusPhpSiteUserInfo(site_name, url, site_cookie, html_text, session=session, ua=ua)
