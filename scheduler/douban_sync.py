from threading import Lock

import log
from config import Config
from pt.douban import DouBan
from pt.searcher import Searcher
from rmt.media import Media
from utils.sqls import get_douban_search_state, insert_douban_media_state, \
    insert_rss_tv, insert_rss_movie
from utils.types import MediaType, SearchType

lock = Lock()


class DoubanSync:
    __interval = None
    __auto_search = True
    __auto_rss = True
    douban = None
    searcher = None
    media = None

    def __init__(self):
        self.douban = DouBan()
        self.searcher = Searcher()
        self.media = Media()
        self.init_config()

    def init_config(self):
        config = Config()
        douban = config.get_config('douban')
        if douban:
            self.__interval = int(douban.get('interval'))
            self.__auto_search = douban.get('auto_search')
            self.__auto_rss = douban.get('auto_rss')

    def run_schedule(self):
        try:
            lock.acquire()
            self.__douban_sync()
        except Exception as err:
            log.error("【RUN】执行任务douban_sync出错：%s" % str(err))
        finally:
            lock.release()

    def __douban_sync(self):
        if not self.__interval:
            return
        log.info("【DOUBAN】开始同步豆瓣数据...")
        # 拉取豆瓣数据
        medias = self.douban.get_all_douban_movies()
        # 开始检索
        if self.__auto_search:
            # 需要检索
            if len(medias) == 0:
                return
            log.info("【DOUBAN】开始检索豆瓣中的影视资源...")
            for media in medias:
                # 查询数据库状态，已经加入RSS的不处理
                search_state = get_douban_search_state(media.get_name(), media.year)
                if not search_state or search_state[0][0] == "NEW":
                    if media.type != MediaType.MOVIE:
                        seasons = media.get_season_list()
                        if len(seasons) == 1:
                            season = seasons[0]
                            search_str = "电视剧 %s 第%s季 %s" % (media.get_name(), season, media.year)
                        else:
                            season = 1
                            search_str = "电视剧 %s 第%s季 %s" % (media.get_name(), season, media.year)
                    else:
                        season = None
                        search_str = "电影 %s %s" % (media.get_name(), media.year)
                    # 开始检索
                    search_result, media, total_seasoninfo, no_exists = self.searcher.search_one_media(
                        input_str=search_str,
                        in_from=SearchType.DB)
                    if not media:
                        continue
                    if not search_result:
                        if self.__auto_rss:
                            if media.type != MediaType.MOVIE:
                                if not total_seasoninfo:
                                    continue
                                # 总集数
                                total_count = 0
                                for seasoninfo in total_seasoninfo:
                                    if seasoninfo.get("season_number") == season:
                                        total_count = seasoninfo.get("episode_count")
                                        break
                                if not total_count:
                                    continue
                                # 缺失集数
                                lack_count = total_count
                                if no_exists and no_exists.get(media.get_title_string()):
                                    no_exist_items = no_exists.get(media.get_title_string())
                                    for no_exist_item in no_exist_items:
                                        if no_exist_item.get("season") == season:
                                            if no_exist_item.get("episodes"):
                                                lack_count = len(no_exist_item.get("episodes"))
                                            break
                                else:
                                    lack_count = 0
                                if not lack_count:
                                    continue
                                # 登记电视剧订阅
                                log.info("【DOUBAN】 %s %s 更新到电视剧订阅中..." % (media.get_name(), media.year))
                                insert_rss_tv(media, total_count, lack_count, "R")
                            else:
                                # 登记电影订阅
                                log.info("【DOUBAN】 %s %s 更新到电影订阅中..." % (media.get_name(), media.year))
                                insert_rss_movie(media)
                            # 插入为已RSS状态
                            insert_douban_media_state(media, "RSS")
                        else:
                            log.info("【DOUBAN】 %s %s 等待下一次处理..." % (media.get_name(), media.year))
                    else:
                        # 更新为已下载状态
                        insert_douban_media_state(media, "DOWNLOADED")
                else:
                    log.info("【DOUBAN】 %s %s 已处理过，跳过..." % (media.get_name(), media.year))
        else:
            # 不需要检索
            if self.__auto_rss:
                # 加入订阅
                for media in medias:
                    # 查询媒体信息
                    if media.type != MediaType.MOVIE:
                        seasons = media.get_season_list()
                        if len(seasons) == 1:
                            season = seasons[0]
                        else:
                            season = 1
                        media_info = self.media.get_media_info(title="%s 第%s季 %s" % (media.get_name(), season, media.year), mtype=media.type, strict=True)
                        if not media_info or not media_info.tmdb_info:
                            continue
                        tv_info = self.media.get_tmdb_tv_info(media_info.tmdb_id)
                        if not tv_info:
                            log.warn("【DOUBAN】%s 未找到剧集信息，跳过..." % media_info.get_title_string())
                            continue
                        total_count = self.media.get_tmdb_season_episodes_num(tv_info.get("seasons"), season)
                        if not total_count:
                            log.warn("【DOUBAN】%s 获取剧集数失败，跳过..." % media_info.get_title_string())
                            continue
                        insert_rss_tv(media_info, total_count)
                    else:
                        media_info = self.media.get_media_info(title=media.get_name(), mtype=media.type, strict=True)
                        if not media_info or not media_info.tmdb_info:
                            continue
                        insert_rss_movie(media)
                log.info("【DOUBAN】豆瓣数据加入订阅完成")
        log.info("【DOUBAN】豆瓣数据同步完成")
