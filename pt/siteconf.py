# 非常规RSS站点
RSS_EXTRA_SITES = {
    'blutopia.xyz': 'Unit3D',
    'desitorrents.tv': 'Unit3D',
    'jptv.club': 'Unit3D',
    'www.torrentseeds.org': 'Unit3D',
    'beyond-hd.me': 'beyondhd',
}
# 检测种子促销的PT站点XPATH，不在此清单的无法开启仅RSS免费种子功能
RSS_SITE_GRAP_CONF = {
    'pthome.net': {
        'FREE': ["//font[@class='free']"],
        '2XFREE': ["//font[@class='twoupfree']"],
        'HR': []
    },
    'ptsbao.club': {
        'FREE': ["//font[@class='free']"],
        '2XFREE': ["//font[@class='twoupfree']"],
        'HR': []
    },
    'totheglory.im': {
        'FREE': ["//img[@class='topic'][contains(@src,'ico_free.gif')]"],
        '2XFREE': [],
        'HR': ["//img[@src='/pic/hit_run.gif']"]
    },
    'www.beitai.pt': {
        'FREE': ["//font[@class='free']"],
        '2XFREE': ["//font[@class='twoupfree']"],
        'HR': []
    },
    'hdtime.org': {
        'FREE': ["//font[@class='free']"],
        '2XFREE': ["//font[@class='twoupfree']"],
        'HR': []
    },
    'www.haidan.video': {
        'FREE': ["//img[@class='pro_free'][@title='免费']"],
        '2XFREE': [],
        'HR': []
    },
    'kp.m-team.cc': {
        'FREE': ["//font[@class='free']"],
        '2XFREE': [],
        'HR': []
    },
    'lemonhd.org': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': [],
        'HR': []
    },
    'discfan.net': {
        'FREE': ["//font[@class='free'][text()='免費']"],
        '2XFREE': [],
        'HR': []
    },
    'pt.sjtu.edu.cn': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': [],
        'HR': []
    },
    'nanyangpt.com': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': [],
        'HR': []
    },
    'audiences.me': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': ["//font[@class='twoupfree']"],
        'HR': ["//img[@class='hitandrun']"]
    },
    'pterclub.com': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
        'HR': []
    },
    'et8.org': {
        'FREE': ["//font[@class='free']"],
        '2XFREE': ["//font[@class='twoupfree']"],
        'HR': []
    },
    'pt.keepfrds.com': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': ["//font[@class='twoupfree']"],
        'HR': []
    },
    'www.pttime.org': {
        'FREE': ["//font[@class='free']", "//font[@class='zeroupzerodown']"],
        '2XFREE': ["//font[@class='twoupfree']"],
        'HR': []
    },
    '1ptba.com': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': [],
        'HR': ["//img[@class='hitandrun']"]
    },
    'www.tjupt.org': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': ["//font[@class='twoup'][text()='2X']"],
        'HR': ["//font[@color='red'][text()='Hit&Run']"]
    },
    'hdhome.org': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
        'HR': []
    },
    'hdsky.me': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
        'HR': []
    },
    'hdcity.city': {
        'FREE': ["//img[@class='pro_free']"],
        '2XFREE': [],
        'HR': []
    },
    'hdcity.leniter.org': {
        'FREE': ["//img[@class='pro_free']"],
        '2XFREE': [],
        'HR': []
    },
    'hdcity.work': {
        'FREE': ["//img[@class='pro_free']"],
        '2XFREE': [],
        'HR': []
    },
    'hdcity4.leniter.org': {
        'FREE': ["//img[@class='pro_free']"],
        '2XFREE': [],
        'HR': []
    },
    'open.cd': {
        'FREE': ["//img[@class='pro_free']"],
        '2XFREE': ["//img[@class='pro_free2up']"],
        'HR': []
    },
    'ourbits.club': {
        'FREE': ["//font[@class='free']"],
        '2XFREE': ["//font[@class='twoupfree']"],
        'HR': []
    },
    'pt.btschool.club': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
        'HR': []
    },
    'pt.eastgame.org': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
        'HR': []
    },
    'pt.soulvoice.club': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': [],
        'HR': ["//img[@class='hitandrun']"]
    },
    'springsunday.net': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
        'HR': ["//img[@class='hitandrun']"]
    },
    'www.htpt.cc': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': [],
        'HR': []
    },
    'chdbits.co': {
        'FREE': ["//img[@class='pro_free']"],
        '2XFREE': [],
        'HR': []
    },
    'hdchina.org': {
        'FREE': ["//img[@class='pro_free']"],
        '2XFREE': [],
        'HR': []
    },
    "ccfbits.org": {
        'FREE': ["//font[@color='red'][text()='本种子不计下载量，只计上传量!']"],
        '2XFREE': [],
        'HR': []
    },
    'u2.dmhy.org': {
        'FREE': ["//img[@class='pro_free']"],
        '2XFREE': [],
        'HR': []
    },
    'www.hdarea.co': {
        'FREE': ["//img[@class='pro_free'][@title='免费']"],
        '2XFREE': ["//img[@class='pro_free'][@title='2X免费']"],
        'HR': []
    },
    'hdatmos.club': {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
        'HR': []
    }
}
