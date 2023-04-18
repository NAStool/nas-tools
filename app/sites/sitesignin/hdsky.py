import json
import time

import log
from app.helper import OcrHelper
from app.sites.sitesignin._base import _ISiteSigninHandler
from app.utils import StringUtils, RequestUtils
from config import Config


class HDSky(_ISiteSigninHandler):
    """
    天空ocr签到
    """
    # 匹配的站点Url，每一个实现类都需要设置为自己的站点Url
    site_url = "hdsky.me"

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

        # 获取验证码请求，考虑到网络问题获取失败，多获取几次试试
        res_times = 0
        img_hash = None
        while not img_hash and res_times <= 3:
            image_res = RequestUtils(cookies=site_cookie,
                                     headers=ua,
                                     proxies=Config().get_proxies() if site_info.get("proxy") else None
                                     ).post_res(url='https://hdsky.me/image_code_ajax.php',
                                                data={'action': 'new'})
            if image_res and image_res.status_code == 200:
                image_json = json.loads(image_res.text)
                if image_json["success"]:
                    img_hash = image_json["code"]
                    break
                res_times += 1
                log.debug(f"【Sites】获取天空验证码失败，正在进行重试，目前重试次数 {res_times}")
                time.sleep(1)

        # 获取到二维码hash
        if img_hash:
            # 完整验证码url
            img_get_url = 'https://hdsky.me/image.php?action=regimage&imagehash=%s' % img_hash
            log.debug(f"【Sites】获取到天空验证码连接 {img_get_url}")
            # ocr识别多次，获取6位验证码
            times = 0
            ocr_result = None
            # 识别几次
            while times <= 3:
                # ocr二维码识别
                ocr_result = OcrHelper().get_captcha_text(image_url=img_get_url,
                                                          cookie=site_cookie,
                                                          ua=ua)
                log.debug(f"【Sites】orc识别天空验证码 {ocr_result}")
                if ocr_result:
                    if len(ocr_result) == 6:
                        log.info(f"【Sites】orc识别天空验证码成功 {ocr_result}")
                        break
                times += 1
                log.debug(f"【Sites】orc识别天空验证码失败，正在进行重试，目前重试次数 {times}")
                time.sleep(1)

            if ocr_result:
                # 组装请求参数
                data = {
                    'action': 'showup',
                    'imagehash': img_hash,
                    'imagestring': ocr_result
                }
                # 访问签到链接
                res = RequestUtils(cookies=site_cookie,
                                   headers=ua,
                                   proxies=Config().get_proxies() if site_info.get("proxy") else None
                                   ).post_res(url='https://hdsky.me/showup.php', data=data)
                if res and res.status_code == 200:
                    if json.loads(res.text)["success"]:
                        log.info(f"【Sites】天空签到成功")
                        return f'【{site}】签到成功'
                    elif str(json.loads(res.text)["message"]) == "date_unmatch":
                        # 重复签到
                        log.warn(f"【Sites】天空重复成功")
                        return f'【{site}】今日已签到'
                    elif str(json.loads(res.text)["message"]) == "invalid_imagehash":
                        # 验证码错误
                        log.warn(f"【Sites】天空签到失败：验证码错误")
                        return f'【{site}】天空签到失败：验证码错误'

        return '【Sites】天空签到失败：未获取到验证码'
