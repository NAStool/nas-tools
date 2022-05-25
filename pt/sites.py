import re
from datetime import datetime

import requests

import log
from config import Config
from utils.functions import singleton, num_filesize
from utils.http_utils import RequestUtils
from utils.sqls import get_config_site, insert_site_statistics


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
        刷新PT站下载上传量，默认间隔3小时
        """
        if not self.__pt_sites:
            return
        if not force and self.__last_update_time and (datetime.now() - self.__last_update_time).seconds < 3 * 3600:
            return
        self.__sites_data = {}
        for site_info in self.__pt_sites:
            if not site_info:
                continue
            site_name = site_info[1]
            site_url = site_info[4]
            if not site_url and site_info[3]:
                site_url = site_info[3]
            if not site_url:
                continue
            split_pos = str(site_url).rfind("/")
            if split_pos != -1 and split_pos > 8:
                site_url = site_url[:split_pos]
            site_cookie = str(site_info[5])
            try:
                res = RequestUtils(headers=self.__user_agent, cookies=site_cookie).get_res(url=site_url)
                if res and res.status_code == 200:
                    res.encoding = res.apparent_encoding
                    html_text = res.text
                    if not html_text:
                        continue
                    html_text = re.sub(r"#\d+", "", html_text)
                    upload_match = re.search(r"上[传傳]量[:：<>/a-zA-Z=\"\s#;]+([0-9,.\s]+[KMGTP]*B)", html_text)
                    download_match = re.search(r"下[载載]量[:：<>/a-zA-Z=\"\s#;]+([0-9,.\s]+[KMGTP]*B)", html_text)
                    ratio_match = re.search(r"分享率[:：<>/a-zA-Z=\"\s#;]+([0-9.\s]+)", html_text)
                    if not upload_match or not download_match:
                        continue
                    # 上传量
                    upload_text = upload_match.group(1)
                    upload = num_filesize(upload_text.strip())
                    # 下载量
                    download_text = download_match.group(1)
                    download = num_filesize(download_text.strip())
                    # 分享率
                    if ratio_match and ratio_match.group(1).strip():
                        ratio = float(ratio_match.group(1).strip())
                    else:
                        ratio = 0
                    if not self.__sites_data.get(site_name):
                        self.__sites_data[site_name] = {"upload": upload, "download": download, "ratio": ratio}
                        # 登记历史数据
                        insert_site_statistics(site=site_name, upload=upload, download=download, ratio=ratio, url=site_url)
                elif not res:
                    log.error("【PT】站点 %s 连接失败：%s" % (site_name, site_url))
                else:
                    log.error("【PT】站点 %s 获取流量数据失败，状态码：%s" % (site_name, res.status_code))
            except Exception as e:
                log.error("【PT】站点 %s 获取流量数据失败：%s" % (site_name, str(e)))
        # 更新时间
        if self.__sites_data:
            self.__last_update_time = datetime.now()

    def refresh_pt_date_now(self):
        """
        强制刷新PT站数据
        """
        self.refresh_pt_data(True)

    def get_pt_date(self):
        """
        获取PT站上传下载量
        """
        return self.__sites_data
