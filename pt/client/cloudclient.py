import requests
import json
import time
from urllib import parse, request
import re

class Cloud115Client:
    cookie = None
    user_agent = None
    uid = None
    sign = None
    err = None
    
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36"

    #登录
    def login(self):
        ret = self.getuid()
        if ret == False:
            return False
        ret = self.getsign() 
        if ret == False:
            return False
        return True

    #获取目录ID
    def getdirid(self, dir):
        try:
            id = ''
            url = "https://webapi.115.com/files/getid?path=" + parse.quote(dir)
            headers = {"User-Agent": self.user_agent, "Cookie": self.cookie}
            p = requests.get(url = url, headers = headers)
            rootobject = json.loads(p.text)
            if (rootobject["state"] != True):
                self.err = "获取目录[{}] ID 错误, {}".format(dir, rootobject["error"])
                return False, id
            id = rootobject["id"]
            return True, id
        except Exception as result:
            self.err = "异常错误, {}".format(result)
            return False, id

    #获取sign
    def getsign(self):
        try:
            self.sign = ''
            url = "https://115.com/?ct=offline&ac=space&_=" + str(round(time.time() * 1000))
            headers = {"User-Agent": self.user_agent, "Cookie": self.cookie}
            p = requests.get(url = url, headers = headers)
            rootobject = json.loads(p.text)
            if (rootobject["state"] != True):
                self.err = "获取 SIGN 错误, {}".format(rootobject["error"])
                return False
            self.sign = rootobject["sign"]
            return True
        except Exception as result:
            self.err = "异常错误, {}".format(result)
            return False

    #获取UID
    def getuid(self):
        try:
            self.uid = ''
            url = "https://webapi.115.com/files?aid=1&cid=0&o=user_ptime&asc=0&offset=0&show_dir=1&limit=30&code=&scid=&snap=0&natsort=1&star=1&source=&format=json"
            headers = {"User-Agent": self.user_agent, "Cookie": self.cookie}
            p = requests.get(url = url, headers = headers)
            rootobject = json.loads(p.text)
            if (rootobject["state"] != True):
                self.err = "获取 UID 错误, {}".format(rootobject["error"])
                return False
            self.uid = rootobject["uid"]
            return True
        except Exception as result:
            self.err = "异常错误, {}".format(result)
            return False

    #获取任务列表
    def gettasklist(self, page = 1):
        try:
            tasks = []
            url = "https://115.com/web/lixian/?ct=lixian&ac=task_lists"
            headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "User-Agent": self.user_agent, "Cookie": self.cookie}
            while True:
                postdata = "page={}&uid={}&sign={}&time={}".format(page, self.uid, self.sign, str(round(time.time() * 1000)))
                p = requests.post(url = url, data = postdata.encode('utf-8'), headers = headers)
                rootobject = json.loads(p.text)
                if (rootobject["state"] != True):
                    self.err = "获取任务列表错误, {}".format(rootobject["error"])
                    return False, tasks
                if rootobject["count"] == 0:
                    break
                tasks += rootobject["tasks"]
                if page >= rootobject["page_count"]:
                    break
            return True, tasks
        except Exception as result:
            self.err = "异常错误, {}".format(result)
            return False, tasks
    
    #添加任务
    def addtask(self, dir, content):
        try:
            hash = ''
            ret, dirid = self.getdirid(dir)
            if (ret == False):
                return False, hash

            #转换为磁力
            if re.match("^https*://", content):
                try:
                    url = content
                    headers = {"User-Agent": self.user_agent}
                    p = requests.get(url = url, verify=False, headers = headers)
                    if p.headers:
                        content = p.headers["Location"]
                except Exception as result:
                    content = str(result).replace("No connection adapters were found for '", "").replace("'", "")
                    


            url = "https://115.com/web/lixian/?ct=lixian&ac=add_task_url"
            postdata = "url={}&savepath=&wp_path_id={}&uid={}&sign={}&time={}".format(parse.quote(content), dirid, self.uid, self.sign, str(round(time.time() * 1000))) 
            headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "User-Agent": self.user_agent, "Cookie": self.cookie}
            p = requests.post(url = url, data = postdata.encode('utf-8'), headers = headers)
            rootobject = json.loads(p.text)
            if (rootobject["state"] != True):
                self.err = "添加下载任务错误, {}".format(rootobject["error"])
                return False, hash
            hash = rootobject["info_hash"]
            return True, hash
        except Exception as result:
            self.err = "异常错误, {}".format(result)
            return False, hash

    #删除任务
    def deltask(self, hash):
        try:
            url = "https://115.com/web/lixian/?ct=lixian&ac=task_del"
            postdata = "hash[0]={}&uid={}&sign={}&time={}".format(hash, self.uid, self.sign, str(round(time.time() * 1000))) 
            headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "User-Agent": self.user_agent, "Cookie": self.cookie}
            p = requests.post(url = url, data = postdata.encode('utf-8'), headers = headers)
            rootobject = json.loads(p.text)
            if (rootobject["state"] != True):
                self.err = "删除下载任务错误, {}".format(rootobject["error"])
                return False
            return True
        except Exception as result:
            self.err = "异常错误, {}".format(result)
            return False

    #根据ID获取文件夹路径
    def getiddir(self, id):
        try:
            path = '/'
            url = "https://aps.115.com/natsort/files.php?aid=1&cid={}&o=file_name&asc=1&offset=0&show_dir=1&limit=40&code=&scid=&snap=0&natsort=1&record_open_time=1&source=&format=json&fc_mix=0&type=&star=&is_share=&suffix=&custom_order=0".format(id)
            headers = {"User-Agent": self.user_agent, "Cookie": self.cookie}
            p = requests.get(url = url, headers = headers)
            rootobject = json.loads(p.text)
            if (rootobject["state"] != True):
                self.err = "获取 ID[{}] 路径错误, {}".format(id, rootobject["error"])
                return False, path
            patharray = rootobject["path"]
            for pathobject in patharray:
                if pathobject["cid"] == 0:
                    continue
                path += pathobject["name"] + '/'
            if path == "/":
                self.err = "文件路径不存在"
                return False, path
            return True, path
        except Exception as result:
            self.err = "异常错误, {}".format(result)
            return False, path