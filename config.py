import logging
import os
from threading import Lock
from subprocess import call
import yaml

from utils.functions import singleton
from utils.types import MediaCatagory

# 菜单对应关系，配置WeChat应用中配置的菜单ID与执行命令的对应关系，需要手工修改
# 菜单序号在https://work.weixin.qq.com/wework_admin/frame#apps 应用自定义菜单中维护，然后看日志输出的菜单序号是啥（按顺利能猜到的）....
# 命令对应关系：/ptt qBittorrent转移；/ptr qBittorrent删种；/pts PT签到；/rst ResilioSync同步；/rss RSS下载
WECHAT_MENU = {'_0_0': '/ptt', '_0_1': '/ptr', '_0_2': '/rss', '_1_0': '/rst', '_1_1': '/db', '_2_0': '/pts'}
# 收藏了的媒体的目录名，名字可以改，在Emby中点击红星则会自动将电影转移到此分类下，需要在Emby Webhook中配置用户行为通知
RMT_FAVTYPE = MediaCatagory.JXDY
# 支持的媒体文件后缀格式
RMT_MEDIAEXT = ['.mp4', '.mkv', '.ts', '.iso', '.rmvb', '.avi', '.mov', '.mpeg', '.mpg', '.wmv', '.3gp', '.asf']
# 支持的字幕文件后缀格式
RMT_SUBEXT = ['.srt', '.ass', '.ssa']
# 欧美国家的简称列表，会将这类剧集移到欧美剧目录
RMT_COUNTRY_EA = ['US', 'FR', 'GB', 'DE', 'ES', 'IT', 'NL', 'PT', 'RU', 'UK']
# 亚洲国家的简称列表，会将这类剧集移到日韩剧目录
RMT_COUNTRY_AS = ['JP', 'KP', 'KR', 'TH', 'IN', 'SG']
# 剩余多少磁盘空间时不再转移，单位GB
RMT_DISKFREESIZE = 10
# PT删除检查时间间隔，默认10分钟
AUTO_REMOVE_TORRENTS_INTERVAL = 600
# PT转移文件检查时间间隔，默认5分钟
PT_TRANSFER_INTERVAL = 300
# SYNC源目录与目的目录的配套关系
SYNC_DIR_CONFIG = {}
# fanart的api，用于拉取封面图片
FANART_MOVIE_API_URL = 'http://webservice.fanart.tv/v3/movies/%s?api_key=d2d31f9ecabea050fc7d68aa3146015f'
FANART_TV_API_URL = 'http://webservice.fanart.tv/v3/tv/%s?api_key=d2d31f9ecabea050fc7d68aa3146015f'
# 日志级别
LOG_LEVEL = logging.INFO

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
            print("开始读取配置...")
            if not self.__config_path:
                print("【ERROR】NASTOOL_CONFIG 环境变量未设置，程序无法工作，正在退出...")
                quit()
            if not os.path.exists(self.__config_path):
                cfg_tp_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config", "config.yaml")
                call(["cp", cfg_tp_path, self.__config_path])
                print("【ERROR】配置文件不存在，已将配置文件模板复制到配置目录，请修改后重新启动...")
                self.__config = {}
                return
            with open(self.__config_path, mode='r', encoding='utf-8') as f:
                try:
                    self.__config = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    print("【ERROR】配置文件格式出现严重错误！请检查：%s" % str(e))
                    self.__config = {}
        except Exception as err:
            print("【ERROR】加载配置出错：%s" % str(err))
            return False

    def get_config(self, node=None):
        if not node:
            return self.__config
        return self.__config.get(node)

    def save_config(self, new_cfg):
        self.__config = new_cfg
        with open(self.__config_path, mode='w', encoding='utf-8') as f:
            return yaml.dump(new_cfg, f, allow_unicode=True)

    def get_config_path(self):
        return self.__config_path
