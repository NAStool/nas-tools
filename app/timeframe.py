import log
import datetime
from app.helper import DbHelper
from app.utils.commons import singleton
from app.utils.types import MediaType, SearchType
from app.filter import Filter
from app.utils import Torrent
from config import Config

@singleton
class Timeframe:
    def __init__(self):
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()
        self.filter = Filter()

    def check_torrent_filter(self, in_from, mtype, rssid, filter_args, media_list):
        """
        timeframe入口
        :param in_from: 来源
        :param mtype: 媒体类型
        :param rssid: 订阅信息
        :param filter_args: 过滤规则
        :param media_list: 命中并已经识别好的媒体信息列表，包括名称、年份、季、集等信息
        """
        # 只处理RSS
        if in_from != SearchType.RSS:
            return media_list
        if not filter_args.get("timeframe"):
            return media_list
        # 初始化数据
        if mtype != MediaType.MOVIE:
            existing_ids = self.dbhelper.get_tv_timeframe_info(rssid=rssid)
        else:
            existing_ids = self.dbhelper.get_movie_timeframe_info(rssid=rssid)
        
        tv_episode = None
        movie_name = None
        existing_id= []
        download_order = None
        timeframe_accept_list_item = []
        
        # 是否站点优先
        pt = Config().get_config('pt')
        if pt:
            download_order = pt.get("download_order")
        # 排序
        download_list = Torrent().get_download_list(media_list,
                                                    download_order)

        for t_existing_id in existing_ids:
            existing_id.append(t_existing_id.TITLE)


        def __check_timeframe_expires(tv_episode):
            """
            检测是否到期
            """
            if tv_episode:
                first_seen = existing_ids[existing_id.index(tv_episode)].FIRST_SEEN
            else:
                first_seen = existing_ids[existing_id.index(movie_name)].FIRST_SEEN
            expires = first_seen + datetime.timedelta(minutes=int(filter_args.get("timeframe"))) 
            if expires <=  datetime.datetime.now():
                return 1
            else:
                return 0

        def __update_timeframe_status(tv_episode):
            """
            更新timeframe状态 
            """
            if tv_episode:
                self.dbhelper.update_tv_timeframe(rssid=rssid ,episode=tv_episode)
            else:
                self.dbhelper.update_movie_timeframe(rssid=rssid ,title=movie_name)
        
        def __insert_timeframe_info(tv_episode):
           """
           插入等待信息
           """
           if tv_episode:
                self.dbhelper.insert_tv_timeframe(rssid=rssid ,episode=tv_episode)
           else:
                self.dbhelper.insert_movie_timeframe(rssid=rssid ,title=movie_name)

        for t_item in download_list:
            match_flag, order_seq = self.filter.check_timeframe_filter(meta_info=t_item,
                                                                       filter_args=filter_args)
            tv_episode = t_item.get_episode_string()
            movie_name = t_item.get_title_string()
            
            if (match_flag):
                # 无子规则返回全部
                if not order_seq:
                    return download_list
                else:
                    # 取最高优先级
                    if (100 - order_seq == 1):
                        timeframe_accept_list_item.append(t_item)
                        if tv_episode in existing_id or movie_name in existing_id:
                            __update_timeframe_status(tv_episode)
                    else:
                        if tv_episode in existing_id or movie_name in existing_id:
                            if __check_timeframe_expires(tv_episode):
                                __update_timeframe_status(tv_episode)
                                timeframe_accept_list_item.append(t_item)
                        else:
                            __insert_timeframe_info(tv_episode)

        return timeframe_accept_list_item
