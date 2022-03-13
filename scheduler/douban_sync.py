import log
from config import get_config
from message.send import Message
from pt.douban import DouBan
from pt.jackett import Jackett
from utils.sqls import insert_douban_medias, get_douban_search_medias, insert_tv_key, insert_movie_key, \
    update_douban_media_state
from utils.types import MediaType, SearchType

DOUBANSYNC_RUNNING = False


class DoubanSync:
    __interval = None
    __auto_search = True
    __auto_rss = True
    message = None
    douban = None
    jackett = None

    def __init__(self):
        self.message = Message()
        self.douban = DouBan()
        self.jackett = Jackett()
        config = get_config()
        if config.get('douban'):
            self.__interval = config['douban'].get('interval')
            self.__auto_search = config['douban'].get('auto_search')
            self.__auto_rss = config['douban'].get('auto_rss')

    def run_schedule(self):
        global DOUBANSYNC_RUNNING
        try:
            if DOUBANSYNC_RUNNING:
                log.warn("【RUN】douban_sync正在执行中...")
                return
            DOUBANSYNC_RUNNING = True
            self.__douban_sync()
            DOUBANSYNC_RUNNING = False
        except Exception as err:
            DOUBANSYNC_RUNNING = False
            log.error("【RUN】执行任务douban_sync出错：%s" % str(err))

    def __douban_sync(self):
        if not self.__interval:
            return
        log.info("【PT】开始同步豆瓣数据...")
        # 拉取豆瓣数据
        medias = self.douban.get_all_douban_movies()
        # 插入数据库
        if not insert_douban_medias(medias):
            log.error("【RUN】豆瓣数据插入数据库失败！")
            return
        else:
            log.info("【PT】豆瓣数据同步完成！")
        # 对于未处理的，开始检索和下载
        if self.__auto_search:
            log.info("【PT】开始检索豆瓣资源...")
            self.__search_douban_media()
            log.info("【PT】豆瓣资源检索完成！")

    def __search_douban_media(self):
        search_list = get_douban_search_medias()
        for item in search_list:
            if not self.jackett.search_one_media("%s %s" % (item[0], item[1]), SearchType.DB):
                if self.__auto_rss:
                    log.info("【PT】 %s %s 没有找到下载资源，更新到RSS订阅中..." % (item[0], item[1]))
                    if item[2] == MediaType.TV.value:
                        insert_tv_key(item[0])
                    else:
                        insert_movie_key(item[0])
                    # 更新状态为已订阅
                    update_douban_media_state(item[0], item[1], 'RSS')
                else:
                    log.info("【PT】 %s %s 未找到下载资源，等待下一次处理..." % (item[0], item[1]))
            else:
                # 更新为已下载
                update_douban_media_state(item[0], item[1], 'DOWNLOADED')


if __name__ == "__main__":
    DoubanSync().run_schedule()
