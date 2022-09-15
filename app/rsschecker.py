import json
import re
import traceback

from apscheduler.schedulers.background import BackgroundScheduler
from lxml import etree

import log
from app.db import SqlHelper
from app.downloader import Downloader
from app.filterrules import FilterRule
from app.media import Media
from app.message import Message
from app.searcher import Searcher
from app.utils import RequestUtils
from app.utils.commons import singleton
from app.utils.types import MediaType, SearchType
from config import Config
from web.backend.subscribe import add_rss_subscribe


@singleton
class RssChecker(object):
    message = None
    searcher = None
    media = None
    filterrule = None
    downloader = None
    _scheduler = None
    _rss_tasks = []

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.message = Message()
        self.searcher = Searcher()
        self.filterrule = FilterRule()
        self.media = Media()
        self.downloader = Downloader()
        # 移除现有任务
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            print(str(e))
        # 读取任务任务列表
        rsstasks = SqlHelper.get_userrss_tasks()
        self._rss_tasks = []
        for task in rsstasks:
            self._rss_tasks.append({
                "id": task[0],
                "name": task[1],
                "address": task[2],
                "parser": task[3],
                "interval": task[4],
                "uses": task[5],
                "include": task[6],
                "exclude": task[7],
                "filter": task[8],
                "state": task[11],
                "note": task[12]
            })
        if not self._rss_tasks:
            return
        # 启动RSS任务
        self._scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        rss_flag = False
        for task in self._rss_tasks:
            if task.get("state") == "Y" and task.get("interval") and str(task.get("interval")).isdigit():
                rss_flag = True
                self._scheduler.add_job(func=self.check_task_rss,
                                        args=[task.get("id")],
                                        trigger='interval',
                                        seconds=int(task.get("interval")) * 60)
        if rss_flag:
            log.info("【RUN】自定议订阅服务启动")

    def get_rsstask_info(self, taskid):
        """
        获取单个RSS任务详细信息
        """
        for task in self._rss_tasks:
            if task.get("id") == taskid:
                return task
        return None

    def check_task_rss(self, taskid):
        """
        处理自定义RSS任务，由定时服务调用
        :param taskid: 自定义RSS的ID
        """
        if not taskid:
            return
        # 需要下载的项目
        rss_download_torrents = []
        # 需要订阅的项目
        rss_subscribe_torrents = []
        # 需要搜索的项目
        rss_search_torrents = []
        # 任务信息
        taskinfo = self.get_rsstask_info(taskid)
        if not taskinfo:
            return
        rss_result = self.__parse_userrss_result(taskinfo)
        if len(rss_result) == 0:
            log.warn("【RSSCHECKER】%s 未下载到数据" % taskinfo.get("name"))
            return
        else:
            log.info("【RSSCHECKER】%s 获取数据：%s" % (taskinfo.get("name"), len(rss_result)))
        # 处理RSS结果
        res_num = 0
        no_exists = {}
        for res in rss_result:
            try:
                # 种子名
                torrent_name = res.get('title')
                # 种子链接
                enclosure = res.get('enclosure')
                # 种子页面
                page_url = res.get('link')
                # 副标题
                description = res.get('description')
                # 种子大小
                size = res.get('size')

                log.info("【RSSCHECKER】开始处理：%s" % torrent_name)

                # 检查是不是处理过
                if SqlHelper.is_userrss_finished(torrent_name, enclosure):
                    log.info("【RSSCHECKER】%s 已处理过" % torrent_name)
                    continue
                # 识别种子名称，开始检索TMDB
                media_info = self.media.get_media_info(title=torrent_name, subtitle=description)
                if not media_info:
                    log.warn("【RSSCHECKER】%s 识别媒体信息出错！" % torrent_name)
                    continue
                elif not media_info.tmdb_info:
                    log.info("【RSSCHECKER】%s 识别为 %s 未匹配到媒体信息" % (torrent_name, media_info.get_name()))
                    continue
                # 大小及种子页面
                media_info.set_torrent_info(size=size,
                                            page_url=page_url,
                                            site=taskinfo.get("name"),
                                            enclosure=enclosure,
                                            download_volume_factor=0.0,
                                            upload_volume_factor=1.0)
                # 检查种子是否匹配过滤条件
                match_flag, res_order = self.__is_match_rss(
                    media_info=media_info,
                    taskinfo=taskinfo)
                # 未匹配
                if not match_flag:
                    log.info("【RSSCHECKER】%s 识别为 %s %s 不匹配" % (
                        torrent_name,
                        media_info.get_title_string(),
                        media_info.get_season_episode_string()))
                    continue
                else:
                    log.info("【RSSCHECKER】%s 识别为 %s %s 匹配成功" % (
                        torrent_name,
                        media_info.get_title_string(),
                        media_info.get_season_episode_string()))
                media_info.set_torrent_info(res_order=res_order)
                # 检查是否已存在
                if media_info.type == MediaType.MOVIE:
                    exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info,
                                                                                   no_exists=no_exists)
                    if exist_flag:
                        log.info("【RSSCHECKER】电影 %s 已存在" % media_info.get_title_string())
                        continue
                else:
                    exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info,
                                                                                   no_exists=no_exists)
                    # 当前剧集已存在，跳过
                    if exist_flag:
                        # 已全部存在
                        if not no_exists or not no_exists.get(
                                media_info.tmdb_id):
                            log.info("【RSSCHECKER】电视剧 %s %s 已存在" % (
                                media_info.get_title_string(), media_info.get_season_episode_string()))
                        continue
                    log.info("【RSSCHECKER】%s 缺失季集：%s" % (media_info.get_title_string(),
                                                         no_exists.get(media_info.tmdb_id)))
                # 插入数据库
                SqlHelper.insert_rss_torrents(media_info)
                # 汇总处理
                res_num = res_num + 1
                if taskinfo.get("uses") == "D":
                    # 下载
                    if media_info not in rss_download_torrents:
                        rss_download_torrents.append(media_info)
                elif taskinfo.get("uses") == "R":
                    # 订阅
                    if media_info not in rss_subscribe_torrents:
                        rss_subscribe_torrents.append(media_info)
                elif taskinfo.get("uses") == "S":
                    # 搜索
                    if media_info not in rss_search_torrents:
                        rss_search_torrents.append(media_info)
            except Exception as e:
                log.error("【RSSCHECKER】处理RSS发生错误：%s - %s" % (str(e), traceback.format_exc()))
                continue
        log.info("【RSSCHECKER】%s 处理结束，匹配到 %s 个有效资源" % (taskinfo.get("name"), res_num))
        # 添加下载
        if rss_download_torrents:
            download_items, _ = self.downloader.check_and_add_pt(SearchType.RSS,
                                                                 rss_download_torrents,
                                                                 no_exists)
            if download_items:
                log.info("【RSSCHECKER】实际下载了 %s 个资源" % len(download_items))
            else:
                log.info("【RSSCHECKER】未下载到任何资源")
        # 添加订阅
        if rss_subscribe_torrents:
            for media in rss_subscribe_torrents:
                code, msg, _ = add_rss_subscribe(mtype=media.type,
                                                 name=media.title,
                                                 year=media.year,
                                                 season=media.begin_season,
                                                 tmdbid=media.tmdb_id)
                if code == 0:
                    self.message.send_rss_success_message(in_from=SearchType.RSS, media_info=media)
                else:
                    log.warn("【RSSCHECKER】%s 添加订阅失败：%s" % (media.title, msg))
        # 直接搜索
        if rss_search_torrents:
            for media in rss_subscribe_torrents:
                self.searcher.search_one_media(in_from=SearchType.RSS,
                                               media_info=media,
                                               no_exists=no_exists)

    def __parse_userrss_result(self, taskinfo):
        """
        获取RSS链接数据，根据PARSER进行解析获取返回结果
        """
        rss_parser = self.__get_userrss_parser(taskinfo.get("parser"))
        if not rss_parser:
            log.warn("【RSSCHECKER】任务 %s 的解析配置不存在" % taskinfo.get("name"))
            return []
        if not rss_parser.get("format"):
            log.warn("【RSSCHECKER】任务 %s 的解析配置不正确" % taskinfo.get("name"))
            return []
        try:
            rss_parser_format = json.loads(rss_parser.get("format"))
        except Exception as e:
            print(str(e))
            log.warn("【RSSCHECKER】任务 %s 的解析配置不是合法的Json格式" % taskinfo.get("name"))
            return []
        # 拼装链接
        rss_url = taskinfo.get("address")
        if not rss_url:
            return []
        if rss_parser.get("params"):
            _dict = {
                "TMDBID": Config().get_config("app").get("rmt_tmdbkey")
            }
            param_url = rss_parser.get("params").format(**_dict)
            rss_url = "%s?%s" % (rss_url, param_url) if rss_url.find("?") == -1 else "%s&%s" % (rss_url, param_url)
        # 请求数据
        try:
            ret = RequestUtils().get_res(rss_url)
            if not ret:
                return []
            ret.encoding = ret.apparent_encoding
        except Exception as e2:
            log.console(str(e2))
            return []
        # 解析数据 XPATH
        rss_result = []
        if rss_parser.get("type") == "XML":
            result_tree = etree.XML(ret.text.encode("utf-8"))
            item_list = result_tree.xpath(rss_parser_format.get("list")) or []
            for item in item_list:
                rss_item = {}
                for key, attr in rss_parser_format.get("torrent", {}).items():
                    value = item.xpath(attr.get("path"))
                    if value:
                        rss_item.update({key: value[0]})
                rss_result.append(rss_item)
        elif rss_parser.get("type") == "JSON":
            pass
        return rss_result

    def __is_match_rss(self, taskinfo, media_info):
        """
        检查是否匹配
        """
        res_order = 0
        if not taskinfo or not media_info:
            return False, 0
        if taskinfo.get("include"):
            if not re.search(r"%s" % taskinfo.get("include"), media_info.org_string, re.IGNORECASE):
                return False, 0
        if taskinfo.get("exclude"):
            if re.search(r"%s" % taskinfo.get("exclude"), media_info.org_string, re.IGNORECASE):
                return False, 0
        if taskinfo.get("filter"):
            match_flag, res_order, _ = self.filterrule.check_rules(meta_info=media_info,
                                                                   rolegroup=taskinfo.get("filter"))
            if not match_flag:
                return False, 0
        return True, res_order

    @staticmethod
    def __get_userrss_parser(pid):
        rss_parser = SqlHelper.get_userrss_parser(pid)
        if not rss_parser:
            return None
        return {
            "id": rss_parser[0][0],
            "name": rss_parser[0][1],
            "type": rss_parser[0][2],
            "format": rss_parser[0][3],
            "params": rss_parser[0][4],
            "note": rss_parser[0][5]
        }
