from pt.siteuserinfo.nexus_php import NexusPhpSiteUserInfo
from pt.siteuserinfo.nexus_project import NexusProjectSiteUserInfo
from utils.http_utils import RequestUtils


class SiteUserInfoFactory(object):
    @staticmethod
    def build(url, user_agent=None, site_cookie=None):
        res = RequestUtils(headers=user_agent, cookies=site_cookie).get_res(url=url)
        if res and res.status_code == 200:
            res.encoding = res.apparent_encoding
            html_text = res.text
        else:
            return None

        if "NexusPHP" in html_text in html_text:
            return NexusPhpSiteUserInfo(url, user_agent, site_cookie, html_text)

        if "Nexus Project" in html_text:
            return NexusProjectSiteUserInfo(url, user_agent, site_cookie, html_text)

        # 默认认为是 NexusPHP
        return NexusPhpSiteUserInfo(url, user_agent, site_cookie, html_text)
