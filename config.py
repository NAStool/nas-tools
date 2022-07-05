import os
import shutil
from threading import Lock
import ruamel.yaml
from werkzeug.security import generate_password_hash

from utils.functions import singleton

# 菜单对应关系，配置WeChat应用中配置的菜单ID与执行命令的对应关系，需要手工修改
# 菜单序号在https://work.weixin.qq.com/wework_admin/frame#apps 应用自定义菜单中维护，然后看日志输出的菜单序号是啥（按顺利能猜到的）....
# 命令对应关系：/ptt PT文件转移；/ptr PT删种；/pts PT签到；/rst 目录同步；/rss RSS下载
WECHAT_MENU = {'_0_0': '/ptt', '_0_1': '/ptr', '_0_2': '/rss', '_1_0': '/rst', '_1_1': '/db', '_2_0': '/pts'}
# 种子名/文件名要素分隔字符
SPLIT_CHARS = r"\.|\s+|\(|\)|\[|]|-|\+|【|】|/|～|;|&|\||#|_|「|」|（|）"
# 收藏了的媒体的目录名，名字可以改，在Emby中点击红星则会自动将电影转移到此分类下，需要在Emby Webhook中配置用户行为通知
RMT_FAVTYPE = '精选'
# 支持的媒体文件后缀格式
RMT_MEDIAEXT = ['.mp4', '.mkv', '.ts', '.iso', '.rmvb', '.avi', '.mov', '.mpeg', '.mpg', '.wmv', '.3gp', '.asf', '.m4v', '.flv']
# 支持的字幕文件后缀格式
RMT_SUBEXT = ['.srt', '.ass', '.ssa']
# 电视剧动漫的分类genre_ids
ANIME_GENREIDS = ['16']
# 默认过滤的文件大小，150M
RMT_MIN_FILESIZE = 150 * 1024 * 1024
# PT删种检查时间间隔
AUTO_REMOVE_TORRENTS_INTERVAL = 1800
# PT转移文件检查时间间隔，
PT_TRANSFER_INTERVAL = 300
# TMDB信息缓存定时保存时间
METAINFO_SAVE_INTERVAL = 600
# 配置文件定时生效时间
RELOAD_CONFIG_INTERVAL = 600
# SYNC目录同步聚合转移时间
SYNC_TRANSFER_INTERVAL = 60
# RSS队列中处理时间间隔
RSS_CHECK_INTERVAL = 300
# PT站流量数据刷新时间间隔（小时）
REFRESH_PT_DATA_INTERVAL = 6
# 将豆瓣订阅转为TMDB订阅的检查时间间隔（小时）
RSS_DOUBAN_TO_TMDB_INTEVAL = 12
# fanart的api，用于拉取封面图片
FANART_MOVIE_API_URL = 'https://webservice.fanart.tv/v3/movies/%s?api_key=d2d31f9ecabea050fc7d68aa3146015f'
FANART_TV_API_URL = 'https://webservice.fanart.tv/v3/tv/%s?api_key=d2d31f9ecabea050fc7d68aa3146015f'
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
        "4k": r"4K|2160K",
        "1080p": r"1080[PIX]",
        "720p": r"720P"
    }
}
# 电影默认命名格式
DEFAULT_MOVIE_FORMAT = '{title} ({year})/{title}-{part} ({year}) - {videoFormat}'
# 电视剧默认命名格式
DEFAULT_TV_FORMAT = '{title} ({year})/Season {season}/{title}-{part} - {season_episode} - 第 {episode} 集'
# 非常规RSS站点
RSS_EXTRA_SITES = {
    'blutopia.xyz': 'Unit3D',
    'desitorrents.tv': 'Unit3D',
    'jptv.club': 'Unit3D',
    'www.torrentseeds.org': 'Unit3D',
    'beyond-hd.me': 'beyondhd',
}
# 检测种子促销的PT站点XPATH，不在此清单的无法开启仅RSS免费种子功能
GRAP_FREE_SITES = {
    'pthome.net': {
        'FREE': ["//font[@class='free']"],
        '2XFREE': ["//font[@class='twoupfree']"]
    },
    'ptsbao.club':  {
        'FREE': ["//font[@class='free']"],
        '2XFREE': ["//font[@class='twoupfree']"]
    },
    'totheglory.im':  {
        'FREE': ["//img[@class='topic'][contains(@src,'ico_free.gif')]"],
        '2XFREE': []
    },
    'www.beitai.pt':  {
        'FREE': ["//font[@class='free']"],
        '2XFREE': ["//font[@class='twoupfree']"]
    },
    'hdtime.org':  {
        'FREE': ["//font[@class='free']"],
        '2XFREE': ["//font[@class='twoupfree']"]
    },
    'www.haidan.video':  {
        'FREE': ["//img[@class='pro_free'][@title='免费']"],
        '2XFREE': []
    },
    'kp.m-team.cc':  {
        'FREE': ["//font[@class='free']"],
        '2XFREE': []
    },
    'lemonhd.org':  {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': []
    },
    'discfan.net':  {
        'FREE': ["//font[@class='free'][text()='免費']"],
        '2XFREE': []
    },
    'pt.sjtu.edu.cn':  {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': []
    },
    'nanyangpt.com':  {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': []
    },
    'audiences.me':  {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': []
    },
    'pterclub.com':  {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': []
    },
    'et8.org':  {
        'FREE': ["//font[@class='free']"],
        '2XFREE': ["//font[@class='twoupfree']"]
    },
    'pt.keepfrds.com':  {
        'FREE': ["//font[@class='free'][text()='免费']"],
        '2XFREE': ["//font[@class='twoupfree']"]
    },
    'www.pttime.org':  {
        'FREE': ["//font[@class='free']"],
        '2XFREE': []
    }
}

