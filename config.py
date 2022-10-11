import os
import random
import shutil
from threading import Lock

import ruamel.yaml
from werkzeug.security import generate_password_hash

# 菜单对应关系，配置WeChat应用中配置的菜单ID与执行命令的对应关系，需要手工修改
# 菜单序号在https://work.weixin.qq.com/wework_admin/frame#apps 应用自定义菜单中维护，然后看日志输出的菜单序号是啥（按顺利能猜到的）....
# 命令对应关系：/ptt 下载文件转移；/ptr 删种；/pts 站点签到；/rst 目录同步；/rss RSS下载
WECHAT_MENU = {'_0_0': '/ptt', '_0_1': '/ptr', '_0_2': '/rss', '_1_0': '/rst', '_1_1': '/db', '_2_0': '/pts'}
# 种子名/文件名要素分隔字符
SPLIT_CHARS = r"\.|\s+|\(|\)|\[|]|-|\+|【|】|/|～|;|&|\||#|_|「|」|（|）"
# 默认User-Agent
DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
# 收藏了的媒体的目录名，名字可以改，在Emby中点击红星则会自动将电影转移到此分类下，需要在Emby Webhook中配置用户行为通知
RMT_FAVTYPE = '精选'
# 支持的媒体文件后缀格式
RMT_MEDIAEXT = ['.mp4', '.mkv', '.ts', '.iso', '.rmvb', '.avi', '.mov', '.mpeg', '.mpg', '.wmv', '.3gp', '.asf', '.m4v',
                '.flv', '.m2ts']
# 支持的字幕文件后缀格式
RMT_SUBEXT = ['.srt', '.ass', '.ssa']
# 电视剧动漫的分类genre_ids
ANIME_GENREIDS = ['16']
# 默认过滤的文件大小，150M
RMT_MIN_FILESIZE = 150 * 1024 * 1024
# 删种检查时间间隔
AUTO_REMOVE_TORRENTS_INTERVAL = 1800
# 下载文件转移检查时间间隔，
PT_TRANSFER_INTERVAL = 300
# TMDB信息缓存定时保存时间
METAINFO_SAVE_INTERVAL = 600
# 配置文件定时生效时间
RELOAD_CONFIG_INTERVAL = 600
# SYNC目录同步聚合转移时间
SYNC_TRANSFER_INTERVAL = 60
# RSS队列中处理时间间隔
RSS_CHECK_INTERVAL = 300
# 站点流量数据刷新时间间隔（小时）
REFRESH_PT_DATA_INTERVAL = 6
# 刷新订阅TMDB数据的时间间隔（小时）
RSS_REFRESH_TMDB_INTERVAL = 6
# 刷流删除的检查时间间隔
BRUSH_REMOVE_TORRENTS_INTERVAL = 300
# 定时清除未识别的缓存时间间隔（小时）
META_DELETE_UNKNOWN_INTERVAL = 12
# 定时刷新壁纸的间隔（小时）
REFRESH_WALLPAPER_INTERVAL = 1
# fanart的api，用于拉取封面图片
FANART_MOVIE_API_URL = 'https://webservice.fanart.tv/v3/movies/%s?api_key=d2d31f9ecabea050fc7d68aa3146015f'
FANART_TV_API_URL = 'https://webservice.fanart.tv/v3/tv/%s?api_key=d2d31f9ecabea050fc7d68aa3146015f'
# 默认背景图地址
DEFAULT_TMDB_IMAGE = 'https://s3.bmp.ovh/imgs/2022/07/10/77ef9500c851935b.webp'
# 默认微信消息代理服务器地址
DEFAULT_WECHAT_PROXY = 'https://wechat.nastool.cn'
# 默认OCR识别服务地址
DEFAULT_OCR_SERVER = 'https://nastool.cn/ocr/'
# 默认TMDB代理服务地址
DEFAULT_TMDB_PROXY = 'https://tmdb.nastool.cn'
# TMDB图片地址
TMDB_IMAGE_W500_URL = 'https://image.tmdb.org/t/p/w500%s'
TMDB_IMAGE_ORIGINAL_URL = 'https://image.tmdb.org/t/p/original/%s'
# 添加下载时增加的标签，开始只监控NASTool添加的下载时有效
PT_TAG = "NASTOOL"
# 搜索种子过滤属性
TORRENT_SEARCH_PARAMS = {
    "restype": {
        "BLURAY": r"Blu-?Ray|BD|BDRIP",
        "REMUX": r"REMUX",
        "DOLBY": r"DOLBY",
        "WEB": r"WEB-?DL|WEBRIP",
        "HDTV": r"U?HDTV",
        "UHD": r"UHD",
        "HDR": r"HDR",
        "3D": r"3D"
    },
    "pix": {
        "8k": r"8K",
        "4k": r"4K|2160P|X2160",
        "1080p": r"1080[PIX]|X1080",
        "720p": r"720P"
    }
}
# 电影默认命名格式
DEFAULT_MOVIE_FORMAT = '{title} ({year})/{title} ({year})-{part} - {videoFormat}'
# 电视剧默认命名格式
DEFAULT_TV_FORMAT = '{title} ({year})/Season {season}/{title} - {season_episode}-{part} - 第 {episode} 集'
# 辅助识别参数
KEYWORD_SEARCH_WEIGHT_1 = [10, 3, 2, 0.5, 0.5]
KEYWORD_SEARCH_WEIGHT_2 = [10, 2, 1]
KEYWORD_SEARCH_WEIGHT_3 = [10, 2]
KEYWORD_STR_SIMILARITY_THRESHOLD = 0.2
KEYWORD_DIFF_SCORE_THRESHOLD = 30
KEYWORD_BLACKLIST = ['中字', '韩语', '双字', '中英', '日语', '双语', '国粤', 'HD', 'BD', '中日', '粤语', '完全版', '法语',
                     '西班牙语', 'HRHDTVAC3264', '未删减版', '未删减', '国语', '字幕组', '人人影视', 'www66ystv',
                     '人人影视制作', '英语', 'www6vhaotv', '无删减版', '完成版', '德意']
