from threading import Lock

import log
from config import Config
from pt.douban import DouBan
from pt.searcher import Searcher
from utils.sqls import insert_tv_key, insert_movie_key, get_douban_search_state, insert_douban_media_state
from utils.types import MediaType, SearchType

lock = Lock()


class DoubanSync:
    __interval = None
    __auto_search = True
    __auto_rss = True
    douban = None
    searcher = None

    def __init__(self):
        self.douban = DouBan()
        self.searcher = Searcher()
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
                    seasons = media.get_season_list()
                    if len(seasons) == 1:
                        search_str = "电视剧 %s 第%s季 %s" % (media.get_name(), seasons[0], media.year)
                    elif media.type == MediaType.TV:
                        search_str = "电视剧 %s %s" % (media.get_name(), media.year)
                    else:
                        search_str = "电影 %s %s" % (media.get_name(), media.year)
                    # 开始检索，传入总集数
                    search_result = self.searcher.search_one_media(input_str=search_str,
                                                                   in_from=SearchType.DB)

                    if not search_result:
                        if self.__auto_rss:
                            log.info("【DOUBAN】 %s %s 更新到RSS订阅中..." % (media.get_name(), media.year))
                            if media.type == MediaType.TV:
                                insert_tv_key(media.get_name())
                            else:
                                insert_movie_key(media.get_name())
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
                    if media.type == MediaType.TV:
                        insert_tv_key(media.get_name())
                    else:
                        insert_movie_key(media.get_name())
                log.info("【DOUBAN】豆瓣数据加入订阅完成")
        log.info("【DOUBAN】豆瓣数据同步完成")
