import random
from time import sleep

import requests
from bs4 import BeautifulSoup

import log
from config import get_config
from rmt.metainfo import MetaInfo
from utils.http_utils import RequestUtils
from utils.types import MediaType


class DouBan:
    __default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"}
    __req = None
    __users = []
    __cookie = None
    __days = 0
    __types = []
    __headers = None

    def __init__(self):
        config = get_config()
        if config.get('douban'):
            # 用户列表
            users = config['douban'].get('users')
            if users:
                if not isinstance(users, list):
                    users = [users]
                self.__users = users
            # 时间范围
            self.__days = config['douban'].get('days')
            # 类型
            types = config['douban'].get('types')
            if types:
                self.__types = types.split(',')
            # headers
            user_agent = config['douban'].get('user_agent')
            if not user_agent:
                self.__headers = self.__default_headers
            else:
                self.__headers = {"User-Agent": f"{user_agent}"}
            # Cookie
            cookie = config['douban'].get('cookie')
            if not cookie:
                try:
                    self.req = RequestUtils(request_interval_mode=True)
                    res = self.req.get_res("https://www.douban.com/", headers=self.__headers)
                    cookies = res.cookies
                    cookie = requests.utils.dict_from_cookiejar(cookies)
                    self.__cookie = cookie
                except Exception as err:
                    log.warn(f"【DOUBAN】获取cookie失败:{format(err)}")

    def get_all_douban_movies(self):
        movie_list = []
        start_number = 0
        # 每一个用户
        for user in self.__users:
            # 每一个类型
            user_succnum = 0
            for mtype in self.__types:
                log.info(f"【DOUBAN】开始获取 {user} 的 {mtype} 数据...")
                err_url = []
                user_type_succnum = 0
                # 每一页
                while True:
                    page_number = int(start_number / 15 + 1)
                    # 每一页的文本
                    log.info(f"【DOUBAN】开始解析第 {page_number} 页数据...")
                    soup = self.__get_html_soup(user_id=user, start_number=start_number)
                    # 获取全部url
                    url_list = self.__get_url_list(soup)
                    url_num = len(url_list)
                    log.info(f"【DOUBAN】第 {page_number} 页有 {url_num} 个媒体")
                    sucess_urlnum = 0
                    url_count = 0
                    for url in url_list:
                        url_count += 1
                        # 随机休眠
                        time_number = random.uniform(0.1, 1)
                        log.info(f"【DOUBAN】解析媒体 {url_count} 随机休眠：{time_number}s")
                        sleep(time_number)
                        # 每一个条目的内容
                        media_soup = self.__get_html_soup(user, url, mtype)
                        if not media_soup:
                            log.warn(f"【DOUBAN】访问该页面出现问题，媒体链接：{url}")
                            err_url.append(url)
                        else:
                            movie_dict = self.__get_movie_dict(media_soup)
                            if movie_dict:
                                movie_dict['url'] = url
                                # 加入数组
                                if movie_dict not in movie_list:
                                    movie_list.append(movie_dict)
                                    sucess_urlnum += 1
                                    user_type_succnum += 1
                                    user_succnum += 1
                    if url_num > 14:
                        start_number += 15
                    else:
                        break
                    log.info(f"【DOUBAN】第 {page_number} 页解析完成，共获取到 {sucess_urlnum} 个媒体")
                log.info(f"【DOUBAN】用户 {user} 的 {mtype} 解析完成，共获取到 {user_type_succnum} 个媒体")
            log.info(f"【DOUBAN】用户 {user} 解析完成，共获取到 {user_succnum} 个媒体")
        log.info(f"【DOUBAN】所有用户解析完成，共获取到 {len(movie_list)} 个媒体")

        return movie_list

    @staticmethod
    def __get_url_list(soup):
        """
        解析个人wish/do/collect内容的每个url
        :return: url数组
        """
        url_list = []
        try:
            info = soup.select('.nbg')
            for url in info:
                url_list.append(url.get('href'))
            return url_list
        except Exception as err:
            log.warn(f"【RUN】解析失败：{err}")
            return []

    def __get_html_soup(self, user_id, url=None, media_status="wish", start_number=0):
        """
        获取链接的html文档
        :param user_id: 用户id(如果url选择第二种则为空）
        :param media_status: 状态（wish/do/collect），同上
        :param start_number: url为空时，该参数必填
        :return: html的text格式
        """
        if not user_id:
            return None
        if not url:
            url = f"https://movie.douban.com/people/{user_id}/{media_status}?start={start_number}&sort=time&rating=all&filter=all&mode=grid"
        try:
            res = self.req.get_res(url=url, headers=self.__headers, cookies=self.__cookie)
            if res.status_code == 200:
                res_text = res.text
                if res_text.find('有异常请求从你的 IP 发出') != -1:
                    log.warn("【DOUBAN】被豆瓣识别到抓取行为了，请更换 IP 后才能使用")
                    return None
                return BeautifulSoup(res_text, 'html.parser')
            elif res.status_code == 404:
                log.warn(f"【DOUBAN】该页面不存在！{url}")
                return None
        except Exception as err:
            log.error(f"【RUN】获取{url}页面失败:{format(err)}")
            return None

    def __get_movie_dict(self, soup):
        # 标签名不加任何修饰，类名前加点，id名前加#
        info = soup.select('#info')
        infos = list(info[0].strings)
        infos = [i.strip() for i in infos if i.strip() != '']
        movie_dict = {}
        # 影视名称
        title = soup.select('#wrapper > div > h1')
        titles = list(title[0].strings)
        titles = [i.strip() for i in titles if i.strip() != '']
        movie_title = ''.join(titles)
        # 这里解析一下，拿到标题和年份
        meta_title_info = MetaInfo(movie_title)
        movie_title = meta_title_info.get_name()
        movie_year = meta_title_info.year

        # 导演
        if '导演' in infos:
            movie_director = self.__multiple_infos_parser(infos, '导演', 2)
        else:
            movie_director = ""

        # 编剧 主演 类型
        screenwriter = self.__multiple_infos_parser(infos, "编剧", 2)
        starring = self.__multiple_infos_parser(infos, "主演", 2)
        movie_type = self.__multiple_infos_parser(infos, "类型:", 1)

        # 国家或地区
        country_or_region = infos[infos.index("制片国家/地区:") + 1]
        country_or_region_list = country_or_region.split('/')
        c_or_r = []
        for i in country_or_region_list:
            c_or_r.append(i.strip(' '))

        # 语言
        language = infos[infos.index("语言:") + 1]
        language_list_tmp = language.split('/')
        language_list = []
        for i in language_list_tmp:
            language_list.append(i.strip(' '))

        # 分类 电影和电视剧 以及 动画片（电影）和动漫（剧集）
        if '上映时间:' in infos or '上映日期:' in infos:
            movie_categories = MediaType.MOVIE.value
        elif "首播:" in infos or "首播时间:" in infos:
            movie_categories = MediaType.TV.value
        else:
            movie_categories = "未知"

        imdb = infos[infos.index('IMDb:') + 1] if 'IMDb' in infos else ""

        # 评分 评价数
        rating_list = self.__get_media_rating_list(soup)

        # 图片网址
        movie_img = soup.select("#mainpic > a > img")[0].attrs['src']

        # 简介
        related_info = soup.select("#content > div > div.article > div > div.indent > span")
        related_infos = self.__get_media_related_infos(related_info)

        # print(rating_infos)
        movie_dict['title'] = movie_title
        movie_dict['year'] = movie_year
        movie_dict['director'] = movie_director
        movie_dict['screenwriter'] = screenwriter
        movie_dict['starring'] = starring
        movie_dict['type'] = movie_type
        movie_dict['country_or_region'] = c_or_r
        movie_dict['language'] = language_list
        movie_dict['category'] = movie_categories
        movie_dict['imdb'] = imdb
        movie_dict['rating'] = float(rating_list[0])
        movie_dict['assess'] = int(rating_list[1])
        movie_dict['image'] = movie_img
        movie_dict['related_infos'] = related_infos
        return movie_dict

    @staticmethod
    def __multiple_infos_parser(str_dict, str_key, next_number):
        str_list = []
        try:
            first_index = str_dict.index(str_key) + next_number
            str_list.append(str_dict[first_index])
            next_index = first_index
            while True:
                if str_dict[next_index + 1] == '/':
                    next_index += 2
                    str_list.append(str_dict[next_index])
                else:
                    break
            return str_list
        except Exception as err:
            log.warn(f"【DOUBAN】未解析到{str_key}数据：{err}")
            return str_list

    @staticmethod
    def __get_media_rating_list(soup):
        rating_list = ['0', '0']
        try:
            rating_info = soup.select("#interest_sectl > div > div.rating_self.clearfix")
            rating_infos = list(rating_info[0].strings)
            rating_infos = [i.strip() for i in rating_infos if i.strip() != '']
            if len(rating_infos) > 2:
                rating_list = rating_infos
                # rating_list[1] = rating_infos[1]
            else:
                rating_list[0] = 0.0
                rating_list[1] = 0
            return rating_list
        except Exception as err:
            log.warn(f"【DOUBAN】未解析到评价数据：{err}")
            return rating_list

    @staticmethod
    def __get_media_related_infos(info):
        try:
            if info:
                related_infos = list(info[0].strings)
                related_infos = [i.strip() for i in related_infos if i.strip() != '']
                related_infos = "\n".join(related_infos)
                return related_infos
            else:
                return "暂无。"
        except Exception as err:
            log.warn(f"【DOUBAN】未解析到简介：{err}")
            return "暂无..."


if __name__ == "__main__":
    print(DouBan().get_all_douban_movies())
