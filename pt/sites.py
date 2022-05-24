import re
from datetime import datetime

import requests

import log
from config import Config
from utils.functions import singleton, num_filesize
from utils.http_utils import RequestUtils
from utils.sqls import get_config_site


@singleton
class Sites:
    __sites_data = {}
    __pt_sites = None
    __user_agent = None
    __last_update_time = None

    def __init__(self):
        self.init_config()
        self.refresh_pt_data()

    def init_config(self):
        config = Config()
        app = config.get_config('app')
        pt = config.get_config('pt')
        if pt:
            self.__pt_sites = get_config_site()
            self.__user_agent = app.get('user_agent')

    def refresh_pt_data(self, force=False):
        """
        刷新PT站下载上传量
        """
        if not self.__pt_sites:
            return
        if not force and self.__last_update_time and (datetime.now() - self.__last_update_time).days < 0.5:
            return
        self.__sites_data = {}
        for site_info in self.__pt_sites:
            if not site_info:
                continue
            site_name = site_info[1]
            site_url = site_info[4]
            site_cookie = site_info[5]
            try:
                res = RequestUtils(headers=self.__user_agent, cookies=site_cookie).get_res(url=site_url)
                if res and res.status_code == 200:
                    html_text = res.text
                    if not html_text:
                        continue
                    upload_match = re.search(r"上[传傳]量[:：<>/a-z=\"\s#;]+([0-9,.\s]+[KMGTP]B)", html_text, flags=re.IGNORECASE)
                    download_match = re.search(r"下[载載]量[:：<>/a-z=\"\s#;]+([0-9,.\s]+[KMGTP]B)", html_text, flags=re.IGNORECASE)
                    if not upload_match or not download_match:
                        continue
                    # 上传量
                    upload_text = upload_match.group(1)
                    upload = num_filesize(upload_text.strip())
                    # 下载量
                    download_text = download_match.group(1)
                    download = num_filesize(download_text.strip())
                    if not self.__sites_data.get(site_name):
                        self.__sites_data[site_name] = {"upload": upload, "download": download}
                elif not res:
                    log.error("【PT】站点 %s 连接失败：%s" % (site_name, site_url))
                else:
                    log.error("【PT】站点 %s 获取流量信息失败，状态码：%s" % (site_name, res.status_code))
            except Exception as e:
                log.error("【PT】站点 %s 获取流量信息失败：%s" % (site_name, str(e)))
        # 更新时间
        if self.__sites_data:
            self.__last_update_time = datetime.now()

    def get_pt_date(self):
        """
        获取PT站上传下载量
        """
        return self.__sites_data
