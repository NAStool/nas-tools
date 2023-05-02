import json
import time
import traceback

import jsonpath
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from lxml import etree

import log
from app.downloader import Downloader
from app.filter import Filter
from app.helper import DbHelper, RssHelper
from app.media import Media
from app.media.meta import MetaInfo
from app.message import Message
from app.searcher import Searcher
from app.subscribe import Subscribe
from app.utils import RequestUtils, StringUtils, ExceptionUtils
from app.utils.commons import singleton
from app.utils.types import MediaType, SearchType, RssType
from config import Config


@singleton
class RssChecker(object):
    message = None
    searcher = None
    filter = None
    media = None
    filterrule = None
    downloader = None
    subscribe = None
    dbhelper = None
    rsshelper = None

    _scheduler = None
    _rss_tasks = []
    _rss_parsers = []
    _site_users = {
        "D": "下载",
        "R": "订阅",
        "S": "搜索"
    }

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()
        self.rsshelper = RssHelper()
        self.message = Message()
        self.searcher = Searcher()
        self.filter = Filter()
        self.media = Media()
        self.downloader = Downloader()
        self.subscribe = Subscribe()
        # 移除现有任务
        self.stop_service()
        # 读取解析器列表
        rss_parsers = self.dbhelper.get_userrss_parser()
        self._rss_parsers = []
        for rss_parser in rss_parsers:
            self._rss_parsers.append(
                {
                    "id": rss_parser.ID,
                    "name": rss_parser.NAME,
                    "type": rss_parser.TYPE,
                    "format": rss_parser.FORMAT,
                    "params": rss_parser.PARAMS,
                    "note": rss_parser.NOTE
                }
            )
        # 读取任务任务列表
        rsstasks = self.dbhelper.get_userrss_tasks()
        self._rss_tasks = []
        for task in rsstasks:
            if task.FILTER:
                filterrule = self.filter.get_rule_groups(groupid=task.FILTER)
            else:
                filterrule = {}
            # 解析属性
            note = {}
            if task.NOTE:
                try:
                    note = json.loads(task.NOTE)
                except Exception as e:
                    print(str(e))
                    note = {}
            save_path = note.get("save_path") or ""
            recognization = note.get("recognization") or "Y"
            proxy = True if note.get("proxy") in ["Y", "1", True] else False
            try:
                addresses = json.loads(task.ADDRESS)
                if not isinstance(addresses, list):
                    addresses = [addresses]
            except Exception as e:
                print(str(e))
                addresses = [task.ADDRESS]
            try:
                parsers = json.loads(task.PARSER)
                if not isinstance(parsers, list):
                    parsers = [task.PARSER]
            except Exception as e:
                print(str(e))
                parsers = [task.PARSER]
            state = True if task.STATE in ["Y", "1", True] else False
            self._rss_tasks.append({
                "id": task.ID,
                "name": task.NAME,
                "address": addresses,
                "proxy": proxy,
                "parser": parsers,
                "interval": task.INTERVAL,
                "uses": task.USES if task.USES != "S" else "R",
                "uses_text": self._site_users.get(task.USES),
                "include": task.INCLUDE,
                "exclude": task.EXCLUDE,
                "filter": task.FILTER,
                "filter_name": filterrule.get("name") if filterrule else "",
                "update_time": task.UPDATE_TIME,
                "counter": task.PROCESS_COUNT,
                "state": state,
                "save_path": task.SAVE_PATH or save_path,
                "download_setting": task.DOWNLOAD_SETTING or "",
                "recognization": task.RECOGNIZATION or recognization,
                "over_edition": task.OVER_EDITION or 0,
                "sites": json.loads(task.SITES) if task.SITES else {"rss_sites": [], "search_sites": []},
                "filter_args": json.loads(task.FILTER_ARGS)
                if task.FILTER_ARGS else {"restype": "", "pix": "", "team": ""},
            })
        if not self._rss_tasks:
            return
        # 启动RSS任务
        self._scheduler = BackgroundScheduler(timezone=Config().get_timezone(),
                                              executors={
                                                  'default': ThreadPoolExecutor(30)
                                              })
        rss_flag = False
        for task in self._rss_tasks:
            if task.get("state") and task.get("interval"):
                cron = str(task.get("interval")).strip()
                if cron.isdigit():
                    # 分钟
                    rss_flag = True
                    self._scheduler.add_job(func=self.check_task_rss,
                                            args=[task.get("id")],
                                            trigger='interval',
                                            seconds=int(cron) * 60)
                elif cron.count(" ") == 4:
                    # cron表达式
                    try:
                        self._scheduler.add_job(func=self.check_task_rss,
                                                args=[task.get("id")],
                                                trigger=CronTrigger.from_crontab(cron))
                        rss_flag = True
                    except Exception as e:
                        log.info("%s 自定义订阅cron表达式 配置格式错误：%s %s" % (task.get("name"), cron, str(e)))
        if rss_flag:
            self._scheduler.print_jobs()
            self._scheduler.start()
            log.info("自定义订阅服务启动")

    def get_rsstask_info(self, taskid=None):
        """
        获取单个RSS任务详细信息
        """
        if taskid:
            if str(taskid).isdigit():
                taskid = int(taskid)
                for task in self._rss_tasks:
                    if task.get("id") == taskid:
                        return task
            else:
                return {}
        return self._rss_tasks

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
            log.warn("【RssChecker】%s 未下载到数据" % taskinfo.get("name"))
            return
        else:
            log.info("【RssChecker】%s 获取数据：%s" % (taskinfo.get("name"), len(rss_result)))
        # 处理RSS结果
        res_num = 0
        no_exists = {}
        for res in rss_result:
            try:
                # 种子名
                title = res.get('title')
                if not title:
                    continue
                # 种子链接
                enclosure = res.get('enclosure')
                # 种子页面
                page_url = res.get('link')
                # 种子大小
                size = StringUtils.str_filesize(res.get('size'))
                # 年份
                year = res.get('year')
                if year and len(year) > 4:
                    year = year[:4]
                # 类型
                mediatype = res.get('type')
                if mediatype:
                    mediatype = MediaType.MOVIE if mediatype == "movie" else MediaType.TV

                log.info("【RssChecker】开始处理：%s" % title)

                task_type = taskinfo.get("uses")
                meta_name = "%s %s" % (title, year) if year else title
                # 检查是否已处理过
                if self.is_article_processed(task_type, title, year, enclosure):
                    log.info("【RssChecker】%s 已处理过" % title)
                    continue

                if task_type == "D":
                    # 识别种子名称，开始搜索TMDB
                    media_info = MetaInfo(title=meta_name,
                                          mtype=mediatype)
                    cache_info = self.media.get_cache_info(media_info)
                    if taskinfo.get("recognization") == "Y":
                        if cache_info.get("id"):
                            # 有缓存，直接使用缓存
                            media_info.tmdb_id = cache_info.get("id")
                            media_info.type = cache_info.get("type")
                            media_info.title = cache_info.get("title")
                            media_info.year = cache_info.get("year")
                        else:
                            media_info = self.media.get_media_info(title=meta_name,
                                                                   mtype=mediatype)
                            if not media_info:
                                log.warn("【RssChecker】%s 识别媒体信息出错！" % title)
                                continue
                            if not media_info.tmdb_info:
                                log.info("【RssChecker】%s 识别为 %s 未匹配到媒体信息" % (title, media_info.get_name()))
                                continue
                        # 检查是否已存在
                        if media_info.type == MediaType.MOVIE:
                            exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info,
                                                                                           no_exists=no_exists)
                            if exist_flag:
                                log.info("【RssChecker】电影 %s 已存在" % media_info.get_title_string())
                                continue
                        else:
                            exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info,
                                                                                           no_exists=no_exists)
                            # 当前剧集已存在，跳过
                            if exist_flag:
                                # 已全部存在
                                if not no_exists or not no_exists.get(
                                        media_info.tmdb_id):
                                    log.info("【RssChecker】电视剧 %s %s 已存在" % (
                                        media_info.get_title_string(), media_info.get_season_episode_string()))
                                continue
                            if no_exists.get(media_info.tmdb_id):
                                log.info("【RssChecker】%s 缺失季集：%s"
                                         % (media_info.get_title_string(), no_exists.get(media_info.tmdb_id)))
                    # 大小及种子页面
                    media_info.set_torrent_info(size=size,
                                                page_url=page_url,
                                                site=taskinfo.get("name"),
                                                enclosure=enclosure)
                    # 检查种子是否匹配过滤条件
                    filter_args = {
                        "include": taskinfo.get("include"),
                        "exclude": taskinfo.get("exclude"),
                        "rule": taskinfo.get("filter")
                    }
                    match_flag, res_order, match_msg = self.filter.check_torrent_filter(meta_info=media_info,
                                                                                        filter_args=filter_args)
                    # 未匹配
                    if not match_flag:
                        log.info(f"【RssChecker】{match_msg}")
                        continue
                    else:
                        # 匹配优先级
                        media_info.set_torrent_info(res_order=res_order)
                        if taskinfo.get("recognization") == "Y":
                            log.info("【RssChecker】%s 识别为 %s %s 匹配成功" % (
                                title,
                                media_info.get_title_string(),
                                media_info.get_season_episode_string()))
                            # 补充TMDB完整信息
                            if not media_info.tmdb_info:
                                media_info.set_tmdb_info(self.media.get_tmdb_info(mtype=media_info.type,
                                                                                  tmdbid=media_info.tmdb_id))
                            # TMDB信息插入订阅任务
                            if media_info.type != MediaType.MOVIE:
                                self.dbhelper.insert_userrss_mediainfos(taskid, media_info)
                        else:
                            log.info(f"【RssChecker】{title}  匹配成功")
                    # 添加下载列表
                    if not enclosure:
                        log.warn("【RssChecker】%s RSS报文中没有enclosure种子链接" % taskinfo.get("name"))
                        continue
                    if media_info not in rss_download_torrents:
                        rss_download_torrents.append(media_info)
                        res_num = res_num + 1
                elif task_type == "R":
                    # 识别种子名称，开始搜索TMDB
                    media_info = MetaInfo(title=meta_name, mtype=mediatype)
                    # 检查种子是否匹配过滤条件
                    filter_args = {
                        "include": taskinfo.get("include"),
                        "exclude": taskinfo.get("exclude"),
                        "rule": -1
                    }
                    match_flag, _, match_msg = self.filter.check_torrent_filter(meta_info=media_info,
                                                                                filter_args=filter_args)
                    # 未匹配
                    if not match_flag:
                        log.info(f"【RssChecker】{match_msg}")
                        continue
                    # 检查是否已订阅过
                    if self.dbhelper.check_rss_history(type_str="MOV" if media_info.type == MediaType.MOVIE else "TV",
                                                       name=media_info.title,
                                                       year=media_info.year,
                                                       season=media_info.get_season_string()):
                        log.info(
                            f"【RssChecker】{media_info.get_title_string()}{media_info.get_season_string()} 已订阅过")
                        continue
                    # 订阅meta_name存enclosure与下载区别
                    media_info.set_torrent_info(enclosure=meta_name)
                    # 添加处理历史
                    self.rsshelper.insert_rss_torrents(media_info)
                    if media_info not in rss_subscribe_torrents:
                        rss_subscribe_torrents.append(media_info)
                        res_num = res_num + 1
                else:
                    continue
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                log.error("【RssChecker】处理RSS发生错误：%s - %s" % (str(e), traceback.format_exc()))
                continue
        log.info("【RssChecker】%s 处理结束，匹配到 %s 个有效资源" % (taskinfo.get("name"), res_num))
        # 添加下载
        if rss_download_torrents:
            for media in rss_download_torrents:
                downloader_id, ret, ret_msg = self.downloader.download(
                    media_info=media,
                    download_dir=taskinfo.get("save_path"),
                    download_setting=taskinfo.get("download_setting"),
                    in_from=SearchType.USERRSS,
                    proxy=taskinfo.get("proxy"))
                if ret:
                    # 下载类型的 这里下载成功了 插入数据库
                    self.rsshelper.insert_rss_torrents(media)
                    # 登记自定义RSS任务下载记录
                    downloader_name = self.downloader.get_downloader_conf(downloader_id).get("name")
                    self.dbhelper.insert_userrss_task_history(taskid, media.org_string, downloader_name)
                else:
                    log.error("【RssChecker】添加下载任务 %s 失败：%s" % (
                        media.get_title_string(), ret_msg or "请检查下载任务是否已存在"))
        # 添加订阅
        if rss_subscribe_torrents:
            for media in rss_subscribe_torrents:
                code, msg, rss_media = self.subscribe.add_rss_subscribe(
                    mtype=media.type,
                    name=media.get_name(),
                    year=media.year,
                    channel=RssType.Manual,
                    season=media.begin_season,
                    rss_sites=taskinfo.get("sites", {}).get("rss_sites"),
                    search_sites=taskinfo.get("sites", {}).get("search_sites"),
                    over_edition=True if taskinfo.get("over_edition") else False,
                    filter_restype=taskinfo.get("filter_args", {}).get("restype"),
                    filter_pix=taskinfo.get("filter_args", {}).get("pix"),
                    filter_team=taskinfo.get("filter_args", {}).get("team"),
                    filter_rule=taskinfo.get("filter"),
                    save_path=taskinfo.get("save_path"),
                    download_setting=taskinfo.get("download_setting"),
                    in_from=SearchType.USERRSS
                )
                if not rss_media or code != 0:
                    log.warn("【RssChecker】%s 添加订阅失败：%s" % (media.get_name(), msg))

        # 更新状态
        counter = len(rss_download_torrents) + len(rss_subscribe_torrents) + len(rss_search_torrents)
        if counter:
            self.dbhelper.update_userrss_task_info(taskid, counter)
            taskinfo["counter"] = int(taskinfo.get("counter")) + counter \
                if str(taskinfo.get("counter")).isdigit() else counter
            taskinfo["update_time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

    def __parse_userrss_result(self, taskinfo):
        """
        获取RSS链接数据，根据PARSER进行解析获取返回结果
        """
        task_name = taskinfo.get("name")
        rss_urls = taskinfo.get("address")
        rss_parsers = taskinfo.get("parser")
        count = min(len(rss_urls), len(rss_parsers))
        rss_result = []
        for i in range(count):
            rss_url = rss_urls[i]
            if not rss_url:
                continue
            # 检查解析器有效性
            rss_parser = self.get_userrss_parser(rss_parsers[i])
            if not rss_parser:
                log.error(f"【RssChecker】任务 {task_name} RSS地址 {rss_url} 配置解析器不存在")
                continue
            parser_name = rss_parser.get("name")
            if not rss_parser.get("format"):
                log.error(f"【RssChecker】任务 {task_name} 配置解析器 {parser_name} 格式不正确")
                continue
            try:
                rss_parser_format = json.loads(rss_parser.get("format"))
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                log.error(f"【RssChecker】任务 {task_name} 配置解析器 {parser_name} 不是合法的Json格式")
                continue

            # 拼装链接
            if rss_parser.get("params"):
                _dict = {
                    "TMDBKEY": Config().get_config("app").get("rmt_tmdbkey")
                }
                try:
                    param_url = rss_parser.get("params").format(**_dict)
                except Exception as e:
                    ExceptionUtils.exception_traceback(e)
                    log.error(f"【RssChecker】任务 {task_name} 配置解析器 {parser_name} 附加参数不合法")
                    continue
                rss_url = "%s?%s" % (rss_url, param_url) if rss_url.find("?") == -1 else "%s&%s" % (rss_url, param_url)
            # 请求数据
            try:
                ret = RequestUtils(proxies=Config().get_proxies() if taskinfo.get("proxy") else None
                                   ).get_res(rss_url)
                if not ret:
                    continue
                ret.encoding = ret.apparent_encoding
            except Exception as e2:
                ExceptionUtils.exception_traceback(e2)
                continue
            # 解析数据 XPATH
            if rss_parser.get("type") == "XML":
                try:
                    result_tree = etree.XML(ret.text.encode("utf-8"))
                    item_list = result_tree.xpath(rss_parser_format.get("list")) or []
                    for item in item_list:
                        rss_item = {}
                        for key, attr in rss_parser_format.get("item", {}).items():
                            if attr.get("path"):
                                if attr.get("namespaces"):
                                    value = item.xpath("//ns:%s" % attr.get("path"),
                                                       namespaces={"ns": attr.get("namespaces")})
                                else:
                                    value = item.xpath(attr.get("path"))
                            elif attr.get("value"):
                                value = attr.get("value")
                            else:
                                continue
                            if value:
                                rss_item.update({key: value[0]})
                        rss_item.update({"address_index": i+1})
                        rss_result.append(rss_item)
                except Exception as err:
                    ExceptionUtils.exception_traceback(err)
                    log.error(f"【RssChecker】任务 {task_name} RSS地址 {rss_url} 获取的订阅报文无法解析：{str(err)}")
                    continue
            elif rss_parser.get("type") == "JSON":
                try:
                    result_json = json.loads(ret.text)
                except Exception as err:
                    ExceptionUtils.exception_traceback(err)
                    log.error(f"【RssChecker】任务 {task_name} RSS地址 {rss_url} 获取的订阅报文不是合法的Json格式：{str(err)}")
                    continue
                item_list = jsonpath.jsonpath(result_json, rss_parser_format.get("list"))[0]
                if not isinstance(item_list, list):
                    log.error(f"【RssChecker】任务 {task_name} RSS地址 {rss_url} 获取的订阅报文list后不是列表")
                    continue
                for item in item_list:
                    rss_item = {}
                    for key, attr in rss_parser_format.get("item", {}).items():
                        if attr.get("path"):
                            value = jsonpath.jsonpath(item, attr.get("path"))
                        elif attr.get("value"):
                            value = attr.get("value")
                        else:
                            continue
                        if value:
                            rss_item.update({key: value[0]})
                    rss_item.update({"address_index": i+1})
                    rss_result.append(rss_item)
        return rss_result

    def get_userrss_parser(self, pid=None):
        if pid:
            for rss_parser in self._rss_parsers:
                if rss_parser.get("id") == int(pid):
                    return rss_parser
            return {}
        else:
            return self._rss_parsers

    def get_rss_articles(self, taskid):
        """
        查看自定义RSS报文
        :param taskid: 自定义RSS的ID
        """
        if not taskid:
            return
        # 下载订阅的文章列表
        rss_articles = []
        # 任务信息
        taskinfo = self.get_rsstask_info(taskid)
        if not taskinfo:
            return
        rss_result = self.__parse_userrss_result(taskinfo)
        if len(rss_result) == 0:
            return []
        for res in rss_result:
            try:
                # 种子名
                title = res.get('title')
                if not title:
                    continue
                # 种子链接
                enclosure = res.get('enclosure')
                # 种子页面
                link = res.get('link')
                # 副标题
                description = res.get('description')
                # 种子大小
                size = StringUtils.str_filesize(res.get('size'))
                # 发布日期
                date = StringUtils.unify_datetime_str(res.get('date')) or ""
                # 年份
                year = res.get('year')
                if year and len(year) > 4:
                    year = year[:4]
                # 检查是不是处理过
                finish_flag = self.is_article_processed(taskinfo.get("uses"), title, year, enclosure)
                # 信息聚合
                params = {
                    "title": title,
                    "link": link,
                    "enclosure": enclosure,
                    "size": size,
                    "description": description,
                    "date": date,
                    "finish_flag": finish_flag,
                    "year": year,
                    "address_index": res.get("address_index")
                }
                if params not in rss_articles:
                    rss_articles.append(params)
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                log.error("【RssChecker】获取RSS报文发生错误：%s - %s" % (str(e), traceback.format_exc()))
        return sorted(rss_articles, key=lambda x: x['date'], reverse=True)

    def test_rss_articles(self, taskid, title):
        """
        测试RSS报文
        :param taskid: 自定义RSS的ID
        :param title: RSS报文title
        """
        # 任务信息
        taskinfo = self.get_rsstask_info(taskid)
        if not taskinfo:
            return
        # 识别种子名称，开始搜索TMDB
        media_info = MetaInfo(title=title)
        cache_info = self.media.get_cache_info(media_info)
        if cache_info.get("id"):
            # 有缓存，直接使用缓存
            media_info.tmdb_id = cache_info.get("id")
            media_info.type = cache_info.get("type")
            media_info.title = cache_info.get("title")
            media_info.year = cache_info.get("year")
        else:
            media_info = self.media.get_media_info(title=title)
            if not media_info:
                log.warn("【RssChecker】%s 识别媒体信息出错！" % title)
        # 检查是否匹配
        filter_args = {
            "include": taskinfo.get("include"),
            "exclude": taskinfo.get("exclude"),
            "rule": taskinfo.get("filter") if taskinfo.get("uses") == "D" else None
        }
        match_flag, res_order, match_msg = self.filter.check_torrent_filter(meta_info=media_info,
                                                                            filter_args=filter_args)
        # 未匹配
        if not match_flag:
            log.info(f"【RssChecker】{match_msg}")
        else:
            log.info("【RssChecker】%s 识别为 %s %s 匹配成功" % (
                title,
                media_info.get_title_string(),
                media_info.get_season_episode_string()))
        media_info.set_torrent_info(res_order=res_order)
        # 检查是否已存在
        no_exists = {}
        exist_flag = False
        if not media_info.tmdb_id:
            log.info("【RssChecker】%s 识别为 %s 未匹配到媒体信息" % (title, media_info.get_name()))
        else:
            if media_info.type == MediaType.MOVIE:
                exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info,
                                                                               no_exists=no_exists)
                if exist_flag:
                    log.info("【RssChecker】电影 %s 已存在" % media_info.get_title_string())
            else:
                exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info,
                                                                               no_exists=no_exists)
                if exist_flag:
                    # 已全部存在
                    if not no_exists or not no_exists.get(
                            media_info.tmdb_id):
                        log.info("【RssChecker】电视剧 %s %s 已存在" % (
                            media_info.get_title_string(), media_info.get_season_episode_string()))
                if no_exists.get(media_info.tmdb_id):
                    log.info("【RssChecker】%s 缺失季集：%s"
                             % (media_info.get_title_string(), no_exists.get(media_info.tmdb_id)))
        return media_info, match_flag, exist_flag

    def check_rss_articles(self, taskid, flag, articles):
        """
        RSS报文处理设置
        :param taskid: 自定义RSS的ID
        :param flag: set_finished/set_unfinish
        :param articles: 报文(title/enclosure)
        """
        try:
            task_type = self.get_rsstask_info(taskid).get("uses")
            if flag == "set_finished":
                for article in articles:
                    title = article.get("title")
                    enclosure = article.get("enclosure")
                    year = article.get("year")
                    meta_name = f"{title} {year}" if year else title
                    if not self.is_article_processed(task_type, title, enclosure, year):
                        if task_type == "D":
                            self.rsshelper.simple_insert_rss_torrents(meta_name, enclosure)
                        elif task_type == "R":
                            self.rsshelper.simple_insert_rss_torrents(meta_name, meta_name)
            elif flag == "set_unfinish":
                for article in articles:
                    title = article.get("title")
                    enclosure = article.get("enclosure")
                    year = article.get("year")
                    meta_name = f"{title} {year}" if year else title
                    if task_type == "D":
                        self.rsshelper.simple_delete_rss_torrents(meta_name, enclosure)
                    elif task_type == "R":
                        self.rsshelper.simple_delete_rss_torrents(meta_name, meta_name)
            else:
                return False
            return True
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
            log.error("【RssChecker】设置RSS报文状态时发生错误：%s - %s" % (str(e), traceback.format_exc()))
            return False

    def download_rss_articles(self, taskid, articles):
        """
        RSS报文下载
        :param taskid: 自定义RSS的ID
        :param articles: 报文(title/enclosure)
        """
        if not taskid:
            return
        # 任务信息
        taskinfo = self.get_rsstask_info(taskid)
        if not taskinfo:
            return
        for article in articles:
            media = self.media.get_media_info(title=article.get("title"))
            media.set_torrent_info(enclosure=article.get("enclosure"))
            downloader_id, ret, ret_msg = self.downloader.download(
                media_info=media,
                download_dir=taskinfo.get("save_path"),
                download_setting=taskinfo.get("download_setting"),
                in_from=SearchType.USERRSS,
                proxy=taskinfo.get("proxy"))
            downloader_name = self.downloader.get_downloader_conf(downloader_id).get("name")
            if ret:
                # 插入数据库
                self.rsshelper.insert_rss_torrents(media)
                # 登记自定义RSS任务下载记录
                self.dbhelper.insert_userrss_task_history(taskid, media.org_string, downloader_name)
            else:
                log.error("【RssChecker】添加下载任务 %s 失败：%s" % (
                    media.get_title_string(), ret_msg or "请检查下载任务是否已存在"))
                return False
        return True

    def get_userrss_mediainfos(self):
        taskinfos = self.dbhelper.get_userrss_tasks()
        mediainfos_all = []
        for taskinfo in taskinfos:
            mediainfos = json.loads(taskinfo.MEDIAINFOS) if taskinfo.MEDIAINFOS else []
            if mediainfos:
                mediainfos_all += mediainfos
        return mediainfos_all

    def stop_service(self):
        """
        停止服务
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            print(str(e))

    def is_article_processed(self, task_type, title, year, enclosure):
        """
        检查报文是否已处理
        :param task_type: 订阅任务类型
        :param title: 报文标题
        :param year: 报文年份
        :param enclosure: 报文链接
        :return:
        """
        meta_name = f"{title} {year}" if year else title
        match task_type:
            case "D":
                return self.rsshelper.is_rssd_by_simple(meta_name, enclosure)
            case "R":
                return self.rsshelper.is_rssd_by_simple(meta_name, meta_name)
            case _:
                return False

    def delete_userrss_task(self, tid):
        """
        删除自定义RSS任务
        :param tid: 任务ID
        """
        ret = self.dbhelper.delete_userrss_task(tid)
        self.init_config()
        return ret

    def update_userrss_task(self, item):
        """
        更新自定义RSS任务
        :param item: 任务信息
        """
        ret = self.dbhelper.update_userrss_task(item)
        self.init_config()
        return ret

    def check_userrss_task(self, tid=None, state=None):
        """
        设置自定义RSS任务
        :param tid: 任务ID
        :param state: 任务状态
        """
        ret = self.dbhelper.check_userrss_task(tid, state)
        self.init_config()
        return ret

    def delete_userrss_parser(self, pid):
        """
        删除自定义RSS解析器
        :param pid: 解析器ID
        """
        ret = self.dbhelper.delete_userrss_parser(pid)
        self.init_config()
        return ret

    def update_userrss_parser(self, item):
        """
        更新自定义RSS解析器
        :param item: 解析器信息
        """
        ret = self.dbhelper.update_userrss_parser(item)
        self.init_config()
        return ret

    def get_userrss_task_history(self, task_id):
        """
        获取自定义RSS任务下载记录
        :param task_id: 任务ID
        """
        return self.dbhelper.get_userrss_task_history(task_id)
