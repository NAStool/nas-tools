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
        site_cookie = site_info.get("cookie")
        ua = site_info.get("ua")

        # 获取北洋签到页面html
        html_res = RequestUtils(cookies=site_cookie,
                                headers=ua,
                                proxies=Config().get_proxies() if site_info.get("proxy") else None
                                ).get_res(url=self._sign_in_url)

        # 获取签到后返回html，判断是否签到成功
        self.__sign_in_result(html_res=html_res.text)

        # 没有签到则解析html
        html = etree.HTML(html_res.text)
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
                return '【北洋】签到失败，未获取到签到图片'
            captcha_img = Image.open(BytesIO(captcha_img_res.content))
            captcha_img_hash = Tjupt()._tohash(captcha_img)
            log.info(f"【Sites】北洋签到图片hash {captcha_img_hash}")

            # 签到答案选项
            values = html.xpath("//input[@name='answer']/@value")
            options = html.xpath("//input[@name='answer']/text()")
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
                            return '【北洋】签到失败，获取签到答案图片失败'
                        answer_img = Image.open(BytesIO(answer_img_res.content))
                        answer_img_hash = Tjupt()._tohash(answer_img)
                        log.info(f"【Sites】北洋签到答案图片hash {answer_title} {answer_img_hash}")

                        score = Tjupt()._comparehash(captcha_img_hash, answer_img_hash)
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
                                return '【北洋】签到失败，签到接口请求失败'

                            # 获取签到后返回html，判断是否签到成功
                            self.__sign_in_result(html_res=sign_in_res.text)

            log.error(f"【Sites】北洋签到失败，未获取到匹配答案")
            # 没有匹配签到成功，则签到失败
            return '【北洋】签到失败，未获取到匹配答案'

    def __sign_in_result(self, html_res):
        # 判断是否签到成功
        html_text = self._prepare_html_text(html_res.text)
        for regex in self._succeed_regex:
            if re.search(str(regex), html_text):
                log.info(f"【Sites】北洋签到成功")
                return '【北洋】签到成功'

    @staticmethod
    def _tohash(img, shape=(10, 10)):
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
