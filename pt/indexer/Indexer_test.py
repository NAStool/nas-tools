# -*- coding: utf-8 -*-
"""
Created on 2022-08-15 11:43:06
---------
@summary:
---------
@author: YerWer
"""
from pt.sites import *

import dateparser
import cssselect
import copy
import re
import yaml
import cssutils
import feapder
import querystring
from pyquery import PyQuery as pq
from jinja2 import Template

cookies_txt="c_secure_ssl=eWVhaA%3D%3D; c_secure_uid=Mzk5MTk%3D; c_secure_pass=948fc5b348732320a396c4ef7d322fb9; c_secure_tracker_ssl=eWVhaA%3D%3D; c_secure_login=bm9wZQ%3D%3D"

mteamcookies="cf_clearance=frC9Wqm27XoWeTyh8Va3QitBqonOGgs0wpHNdzX3lhQ-1659945429-0-150; tp=MDRlNDQ3MTAwYWQ0MGIyZDg0N2M5YTI2Y2E2ZTZlZGU2ZTliM2M5ZQ%3D%3D"


keepfrdscookies="c_secure_uid=MzU4NzA%3D; c_secure_pass=336bf06d014ef8bec9b72aa901c0d736; c_secure_ssl=eWVhaA%3D%3D; c_secure_tracker_ssl=eWVhaA%3D%3D; c_secure_login=bm9wZQ%3D%3D; _ga=GA1.2.1159861350.1651643224;"

audiencescookies="c_secure_uid=MTYxNjY%3D; c_secure_pass=32644443b8d10d9f8904c5010d9fc3ae; c_secure_ssl=eWVhaA%3D%3D; c_secure_tracker_ssl=eWVhaA%3D%3D; c_secure_login=bm9wZQ%3D%3D;"



serchurl="https://lemonhd.org/torrents_movie.php?search=钢铁侠&search_area=name&column=g_last_upload_date&sort=asc&suggest=6"
searchurl="https://lemonhd.org/torrents_movie.php?stype=s&search=%E9%92%A2%E9%93%81%E4%BE%A0&search_area=name&seed_count=&column=added&sort=asc&suggest=4"

