import json
import re
import traceback

import jsonpath
from apscheduler.schedulers.background import BackgroundScheduler
from lxml import etree

import log
from app.helper import SqlHelper
from app.filterrules import FilterRule
from app.media import Media
from app.message import Message
from app.searcher import Searcher
from app.downloader import Downloader
from app.utils import RequestUtils, StringUtils
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
    _site_users = {
        "D": "下载",
        "R": "订阅",
        "S": "搜索"
    }

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
            parser = self.get_userrss_parser(task[3])
            if task[8]:
                filterrule = self.filterrule.get_rule_groups(groupid=task[8])
            else:
                filterrule = {}
            # 兼容旧配置
            note = task[12]
            if str(note).find('seeding_time_limit') != -1:
                note = json.loads(task[12])
            else:
                note = {"save_path": note,
                        "category": '',
                        "tags": '',
                        "content_layout": '',
                        "is_paused": '',
                        "upload_limit": '',
                        "download_limit": '',
                        "ratio_limit": '',
                        "seeding_time_limit": ''}
            self._rss_tasks.append({
                "id": task[0],
                "name": task[1],
                "address": task[2],
                "parser": task[3],
                "parser_name": parser.get("name") if parser else "",
                "interval": task[4],
                "uses": task[5],
                "uses_text": self._site_users.get(task[5]),
                "include": task[6],
                "exclude": task[7],
                "filter": task[8],
                "filter_name": filterrule.get("name") if filterrule else "",
                "update_time": task[9],
                "counter": task[10],
                "state": task[11],
                "note": note
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
            log_info("自定义订阅服务启动")

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
            log_warn("【RSSCHECKER】%s 未下载到数据" % taskinfo.get("name"))
            return
        else:
            log_info("【RSSCHECKER】%s 获取数据：%s" % (taskinfo.get("name"), len(rss_result)))
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

                log_info("【RSSCHECKER】开始处理：%s" % title)

                # 检查是不是处理过
                meta_name = "%s %s" % (title, year) if year else title
                if SqlHelper.is_userrss_finished(meta_name, enclosure):
                    log_info("【RSSCHECKER】%s 已处理过" % title)
                    continue
                # 识别种子名称，开始检索TMDB
                media_info = self.media.get_media_info(title=meta_name,
                                                       subtitle=description,
                                                       mtype=mediatype)
                if not media_info:
                    log_warn("【RSSCHECKER】%s 识别媒体信息出错！" % title)
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
                    log_info("【RSSCHECKER】%s 不匹配" % title)
                    continue
                else:
                    log_info("【RSSCHECKER】%s 识别为 %s %s 匹配成功" % (
                        title,
                        media_info.get_title_string(),
                        media_info.get_season_episode_string()))
                media_info.set_torrent_info(res_order=res_order)
                # 检查是否已存在
                if taskinfo.get("uses") != "D":
                    if not media_info.tmdb_info:
                        log_info("【RSSCHECKER】%s 识别为 %s 未匹配到媒体信息" % (title, media_info.get_name()))
                        continue
                    if media_info.type == MediaType.MOVIE:
                        exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info,
                                                                                       no_exists=no_exists)
                        if exist_flag:
                            log_info("【RSSCHECKER】电影 %s 已存在" % media_info.get_title_string())
                            continue
                    else:
                        exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info,
                                                                                       no_exists=no_exists)
                        # 当前剧集已存在，跳过
                        if exist_flag:
                            # 已全部存在
                            if not no_exists or not no_exists.get(
                                    media_info.tmdb_id):
                                log_info("【RSSCHECKER】电视剧 %s %s 已存在" % (
                                    media_info.get_title_string(), media_info.get_season_episode_string()))
                            continue
                        if no_exists.get(media_info.tmdb_id):
                            log_info("【RSSCHECKER】%s 缺失季集：%s" % (media_info.get_title_string(),
                                                                 no_exists.get(media_info.tmdb_id)))
                elif not enclosure:
                    log_warn("【RSSCHECKER】%s RSS报文中没有enclosure种子链接" % taskinfo.get("name"))
                    continue
                # 插入数据库
                SqlHelper.insert_rss_torrents(media_info)
                # 汇总处理
                res_num = res_num + 1
                if taskinfo.get("uses") == "D":
                    # 下载
                    if media_info not in rss_download_torrents:
                        media_info.note = taskinfo.get("note")
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
                log_error("【RSSCHECKER】处理RSS发生错误：%s - %s" % (str(e), traceback.format_exc()))
                continue
        log_info("【RSSCHECKER】%s 处理结束，匹配到 %s 个有效资源" % (taskinfo.get("name"), res_num))
        # 添加下载
        if rss_download_torrents:
            for media in rss_download_torrents:
                ret, ret_msg = self.downloader.download(media_info=media,
                                                        is_paused=media.note.get("is_paused"),
                                                        tag=media.note.get("tags"),
                                                        download_dir=media.note.get("save_path"),
                                                        category=media.note.get("category"),
                                                        content_layout=media.note.get("content_layout"),
                                                        upload_limit=media.note.get("upload_limit"),
                                                        download_limit=media.note.get("download_limit"),
                                                        ratio_limit=media.note.get("ratio_limit"),
                                                        seeding_time_limit=media.note.get("seeding_time_limit"))
                if ret:
                    self.message.send_download_message(in_from=SearchType.RSS,
                                                       can_item=media)
                    # 登记自定义RSS任务下载记录
                    SqlHelper.insert_userrss_task_history(taskid, media.org_string, Downloader().get_type().value)
                else:
                    log_error("【RSSCHECKER】添加下载任务 %s 失败：%s" % (media.get_title_string(), ret_msg or "请检查下载任务是否已存在"))
                    if ret_msg:
                        self.message.send_download_fail_message(media, ret_msg)
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
                    log_warn("【RSSCHECKER】%s 添加订阅失败：%s" % (media.title, msg))
        # 直接搜索
        if rss_search_torrents:
            for media in rss_search_torrents:
                self.searcher.search_one_media(in_from=SearchType.RSS,
                                               media_info=media,
                                               no_exists=no_exists)

        # 更新状态
        counter = len(rss_download_torrents) + len(rss_subscribe_torrents) + len(rss_search_torrents)
        if counter:
            SqlHelper.update_userrss_task_info(taskid, counter)

    def __parse_userrss_result(self, taskinfo):
        """
        获取RSS链接数据，根据PARSER进行解析获取返回结果
        """
        rss_parser = self.get_userrss_parser(taskinfo.get("parser"))
        if not rss_parser:
            log_error("【RSSCHECKER】任务 %s 的解析配置不存在" % taskinfo.get("name"))
            return []
        if not rss_parser.get("format"):
            log_error("【RSSCHECKER】任务 %s 的解析配置不正确" % taskinfo.get("name"))
            return []
        try:
            rss_parser_format = json.loads(rss_parser.get("format"))
        except Exception as e:
            print(str(e))
            log_error("【RSSCHECKER】任务 %s 的解析配置不是合法的Json格式" % taskinfo.get("name"))
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
                log_error("【RSSCHECKER】任务 %s 的解析配置附加参数不合法" % taskinfo.get("name"))
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
                log_error("【RSSCHECKER】任务 %s 获取的订阅报文无法解析：%s" % (taskinfo.get("name"), str(err)))
                return []
        elif rss_parser.get("type") == "JSON":
            try:
                result_json = json.loads(ret.text)
            except Exception as err:
                log_error("【RSSCHECKER】任务 %s 获取的订阅报文不是合法的Json格式：%s" % (taskinfo.get("name"), str(err)))
                return []
            item_list = jsonpath.jsonpath(result_json, rss_parser_format.get("list"))[0]
            if not isinstance(item_list, list):
                log_error("【RSSCHECKER】任务 %s 获取的订阅报文list后不是列表" % taskinfo.get("name"))
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
    def get_userrss_parser(pid=None):
        if pid:
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
        else:
            return_parsers = []
            rss_parsers = SqlHelper.get_userrss_parser()
            for rss_parser in rss_parsers:
                return_parsers.append(
                    {
                        "id": rss_parser[0],
                        "name": rss_parser[1],
                        "type": rss_parser[2],
                        "format": rss_parser[3],
                        "params": rss_parser[4],
                        "note": rss_parser[5]
                    }
                )
            return return_parsers

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
                finish_flag = SqlHelper.is_userrss_finished(meta_name, enclosure)
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
                log_error("【RSSCHECKER】获取RSS报文发生错误：%s - %s" % (str(e), traceback.format_exc()))
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
            log_warn("【RSSCHECKER】%s 识别媒体信息出错！" % title)
        # 检查种子是否匹配过滤条件
        match_flag, res_order = self.__is_match_rss(
            media_info=media_info,
            taskinfo=taskinfo)
        # 未匹配
        if not match_flag:
            log_info("【RSSCHECKER】%s 不匹配" % title)
        else:
            log_info("【RSSCHECKER】%s 识别为 %s %s 匹配成功" % (
                title,
                media_info.get_title_string(),
                media_info.get_season_episode_string()))
        media_info.set_torrent_info(res_order=res_order)
        # 检查是否已存在
        no_exists = {}
        exist_flag = False
        if not media_info.tmdb_info:
            log_info("【RSSCHECKER】%s 识别为 %s 未匹配到媒体信息" % (title, media_info.get_name()))
        else:
            if media_info.type == MediaType.MOVIE:
                exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info,
                                                                               no_exists=no_exists)
                if exist_flag:
                    log_info("【RSSCHECKER】电影 %s 已存在" % media_info.get_title_string())
            else:
                exist_flag, no_exists, _ = self.downloader.check_exists_medias(meta_info=media_info,
                                                                               no_exists=no_exists)
                if exist_flag:
                    # 已全部存在
                    if not no_exists or not no_exists.get(
                            media_info.tmdb_id):
                        log_info("【RSSCHECKER】电视剧 %s %s 已存在" % (
                            media_info.get_title_string(), media_info.get_season_episode_string()))
                if no_exists.get(media_info.tmdb_id):
                    log_info("【RSSCHECKER】%s 缺失季集：%s" % (media_info.get_title_string(),
                                                         no_exists.get(media_info.tmdb_id)))
        return media_info, match_flag, exist_flag

    @staticmethod
    def check_rss_articles(flag, articles):
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
                    if not SqlHelper.is_userrss_finished(title, enclosure):
                        SqlHelper.simple_insert_rss_torrents(title, enclosure)
            elif flag == "set_unfinish":
                for article in articles:
                    SqlHelper.simple_delete_rss_torrents(article.get("title"), article.get("enclosure"))
            else:
                return False
            return True
        except Exception as e:
            log_error("【RSSCHECKER】设置RSS报文状态时发生错误：%s - %s" % (str(e), traceback.format_exc()))
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
                                                    is_paused=taskinfo["note"].get("is_paused"),
                                                    tag=taskinfo["note"].get("tags"),
                                                    download_dir=taskinfo["note"].get("save_path"),
                                                    category=taskinfo["note"].get("category"),
                                                    content_layout=taskinfo["note"].get("content_layout"),
                                                    upload_limit=taskinfo["note"].get("upload_limit"),
                                                    download_limit=taskinfo["note"].get("download_limit"),
                                                    ratio_limit=taskinfo["note"].get("ratio_limit"),
                                                    seeding_time_limit=taskinfo["note"].get("seeding_time_limit"))
            if ret:
                self.message.send_download_message(in_from=SearchType.RSS,
                                                   can_item=media)
                # 插入数据库
                SqlHelper.insert_rss_torrents(media)
                # 登记自定义RSS任务下载记录
                SqlHelper.insert_userrss_task_history(taskid, media.org_string, Downloader().get_type().value)
            else:
                log_error("【RSSCHECKER】添加下载任务 %s 失败：%s" % (media.get_title_string(), ret_msg or "请检查下载任务是否已存在"))
                if ret_msg:
                    self.message.send_download_fail_message(media, ret_msg)
                return False
        return True


def log_info(text):
    log.info(text, module="rsschecker")


def log_warn(text):
    log.warn(text, module="rsschecker")


def log_error(text):
    log.error(text, module="rsschecker")
