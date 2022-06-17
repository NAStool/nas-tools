import re
import traceback
from datetime import datetime
from multiprocessing.dummy import Pool as ThreadPool
from threading import Lock

import log
from config import Config
from message.send import Message
from utils.functions import singleton, num_filesize
from utils.http_utils import RequestUtils
from utils.sqls import get_config_site, insert_site_statistics_history, update_site_user_statistics

lock = Lock()


@singleton
class Sites:
    message = None
    __sites_data = {}
    __pt_sites = None
    __user_agent = None
    __last_update_time = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.message = Message()
        config = Config()
        app = config.get_config('app')
        pt = config.get_config('pt')
        if pt:
            self.__pt_sites = get_config_site()
            self.__user_agent = app.get('user_agent')
            self.__sites_data = {}

    def refresh_all_pt_data(self, force=False, specify_sites=None):
        """
        多线程刷新PT站下载上传量，默认间隔3小时
        """
        if not self.__pt_sites:
            return
        if not force and self.__last_update_time and (datetime.now() - self.__last_update_time).seconds < 3 * 3600:
            return

        with lock:
            # 没有指定站点，默认使用全部站点
            if not specify_sites:
                refresh_site_names = [site[1] for site in self.__pt_sites]
            else:
                refresh_site_names = specify_sites

            refresh_sites = [site for site in self.__pt_sites if site[1] in refresh_site_names]
            for site in refresh_site_names:
                self.__sites_data.pop(site, None)

            with ThreadPool(len(refresh_sites)) as p:
                p.map(self.__refresh_pt_data, refresh_sites)

        # 更新时间
        if self.__sites_data and not specify_sites:
            self.__last_update_time = datetime.now()

    def __refresh_pt_data(self, site_info):
        """
        更新单个pt site 数据信息
        :param site_info:
        :return:
        """
        if not site_info:
            return
        site_name = site_info[1]
        site_url = site_info[4]
        if not site_url and site_info[3]:
            site_url = site_info[3]
        if not site_url:
            return
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
                    return
                # 上传量
                upload = self.__get_site_upload(html_text)
                # 下载量
                download = self.__get_site_download(html_text)
                if upload is None and download is None:
                    return
                # 分享率
                ratio = self.__get_site_ratio(html_text)

                # 用户名
                username = self.__get_site_user_name(html_text)
                # 做种/下载
                seeding, leeching = self.__get_site_torrents(html_text)
                # 魔力值
                bonus = self.__get_site_bonus(html_text)

                if not self.__sites_data.get(site_name):
                    self.__sites_data[site_name] = {"upload": upload or 0, "download": download or 0,
                                                    "ratio": ratio}
                    # 登记历史数据
                    insert_site_statistics_history(site=site_name, upload=upload or 0, download=download or 0,
                                                   ratio=ratio, url=site_url)
                    # 实时用户数据
                    update_site_user_statistics(site=site_name, username=username, upload=upload, download=download,
                                                ratio=ratio, seeding=seeding, leeching=leeching, bonus=bonus,
                                                url=site_url)

            elif not res:
                log.error("【PT】站点 %s 连接失败：%s" % (site_name, site_url))
            else:
                log.error("【PT】站点 %s 获取流量数据失败，状态码：%s" % (site_name, res.status_code))
        except Exception as e:
            log.error("【PT】站点 %s 获取流量数据失败：%s - %s" % (site_name, str(e), traceback.format_exc()))

    def signin(self):
        """
        PT站签到入口，由定时服务调用
        """
        status = []
        if self.__pt_sites:
            for site_info in self.__pt_sites:
                if not site_info:
                    continue
                pt_task = site_info[1]
                try:
                    pt_url = site_info[4]
                    pt_cookie = site_info[5]
                    log.info("【PT】开始PT签到：%s" % pt_task)
                    if not pt_url or not pt_cookie:
                        log.warn("【PT】未配置 %s 的Url或Cookie，无法签到" % str(pt_task))
                        continue
                    res = RequestUtils(headers=self.__user_agent, cookies=pt_cookie).get_res(url=pt_url)
                    if res and res.status_code == 200:
                        if not self.__is_signin_success(res.text):
                            status.append("%s 签到失败，Cookie已过期" % pt_task)
                        else:
                            status.append("%s 签到成功" % pt_task)
                    elif not res:
                        status.append("%s 签到失败，无法打开网站" % pt_task)
                    else:
                        status.append("%s 签到失败，状态码：%s" % (pt_task, res.status_code))
                except Exception as e:
                    log.error("【PT】%s 签到出错：%s - %s" % (pt_task, str(e), traceback.format_exc()))
        if status:
            self.message.sendmsg(title="\n".join(status))

    @staticmethod
    def __prepare_html_text(html_text):
        """
        处理掉HTML中的干扰部分
        """
        return re.sub(r"#\d+", "", re.sub(r"\d+px", "", html_text))

    def __get_site_upload(self, html_text):
        """
        解析上传量
        """
        html_text = self.__prepare_html_text(html_text)
        upload_match = re.search(r"[^总]上[传傳]量?[:：<>/a-zA-Z-=\"'\s#;]+([0-9,.\s]+[KMGTPI]*B)", html_text, re.IGNORECASE)
        if upload_match:
            return num_filesize(upload_match.group(1).strip())
        else:
            return 0

    def __get_site_download(self, html_text):
        """
        解析下载量
        """
        html_text = self.__prepare_html_text(html_text)
        download_match = re.search(r"[^总]下[载載]量?[:：<>/a-zA-Z-=\"'\s#;]+([0-9,.\s]+[KMGTPI]*B)", html_text,
                                   re.IGNORECASE)
        if download_match:
            return num_filesize(download_match.group(1).strip())
        else:
            return 0

    def __get_site_ratio(self, html_text):
        """
        解析分享率
        """
        html_text = self.__prepare_html_text(html_text)
        ratio_match = re.search(r"分享率[:：<>/a-zA-Z-=\"'\s#;]+([0-9.\s]+)", html_text)
        if ratio_match and ratio_match.group(1).strip():
            return float(ratio_match.group(1).strip())
        else:
            return 0

    def __get_site_user_url(self, html_text):
        """
        解析用户信息url
        :param html_text:
        :return:
        """
        html_text = self.__prepare_html_text(html_text)
        user_detail = re.search(r"userdetails.php\?id=\d+", html_text)
        if user_detail and user_detail.group().strip():
            return user_detail.group().strip().lstrip('/')
        else:
            return ""

    def __get_site_user_name(self, html_text):
        """
        解析用户名称
        :param html_text:
        :return:
        """
        html_text = self.__prepare_html_text(html_text)
        user_name = re.search(r"userdetails.php\?id=\d+[a-zA-Z\"'=_\-\s]+>[<b>\s]*([^<>]*)[</b>]*</a>", html_text)
        if user_name and user_name.group(1).strip():
            return user_name.group(1).strip()
        else:
            return ""

    def __get_site_torrents(self, html_text):
        """
        解析做种/下载数量
        :param html_text:
        :return: 做种数,下载数
        """
        seeding = 0
        leeching = 0
        html_text = self.__prepare_html_text(html_text)
        seeding_match = re.search(r"(Torrents seeding|做种中)[\u4E00-\u9FA5\D\s]+(\d+)[\s\S]+<", html_text)
        leeching_match = re.search(r"(Torrents leeching|下载中)[\u4E00-\u9FA5\D\s]+(\d+)[\s\S]+<", html_text)

        if seeding_match and seeding_match.group(2).strip():
            seeding = int(seeding_match.group(2).strip())

        if leeching_match and leeching_match.group(2).strip():
            leeching = int(leeching_match.group(2).strip())

        return seeding, leeching

    def __get_site_bonus(self, html_text):
        """
        解析魔力值
        :param html_text:
        :return:
        """
        html_text = self.__prepare_html_text(html_text)
        bonus_match = re.search(r"mybonus.php[\[\]:：<>/a-zA-Z-=\"'\s#;.(使用魔力值豆]+\s*([\d,.\s]+)", html_text)
        if bonus_match and bonus_match.group(1).strip():
            return float(bonus_match.group(1).strip().replace(',', ''))
        bonus_match = re.search(r"魔力值[\[\]:：<>/a-zA-Z-=\"'\s#;]+\s*([\d,.\s]+)", html_text)
        if bonus_match and bonus_match.group(1).strip():
            return float(bonus_match.group(1).strip().replace(',', ''))
        else:
            return 0.0

    @staticmethod
    def __is_signin_success(html_text):
        """
        检进是否成功进入PT网站而不是登录界面
        """
        if not html_text:
            return False
        return True if html_text.find("userdetails") != -1 else False

    def refresh_pt_date_now(self):
        """
        强制刷新PT站数据
        """
        self.refresh_all_pt_data(True)

    def get_pt_date(self):
        """
        获取PT站上传下载量
        """
        self.refresh_all_pt_data()
        return self.__sites_data

    def refresh_pt(self, specify_sites=None):
        """
        强制刷新PT指定站数据
        """
        if not specify_sites:
            return

        if not isinstance(specify_sites, list):
            specify_sites = [specify_sites]

        self.refresh_all_pt_data(force=True, specify_sites=specify_sites)
