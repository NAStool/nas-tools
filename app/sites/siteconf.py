# 非常规RSS站点
from app.utils.string_utils import StringUtils

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
        'HR': [],
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
        'HR': [],
        'PEER_COUNT': [],
    },
    'hdchina.org': {
        'FREE': ["//img[@class='pro_free']"],
        '2XFREE': [],
        'HR': [],
        'PEER_COUNT': [],
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
    'azusa.ru': {
        'FREE': ["//font[@class='free']"],
        '2XFREE': [],
        'HR': [],
        'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
    }
}


def get_extrasite_conf(url):
    """
    根据地址找到RSS_EXTRA_SITES对应配置
    """
    for k, v in RSS_EXTRA_SITES.items():
        if StringUtils.url_equal(k, url):
            return v
    return None


def get_grapsite_conf(url):
    """
    根据地址找到RSS_SITE_GRAP_CONF对应配置
    """
    for k, v in RSS_SITE_GRAP_CONF.items():
        if StringUtils.url_equal(k, url):
            return v
    return {}
