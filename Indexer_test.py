# -*- coding: utf-8 -*-
"""
Created on 2022-08-15 11:43:06
---------
@summary:
---------
@author: YerWer
"""
import yaml
import cssutils
import feapder
manual_cookies={}
from pyquery import PyQuery as pq

cookies_txt="c_secure_ssl=eWVhaA%3D%3D; c_secure_uid=Mzk5MTk%3D; c_secure_pass=948fc5b348732320a396c4ef7d322fb9; c_secure_tracker_ssl=eWVhaA%3D%3D; c_secure_login=bm9wZQ%3D%3D"
cookiesdic=cookies_txt.split(';')
import requests
session = requests.session()

#设置请求头信息
for item in cookiesdic:
    if item !='' :
        name,value=item.strip().split('=',1)  #用=号分割，分割1次
        manual_cookies[name]=value  #为字典cookies添加内容

#将字典转为CookieJar：
cookiesJar = requests.utils.cookiejar_from_dict(manual_cookies, cookiejar=None,overwrite=True)

#将cookiesJar赋值给会话
session.cookies=cookiesJar

#向目标网站发起请求

#将CookieJar转为字典：
# res_cookies_dic = requests.utils.dict_from_cookiejar(res.cookies)
'//*[@id="outer"]/table/tbody/tr/td/table[2]/tbody/tr[2]/td[3]/div[1]/a'
xpath='//*[@id="outer"]/table/tbody/tr/td/table[2]/tbody/tr[2]/td[3]/div[2]'
serchurl="https://lemonhd.org/torrents_movie.php?search=钢铁侠&search_area=name&column=g_last_upload_date&sort=asc&suggest=6"
searchurl="https://lemonhd.org/torrents_movie.php?stype=s&search=%E9%92%A2%E9%93%81%E4%BE%A0&search_area=name&seed_count=&column=added&sort=asc&suggest=4"

class indexers():
    def __init__(self,url):
        with open(url) as f:
            datas = yaml.safe_load(f)
            self.datas = datas
            self.id = self.datas['id']
            self.name = self.datas['name']
            self.domain = self.datas['domain']
            self.userinfo = self.datas['userinfo']
            self.search = self.datas['search']
            self.torrents = self.datas['torrents']
            self.category_mappings = self.datas['category_mappings']

    def get_userinfo(self):
        return self.userinfo

    def get_search(self):
        return self.search

    def get_torrents(self):
        return self.torrents

    def get_category_mapping(self):
        return self.category_mappings


class torrentclass():
    def __init__(self):
        pass



searchurl="https://lemonhd.org/torrents_movie.php?stype=s&search=%E9%92%A2%E9%93%81%E4%BE%A0&search_area=name&seed_count=&column=added&sort=asc&suggest=4"


