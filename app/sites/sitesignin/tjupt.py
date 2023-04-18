import json
import re
from io import BytesIO

from lxml import etree
from PIL import Image
import log
from app.sites.sitesignin._base import _ISiteSigninHandler
from app.utils import StringUtils, RequestUtils
from config import Config


class Tjupt(_ISiteSigninHandler):
    """
    北洋签到
    """
    # 匹配的站点Url，每一个实现类都需要设置为自己的站点Url
    site_url = "tjupt.org"

    # 签到地址
    _sign_in_url = 'https://www.tjupt.org/attendance.php'

    # 签到成功
    _succeed_regex = ['这是您的首次签到，本次签到获得.*?个魔力值。',
                      '签到成功，这是您的第.*?次签到，已连续签到.*?天，本次签到获得.*?个魔力值。',
                      '重新签到成功，本次签到获得.*?个魔力值'],

    @classmethod
    def match(cls, url):
        """
        根据站点Url判断是否匹配当前站点签到类，大部分情况使用默认实现即可
        :param url: 站点Url
        :return: 是否匹配，如匹配则会调用该类的signin方法
        """
        return True if StringUtils.url_equal(url, cls.site_url) else False

    def signin(self, site_info: dict):
        """
        执行签到操作
        :param site_info: 站点信息，含有站点Url、站点Cookie、UA等信息
        :return: 签到结果信息
        """
        site = site_info.get("name")
        site_cookie = site_info.get("cookie")
        ua = site_info.get("ua")

        # 获取北洋签到页面html
        # html_res = RequestUtils(cookies=site_cookie,
        #                         headers=ua,
        #                         proxies=Config().get_proxies() if site_info.get("proxy") else None
        #                         ).get_res(url=self._sign_in_url)
        #
        # # 获取签到后返回html，判断是否签到成功
        # if not html_res:
        #     log.error("【Sites】北洋签到失败，请检查站点连通性")
        #     return f'【{site}】签到失败，请检查站点连通性'
        # self.__sign_in_result(html_res=html_res.text,
        #                       site=site)

        # 没有签到则解析html
        # html = etree.HTML(html_res.text)
        html = '''
            <!DOCTYPE html>
    <html lang="zh-cmn-Hans">
<head>
    <meta charset="UTF-8">
    <meta name='keywords' content='PT 校园 资源'>    <meta name='description' content='TJUPT是天津市首个、全国前列的校园Private Tracker，建立于2010年，由天津大学信网协会和天外天共同开发的，旨在为大家建立一个更好的资源共享环境，提高资源水准。'>    <meta name="generator" content="NexusPHP">
    <meta name="referrer" content="same-origin">
    <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1">
    <meta name="renderer" content="webkit">

    <title>北洋园PT :: 签到 - Powered by NexusPHP</title>
    
    <link rel="dns-prefetch" href="//usercontent.tju.pt" />
    <link rel="dns-prefetch" href="//ptgen.tju.pt" />
    <link rel="shortcut icon" type="image/x-icon" href="/favicon.ico?v=2022" />
    <link rel="alternate icon" type="image/png" href="/assets/favicon/favicon.png" />
    <link rel="icon" type="image/svg+xml" href="/assets/favicon/favicon.svg" />
    <link rel="apple-touch-icon" sizes="180x180" href="/assets/favicon/apple-touch-icon.png" />
    <link rel="manifest" href="/manifest.json" />
    <link rel="search" type="application/opensearchdescription+xml" title="北洋园PT Torrents"
          href="/opensearch.php">
    <link rel='alternate' type='application/rss+xml' title='Latest Torrents' href='/torrentrss.php?passkey=de694ae935381c1d28c9b0466c541396'>
    <link rel="stylesheet" href="/styles/curtain_imageresizer.css?202303140030">
    <link rel="stylesheet" href="/styles/sprites.css?202303140030">
    <link rel="stylesheet" href="/styles/userAutoTips.css?202303140030">
    <link rel="stylesheet" href="/styles/mediumfont.css?202303140030">
    <link rel="stylesheet" href="pic/forum_pic/chs/forumsprites.css?202303140030">
    <link rel="stylesheet" href="styles/FlowerPink/theme.css?202303140030">
    <link rel="stylesheet" href="styles/FlowerPink/DomTT.css?202303140030">
    <link rel='stylesheet' href='pic/category/chd/hdlxhh/catsprites.css?202303140030'>
    <link rel="stylesheet" href="https://cdn.staticfile.org/font-awesome/4.7.0/css/font-awesome.min.css">
    <link rel="stylesheet" href="https://cdn.staticfile.org/flatpickr/4.6.9/flatpickr.min.css">

     
    <!-- 外部引入 -->
    <script src="/assets/js/libs.481d7dcb.min.js"></script>

    <!-- 业务代码 -->
            <script src="/assets/js/common.dc3da021.min.js"></script>
        <script src="/assets/js/nexusphp_libs.1c4d30a9.min.js"></script>
    </head>
    <body><style>
    table.mainouter, #header, #footer, #main-logo {
        width: 1250px;
    }
</style>        <table id="header" class="head">
            <tr>
                <td class="clear">
                    <div class="logo_img" style="overflow: hidden">
                        <a style="display: flex;" href="forums.php?action=viewtopic&topicid=20180&page=p213065#pid213065">
                            <img src="https://usercontent.tju.pt/lldq2 4.49.png?file_id=11d097a51c394047675552881d530dc0ea994d1f249c36ba05397362d94b9f3f"
                                    alt="北洋园PT"
                                    title="北洋园PT"
                                    width="1250"/>
                        </a>
                    </div>
                </td>
                <td class="clear nowrap" style="text-align: right; vertical-align: middle">
                                    </td>
            </tr>
        </table>
        <table class='mainouter'>    <tr>
        <td id="nav_block">
            <table class="main" style='width: 100%'><tr><td class="embedded"  style="text-align: center"><div id="nav"><ul id="mainmenu" class="menu"><li><a href="index.php">&nbsp;首&nbsp;&nbsp;页&nbsp;</a></li><li><a href="forums.php">&nbsp;论&nbsp;&nbsp;坛&nbsp;</a></li><li><a href="torrents.php">&nbsp;种&nbsp;&nbsp;子&nbsp;</a></li><li><a href="viewrequests.php">&nbsp;求&nbsp;&nbsp;种&nbsp;</a></li><li><a href="offers.php">&nbsp;候&nbsp;&nbsp;选&nbsp;</a></li><li><a href="upload.php">&nbsp;发&nbsp;&nbsp;布&nbsp;</a></li><li><a href="jc_currentbet_L.php" title='当前进行中的竞猜（共11条）：&#10;【英国公投】2023年苏格兰是否可以独立脱英&#10;22-23赛季英超第25轮-纽卡VS布莱顿&#10;iPhone15 充电接口是否会使用type c&#10;22-23赛季欧冠四分之一决赛次回合-那不勒斯VSAC米兰&#10;22-23赛季欧冠四分之一决赛次回合-拜仁VS曼城&#10;22-23赛季欧冠四分之一决赛次回合-国米VS本菲卡&#10;22-23赛季欧冠四分之一决赛次回合-切尔西VS皇马&#10;【22-23赛季欧冠1/4决赛次回合-国米VS本菲卡】国米一高一快能否进球&#10;22-23赛季CBA总冠军&#10;22-23赛季英超第32轮-纽卡VS热刺&#10;22-23赛季英超第32轮-阿森纳VS南安普顿（阿森纳让两球）'>&nbsp;竞&nbsp;&nbsp;猜&nbsp;</a></li><li><a href="rules.php">&nbsp;规&nbsp;&nbsp;则&nbsp;</a></li><li><a href="faq.php">&nbsp;常见问题&nbsp;</a></li><li><a href="usercp.php">&nbsp;控制面板&nbsp;</a></li><li><a href="topten.php">排&nbsp;行&nbsp;榜</a></li><li><a href="log.php">&nbsp;日&nbsp;&nbsp;志&nbsp;</a></li><li><a href="staff.php">管&nbsp;理&nbsp;组</a></li></ul></div></td></tr></table>

                <table id="info_block">
                    <tr>
                        <td class="bottom" style="text-align: left">
                            欢迎, <span class="nowrap"><a  href="userdetails.php?id=136307" target="_blank" class='EliteUser_Name'><b><span style="text-decoration: none;">thsrite666</span></b></a></span> [<a href='logout.php'>退出</a>]                            [<a href="torrents.php?inclbookmarked=1&amp;allsec=1&amp;incldead=0">收藏</a>]
                            <span class="color_bonus"> 等级 </span>[<a href="/classes.php#3">详情/升级</a>]: <span class='EliteUser_Name' style='font-weight: bold'>持剑下山</span>                            <span class='color_bonus'> 魔力值  </span>[<a href="mybonus.php">使用</a>|<a href="mybonusapps.php">茉莉园</a>]: 241,584.5                            <span class='color_invite'> 邀请  </span>[<a href="invite.php?id=136307">发送</a>]: <span title='永久邀请'>0</span><br/>
                            <span class="color_bonus">H&R </span>[<a href="/hnr_bonus.php">积分</a>|<a href="/hnr_details.php">详情</a>]: <a href="/hnr_bonus.php">100</a>(<a href="/hnr_details.php">0</a>)
                            <span class='color_uploaded'>上传量:</span> 573.64 GiB                            <span class="color_active"> 上传排名:</span> <a href="/topten.php">24364</a>&nbsp;
                            <span class='color_active'>活动种子:</span>
                            <img class="arrowup" alt="Torrents seeding"
                                 title="当前做种数"
                                 src="pic/trans.gif"/>284                            <img class="arrowdown" alt="Torrents leeching"
                                 title="当前下载数"
                                 src="pic/trans.gif"/>3&nbsp;
                            <span class='color_connectable'>网络状态: </span>非天大IPv4<span style='color: green' class='fa fa-check'></span> / IPv6<span style='color: green' class='fa fa-check'></span> / 天大IPv4<span style='color: red' class='fa fa-close'></span>                        </td>
                        <td class="bottom" style="text-align: right">
                                                            [<a href="attendance.php" class="faqlink">签到得魔力</a>]&nbsp;
                                当前时间:4/18&nbsp;13:29                            <br/>

                            <a href="messages.php"><img class="inbox" src="pic/trans.gif" alt="inbox" title="收件箱&nbsp;(无新短讯)" /></a> 43 (0 新)  <a href="messages.php?action=viewmailbox&amp;box=-1"><img class="sentbox" alt="sentbox" title="发件箱" src="pic/trans.gif" /></a> 0 <a href="friends.php"><img class="buddylist" alt="Buddylist" title="社交名单" src="pic/trans.gif" /></a> <a href="getrss.php"><img class="rss" alt="RSS" title="获取RSS" src="pic/trans.gif" /></a>                        </td>
                    </tr>
                </table>
                <br>        </td>
    </tr>
    <tr><td id="outer"><table class="main" style='width: 97%'><tr><td class="embedded" ><h2 style="text-align: left">签到</h2><table style="width: 100%"><tr><td class="text" style='padding: 10'>
<table class='captcha'><tr valign='top'><td><img src='/pic/attend/2023-04-18/4s-QJFWZ0EBgIz2QpoeBCg.jpg'/></td><td>&nbsp;&nbsp;</td><td>
        <form action='attendance.php' method='post'>
        <table><tr><td class='text' align='left' width='100%'><b>签到验证码</b><br \>请选择与左侧图片对应的影视名称：</td></tr>
        <tr><td><input type='radio' name='answer' value='2023-04-18 13:29:20.172578&33'>君有云<br><input type='radio' name='answer' value='2023-04-18 13:29:20.172578&36'>林深时见麓<br><input type='radio' name='answer' value='2023-04-18 13:29:20.172578&35'>耀眼的你啊<br><input type='radio' name='answer' value='2023-04-18 13:29:20.172578&6'>爱情而已<br><input type='radio' name='answer' value='2023-04-18 13:29:20.172578&0'>尘封十三载<br><input type='radio' name='answer' value='2023-04-18 13:29:20.172578&45'>虫图腾<br></td></tr>
            <tr><td class='text' align='left' width='100%'><input type='submit' name='submit' value='提交'/></td></tr>
            <tr><td class='text' align='left' width='100%'><b>注意：</b>
            <li>请谨慎选择，<font color='green'>回答正确将获得</font>相应的魔力值，<font color='red'>回答错误将反向扣除</font>相应的魔力值</li>
            <li>如图片未正常加载或无法辨别图片对应的影视名称，可手动刷新当前页面更换题目</li>
            </table></form></td></tr></table></td></tr></table>
</td></tr></table>
</td></tr></table><div id="footer"><div style="margin-top: 20px; margin-bottom: 20px;" align="center" onclick='debugMode()'> (c)  <a href="https://www.tjupt.org" target="_self">北洋园PT</a> 2010-2023 Powered by <a href="aboutnexus.php">NexusPHP</a><br /><br />All rights reserved. 北洋园PT版权所有<br /><br /></div>
<a style="display: none;" id="lightbox" class="lightbox" onclick="Return();" onmousewheel="return false;"  ondragstart="return false;" onselectstart="return false;"></a><div style="display: none;" id="curtain" class="curtain" onclick="Return();" onmousewheel="return false;"></div></div>                    <script>
                        addBackToTop({
                            diameter: 40,
                            backgroundColor: '#ddd',
                            textColor: '#dc204a',
                            scrollDuration: 400
                        });
                    </script>
                    
<!-- Global site tag (gtag.js) - Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=UA-132352893-1"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'UA-132352893-1');
</script>
</body></html>
        '''

        html = etree.HTML(html)
        if not html:
            return
        img_url = html.xpath('//table[@class="captcha"]//img/@src')[0]
        if img_url:
            # 签到图片
            img_url = "https://www.tjupt.org" + img_url
            log.info(f"【Sites】获取到北洋签到图片 {img_url}")
            # 获取签到图片hash
            captcha_img_res = RequestUtils(cookies=site_cookie,
                                           headers=ua,
                                           proxies=Config().get_proxies() if site_info.get("proxy") else None
                                           ).get_res(url=img_url)
            if not captcha_img_res or captcha_img_res.status_code != 200:
                log.error(f"【Sites】北洋签到图片 {img_url} 请求失败")
                return f'【{site}】签到失败，未获取到签到图片'
            captcha_img = Image.open(BytesIO(captcha_img_res.content))
            captcha_img_hash = self._tohash(captcha_img)
            log.info(f"【Sites】北洋签到图片hash {captcha_img_hash}")

            # 签到答案选项
            values = html.xpath("//input[@name='answer']/@value")
            options = html.xpath("//input[@name='answer']/following-sibling::text()")
            # value+选项
            answers = list(zip(values, options))
            for value, answer in answers:
                if answer:
                    # 豆瓣检索
                    db_res = RequestUtils().get_res(url=f'https://movie.douban.com/j/subject_suggest?q={answer}')
                    if not db_res or db_res.status_code != 200:
                        log.warn(f"【Sites】北洋签到选项 {answer} 未查询到豆瓣数据")
                        continue
                    # 豆瓣返回结果
                    db_answers = json.loads(db_res.text)
                    if not isinstance(db_answers, list):
                        db_answers = [db_answers]

                    for db_answer in db_answers:
                        answer_title = db_answer['title']
                        answer_img_url = db_answer['img']

                        # 获取答案hash
                        answer_img_res = RequestUtils().get_res(url=answer_img_url)
                        if not answer_img_res or answer_img_res.status_code != 200:
                            log.error(f"【Sites】北洋签到答案 {answer_title} {answer_img_url} 请求失败")
                            return f'【{site}】签到失败，获取签到答案图片失败'
                        answer_img = Image.open(BytesIO(answer_img_res.content))
                        answer_img_hash = self._tohash(answer_img)
                        log.info(f"【Sites】北洋签到答案图片hash {answer_title} {answer_img_hash}")

                        # 获取选项图片与签到图片相似度，大于0.9默认是正确答案
                        score = self._comparehash(captcha_img_hash, answer_img_hash)
                        log.info(f"【Sites】北洋签到图片与选项 {answer} 豆瓣图片相似度 {score}")
                        if score > 0.9:
                            # 确实是答案
                            data = {
                                'answer': value,
                                'submit': '提交'
                            }
                            log.info(f"提交data {data}")
                            sign_in_res = RequestUtils(cookies=site_cookie,
                                                       headers=ua,
                                                       proxies=Config().get_proxies() if site_info.get(
                                                           "proxy") else None
                                                       ).post_res(url=self._sign_in_url, data=data)
                            if not sign_in_res or sign_in_res.status_code != 200:
                                log.error(f"【Sites】北洋签到失败，签到接口请求失败")
                                return f'【{site}】签到失败，签到接口请求失败'

                            # 获取签到后返回html，判断是否签到成功
                            self.__sign_in_result(html_res=sign_in_res.text,
                                                  site=site)

            log.error(f"【Sites】北洋签到失败，未获取到匹配答案")
            # 没有匹配签到成功，则签到失败
            return f'【{site}】签到失败，未获取到匹配答案'

    def __sign_in_result(self, html_res, site):
        """
        判断是否签到成功
        """
        html_text = self._prepare_html_text(html_res.text)
        for regex in self._succeed_regex:
            if re.search(str(regex), html_text):
                log.info(f"【Sites】北洋签到成功")
                return f'【{site}】签到成功'

    @staticmethod
    def _tohash(img, shape=(10, 10)):
        """
        获取图片hash
        """
        img = img.resize(shape)
        gray = img.convert('L')
        s = 0
        hash_str = ''
        for i in range(shape[1]):
            for j in range(shape[0]):
                s = s + gray.getpixel((j, i))
        avg = s / (shape[0] * shape[1])
        for i in range(shape[1]):
            for j in range(shape[0]):
                if gray.getpixel((j, i)) > avg:
                    hash_str = hash_str + '1'
                else:
                    hash_str = hash_str + '0'
        return hash_str

    @staticmethod
    def _comparehash(hash1, hash2, shape=(10, 10)):
        """
        比较图片hash
        返回相似度
        """
        n = 0
        if len(hash1) != len(hash2):
            return -1
        for i in range(len(hash1)):
            if hash1[i] == hash2[i]:
                n = n + 1
        return n / (shape[0] * shape[1])

    @staticmethod
    def _prepare_html_text(html_text):
        """
        处理掉HTML中的干扰部分
        """
        return re.sub(r"#\d+", "", re.sub(r"\d+px", "", html_text))
