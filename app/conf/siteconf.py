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
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
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
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
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
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'springsunday.net': {
            'FREE': ["//font[@class='free'][text()='免费']"],
            '2XFREE': ["//font[@class='twoupfree'][text()='2X免费']"],
            'HR': ["//img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
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
            'HR': ["//b[contains(text(),'H&R:')]"],
            'PEER_COUNT': [],
        },
        'hdchina.org': {
            'RENDER': True,
            'FREE': ["//div[@class='m_name']/h2/img[@class='pro_free']"],
            '2XFREE': ["//div[@class='m_name']/h2/img[@class='pro_free2up']"],
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
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
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
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
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
            'LOGIN': 'user/login/index',
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
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'piggo.me': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': ["//img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'pt.0ff.cc': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': ["//img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
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
            'HR': ["//img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'zmpt.cc': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        'ihdbits.me': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': [],
        },
        'leaves.red': {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        "sharkpt.net": {
            'FREE': ["//font[@class='free']"],
            '2XFREE': [],
            'HR': ["//img[@class='hitandrun']"],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        "pt.2xfree.org": {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        "uploads.ltd": {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
            'HR': [],
            'PEER_COUNT': ["//div[@id='peercount']/b[1]"],
        },
        "www.icc2022.com": {
            'FREE': ["//font[@class='free']"],
            '2XFREE': ["//font[@class='twoupfree']"],
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
