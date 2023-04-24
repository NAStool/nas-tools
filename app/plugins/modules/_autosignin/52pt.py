import json
import os
import random
import re

from lxml import etree

from app.helper.openai_helper import OpenAiHelper
from app.plugins.modules._autosignin._base import _ISiteSigninHandler
from app.utils import StringUtils, RequestUtils
from config import Config


class FWpt(_ISiteSigninHandler):
    """
    52pt
    如果填写openai key则调用chatgpt获取答案
    否则随机
    """
    # 匹配的站点Url，每一个实现类都需要设置为自己的站点Url
    site_url = "52pt.site"

    # 已签到
    _sign_regex = ['今天已经签过到了']

    # 签到成功，待补充
    _success_regex = ['\\d+点魔力值']

    # 存储正确的答案，后续可直接查
    _answer_path = os.path.join(Config().get_temp_path(), "signin")
    _answer_file = _answer_path + "/52pt.json"

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
        proxy = Config().get_proxies() if site_info.get("proxy") else None

        # 创建正确答案存储目录
        if not os.path.exists(os.path.dirname(self._answer_file)):
            os.makedirs(os.path.dirname(self._answer_file))

        # 判断今日是否已签到
        index_res = RequestUtils(cookies=site_cookie,
                                 headers=ua,
                                 proxies=proxy
                                 ).get_res(url='https://52pt.site/bakatest.php')
        if not index_res or index_res.status_code != 200:
            self.error(f"签到失败，请检查站点连通性")
            return False, f'【{site}】签到失败，请检查站点连通性'

        if "login.php" in index_res.text:
            self.error(f"签到失败，cookie失效")
            return False, f'【{site}】签到失败，cookie失效'

        sign_status = self.sign_in_result(html_res=index_res.text,
                                          regexs=self._sign_regex)
        if sign_status:
            self.info(f"今日已签到")
            return True, f'【{site}】今日已签到'

        # 没有签到则解析html
        html = etree.HTML(index_res.text)

        if not html:
            return False, f'【{site}】签到失败'

        # 获取页面问题、答案
        questionid = html.xpath("//input[@name='questionid']/@value")[0]
        option_ids = html.xpath("//input[@name='choice[]']/@value")
        option_values = html.xpath("//input[@name='choice[]']/following-sibling::text()")
        question_str = html.xpath("//td[@class='text' and contains(text(),'请问：')]/text()")[0]
        answers = list(zip(option_ids, option_values))

        # 正则获取问题
        match = re.search(r'请问：(.+)', question_str)
        if match:
            question_str = match.group(1)
            self.debug(f"获取到签到问题 {question_str}")
        else:
            self.error(f"未获取到签到问题")
            return False, f"【{site}】签到失败，未获取到签到问题"

        # 查询已有答案
        exits_answers = {}
        try:
            with open(self._answer_file, 'r') as f:
                json_str = f.read()
            exits_answers = json.loads(json_str)
            # 查询本地本次验证码hash答案
            question_answer = exits_answers[question_str]
            # question_answer是数组
            if not isinstance(question_answer, list):
                question_answer = [question_answer]
            # 本地存在本次hash对应的正确答案再遍历查询
            choice = []
            for q in question_answer:
                for num, answer in answers:
                    if str(q) == str(num):
                        choice.append(int(q))
            if len(choice) > 0:
                # 签到
                return self.__signin(questionid=questionid,
                                     choice=choice,
                                     site_cookie=site_cookie,
                                     ua=ua,
                                     proxy=proxy,
                                     site=site)
        except (FileNotFoundError, IOError, OSError) as e:
            self.debug("查询本地已知答案失败，继续请求豆瓣查询")

        # 正确答案，默认随机，如果gpt返回则用gpt返回的答案提交
        choice = [option_ids[random.randint(0, len(option_ids) - 1)]]

        # 组装gpt问题
        gpt_options = "{\n" + ",\n".join([f"{num}:{value}" for num, value in answers]) + "\n}"
        gpt_question = f"题目：{question_str}\n" \
                       f"选项：{gpt_options}"
        self.debug(f"组装chatgpt问题 {gpt_question}")

        # chatgpt获取答案
        answer = OpenAiHelper().get_question_answer(question=gpt_question)
        self.debug(f"chatpgt返回结果 {answer}")

        # 处理chatgpt返回的答案信息
        if answer is None:
            self.warn(f"ChatGPT未启用, 开始随机签到")
            # return f"【{site}】签到失败，ChatGPT未启用"
        elif answer:
            # 正则获取字符串中的数字
            answer_nums = list(map(int, re.findall("\d+", answer)))
            if not answer_nums:
                self.warn(f"无法从chatgpt回复 {answer} 中获取答案, 将采用随机签到")
            else:
                choice = []
                for answer in answer_nums:
                    # 如果返回的数字在option_ids范围内，则直接作为答案
                    if str(answer) in option_ids:
                        choice.append(int(answer))
                        self.info(f"chatgpt返回答案id {answer} 在签到选项 {option_ids} 中")
        # 签到
        return self.__signin(questionid=questionid,
                             choice=choice,
                             site_cookie=site_cookie,
                             ua=ua,
                             proxy=proxy,
                             site=site,
                             exits_answers=exits_answers,
                             question=question_str)

    def __signin(self, questionid, choice, site, site_cookie, ua, proxy, exits_answers=None, question=None):
        """
        签到请求
        questionid: 450
        choice[]: 8
        choice[]: 4
        usercomment: 此刻心情:无
        submit: 提交
        多选会有多个choice[]....
        """
        data = {
            'questionid': questionid,
            'choice[]': choice[0] if len(choice) == 1 else choice,
            'usercomment': '太难了！',
            'wantskip': '不会'
        }
        self.debug(f"签到请求参数 {data}")

        sign_res = RequestUtils(cookies=site_cookie,
                                headers=ua,
                                proxies=proxy
                                ).post_res(url='https://52pt.site/bakatest.php', data=data)
        if not sign_res or sign_res.status_code != 200:
            self.error(f"签到失败，签到接口请求失败")
            return False, f'【{site}】签到失败，签到接口请求失败'

        # 判断是否签到成功
        sign_status = self.sign_in_result(html_res=sign_res.text,
                                          regexs=self._success_regex)
        if sign_status:
            self.info(f"{site}签到成功")
            if exits_answers and question:
                # 签到成功写入本地文件
                self.__write_local_answer(exits_answers=exits_answers or {},
                                          question=question,
                                          answer=choice)
            return True, f'【{site}】签到成功'
        else:
            sign_status = self.sign_in_result(html_res=sign_res.text,
                                              regexs=self._sign_regex)
            if sign_status:
                self.info(f"今日已签到")
                return True, f'【{site}】今日已签到'

            self.error(f"签到失败，请到页面查看")
            return False, f'【{site}】签到失败，请到页面查看'

    def __write_local_answer(self, exits_answers, question, answer):
        """
        签到成功写入本地文件
        """
        try:
            exits_answers[question] = answer
            # 序列化数据
            formatted_data = json.dumps(exits_answers, indent=4)
            with open(self._answer_file, 'w') as f:
                f.write(formatted_data)
        except (FileNotFoundError, IOError, OSError) as e:
            self.debug("签到成功写入本地文件失败")
