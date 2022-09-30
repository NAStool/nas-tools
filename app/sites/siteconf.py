from app.utils import StringUtils


class SiteConf:
    # 非常规RSS站点
    RSS_EXTRA_SITES = {
        'blutopia.xyz': 'Unit3D',
        'desitorrents.tv': 'Unit3D',
        'jptv.club': 'Unit3D',
        'www.torrentseeds.org': 'Unit3D',
        'beyond-hd.me': 'beyondhd',
    }
    # 检测种子促销的站点XPATH，不在此清单的无法开启仅RSS免费种子功能
    RSS_SITE_GRAP_CONF = {
        'pthome.net': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'ptsbao.club': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'totheglory.im': {
            'FREE': ["//img[@class='topic'][contains(@src,'ico_free.gif')]"],
            '2XFREE': [],
            'HR': ["//img[@src='/pic/hit_run.gif']"],
            'PEER_COUNT': ["//span[@id='dlstatus']"],
        },
        'www.beitai.pt': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'hdtime.org': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'www.haidan.video': {
            'FREE': ["//img[@class='pro_free'][@title='免费']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': ["//div[@class='torrent']/div[1]/div[1]/div[3]"],
        },
        'kp.m-team.cc': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'lemonhd.org': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"]
        },
        'discfan.net': {
            'FREE': ["//font[@class='free'][text()='免費']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'pt.sjtu.edu.cn': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': [],
        },
        'nanyangpt.com': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': [],
        },
        'audiences.me': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': ["//img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"]
        },
        'pterclub.com': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': ["(//td[@align='left' and @class='rowfollow' and @valign='top']/b[1])[3]"]
        },
        'et8.org': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'pt.keepfrds.com': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'www.pttime.org': {
            'FREE': ["//font[@class='free']", "//font[@class='zeroupzerodown']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        '1ptba.com': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': [],
            'HR': ["//img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'www.tjupt.org': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoup'][text()='2X']"],
            'HR': ["//font[@color='red'][text()='Hit&Run']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'hdhome.org': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'hdsky.me': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'hdcity.city': {
            'FREE': ["//img[@class='pro_free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': [],
        },
        'hdcity.leniter.org': {
            'FREE': ["//img[@class='pro_free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': [],
        },
        'hdcity.work': {
            'FREE': ["//img[@class='pro_free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': [],
        },
        'hdcity4.leniter.org': {
            'FREE': ["//img[@class='pro_free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': [],
        },
        'open.cd': {
            'FREE': ["//img[@class='pro_free']"],
            '2XFREE': ["//img[@class='pro_free2up']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'ourbits.club': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': ["//img[@class='hitandrun']"],
            'PEER_COUNT': [],
        },
        'pt.btschool.club': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'pt.eastgame.org': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'pt.soulvoice.club': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': [],
            'HR': ["//img[@class='hitandrun']"],
            'PEER_COUNT': [],
        },
        'springsunday.net': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': ["//img[@class='hitandrun']"],
            'PEER_COUNT': [],
        },
        'www.htpt.cc': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'chdbits.co': {
            'FREE': ["//img[@class='pro_free']"],
            '2XFREE': [],
            'HR': ["//b[text()='H&amp;R:&nbsp;']"],
            'PEER_COUNT': [],
        },
        'hdchina.org': {
            'FREE': ["//img[@class='pro_free']"],
            '2XFREE': ["//img[@class='pro_free2up"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        "ccfbits.org": {
            'FREE': ["//font[@color='red'][text()='本种子不计下载量，只计上传量!']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': [],
        },
        'u2.dmhy.org': {
            'FREE': ["//img[@class='pro_free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': [],
        },
        'www.hdarea.co': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'hdatmos.club': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'avgv.cc': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'hdfans.org': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'hdpt.xyz': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'azusa.ru': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'hdmayi.com': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'hdzone.me': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'gainbound.net': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'hdvideo.one': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        '52pt.site': {
            'FREE': ["//font[@class='free'][text()='免费（下载量不统计）']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2x 免费(上传量双倍 下载量不统计)']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'pt.msg.vg': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'kamept.com': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'carpt.net': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': ["//img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'club.hares.top': {
            'FREE': ["//b[@class='free'][text()='免费']"],
            '2XFREE': ["//b[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'www.hddolby.com': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'piggo.me': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': ["//img[@class='hitandrun']"],
            'PEER_COUNT': [],
        },
        'pt.0ff.cc': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': ["//img[@class='hitandrun']"],
            'PEER_COUNT': [],
        },
        'wintersakura.net': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'pt.hdupt.com': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'pt.upxin.net': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'www.nicept.net': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'ptchina.org': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'www.hd.ai': {
            'FREE': ["//img[@class='pro_free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': [],
        },
        'hhanclub.top': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': [],
        },
    }
    # 公共BT站点
    PUBLIC_TORRENT_SITES = {
        'rarbg.to': {
            "parser": "rarbg",
            "proxy": True,
            "language": "en"
        },
        'dmhy.org': {
            "proxy": True
        },
        'eztv.re': {
            "proxy": True,
            "language": "en"
        },
        'acg.rip': {
            "proxy": False
        },
        'thepiratebay.org': {
            "proxy": True,
            "render": True,
            "language": "en"
        },
        'nyaa.si': {
            "proxy": True,
            "language": "en"
        },
        '1337x.to': {
            "proxy": True,
            "language": "en"
        },
        'ext.to': {
            "proxy": True,
            "language": "en"
        },
        'torrentgalaxy.to': {
            "proxy": True,
            "language": "en"
        },
        'mikanani.me': {
            "proxy": False
        },
        'gaoqing.fm': {
            "proxy": False
        },
        'www.mp4ba.vip': {
            "proxy": False
        },
        'www.miobt.com': {
            "proxy": True
        },
        'katcr.to': {
            "proxy": True
        }
    }

    def get_extrasite_conf(self, url):
        """
        根据地址找到RSS_EXTRA_SITES对应配置
        """
        for k, v in self.RSS_EXTRA_SITES.items():
            if StringUtils.url_equal(k, url):
                return v
        return None

    def get_grapsite_conf(self, url):
        """
        根据地址找到RSS_SITE_GRAP_CONF对应配置
        """
        for k, v in self.RSS_SITE_GRAP_CONF.items():
            if StringUtils.url_equal(k, url):
                return v
        return {}

    def is_public_site(self, url):
        """
        判断是否为公开BT站点
        """
        _, netloc = StringUtils.get_url_netloc(url)
        if netloc in self.PUBLIC_TORRENT_SITES.keys():
            return True
        return False

    def get_public_sites(self, url=None):
        """
        查询所有公开BT站点
        """
        if url:
            _, netloc = StringUtils.get_url_netloc(url)
            return self.PUBLIC_TORRENT_SITES.get(netloc)
        else:
            return self.PUBLIC_TORRENT_SITES.items()
