import logging
import os
import shutil
from collections import deque
from threading import Lock
import ruamel.yaml

import log
from utils.functions import singleton

# 菜单对应关系，配置WeChat应用中配置的菜单ID与执行命令的对应关系，需要手工修改
# 菜单序号在https://work.weixin.qq.com/wework_admin/frame#apps 应用自定义菜单中维护，然后看日志输出的菜单序号是啥（按顺利能猜到的）....
# 命令对应关系：/ptt qBittorrent转移；/ptr qBittorrent删种；/pts PT签到；/rst ResilioSync同步；/rss RSS下载
WECHAT_MENU = {'_0_0': '/ptt', '_0_1': '/ptr', '_0_2': '/rss', '_1_0': '/rst', '_1_1': '/db', '_2_0': '/pts'}
# 收藏了的媒体的目录名，名字可以改，在Emby中点击红星则会自动将电影转移到此分类下，需要在Emby Webhook中配置用户行为通知
RMT_FAVTYPE = '精选'
# 支持的媒体文件后缀格式
RMT_MEDIAEXT = ['.mp4', '.mkv', '.ts', '.iso', '.rmvb', '.avi', '.mov', '.mpeg', '.mpg', '.wmv', '.3gp', '.asf']
# 支持的字幕文件后缀格式
RMT_SUBEXT = ['.srt', '.ass', '.ssa']
# 默认Headers
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"}
# 电视剧动漫的分类genre_ids
ANIME_GENREIDS = ['16']
# 默认过滤的文件大小，200M
RMT_MIN_FILESIZE = 200 * 1024 * 1024
# PT删种检查时间间隔
AUTO_REMOVE_TORRENTS_INTERVAL = 1700
# PT转移文件检查时间间隔，
PT_TRANSFER_INTERVAL = 300
# TMDB信息缓存定时保存时间
METAINFO_SAVE_INTERVAL = 600
# 配置文件定时生效时间
RELOAD_CONFIG_INTERVAL = 600
# SYNC目录同步聚合转移时间
SYNC_TRANSFER_INTERVAL = 300
# RSS队列中处理时间间隔
RSS_SEARCH_INTERVAL = 600
# fanart的api，用于拉取封面图片
FANART_MOVIE_API_URL = 'http://webservice.fanart.tv/v3/movies/%s?api_key=d2d31f9ecabea050fc7d68aa3146015f'
FANART_TV_API_URL = 'http://webservice.fanart.tv/v3/tv/%s?api_key=d2d31f9ecabea050fc7d68aa3146015f'
# 日志级别
LOG_LEVEL = logging.INFO
# 定义一个列表用来保存最近的日志，以便查看
LOG_QUEUE = deque(maxlen=200)

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
                log.console("【ERROR】NASTOOL_CONFIG 环境变量未设置，程序无法工作，正在退出...")
                quit()
            if not os.path.exists(self.__config_path):
                cfg_tp_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config", "config.yaml")
                shutil.copy(cfg_tp_path, self.__config_path)
                log.console("【ERROR】config.yaml 配置文件不存在，已将配置文件模板复制到配置目录...")
            with open(self.__config_path, mode='r', encoding='utf-8') as f:
                try:
                    yaml = ruamel.yaml.YAML()
                    self.__config = yaml.load(f)
                except Exception as e:
                    log.console("【ERROR】配置文件 config.yaml 格式出现严重错误！请检查：%s" % str(e))
                    self.__config = {}
        except Exception as err:
            log.console("【ERROR】加载 config.yaml 配置出错：%s" % str(err))
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