resultarray={}
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
    def setcookies(self,cookies,yaml,keyword):
        self.cookies=cookies
        self.config_yaml=yaml
        self.keyword=keyword
        self.torrents_info_array = []
    def start_requests(self):
        cookiesdic=self.cookies.split(';')
        import requests
        session = requests.session()
        manual_cookies={}
        #设置请求头信息
        for item in cookiesdic:
            if item !='' and item !=' ':
                name,value=item.strip().split('=',1)  #用=号分割，分割1次
                manual_cookies[name]=value  #为字典cookies添加内容


        self.indexer=indexers(self.config_yaml)
        domain=self.indexer.domain
        torrentspath=  self.indexer.search['paths'][0]['path']

        searchurl=domain+torrentspath+'?stypes=s&search='+self.keyword

        testurl="https://lemonhd.org/torrents_new.php"
        testurl3="https://kp.m-team.cc/movie.php"
        testurl2=domain+"torrents.php"
        yield feapder.Request(searchurl,cookies=manual_cookies)

    # def detail_requests(self,download_url):
    #     searchurl=self.indexer.domain+download_url
    #
    #     yield feapder.Request(searchurl, cookies=manual_cookies, callback=self.get_title_optional)

    # def get_title_optional(self, request, response):
    #     article_list = response.extract()
    #     doc = pq(article_list)
    #     t_o=doc(self.fields['title_optional']['selector'])
    #     items = [item.attr(self.fields['title_optional']['attribute']) for item in t_o.items()]
    #     self.title_optional.append(items)

    def Getdownloadvolumefactorselector(self,torrent):
        self.tor.downloadvolumefactor=[]
        for downloadvolumefactorselector in list(self.fields['downloadvolumefactor']['case'].keys()):
             downloadvolumefactor=pq(torrent)(downloadvolumefactorselector)
             if len(downloadvolumefactor)>0:
                self.tor.downloadvolumefactor.append(self.fields['downloadvolumefactor']['case'][downloadvolumefactorselector])
                self.torrents_info['downloadvolumefactor']=self.fields['downloadvolumefactor']['case'][downloadvolumefactorselector]
                break
    def Getuploadvolumefactorselector(self,torrent):
        self.tor.uploadvolumefactor=[]
        for uploadvolumefactorselector in list(self.fields['uploadvolumefactor']['case'].keys()):
             uploadvolumefactor=pq(torrent)(uploadvolumefactorselector)
             if len(uploadvolumefactor)>0:
                self.tor.uploadvolumefactor.append(self.fields['uploadvolumefactor']['case'][uploadvolumefactorselector])
                self.torrents_info['uploadvolumefactor']=self.fields['uploadvolumefactor']['case'][uploadvolumefactorselector]
                break

    #gettitle
    def Gettitle_default(self,torrent):
        # title_default
        selector=''

        if "title_default" in self.fields:
            title_default = torrent(self.fields['title_default']['selector']).clone()
            selector=self.fields['title_default']
        else:
            title_default = torrent(self.fields['title']['selector']).clone()
            selector = self.fields['title']
        if 'remove' in selector:
            removelist = selector['remove'].split(', ')
            for v in removelist:
                title_default.remove(v)


        items = [item.text() for item in title_default.items()]
        self.tor.title=items
        self.torrents_info['title']=items[0]

    def Getdetails(self,torrent):
        # details
        details=torrent(self.fields['details']['selector'])
        items = [item.attr(self.fields['details']['attribute']) for item in details.items()]
        self.tor.page_url=self.indexer.domain+items[0]
        self.tor.details=items
        self.torrents_info['details']=items[0]
        self.torrents_info['page_url']=self.indexer.domain+items[0]

    def Getdownload(self,torrent):
        # download link
        download = torrent(self.fields['download']['selector'])
        items = [item.attr(self.fields['download']['attribute']) for item in download.items()]
        self.tor.download=items
        self.torrents_info['download']=items[0]

    def Getimdbid(self,torrent):
        # imdb
        if "imdbid" in self.fields:
            imdbid = torrent(self.fields['imdbid']['selector'])
            items = [item.attr(self.fields['imdbid']['attribute']) for item in imdbid.items()]
            self.tor.imdbid=items
            if len(items)>0:
                self.torrents_info['imdbid']=items[0]


    def Getsize(self,torrent):
        # torrent size
        size=torrent(self.fields['size']['selector'])
        items = [item.text() for item in size.items()]
        self.tor.size=items
        size=items[0].split("\n")
        if size[1]=='GB':
            size=float(size[0])*1073741824
        else:
            size = float(size[0]) * 1048576
        self.torrents_info['size']=size

    def Getleechers(self,torrent):
        # torrent leechers
        leechers=torrent(self.fields['leechers']['selector'])
        items = [item.text() for item in leechers.items()]
        self.tor.leechers=items
        self.tor.peers=items
        self.torrents_info['leechers']=items[0]
        self.torrents_info['peers']=items[0]
    def Getseeders(self,torrent):
        # torrent leechers
        seeders=torrent(self.fields['seeders']['selector'])
        items = [item.text() for item in seeders.items()]
        self.tor.seeders=items
        self.torrents_info['seeders']=items[0]

    def Getgrabs(self,torrent):
        # torrent grabs
        grabs=torrent(self.fields['grabs']['selector'])
        items = [item.text() for item in grabs.items()]
        self.tor.grabs=items
        self.torrents_info['grabs']=items[0]

    def Gettitle_optional(self,torrent,fields):
        # title_optional
        if "selector" in self.fields['description']:
            selector=self.fields['description']
            t_o=torrent(selector['selector']).clone()
            items=''
            if 'attribute' in selector:
                items = [item.attr(self.fields['description']['attribute']) for item in t_o.items()]

            if 'remove' in selector:
                removelist=selector['remove'].split(', ')
                for v in removelist:
                    t_o.remove(v)

            if "contents" in selector:
                if selector['selector'].find("td.embedded") != -1:
                    t_o = t_o("span")
                items = [item.text() for item in t_o.items()]
                items=items[selector["contents"]]
                # t_o = t_o("span")[selector["contents"]]
                # items = t_o.text
            elif "index" in selector:
                items = [item.text() for item in t_o.items()]
                items=items[selector["index"]]


            self.tor.description=items
            self.torrents_info['description']=items

        if "text" in self.fields['description']:
            template = Template(self.fields['description']['text'])

            # template.render(fields=self.fields)
            tags =torrent(self.fields['tags']['selector']).text()
            subject =torrent(self.fields['subject']['selector']).text()
            render_dict={}
            render_dict['tags']=tags
            render_dict['subject']=subject
            title= template.render(fields = render_dict)
            self.torrents_info['description'] = title
            # exec(self.fields['description']['text'])



        # items = [item.text() for item in t_o.items()]

        # self.tor.description=[]
        # for i in range(int(len(items)/3)):


    def Getdate_added(self,torrent):
        # date_added
        selector=torrent(self.fields['date_elapsed']['selector'])
        items = [item.attr(self.fields['date_elapsed']['attribute']) for item in selector.items()]
        self.tor.date_added=items
        self.torrents_info['date_added']=items[0]

    def Getdate_elapsed(self,torrent):
        # date_added
        selector=torrent(self.fields['date_elapsed']['selector'])
        items = [item.text() for item in selector.items()]
        self.tor.date_elapsed=items
        self.torrents_info['date_elapsed']=items[0]


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


                    # items=querystring.parse_qs(str)

        self.tor.category=items[0]
        self.torrents_info['category']=items[0]

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
                            items = dateparser.parse(itemdata, date_formats=[arg1])

        self.tor.free_deadline=items
        self.torrents_info['free_deadline']=items

    def Getinfo(self,torrent):
        self.Gettitle_default(torrent)
        self.Gettitle_optional(torrent , self.fields )
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
        return self.torrents_info

    def parse(self, request, response):
        # 提取网站title


        print(response.xpath("//title/text()").extract_first())
        self.article_list = response.extract()
        # torrentlist=article_list.xpath('//table[@class="torrents"]/tr[acontains(@href,"download.php?")]')
        # detials=response.xpath('string(//a[@href="details_movie.php?id=276488"])')
        self.fields=self.indexer.torrents['fields']
        doc = pq(self.article_list)
        torrents_selector=self.indexer.torrents['list']['selector']
        str_list = list(torrents_selector)
        has_index = 0
        has_index = torrents_selector.find('has')
        flag = 0
        if has_index != 0:
            str_list.insert(has_index+4, '"')
            for i in range(len(str_list)):
                if i > has_index+2:
                    n = str_list[i]
                    if n == '(':
                        flag = flag+1
                    if n == ')':
                        flag = flag - 1
                    if flag == 0:
                        str_list.insert(i, '"')
            torrents_selector = "".join(str_list)

        torrents=doc(torrents_selector)
        self.videos=[]
        self.tor=torrentclass()
        self.torrents_info={}
        # title_default


        self.tor.downloadvolumefactor=[]
        for torn in torrents:
            torn=pq(torn)
            self.tor.indexer=self.indexer.id
            self.torrents_info_array.append(copy.deepcopy(self.Getinfo(torn)))
        global resultarray
        resultarray=self.torrents_info_array


import time
if __name__ == "__main__":
    sites_array = Sites().get_sites()
    result_array = []
    for sites_select in range(8):
        if sites_select==8:
            continue
        spider = SpiderTest()
        spider.setcookies(sites_array[sites_select]["cookie"], "sites/" + sites_array[sites_select]["name"] + ".yml", "钢铁侠3")
        status = len(spider.torrents_info_array)
        spider.start()
        status = len(spider.torrents_info_array)
        while status == 0:
            status=len(spider.torrents_info_array)
            time.sleep(1)
        result_array.append(spider.torrents_info_array.copy())
        spider.torrents_info_array.clear()

