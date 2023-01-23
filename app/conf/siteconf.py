class SiteConf:

    # 站点签到支持的识别XPATH
    SITE_CHECKIN_XPATH = [
        '//a[@id="signed"]',
        '//a[contains(@href, "attendance")]',
        '//a[contains(text(), "签到")]',
        '//a/b[contains(text(), "签 到")]',
        '//span[@id="sign_in"]/a',
        '//a[contains(@href, "addbonus")]',
        '//input[@class="dt_button"][contains(@value, "打卡")]',
        '//a[contains(@href, "sign_in")]',
        '//a[contains(@onclick, "do_signin")]',
        '//a[@id="do-attendance"]'
    ]

    # 站点详情页字幕下载链接识别XPATH
    SITE_SUBTITLE_XPATH = [
        '//td[@class="rowhead"][text()="字幕"]/following-sibling::td//a/@href',
    ]

    # 站点登录界面元素XPATH
    SITE_LOGIN_XPATH = {
        "username": [
            '//input[@name="username"]'
        ],
        "password": [
            '//input[@name="password"]'
        ],
        "captcha": [
            '//input[@name="imagestring"]',
            '//input[@name="captcha"]'
        ],
        "captcha_img": [
            '//img[@alt="CAPTCHA"]/@src',
            '//img[@alt="SECURITY CODE"]/@src',
            '//img[@id="LAY-user-get-vercode"]/@src'
        ],
        "submit": [
            '//input[@type="submit"]',
            '//button[@type="submit"]',
            '//button[@lay-filter="login"]',
            '//button[@lay-filter="formLogin"]',
            '//input[@type="button"][@value="登录"]'
        ],
        "error": [
            "//table[@class='main']//td[@class='text']/text()"
        ],
        "twostep": [
            '//input[@name="two_step_code"]',
            '//input[@name="2fa_secret"]'
        ]
    }

    # 检测种子促销的站点XPATH，不在此清单的无法开启仅RSS免费种子功能
    RSS_SITE_GRAP_CONF = {
        'jptv.club': {
            'FREE': ["//span/i[@class='fas fa-star text-gold']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': ["//span[@class='badge-extra text-green']"],
        },
        'pthome.net': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'ptsbao.club': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
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
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'hdtime.org': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
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
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'lemonhd.org': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"]
        },
        'discfan.net': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'pt.sjtu.edu.cn': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': [],
        },
        'nanyangpt.com': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': [],
        },
        'audiences.me': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': ["//h1[@id='top']/img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"]
        },
        'pterclub.com': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["(//td[@align='left' and @class='rowfollow' and @valign='top']/b[1])[3]"]
        },
        'et8.org': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'pt.keepfrds.com': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'www.pttime.org': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']", "//h1[@id='top']/b/font[@class='zeroupzerodown']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        '1ptba.com': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': [],
            'HR': ["//h1[@id='top']/img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'www.tjupt.org': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//font[@class='twoup'][text()='2X']"],
            'HR': ["//font[@color='red'][text()='Hit&Run']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'hdhome.org': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'hdsky.me': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
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
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': ["//h1[@id='top']/img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'pt.btschool.club': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'pt.eastgame.org': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'pt.soulvoice.club': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': [],
            'HR': ["//img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'springsunday.net': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': ["//h1[@id='top']/img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'www.htpt.cc': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': [],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'chdbits.co': {
            'FREE': ["//h1[@id='top']/img[@class='pro_free']"],
            '2XFREE': [],
            'HR': ["//b[contains(text(),'H&R:')]"],
            'PEER_COUNT': [],
        },
        'hdchina.org': {
            'RENDER': True,
            'FREE': ["//h2[@id='top']/img[@class='pro_free']"],
            '2XFREE': ["//h2[@id='top']/img[@class='pro_free2up']"],
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
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'hdatmos.club': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'avgv.cc': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'hdfans.org': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'hdpt.xyz': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'azusa.ru': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'hdmayi.com': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'hdzone.me': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'gainbound.net': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'hdvideo.one': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        '52pt.site': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'pt.msg.vg': {
            'LOGIN': 'user/login/index',
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'kamept.com': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'carpt.net': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': ["//h1[@id='top']/img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'club.hares.top': {
            'FREE': ["//b[@class='free'][text()='免费']"],
            '2XFREE': ["//b[@class='twoupfree'][text()='2X免费']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'www.hddolby.com': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'piggo.me': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': ["//h1[@id='top']/img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'pt.0ff.cc': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': ["//h1[@id='top']/img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'wintersakura.net': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'pt.hdupt.com': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'pt.upxin.net': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'www.nicept.net': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'ptchina.org': {
            'FREE': ["//h1[@id='top']/b/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/b/font[@class='twoupfree']"],
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
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': [],
            'HR': ["//h1[@id='top']/img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'zmpt.cc': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'ihdbits.me': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'leaves.red': {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        "sharkpt.net": {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': ["//h1[@id='top']/img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        "pt.2xfree.org": {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        "uploads.ltd": {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        "www.icc2022.com": {
            'FREE': ["//h1[@id='top']/b/font[@class='free']"],
            '2XFREE': ["//h1[@id='top']/b/font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        }
    }
    # 公共BT站点
    PUBLIC_TORRENT_SITES = {
        'rarbg.to': {
            "parser": "Rarbg",
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
            "language": "en",
            "parser": "RenderSpider"
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
            "proxy": False,
            "referer": True
        },
        'www.miobt.com': {
            "proxy": True
        },
        'katcr.to': {
            "proxy": True,
            "language": "en"
        },
        'btsow.quest': {
            "proxy": True
        },
        'www.hdpianyuan.com': {
            "proxy": False
        },
        'skrbtfi.top': {
            "proxy": False,
            "referer": True,
            "parser": "RenderSpider"
        }
    }
