from datetime import datetime

from config import Config
from utils.functions import singleton
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
            # TODO 读取PT站的上传量和下载量
            upload = 0
            download = 0
            self.__sites_data[site_name] = {"upload": upload, "download": download}
        # 更新时间
        self.__last_update_time = datetime.now()

    def get_pt_date(self):
        """
        获取PT站上传下载量
        """
        return self.__sites_data