lock = Lock()


@singleton
class Config(object):
    __config = {}
    __config_path = None

    def __init__(self):
        self.__config_path = os.environ.get('NASTOOL_CONFIG')
        self.init_config()

    def init_config(self):
        try:
            if not self.__config_path:
                print("【ERROR】NASTOOL_CONFIG 环境变量未设置，程序无法工作，正在退出...")
                quit()
            if not os.path.exists(self.__config_path):
                cfg_tp_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config", "config.yaml")
                shutil.copy(cfg_tp_path, self.__config_path)
                print("【ERROR】config.yaml 配置文件不存在，已将配置文件模板复制到配置目录...")
            with open(self.__config_path, mode='r', encoding='utf-8') as f:
                try:
                    yaml = ruamel.yaml.YAML()
                    self.__config = yaml.load(f)
                    if self.__config.get("app"):
                        login_password = self.__config.get("app").get("login_password")
                        if login_password and not login_password.startswith("[hash]"):
                            self.__config['app']['login_password'] = "[hash]%s" % generate_password_hash(login_password)
                            self.save_config(self.__config)
                    if not self.__config.get("security"):
                        self.__config['security'] = {
                            'media_server_webhook_allow_ip': {
                                'ipv4': '0.0.0.0/0',
                                'ipv6': '::/0'
                            }
                        }

                        self.save_config(self.__config)

                except Exception as e:
                    print("【ERROR】配置文件 config.yaml 格式出现严重错误！请检查：%s" % str(e))
                    self.__config = {}
        except Exception as err:
            print("【ERROR】加载 config.yaml 配置出错：%s" % str(err))
            return False

    def get_proxies(self):
        return self.get_config('app').get("proxies")

    def get_config(self, node=None):
        if not node:
            return self.__config
        return self.__config.get(node, {})

    def save_config(self, new_cfg):
        self.__config = new_cfg
        with open(self.__config_path, mode='w', encoding='utf-8') as f:
            yaml = ruamel.yaml.YAML()
            return yaml.dump(new_cfg, f)

    def get_config_path(self):
        return self.__config_path
