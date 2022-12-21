import re
import time
from urllib import parse

import requests

from app.utils import RequestUtils
from app.utils.exception_utils import ExceptionUtils


class Py115:
    cookie = None
    user_agent = None
    req = None
    uid = None
    sign = None
    err = None

    def __init__(self, cookie):
        self.cookie = cookie
        self.req = RequestUtils(cookies=self.cookie, session=requests.Session())

    # 登录
    def login(self):
        if not self.getuid():
            return False
        if not self.getsign():
            return False
        return True

    # 获取目录ID
    def getdirid(self, tdir):
        try:
            url = "https://webapi.115.com/files/getid?path=" + parse.quote(tdir or '/')
            p = self.req.get_res(url=url)
            if p:
                rootobject = p.json()
                if not rootobject.get("state"):
                    self.err = "获取目录 [{}]ID 错误：{}".format(tdir, rootobject["error"])
                    return False, ''
                return True, rootobject.get("id")
        except Exception as result:
            ExceptionUtils.exception_traceback(result)
            self.err = "异常错误：{}".format(result)
        return False, ''

    # 获取sign
    def getsign(self):
        try:
            self.sign = ''
            url = "https://115.com/?ct=offline&ac=space&_=" + str(round(time.time() * 1000))
            p = self.req.get_res(url=url)
            if p:
                rootobject = p.json()
                if not rootobject.get("state"):
                    self.err = "获取 SIGN 错误：{}".format(rootobject.get("error_msg"))
                    return False
                self.sign = rootobject.get("sign")
                return True
        except Exception as result:
            ExceptionUtils.exception_traceback(result)
            self.err = "异常错误：{}".format(result)
        return False

    # 获取UID
    def getuid(self):
        try:
            self.uid = ''
            url = "https://webapi.115.com/files?aid=1&cid=0&o=user_ptime&asc=0&offset=0&show_dir=1&limit=30&code=&scid=&snap=0&natsort=1&star=1&source=&format=json"
            p = self.req.get_res(url=url)
            if p:
                rootobject = p.json()
                if not rootobject.get("state"):
                    self.err = "获取 UID 错误：{}".format(rootobject.get("error_msg"))
                    return False
                self.uid = rootobject.get("uid")
                return True
        except Exception as result:
            ExceptionUtils.exception_traceback(result)
            self.err = "异常错误：{}".format(result)
        return False

    # 获取任务列表
    def gettasklist(self, page=1):
        try:
            tasks = []
            url = "https://115.com/web/lixian/?ct=lixian&ac=task_lists"
            while True:
                postdata = "page={}&uid={}&sign={}&time={}".format(page, self.uid, self.sign,
                                                                   str(round(time.time() * 1000)))
                p = self.req.post_res(url=url, params=postdata.encode('utf-8'))
                if p:
                    rootobject = p.json()
                    if not rootobject.get("state"):
                        self.err = "获取任务列表错误：{}".format(rootobject["error"])
                        return False, tasks
                    if rootobject.get("count") == 0:
                        break
                    tasks += rootobject.get("tasks") or []
                    if page >= rootobject.get("page_count"):
                        break
            return True, tasks
        except Exception as result:
            ExceptionUtils.exception_traceback(result)
            self.err = "异常错误：{}".format(result)
        return False, []

    # 添加任务
    def addtask(self, tdir, content):
        try:
            ret, dirid = self.getdirid(tdir)
            if not ret:
                return False, ''

            # 转换为磁力
            if re.match("^https*://", content):
                try:
                    p = self.req.get_res(url=content)
                    if p and p.headers.get("Location"):
                        content = p.headers.get("Location")
                except Exception as result:
                    ExceptionUtils.exception_traceback(result)
                    content = str(result).replace("No connection adapters were found for '", "").replace("'", "")

            url = "https://115.com/web/lixian/?ct=lixian&ac=add_task_url"
            postdata = "url={}&savepath=&wp_path_id={}&uid={}&sign={}&time={}".format(parse.quote(content), dirid,
                                                                                      self.uid, self.sign,
                                                                                      str(round(time.time() * 1000)))
            p = self.req.post_res(url=url, params=postdata.encode('utf-8'))
            if p:
                rootobject = p.json()
                if not rootobject.get("state"):
                    self.err = rootobject.get("error_msg")
                    return False, ''
                return True, rootobject.get("info_hash")
        except Exception as result:
            ExceptionUtils.exception_traceback(result)
            self.err = "异常错误：{}".format(result)
        return False, ''

    # 删除任务
    def deltask(self, thash):
        try:
            url = "https://115.com/web/lixian/?ct=lixian&ac=task_del"
            postdata = "hash[0]={}&uid={}&sign={}&time={}".format(thash, self.uid, self.sign,
                                                                  str(round(time.time() * 1000)))
            p = self.req.post_res(url=url, params=postdata.encode('utf-8'))
            if p:
                rootobject = p.json()
                if not rootobject.get("state"):
                    self.err = rootobject.get("error_msg")
                    return False
                return True
        except Exception as result:
            ExceptionUtils.exception_traceback(result)
            self.err = "异常错误：{}".format(result)
        return False

    # 根据ID获取文件夹路径
    def getiddir(self, tid):
        try:
            path = '/'
            url = "https://aps.115.com/natsort/files.php?aid=1&cid={}&o=file_name&asc=1&offset=0&show_dir=1&limit=40&code=&scid=&snap=0&natsort=1&record_open_time=1&source=&format=json&fc_mix=0&type=&star=&is_share=&suffix=&custom_order=0".format(
                tid)
            p = self.req.get_res(url=url)
            if p:
                rootobject = p.json()
                if not rootobject.get("state"):
                    self.err = "获取 ID[{}]路径 错误：{}".format(id, rootobject["error"])
                    return False, path
                patharray = rootobject["path"]
                for pathobject in patharray:
                    if pathobject.get("cid") == 0:
                        continue
                    path += pathobject.get("name") + '/'
                if path == "/":
                    self.err = "文件路径不存在"
                    return False, path
                return True, path
        except Exception as result:
            ExceptionUtils.exception_traceback(result)
            self.err = "异常错误：{}".format(result)
        return False, '/'
