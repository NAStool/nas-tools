import json
import traceback

import jsonpath
from apscheduler.schedulers.background import BackgroundScheduler
from lxml import etree

import log
from app.downloader import Downloader
from app.filter import Filter
from app.helper import DbHelper
from app.media import Media
from app.message import Message
from app.searcher import Searcher
from app.subscribe import Subscribe
from app.utils import RequestUtils, StringUtils
from app.utils.commons import singleton
from app.utils.types import MediaType, SearchType
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

    _scheduler = None
    _rss_tasks = []
    _rss_parsers = []
    _site_users = {
        "D": "下载",
        "R": "订阅",
        "S": "搜索"
    }

    def __init__(self):
        self.dbhelper = DbHelper()
        self.init_config()

    def init_config(self):
        self.message = Message()
        self.searcher = Searcher()
        self.filter = Filter()
        self.media = Media()
        self.downloader = Downloader()
        self.subscribe = Subscribe()
        # 移除现有任务
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            print(str(e))
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
            parser = self.get_userrss_parser(task.PARSER)
            if task.FILTER:
                filterrule = self.filter.get_rule_groups(groupid=task.FILTER)
            else:
                filterrule = {}
            # 兼容旧配置
            note = task.NOTE
            if str(note).find('seeding_time_limit') != -1:
                note = json.loads(task.NOTE)
                save_path = note.get("save_path")
                download_setting = -1
            else:
                save_path = note
                download_setting = -1
            self._rss_tasks.append({
                "id": task.ID,
                "name": task.NAME,
                "address": task.ADDRESS,
                "parser": task.PARSER,
                "parser_name": parser.get("name") if parser else "",
                "interval": task.INTERVAL,
                "uses": task.USES,
                "uses_text": self._site_users.get(task.USES),
                "include": task.INCLUDE,
                "exclude": task.EXCLUDE,
                "filter": task.FILTER,
                "filter_name": filterrule.get("name") if filterrule else "",
                "update_time": task.UPDATE_TIME,
                "counter": task.PROCESS_COUNT,
                "state": task.STATE,
                "save_path": task.SAVE_PATH or save_path,
                "download_setting": task.DOWNLOAD_SETTING or download_setting
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
            self._scheduler.print_jobs()
            self._scheduler.start()
            log.info("自定义订阅服务启动")

    def get_rsstask_info(self, taskid=None):
        """
        获取单个RSS任务详细信息
        """
        if taskid:
            for task in self._rss_tasks:
                if task.get("id") == int(taskid):
                    return task
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
                # 副标题
                description = res.get('description')
                # 种子大小
                size = res.get('size')
                # 年份
                year = res.get('year')
                if year and len(year) > 4:
                    year = year[:4]
                # 类型
                mediatype = res.get('type')
                if mediatype:
                    mediatype = MediaType.MOVIE if mediatype == "movie" else MediaType.TV

                log.info("【RssChecker】开始处理：%s" % title)

                # 检查是不是处理过
                meta_name = "%s %s" % (title, year) if year else title
                if self.dbhelper.is_userrss_finished(meta_name, enclosure):
                    log.info("【RssChecker】%s 已处理过" % title)
                    continue
                # 识别种子名称，开始检索TMDB
                media_info = self.media.get_media_info(title=meta_name,
                                                       subtitle=description,
                                                       mtype=mediatype)
                if not media_info:
                    log.warn("【RssChecker】%s 识别媒体信息出错！" % title)
                    continue
                # 检查是否已存在
                if not media_info.tmdb_info:
                    log.info("【RssChecker】%s 识别为 %s 未匹配到媒体信息" % (title, media_info.get_name()))
                    continue
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
                        log.info("【RssChecker】%s 缺失季集：%s" % (media_info.get_title_string(),
                                                             no_exists.get(media_info.tmdb_id)))
                if taskinfo.get("uses") == "D":
                    if not enclosure:
                        log.warn("【RssChecker】%s RSS报文中没有enclosure种子链接" % taskinfo.get("name"))
                        continue
                    # 大小及种子页面
                    media_info.set_torrent_info(size=size,
                                                page_url=page_url,
                                                site=taskinfo.get("name"),
                                                enclosure=enclosure,
                                                download_volume_factor=0.0,
                                                upload_volume_factor=1.0)
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
                        log.info("【RssChecker】%s 识别为 %s %s 匹配成功" % (
                            title,
                            media_info.get_title_string(),
                            media_info.get_season_episode_string()))
                    media_info.set_torrent_info(res_order=res_order)
                # 插入数据库
                # FIXME: 这里不能所有的种子都直接插入数据库
                """
                如果是下载类型的任务, 需要下载完成后在进行插入, 否则会导致下载失败的种子也插入数据库 不会再次重试
                # self.dbhelper.insert_rss_torrents(media_info) 
                好的做法应该是, 下载任务的种子的完成状态 用一个新的字段来存储 或者用一个新的表来存储
                下面针对针对不同的任务类型, 有不同的处理方式, 下载的类型的任务, 下载完成后再插入数据库, 其他的直接插入数据库
                还有极端情况, 如果RSS任务的种子有重叠, 即 搜索/订阅 和 下载类型 的种子重叠, 就会导致 搜索/订阅 的种子 处理后 也会认为是 下载类型 的种子 处理完成了
                """
                # 汇总处理
                res_num = res_num + 1
                if taskinfo.get("uses") == "D":
                    # 下载
                    if media_info not in rss_download_torrents:
                        media_info.save_path = taskinfo.get("save_path")
                        media_info.download_setting = taskinfo.get("download_setting")
                        rss_download_torrents.append(media_info)
                elif taskinfo.get("uses") == "R":
                    # 订阅
                    # 订阅类型的 保持现状直接插入数据库
                    self.dbhelper.insert_rss_torrents(media_info)
                    if media_info not in rss_subscribe_torrents:
                        rss_subscribe_torrents.append(media_info)
                elif taskinfo.get("uses") == "S":
                    # 搜索
                    # 搜索类型的 保持现状直接插入数据库
                    self.dbhelper.insert_rss_torrents(media_info)
                    if media_info not in rss_search_torrents:
                        rss_search_torrents.append(media_info)
            except Exception as e:
                log.error("【RssChecker】处理RSS发生错误：%s - %s" % (str(e), traceback.format_exc()))
                continue
        log.info("【RssChecker】%s 处理结束，匹配到 %s 个有效资源" % (taskinfo.get("name"), res_num))
        # 添加下载
        if rss_download_torrents:
            for media in rss_download_torrents:
                ret, ret_msg = self.downloader.download(media_info=media,
                                                        download_dir=media.save_path,
                                                        download_setting=media.download_setting)
                if ret:
                    self.message.send_download_message(in_from=SearchType.USERRSS,
                                                       can_item=media)
                    # 下载类型的 这里下载成功了 插入数据库
                    self.dbhelper.insert_rss_torrents(media)
                    # 登记自定义RSS任务下载记录
                    # FIXME 自定义RSS任务下载记录 里面缺少必要字段无法进行种子是否已下载去重 需要进行表结构升级
                    downloader = Downloader().get_default_client_type().value
                    if media.download_setting:
                        download_attr = self.get_download_setting(media.download_setting)
                        if download_attr.get("downloader"):
                            downloader = download_attr.get("downloader")
                    self.dbhelper.insert_userrss_task_history(taskid, media.org_string, downloader)
                else:
                    log.error("【RssChecker】添加下载任务 %s 失败：%s" % (media.get_title_string(), ret_msg or "请检查下载任务是否已存在"))
                    if ret_msg:
                        self.message.send_download_fail_message(media, ret_msg)
        # 添加订阅
        if rss_subscribe_torrents:
            for media in rss_subscribe_torrents:
                code, msg, _ = self.subscribe.add_rss_subscribe(mtype=media.type,
                                                                name=media.title,
                                                                year=media.year,
                                                                season=media.begin_season,
                                                                tmdbid=media.tmdb_id)
                if code == 0:
                    self.message.send_rss_success_message(in_from=SearchType.USERRSS, media_info=media)
                else:
                    log.warn("【RssChecker】%s 添加订阅失败：%s" % (media.title, msg))
        # 直接搜索
        if rss_search_torrents:
            for media in rss_search_torrents:
                self.searcher.search_one_media(in_from=SearchType.USERRSS,
                                               media_info=media,
                                               no_exists=no_exists)

        # 更新状态
        counter = len(rss_download_torrents) + len(rss_subscribe_torrents) + len(rss_search_torrents)
        if counter:
            self.dbhelper.update_userrss_task_info(taskid, counter)

    def __parse_userrss_result(self, taskinfo):
        """
        获取RSS链接数据，根据PARSER进行解析获取返回结果
        """
        rss_parser = self.get_userrss_parser(taskinfo.get("parser"))
        if not rss_parser:
            log.error("【RssChecker】任务 %s 的解析配置不存在" % taskinfo.get("name"))
            return []
        if not rss_parser.get("format"):
            log.error("【RssChecker】任务 %s 的解析配置不正确" % taskinfo.get("name"))
            return []
        try:
            rss_parser_format = json.loads(rss_parser.get("format"))
        except Exception as e:
            print(str(e))
            log.error("【RssChecker】任务 %s 的解析配置不是合法的Json格式" % taskinfo.get("name"))
            return []
        # 拼装链接
        rss_url = taskinfo.get("address")
        if not rss_url:
            return []
        if rss_parser.get("params"):
            _dict = {
                "TMDBKEY": Config().get_config("app").get("rmt_tmdbkey")
            }
            try:
                param_url = rss_parser.get("params").format(**_dict)
            except Exception as e:
                log.console(str(e))
                log.error("【RssChecker】任务 %s 的解析配置附加参数不合法" % taskinfo.get("name"))
                return []
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
                    rss_result.append(rss_item)
            except Exception as err:
                log.error("【RssChecker】任务 %s 获取的订阅报文无法解析：%s" % (taskinfo.get("name"), str(err)))
                return []
        elif rss_parser.get("type") == "JSON":
            try:
                result_json = json.loads(ret.text)
            except Exception as err:
                log.error("【RssChecker】任务 %s 获取的订阅报文不是合法的Json格式：%s" % (taskinfo.get("name"), str(err)))
                return []
            item_list = jsonpath.jsonpath(result_json, rss_parser_format.get("list"))[0]
            if not isinstance(item_list, list):
                log.error("【RssChecker】任务 %s 获取的订阅报文list后不是列表" % taskinfo.get("name"))
                return []
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
                size = res.get('size')
                # 发布日期
                date = StringUtils.unify_datetime_str(res.get('date'))
                # 年份
                year = res.get('year')
                if year and len(year) > 4:
                    year = year[:4]
                # 检查是不是处理过
                meta_name = "%s %s" % (title, year) if year else title
                finish_flag = self.dbhelper.is_userrss_finished(meta_name, enclosure)
                # 信息聚合
                params = {
                    "title": title,
                    "link": link,
                    "enclosure": enclosure,
                    "size": size,
                    "description": description,
                    "date": date,
                    "finish_flag": finish_flag,
                }
                if params not in rss_articles:
                    rss_articles.append(params)
            except Exception as e:
                log.error("【RssChecker】获取RSS报文发生错误：%s - %s" % (str(e), traceback.format_exc()))
        return rss_articles

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
        # 识别种子名称，开始检索TMDB
        media_info = self.media.get_media_info(title=title)
        if not media_info:
            log.warn("【RssChecker】%s 识别媒体信息出错！" % title)
        # 检查是否匹配
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
        else:
            log.info("【RssChecker】%s 识别为 %s %s 匹配成功" % (
                title,
                media_info.get_title_string(),
                media_info.get_season_episode_string()))
        media_info.set_torrent_info(res_order=res_order)
        # 检查是否已存在
        no_exists = {}
        exist_flag = False
        if not media_info.tmdb_info:
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
                    log.info("【RssChecker】%s 缺失季集：%s" % (media_info.get_title_string(),
                                                         no_exists.get(media_info.tmdb_id)))
        return media_info, match_flag, exist_flag

    def check_rss_articles(self, flag, articles):
        """
        RSS报文处理设置
        :param flag: set_finished/set_unfinish
        :param articles: 报文(title/enclosure)
        """
        try:
            if flag == "set_finished":
                for article in articles:
                    title = article.get("title")
                    enclosure = article.get("enclosure")
                    if not self.dbhelper.is_userrss_finished(title, enclosure):
                        self.dbhelper.simple_insert_rss_torrents(title, enclosure)
            elif flag == "set_unfinish":
                for article in articles:
                    self.dbhelper.simple_delete_rss_torrents(article.get("title"), article.get("enclosure"))
            else:
                return False
            return True
        except Exception as e:
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
            ret, ret_msg = self.downloader.download(media_info=media,
                                                    download_dir=taskinfo.get("save_path"),
                                                    download_setting=taskinfo.get("download_setting"))
            if ret:
                self.message.send_download_message(in_from=SearchType.USERRSS,
                                                   can_item=media)
                # 插入数据库
                self.dbhelper.insert_rss_torrents(media)
                # 登记自定义RSS任务下载记录
                downloader = self.downloader.get_default_client_type().value
                if taskinfo.get("download_setting"):
                    download_attr = self.downloader.get_download_setting(taskinfo.get("download_setting"))
                    if download_attr.get("downloader"):
                        downloader = download_attr.get("downloader")
                self.dbhelper.insert_userrss_task_history(taskid, media.org_string, downloader)
            else:
                log.error("【RssChecker】添加下载任务 %s 失败：%s" % (media.get_title_string(), ret_msg or "请检查下载任务是否已存在"))
                if ret_msg:
                    self.message.send_download_fail_message(media, ret_msg)
                return False
        return True