#  网络测试对象
NETTEST_TARGETS = ["www.themoviedb.org",
                   "api.themoviedb.org",
                   "api.tmdb.org",
                   "image.tmdb.org",
                   "webservice.fanart.tv",
                   "api.telegram.org",
                   "qyapi.weixin.qq.com",
                   "www.opensubtitles.org"]

# 站点签到支持的识别XPATH
SITE_CHECKIN_XPATH = [
    '//a[@id="signed"]',
    '//a[contains(@href, "attendance.php")]',
    '//a[contains(@text, "签到")]',
    '//span[@id="sign_in"]/a',
    '//a[contains(@href, "addbonus")]'
]

# 线程锁
lock = Lock()


class Config(object):
    _INSTANSE = None
    _INSTANSE_FLAG = False
    _config = {}
    _config_path = None

    def __new__(cls, *args, **kwargs):
        with lock:
            if not cls._INSTANSE:
                cls._INSTANSE = super().__new__(cls)
            return cls._INSTANSE

    def __init__(self):
        with lock:
            if Config._INSTANSE_FLAG:
                return
            Config._INSTANSE_FLAG = True
        self._config_path = os.environ.get('NASTOOL_CONFIG')
        self.init_config()

    def init_config(self):
        try:
            if not self._config_path:
                print("【ERROR】NASTOOL_CONFIG 环境变量未设置，程序无法工作，正在退出...")
                quit()
            if not os.path.exists(self._config_path):
                cfg_tp_path = os.path.join(self.get_inner_config_path(), "config.yaml")
                cfg_tp_path = cfg_tp_path.replace("\\", "/")
                shutil.copy(cfg_tp_path, self._config_path)
                print("【ERROR】config.yaml 配置文件不存在，已将配置文件模板复制到配置目录...")
            with open(self._config_path, mode='r', encoding='utf-8') as f:
                try:
                    # 读取配置
                    print("正在加载配置...")
                    self._config = ruamel.yaml.YAML().load(f)
                    overwrite_cofig = False
                    # 密码初始化
                    login_password = self._config.get("app", {}).get("login_password")
                    if login_password and not login_password.startswith("[hash]"):
                        self._config['app']['login_password'] = "[hash]%s" % generate_password_hash(login_password)
                        overwrite_cofig = True
                    # 实验室配置初始化
                    if not self._config.get("laboratory"):
                        self._config['laboratory'] = {
                            'search_keyword': False,
                            'tmdb_cache_expire': True,
                            'use_douban_titles': True,
                            'search_en_title': True,
                            'ignored_words': '',
                            'replaced_words': '',
                            'offset_words': '',
                            'chrome_browser': False
                        }
                        overwrite_cofig = True
                    # 安全配置初始化
                    if not self._config.get("security"):
                        self._config['security'] = {
                            'media_server_webhook_allow_ip': {
                                'ipv4': '0.0.0.0/0',
                                'ipv6': '::/0'
                            },
                            'telegram_webhook_allow_ip': {
                                'ipv4': '127.0.0.1',
                                'ipv6': '::/0'
                            }
                        }
                        overwrite_cofig = True
                    # API密钥初始化
                    if not self._config.get("security", {}).get("subscribe_token"):
                        self._config['security']['subscribe_token'] = self._config.get("laboratory",
                                                                                       {}).get("subscribe_token") \
                                                                      or self.__generate_random_str()
                        overwrite_cofig = True
                    # 消息推送开关初始化
                    if not self._config.get("message", {}).get("switch"):
                        self._config['message']['switch'] = {
                            "download_start": True,
                            "download_fail": True,
                            "transfer_finished": True,
                            "transfer_fail": True,
                            "rss_added": True,
                            "rss_finished": True,
                            "site_signin": True
                        }
                        overwrite_cofig = True
                    # 刮削NFO配置初始化
                    if not self._config.get("scraper_nfo"):
                        self._config['scraper_nfo'] = {
                            "movie": {
                                "basic": True,
                                "credits": True,
                                "credits_chinese": False},
                            "tv": {
                                "basic": True,
                                "credits": True,
                                "credits_chinese": False,
                                "season_basic": True,
                                "episode_basic": True,
                                "episode_credits": True}
                        }
                        overwrite_cofig = True
                    # 刮削图片配置初始化
                    if not self._config.get("scraper_pic"):
                        self._config['scraper_pic'] = {
                            "movie": {
                                "poster": True,
                                "backdrop": True,
                                "background": True,
                                "logo": True,
                                "disc": True,
                                "banner": True,
                                "thumb": True},
                            "tv": {
                                "poster": True,
                                "backdrop": True,
                                "background": True,
                                "logo": True,
                                "clearart": True,
                                "banner": True,
                                "thumb": True,
                                "season_poster": True,
                                "season_banner": True,
                                "season_thumb": True}
                        }
                        overwrite_cofig = True
                    # 下载目录配置初始化
                    if not self._config.get('downloaddir'):
                        dl_client = self._config.get('pt', {}).get('pt_client')
                        if dl_client and self._config.get(dl_client):
                            save_path = self._config.get(dl_client).get('save_path')
                            if not isinstance(save_path, dict):
                                save_path = {"movie": save_path, "tv": save_path, "anime": save_path}
                            container_path = self._config.get(dl_client).get('save_containerpath')
                            if not isinstance(container_path, dict):
                                container_path = {"movie": container_path, "tv": container_path, "anime": container_path}
                            downloaddir = {}
                            type_dict = {"movie": "电影", "tv": "电视剧", "anime": "动漫"}
                            for mtype, path in save_path.items():
                                if not path:
                                    continue
                                save_dir = path.split('|')[0]
                                save_label = None
                                if len(path.split('|')) > 1:
                                    save_label = path.split('|')[1]
                                container_dir = container_path.get(mtype)
                                if save_dir not in downloaddir.keys():
                                    downloaddir[save_dir] = {"type": type_dict.get(mtype),
                                                             "category": "",
                                                             "path": container_dir,
                                                             "label": save_label}
                                else:
                                    downloaddir[save_dir] = {"type": "",
                                                             "category": "",
                                                             "path": container_dir,
                                                             "label": save_label}
                            self._config['downloaddir'] = downloaddir
                            overwrite_cofig = True
                    # 重写配置文件
                    if overwrite_cofig:
                        self.save_config(self._config)
                except Exception as e:
                    print("【ERROR】配置文件 config.yaml 格式出现严重错误！请检查：%s" % str(e))
                    self._config = {}
        except Exception as err:
            print("【ERROR】加载 config.yaml 配置出错：%s" % str(err))
            return False

    def get_proxies(self):
        return self.get_config('app').get("proxies")

    def get_ua(self):
        return self.get_config('app').get("user_agent") or DEFAULT_UA

    def get_config(self, node=None):
        if not node:
            return self._config
        return self._config.get(node, {})

    def save_config(self, new_cfg):
        self._config = new_cfg
        with open(self._config_path, mode='w', encoding='utf-8') as f:
            yaml = ruamel.yaml.YAML()
            return yaml.dump(new_cfg, f)

    def get_config_path(self):
        return os.path.dirname(self._config_path)

    @staticmethod
    def get_root_path():
        return os.path.dirname(os.path.realpath(__file__))

    def get_inner_config_path(self):
        return os.path.join(self.get_root_path(), "config")

    @staticmethod
    def __generate_random_str(randomlength=16):
        """
        生成一个指定长度的随机字符串
        """
        random_str = ''
        base_str = 'ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789'
        length = len(base_str) - 1
        for i in range(randomlength):
            random_str += base_str[random.randint(0, length)]
        return random_str
