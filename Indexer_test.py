# -*- coding: utf-8 -*-
"""
Created on 2022-08-15 11:43:06
---------
@summary:
---------
@author: YerWer
"""
import cssselect
import copy
import dateparser
import re
import yaml
import cssutils
import feapder
import querystring
manual_cookies={}
from pyquery import PyQuery as pq
cookies_txt="c_secure_ssl=eWVhaA%3D%3D; c_secure_uid=Mzk5MTk%3D; c_secure_pass=948fc5b348732320a396c4ef7d322fb9; c_secure_tracker_ssl=eWVhaA%3D%3D; c_secure_login=bm9wZQ%3D%3D"

mteamcookies="cf_clearance=frC9Wqm27XoWeTyh8Va3QitBqonOGgs0wpHNdzX3lhQ-1659945429-0-150; tp=MDRlNDQ3MTAwYWQ0MGIyZDg0N2M5YTI2Y2E2ZTZlZGU2ZTliM2M5ZQ%3D%3D"


keepfrdscookies="c_secure_uid=MzU4NzA%3D; c_secure_pass=336bf06d014ef8bec9b72aa901c0d736; c_secure_ssl=eWVhaA%3D%3D; c_secure_tracker_ssl=eWVhaA%3D%3D; c_secure_login=bm9wZQ%3D%3D; _ga=GA1.2.1159861350.1651643224;"

audiencescookies="c_secure_uid=MTYxNjY%3D; c_secure_pass=32644443b8d10d9f8904c5010d9fc3ae; c_secure_ssl=eWVhaA%3D%3D; c_secure_tracker_ssl=eWVhaA%3D%3D; c_secure_login=bm9wZQ%3D%3D;"

cookiesdic=audiencescookies.split(';')
import requests
session = requests.session()

#设置请求头信息
for item in cookiesdic:
    if item !='':
        name,value=item.strip().split('=',1)  #用=号分割，分割1次
        manual_cookies[name]=value  #为字典cookies添加内容

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
        self.indexer=indexers('sites/audiences.yml')
        domain=self.indexer.domain
        torrentspath=  self.indexer.search['paths'][0]['path']
        searchurl=domain+torrentspath+'?stypes=s&search='+'钢铁侠'+'&search_area=name&seed_count=&column=added&sort=asc&suggest=4'

        testurl="https://lemonhd.org/torrents_new.php"
        testurl3="https://kp.m-team.cc/movie.php"
        testurl2=domain+"torrents.php"
        yield feapder.Request(testurl2,cookies=manual_cookies)

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
    def Getuploadvolumefactorselector(self,torrent):
        self.tor.uploadvolumefactor=[]
        for uploadvolumefactorselector in list(self.fields['uploadvolumefactor']['case'].keys()):
             uploadvolumefactor=pq(torrent)(uploadvolumefactorselector)
             if len(uploadvolumefactor)>0:
                self.tor.uploadvolumefactor.append(self.fields['uploadvolumefactor']['case'][uploadvolumefactorselector])
                break
    def Gettitle_default(self,torrent):
        # title_default
        if "title_default" in self.fields:
            title_default = torrent(self.fields['title_default']['selector'])
        else:
            title_default = torrent(self.fields['title']['selector'])
        items = [item.text() for item in title_default.items()]
        self.tor.title=items

    def Getdetails(self,torrent):
        # details
        details=torrent(self.fields['details']['selector'])
        items = [item.attr(self.fields['details']['attribute']) for item in details.items()]
        self.tor.page_url=self.indexer.domain+items[0]
        self.tor.details=items

    def Getdownload(self,torrent):
        # download link
        download = torrent(self.fields['download']['selector'])
        items = [item.attr(self.fields['download']['attribute']) for item in download.items()]
        self.tor.download=items

    def Getimdbid(self,torrent):
        # imdb
        if "imdbid" in self.fields:
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
        self.tor.peers=items

    def Getseeders(self,torrent):
        # torrent leechers
        seeders=torrent(self.fields['seeders']['selector'])
        items = [item.text() for item in seeders.items()]
        self.tor.seeders=items
    def Getgrabs(self,torrent):
        # torrent grabs
        grabs=torrent(self.fields['grabs']['selector'])
        items = [item.text() for item in grabs.items()]
        self.tor.grabs=items
    def Gettitle_optional(self,torrent):
        # title_optional
        selector=self.fields['description']
        t_o=torrent(selector['selector'])
        if "contents" in selector:
            t_o=t_o("span")[selector["contents"]]
            items=t_o.text


        # items = [item.text() for item in t_o.items()]

        # self.tor.description=[]
        # for i in range(int(len(items)/3)):
        self.tor.description=items

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
                if filter['name']=="querystring":
                    arg1=filter['args']
                    str=items[0]
                    str="car=daasd$dada=dasda"


                    items=querystring.parse_qs(str)

        self.tor.category=items


    def Getfree_deadline(self,torrent):
        # date_added
        selector=torrent(self.fields['free_deadline']['selector'])
        # items = [item.text() for item in selector.items()]
        items = [item.attr(self.fields['free_deadline']['attribute']) for item in selector.items()]
        # print(items)
        # print(len(items))
        if len(items)>0 and items != None:
            if items[0]!=None:
                # print(len(items))
                if "filters" in self.fields['free_deadline']:
                     itemdata=items[0]
                     for filter in self.fields['free_deadline']['filters']:
                        if filter['name']=="re_search":
                            arg1=filter['args'][0]
                            arg2=filter['args'][1]
                            items=re.search(arg1,itemdata,arg2)[0]
                        if filter['name']=="dateparse":
                            arg1=filter['args']
                            items = dateparser.parse(items, date_formats=[arg1])

        self.tor.free_deadline=items


    def Getinfo(self,torrent):
        self.Gettitle_default(torrent)
        self.Gettitle_optional(torrent)
        self.Getgrabs(torrent)
        self.Getleechers(torrent)
        self.Getseeders(torrent)
        self.Getsize(torrent)
        self.Getimdbid(torrent)
        self.Getdownload(torrent)
        self.Getdetails(torrent)
        self.Getdownloadvolumefactorselector(torrent)
        self.Getuploadvolumefactorselector(torrent)

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
        # torrents=doc.css("table.torrents > tr:has(table.torrentname)")

        # html_obj = etree.HTML(article_list)
        # span = doc.cssselect(
        # '.list > .four')[
        # 0]



        # aa=doc('a[href^="download.php?"]')



        torrents=doc(self.indexer.torrents['list']['selector'])
        self.videos=[]
        self.tor=torrentclass()
        # title_default

        self.torrents_info=[]
        self.tor.downloadvolumefactor=[]
        for torn in torrents:
            torn=pq(torn)
            self.tor.indexer=self.indexer.id
            self.torrents_info.append(copy.deepcopy(self.Getinfo(torn)))

        html_data=response.xpath('//a[@herf="download.php"]')

        print("网站地址: ", response.url)





if __name__ == "__main__":
    SpiderTest().start()
