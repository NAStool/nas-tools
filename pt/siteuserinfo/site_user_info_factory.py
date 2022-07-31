import requests
from lxml import etree

from pt.siteuserinfo.discuz import DiscuzUserInfo
from pt.siteuserinfo.gazelle import GazelleUserInfo
from pt.siteuserinfo.nexus_php import NexusPhpSiteUserInfo
from pt.siteuserinfo.nexus_project import NexusProjectSiteUserInfo
from pt.siteuserinfo.ipt_project import IptSiteUserInfo
from pt.siteuserinfo.small_horse import SmallHorseSiteUserInfo
from utils.http_utils import RequestUtils
import log


class SiteUserInfoFactory(object):
    @staticmethod
    def build(url, site_name, site_cookie=None):
        if not site_cookie:
            return None
        session = requests.Session()
        res = RequestUtils(cookies=site_cookie, session=session).get_res(url=url)
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
                res = RequestUtils(cookies=site_cookie, session=session).get_res(url=tmp_url)
                if res and res.status_code == 200:
                    if "charset=utf-8" in res.text or "charset=UTF-8" in res.text:
                        res.encoding = "UTF-8"
                    else:
                        res.encoding = res.apparent_encoding
                    html_text = res.text
                    if not html_text:
                        return None
                else:
                    log.error("【PT】站点 %s 被反爬限制：%s, 状态码：%s" % (site_name, url, res.status_code))
                    return None

            # 兼容假首页情况，假首页通常没有 <link rel="search" 属性
            if '"search"' not in html_text:
                res = RequestUtils(cookies=site_cookie, session=session).get_res(url=url+"/index.php")
                if res and res.status_code == 200:
                    if "charset=utf-8" in res.text or "charset=UTF-8" in res.text:
                        res.encoding = "UTF-8"
                    else:
                        res.encoding = res.apparent_encoding
                    html_text = res.text
                    if not html_text:
                        return None

            html = etree.HTML(html_text)
            printable_text = html.xpath("string(.)") if html else ""

            if "Powered by Gazelle" in printable_text:
                return GazelleUserInfo(site_name, url, site_cookie, html_text, session=session)

            if "Powered by Discuz!" in printable_text:
                return DiscuzUserInfo(site_name, url, site_cookie, html_text, session=session)

            if "NexusPHP" in html_text in html_text:
                return NexusPhpSiteUserInfo(site_name, url, site_cookie, html_text, session=session)

            if "Nexus Project" in html_text:
                return NexusProjectSiteUserInfo(site_name, url, site_cookie, html_text, session=session)

            if "Small Horse" in html_text:
                return SmallHorseSiteUserInfo(site_name, url, site_cookie, html_text, session=session)

            if "IPTorrents" in html_text:
                return IptSiteUserInfo(site_name, url, site_cookie, html_text, session=session)
            # 默认NexusPhp
            return NexusPhpSiteUserInfo(site_name, url, site_cookie, html_text, session=session)
        elif not res:
            log.error("【PT】站点 %s 连接失败：%s" % (site_name, url))
            return None
        else:
            log.error("【PT】站点 %s 获取流量数据失败，状态码：%s" % (site_name, res.status_code))
