import datetime
import html
import re

import cn2an
from lxml import etree

import log
from utils.http_utils import RequestUtils


class DoubanMovie:
    __headers = {
        'Referer': 'https://movie.douban.com/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/96.0.4664.110 Safari/537.36 '
    }

    def __init__(self):
        self.cookies = None
        self.req = RequestUtils(request_interval_mode=True)
        # 先访问一次首页，显得像个正常人
        ret = self.req.get_res('https://movie.douban.com/', headers=self.__headers)
        self.__set_cookies(ret)

    def __set_cookies(self, rest):
        if self.cookies is None:
            self.cookies = rest.cookies

    def get_movie_by_id(self, i_id):
        return self.get_movie_detail('https://movie.douban.com/subject/%s' % i_id)

    @staticmethod
    def trans_season_number(i_str):
        if i_str.isdigit():
            return int(i_str)
        else:
            return cn2an.cn2an(i_str)

    def get_movie_detail(self, url):
        rest = self.req.get_res(url, headers=self.__headers, cookies=self.cookies)
        self.__set_cookies(rest)
        text = rest.text
        if text.find('有异常请求从你的 IP 发出') != -1:
            log.error('【DOUBAN】被豆瓣识别到抓取行为了，请更换IP后才能使用')
            return None
        match_name = re.findall('<span property="v:itemreviewed">(.+)</span>', text)
        if len(match_name) > 0:
            name = match_name[0]
        else:
            return None
        match_alias = re.findall('<span class="pl">又名:</span>([^<]+)<br/>', text)
        alias_list = []
        if len(match_alias) > 0:
            alias_list = match_alias[0].strip().split(' / ')
        alias_list = list(map(lambda x: html.unescape(x), alias_list))
        match_year = re.findall(r'<span class="year">\((\d+)\)</span>', text)
        if len(match_year) > 0:
            year = match_year[0]
        else:
            year = ""
        match_cates = re.findall(r'<span\s+property="v:genre">([^>]+)</span>', text)
        cates = []
        for cate in match_cates:
            cates.append(cate)
        match_dates = re.findall(r'<span property="v:initialReleaseDate" content="(\d+-\d+-\d+)\(([^)]+)\)">', text)
        dates = []
        match_dates.sort(reverse=False)
        for date in match_dates:
            dates.append({'date': date[0], 'aera': date[1]})
        match_season = re.search(r'<span\s*class="pl">季数:</span>\s*(\d+)<br/>', text)
        season_number = None
        if match_season:
            season_number = match_season.group(1)
        match_js = re.findall(r'<span class="pl">集数:</span>\s*(\d+)<br/>', text)
        if match_js is not None and len(match_js) > 0:
            episode = int(str(match_js[0]))
            mtype = 'Series'
            # 当影视为剧集时，本地语言影视名，需要考虑到第*季字符的影响，不能直接按空格切分，如 权力的游戏 第八季 Game。。。
            match_season = re.search('第(.+)季', name)
            if match_season:
                season_str_in_name = match_season.group()
                if season_number is None:
                    season_number = self.trans_season_number(match_season.group(1))
                first_space_idx = name.find(season_str_in_name + ' ')
                if first_space_idx != -1:
                    first_space_idx = first_space_idx + len(season_str_in_name)
            else:
                first_space_idx = name.find(' ')
                season_number = 1
            local_name = name[first_space_idx + 1:len(name)]
        else:
            mtype = 'Movie'
            episode = 1
            first_space_idx = name.find(' ')
            local_name = name[first_space_idx + 1:len(name)]
        if first_space_idx != -1:
            name = name[0:first_space_idx]
        return {'type': mtype,
                'name': html.unescape(name),
                'local_name': html.unescape(local_name),
                'alias': alias_list,
                'year': year,
                'cate': cates,
                'release_date': dates,
                'season_number': season_number,
                'episode': episode}

    def get_user_movie_list(self, user, types=None, within_days=365, turn_page=True) -> object:
        """
        获取豆瓣电影想看 :param user: 豆瓣唯一账号 :param types: 豆瓣用户电影类型，支持wish（想看）、do（在看）、collect（看过） :param
        within_days:多少天内加入想看的影视，默认365 :param turn_page: 是否自动翻页 :return: {'name': '地球改变之年', 'local_name': 'The Year
        Earth Changed', 'year': '2021', 'type': 'Movie', 'count': None, 'release_date': [{'date': '2021-04-16',
        'aera': '美国'}], 'cate': ['纪录片'], 'add_date': '2022-01-01'}
        """
        if types is None:
            types = ['wish']
        all_result = []
        for type_item in types:
            log.info('【DOUBAN】开始获取%s(%s)的电影' % (user, type_item))
            offset = 0
            uri = '/people/%s/%s?start=%s&sort=time&rating=all&filter=all&mode=grid' % (user, type_item, offset)
            page_cnt = 1
            result = []
            while uri is not None:
                url = 'https://movie.douban.com' + uri
                rest = self.req.get_res(url, headers=self.__headers, cookies=self.cookies)
                self.__set_cookies(rest)
                text = rest.text
                if text.find('有异常请求从你的 IP 发出') != -1:
                    log.error('【DOUBAN】被豆瓣识别到抓取行为了，请更换IP后才能使用')
                    return None
                html_content = etree.HTML(text)
                page = html_content.xpath('//div[@class="paginator"]/span[@class="next"]/a')
                if len(page) > 0:
                    uri = page[0].attrib['href']
                else:
                    uri = None
                movie_url_list = html_content.xpath('//li[@class="title"]/a/@href')
                add_date_list = html_content.xpath('//li/span[@class="date"]/text()')
                movie_list_a = html_content.xpath('//div[@class="item"]/div[@class="info"]/ul/li['
                                                  '@class="title"]/a/em/text()')
                for i in range(len(movie_list_a)):
                    add_date = add_date_list[i]
                    days_ago = (datetime.datetime.now() - datetime.datetime.strptime(add_date, "%Y-%m-%d")).days
                    if within_days is not None and days_ago > within_days:
                        turn_page = False
                        continue
                    url = movie_url_list[i]
                    a_name = movie_list_a[i]
                    name_arr = a_name.split(' / ')
                    if len(name_arr) > 1:
                        local_name = name_arr[1]
                    else:
                        local_name = None
                    match_id = re.search(r'/subject/(\d+)', url)
                    if match_id:
                        ids = match_id.group(1)
                    else:
                        ids = None
                    result.append(
                        {'id': ids, 'name': name_arr[0], 'local_name': local_name, 'url': url,
                         'add_date': add_date})
                if not turn_page:
                    break
                if uri is not None:
                    log.info('【DOUBAN】已经完成%s页数据的获取，开始获取下一页...' % page_cnt)
                    page_cnt = page_cnt + 1
            all_result = all_result + result
            log.info('【DOUBAN】%s天之内加入%s的影视，共%s部' % (within_days, type_item, len(result)))
        return all_result


if __name__ == "__main__":
    res = DoubanMovie().get_user_movie_list('232496822')
    print(str(res))
