import log
import datetime
from app.helper import DbHelper
from app.utils.commons import singleton
from app.utils.types import MediaType, SearchType
from app.utils import Torrent
from config import Config

@singleton
class Timeframe:
    def __init__(self):
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()

    def check_timeframe_expires(self, timeframe_info, existing_id, media_wating_title, media_wait_time):
        """
        检测是否到期
        :param timeframe_info: 存在的等待中的电视剧或电影信息
        :param existing_id: 等待中的电视剧或电影标题
        :param media_wating_title: 识别的电视剧集数或电影标题
        :param media_wating_time: 等待事件
        """
        first_seen = timeframe_info[existing_id.index(media_wating_title)].FIRST_SEEN
        expires = first_seen + datetime.timedelta(minutes=int(media_wait_time)) 
        if expires <=  datetime.datetime.now():
            return 1
        else:
            return 0

    def update_timeframe_status(self, rssid, mtype, media_wating_title):
        """
        更新timeframe状态
        :param rssid: 订阅ID
        :param mtype: 媒体类型
        :param media_wating_title: 识别的电视剧集数或电影标题
        """
        if mtype != MediaType.MOVIE:
            self.dbhelper.update_tv_timeframe(rssid=rssid ,episode=media_wating_title)
        else:
            self.dbhelper.update_movie_timeframe(rssid=rssid ,title=media_wating_title)
    
    def insert_timeframe_info(self, rssid, mtype, media_wating_title):
        """
        插入等待信息
        :param rssid: 订阅ID
        :param mtype: 媒体类型
        :param media_wating_title: 需要等待的电视剧集数或电影标题
        """
        if mtype != MediaType.MOVIE:
            self.dbhelper.insert_tv_timeframe(rssid=rssid ,episode=media_wating_title)
        else:
            self.dbhelper.insert_movie_timeframe(rssid=rssid ,title=media_wating_title)

    def check_timeframe_filter(self, media_info, timeframe_info, existing_id, media_wait_time):
        if media_info.type != MediaType.MOVIE:
            media_wait_title = media_info.get_episode_string()
        else:
            media_wait_title = media_info.get_title_string()
        if (100 - media_info.res_order == 1):
            if media_wait_title in existing_id:
                self.update_timeframe_status(media_info.rssid, media_info.type, media_wait_title)
            return 1
        else:
            if media_wait_title in existing_id:
                if self.check_timeframe_expires(timeframe_info, existing_id, media_wait_title, media_wait_time):
                    self.update_timeframe_status(media_info.rssid, media_info.type, media_wait_title)
                    return 1
                return 0
            else:
                self.insert_timeframe_info(media_info.rssid, media_info.type, media_wait_title)
                return 0

    def check_search_filter(self, in_from, rssid, mtype, media_wait_time, media_list):
        """
        timeframe search入口
        :param in_from: 来源
        :param mtype: 媒体类型
        :param rssid: 订阅信息
        :param media_wait_time: 等待时间
        :param media_list: 命中并已经识别好的媒体信息列表，包括名称、年份、季、集等信息
        """
        # 只处理RSS
        if in_from != SearchType.RSS:
            return media_list
        # 判断是否需要处理
        if not media_wait_time:
            return media_list
        # 初始化数据
        existing_id= []
        download_order = None
        timeframe_accept_list_item = []
        if mtype != MediaType.MOVIE:
            timeframe_info = self.dbhelper.get_tv_timeframe_info(rssid=rssid)
        else:
            timeframe_info = self.dbhelper.get_movie_timeframe_info(rssid=rssid)

        for t_existing_id in timeframe_info:
            existing_id.append(t_existing_id.TITLE)
        
        # 是否站点优先
        pt = Config().get_config('pt')
        if pt:
            download_order = pt.get("download_order")
        # 排序
        download_list = Torrent().get_download_list(media_list,
                                                    download_order)

        for t_item in download_list:
            # 无子规则返回全部
            if not t_item.res_order:
                return download_list
            else:
                # 取最高优先级
                t_item.set_torrent_info(rssid=rssid)
                if self.check_timeframe_filter(t_item, timeframe_info, existing_id, media_wait_time):
                    timeframe_accept_list_item.append(t_item)
        return timeframe_accept_list_item
    
    def check_rss_filter(self, media_info, media_wait_time):
        """
        timeframe rss入口
        :param media_wait_time: 等待时间      
        :param media_info: 命中并已经识别好的媒体信息，包括名称、年份、季、集等信息
        """
        # 判断是否需要处理
        if not media_wait_time:
            return 1
        existing_id = []
        # 初始化数据
        if media_info.type != MediaType.MOVIE:
            timeframe_info = self.dbhelper.get_tv_timeframe_info(rssid=media_info.rssid)
        else:
            timeframe_info = self.dbhelper.get_movie_timeframe_info(rssid=media_info.rssid)

        for t_existing_id in timeframe_info:
            existing_id.append(t_existing_id.TITLE)
        
        # 无子规则直接返回
        if not media_info.res_order:
            return 1
        else:
            return self.check_timeframe_filter(media_info, timeframe_info, existing_id, media_wait_time)