class SpiderTest(feapder.AirSpider):

    def start_requests(self):
        self.indexer=indexers('./nm.yml')
        domain=self.indexer.domain
        torrentspath=  self.indexer.search['paths'][0]['path']
        searchurl=domain+torrentspath+'?stypes=s&search='+'钢铁侠'+'&search_area=name&seed_count=&column=added&sort=asc&suggest=4'

        testurl="https://lemonhd.org/torrents_new.php"
        yield feapder.Request(searchurl,cookies=manual_cookies)

    def detail_requests(self,download_url):
        searchurl=self.indexer.domain+download_url

        yield feapder.Request(searchurl, cookies=manual_cookies, callback=self.get_title_optional)

    def get_title_optional(self, request, response):
        article_list = response.extract()
        doc = pq(article_list)
        t_o=doc(self.fields['title_optional']['selector'])
        items = [item.attr(self.fields['title_optional']['attribute']) for item in t_o.items()]
        self.title_optional.append(items)

    def Getdownloadvolumefactorselector(self,torrent):
        self.tor.downloadvolumefactor=[]
        for downloadvolumefactorselector in list(self.fields['downloadvolumefactor']['case'].keys()):
             downloadvolumefactor=pq(torrent)(downloadvolumefactorselector)
             if len(downloadvolumefactor)>0:
                self.tor.downloadvolumefactor.append(self.fields['downloadvolumefactor']['case'][downloadvolumefactorselector])
                break

    def Gettitle_default(self,torrent):
        # title_default
        title_default = torrent(self.fields['title_default']['selector'])
        items = [item.text() for item in title_default.items()]
        self.tor.title_default=items

    def Getdetails(self,torrent):
        # details
        details=torrent(self.fields['details']['selector'])
        items = [item.attr(self.fields['details']['attribute']) for item in details.items()]
        self.tor.details=items

    def Getdownload(self,torrent):
        # download link
        download = torrent(self.fields['download']['selector'])
        items = [item.attr(self.fields['download']['attribute']) for item in download.items()]
        self.tor.download=items

    def Getimdbid(self,torrent):
        # imdb
        imdbid = torrent(self.fields['imdbid']['selector'])
        items = [item.attr(self.fields['imdbid']['attribute']) for item in imdbid.items()]
        self.tor.imdbid=items

    def Getsize(self,torrent):
        # torrent size
        size=torrent(self.fields['size']['selector'])
        items = [item.text() for item in size.items()]
        self.tor.size=items

    def Getleechers(self,torrent):
        # torrent leechers
        leechers=torrent(self.fields['leechers']['selector'])
        items = [item.text() for item in leechers.items()]
        self.tor.leechers=items

    def Getgrabs(self,torrent):
        # torrent grabs
        grabs=torrent(self.fields['grabs']['selector'])
        items = [item.text() for item in grabs.items()]
        self.tor.grabs=items
    def Gettitle_optional(self,torrent):
        # title_optional
        t_o=torrent(self.fields['description']['selectors'])
        items = [item.text() for item in t_o.items()]
        self.tor.title_optional=[]
        for i in range(int(len(items)/3)):
            self.tor.title_optional.append(items[i*3+1])

    def Getdate_added(self,torrent):
        # date_added
        selector=torrent(self.fields['date_elapsed']['selector'])
        items = [item.attr(self.fields['date_elapsed']['attribute']) for item in selector.items()]
        self.tor.date_added=items

    def Getdate_elapsed(self,torrent):
        # date_added
        selector=torrent(self.fields['date_elapsed']['selector'])
        items = [item.text() for item in selector.items()]
        self.tor.date_elapsed=items

    def Getcategory(self,torrent):
        # date_added
        selector=torrent(self.fields['category']['selector'])
        items = [item.attr(self.fields['category']['attribute']) for item in selector.items()]
        if "filters" in self.fields['category']:
            for filter in self.fields['category']['filters']:
                if filter['name']=="replace":
                    arg1=filter['args'][0]
                    arg2=filter['args'][1]
                    for i in range(len(items)):
                        items[i]=items[i].replace(arg1,arg2)
        self.tor.category=items

    def Getfree_deadline(self,torrent):
        # date_added
        selector=torrent(self.fields['free_deadline']['selector'])
        items = [item.text() for item in selector.items()]
        self.tor.free_deadline=items


    def Getinfo(self,torrent):
        self.Gettitle_default(torrent)
        self.Gettitle_optional(torrent)
        self.Getgrabs(torrent)
        self.Getleechers(torrent)
        self.Getsize(torrent)
        self.Getimdbid(torrent)
        self.Getdownload(torrent)
        self.Getdetails(torrent)
        self.Getdownloadvolumefactorselector(torrent)
        self.Getdate_added(torrent)
        self.Getdate_elapsed(torrent)
        self.Getcategory(torrent)
        self.Getfree_deadline(torrent)
        return self.tor

    def parse(self, request, response):
        # 提取网站title


        print(response.xpath("//title/text()").extract_first())
        article_list = response.extract()

        # torrentlist=article_list.xpath('//table[@class="torrents"]/tr[acontains(@href,"download.php?")]')
        # detials=response.xpath('string(//a[@href="details_movie.php?id=276488"])')
        self.fields=self.indexer.torrents['fields']

        doc = pq(article_list)
        # aa=doc('a[href^="download.php?"]')


        torrents=doc(self.indexer.torrents['list']['selector'])
        self.videos=[]

        self.tor=torrentclass()
        # title_default

#outer > table > tbody > tr > td > table.torrents > tbody > tr:nth-child(2) > td:nth-child(3) > div:nth-child(2)
#form_torrent > table > tbody > tr:nth-child(2) > td.torrenttr > table > tbody > tr > td:nth-child(2) > a > b
#form_torrent > table > tbody > tr:nth-child(2) > td.torrenttr > table > tbody > tr > td:nth-child(2) > br




        # downloadvolumefactorselector


        # torrentslist=torrents("td")
        self.torrents_info=[]
        self.tor.downloadvolumefactor=[]
        for torn in torrents:
            torn=pq(torn)
            self.torrents_info.append(self.Getinfo(torn))



        # items = [item.attr(self.fields['title_optional']['attribute']) for item in t_o.items()]


        # self.title_optional=[]
        # searchurl=self.indexer.domain+self.tor.details[0]

        # yield feapder.Request(searchurl,callback=self.get_title_optional,cookies=manual_cookies) # 不指定callback，任务会调度默认的parser上


        # title_optional
        # self.detail_requests(self.tor.details[0])
        # title_optional =self.title_optional
        # items = [item.text() for item in title_optional.items()]
        # tor.title_optional=items

        # self.videos.append(tor)





#        # detials = response.xpath('//a[starts-with(@href,"details_")]')
#         download =response.xpath('//a[starts-with(@href,"download.php?")]')

        # a[href^="download.php?"]
        # titles=torrent.xpath('string(//a[@title][@href="details_movie.php?id=276488"])').extract_first()
        # torrent.
        # article_list = response.xpath('a[@herf="details_"]')
        html_data=response.xpath('//a[@herf="download.php"]')
        # for torrent in html_data:
        #     title = torrent.xpath("./text()").extract_first()
        #     url = torrent.xpath("./@href").extract_first()

        # content = response.xpath(
        #     'string(//[@class="mainouter"])'
        # ).extract_first()  # string 表达式是取某个标签下的文本，包括子标签文本
        # 提取网站描述
        # print(response.xpath("//torrents"))
        print("网站地址: ", response.url)

# class GetTitleOptional(feapder.AirSpider):
#     def start_requests(self,download_url):
#         searchurl=self.indexer.domain+download_url
#         yield feapder.Request(searchurl, cookies=manual_cookies)
#
#     def parse(self, request, response):
#         t_o=response(self.fields['title_optional']['selector'])
#         # item.attr(self.fields['title_optional']['attribute'])
#         items = [item.attr(self.fields['title_optional']['attribute']) for item in t_o.items()]
#         self.title_optional.append(items)



if __name__ == "__main__":
    SpiderTest().start()
