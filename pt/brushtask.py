import re
from datetime import datetime
from time import sleep

from apscheduler.schedulers.background import BackgroundScheduler

import log
from config import BRUSH_REMOVE_TORRENTS_INTERVAL
from pt.client.qbittorrent import Qbittorrent
from pt.client.transmission import Transmission
from pt.rss import Rss
from pt.torrent import Torrent
from utils.functions import singleton
from utils.sqls import get_brushtasks, get_brushtask_totalsize, add_brushtask_download_count, insert_brushtask_torrent, \
    get_brushtask_torrents, add_brushtask_upload_count
from utils.types import MediaType


@singleton
class BrushTask(object):
    _scheduler = None
    _brush_tasks = []
    _torrents_cache = []
    _qb_client = "qbittorrent"
    _tr_client = "transmission"

    def __init__(self):
        self.init_config()

    def init_config(self):
        # 移除现有任务
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            print(str(e))
        # 读取任务任务列表
        brushtasks = get_brushtasks()
        self._brush_tasks = []
        for task in brushtasks:
            self._brush_tasks.append({
                "id": task[0],
                "name": task[1],
                "site": task[3],
                "interval": task[4],
                "state": task[5],
                "downloader": task[6],
                "transfer": task[7],
                "free": task[8],
                "rss_rule": eval(task[9]),
                "remove_rule": eval(task[10]),
                "seed_size": task[11],
                "rss_url": task[17],
                "cookie": task[18]
            })
        if not self._brush_tasks:
            return
        # 启动RSS任务
        task_flag = False
        self._scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
        for task in self._brush_tasks:
            if task.get("state") == "Y" and task.get("interval") and str(task.get("interval")).isdigit():
                task_flag = True
                self._scheduler.add_job(func=self.check_task_rss,
                                        args=[task.get("id")],
                                        trigger='interval',
                                        seconds=int(task.get("interval")) * 60)
        # 启动删种任务
        if task_flag:
            self._scheduler.add_job(func=self.remove_tasks_torrents,
                                    trigger='interval',
                                    seconds=BRUSH_REMOVE_TORRENTS_INTERVAL)
            # 启动
            self._scheduler.print_jobs()
            self._scheduler.start()
            log.info("【RUN】刷流服务启动...")

    def get_brushtask_info(self, taskid):
        for task in self._brush_tasks:
            if task.get("id") == taskid:
                return task
        return None

    def check_task_rss(self, taskid):
        """
        检查RSS并添加下载，由定时服务调用
        """
        if not taskid:
            return
        taskinfo = self.get_brushtask_info(taskid)
        if not taskinfo:
            return
        # 检查是否达到保种体积
        if not self.__is_allow_new_torrent(taskid):
            return
        # 检索RSS
        task_name = taskinfo.get("name")
        site_name = taskinfo.get("site")
        rss_url = taskinfo.get("rss_url")
        log.info("【BRUSH】开始站点 %s 的刷流任务：%s..." % (site_name, task_name))
        if not rss_url:
            log.warn("【BRUSH】站点 %s 未配置RSS订阅地址，无法刷流" % site_name)
            return
        cookie = taskinfo.get("cookie")
        rss_free = taskinfo.get("free")
        if rss_free and not cookie:
            log.warn("【BRUSH】站点 %s 未配置Cookie，无法开启促销刷流" % site_name)
            return
        rss_result = Rss.parse_rssxml(rss_url)
        if len(rss_result) == 0:
            log.warn("【BRUSH】%s RSS未下载到数据" % site_name)
            return
        else:
            log.info("【BRUSH】%s RSS获取数据：%s" % (site_name, len(rss_result)))
        success_count = 0
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

                if enclosure not in self._torrents_cache:
                    self._torrents_cache.append(enclosure)
                else:
                    log.debug("【BRUSH】%s 已处理过" % torrent_name)
                    continue

                # 检查种子大小是否符合要求
                if not self.__check_rss_rule(rss_rule=taskinfo.get("rss_rule"),
                                             title=torrent_name,
                                             description=description,
                                             torrent_url=page_url,
                                             torrent_size=size,
                                             cookie=taskinfo.get("cookie")):
                    continue

                if not self.__is_allow_new_torrent(taskid, size):
                    log.warn("【BRUSH】刷流任务 %s 已达到保种体积 %sGB，不再新增下载" % (task_name, taskinfo.get("seed_size")))
                    return

                log.info("【BRUSH】%s 符合条件，开始下载..." % torrent_name)
                self.__download_torrent(client=taskinfo.get("downloader"),
                                        title=torrent_name,
                                        enclosure=enclosure,
                                        size=size,
                                        taskid=taskid,
                                        transfer=True if taskinfo.get("transfer") == 'Y' else False)
                success_count += 1
            except Exception as err:
                print(str(err))
                continue
        log.info("【BRUSH】任务 %s 本次添加了 %s 个下载" % (task_name, success_count))

    def remove_tasks_torrents(self):
        """
        根据条件检查所有任务下载完成的种子，按条件进行删除，并更新任务数据
        由定时服务调用
        """
        # 遍历所有任务
        delete_count = 0
        for taskinfo in self._brush_tasks:
            # 查询所有种子
            total_uploaded = 0
            taskid = taskinfo.get("id")
            task_torrents = get_brushtask_torrents(taskid)
            torrent_ids = [item[6] for item in task_torrents if item[6]]
            if taskinfo.get("downloader") == self._qb_client:
                torrents = Qbittorrent().get_torrents(ids=torrent_ids, status=["completed"])
                for torrent in torrents:
                    # ID
                    torrent_id = torrent.get("hash")
                    # 做种时间
                    seeding_time = torrent.get('seeding_time')
                    # 分享率
                    ratio = torrent.get("ratio")
                    # 上传量
                    uploaded = torrent.get("uploaded")
                    total_uploaded += uploaded
                    if self.__check_remove_rule(remove_rule=taskinfo.get("remove_rule"),
                                                seeding_time=seeding_time,
                                                ratio=ratio,
                                                uploaded=uploaded):
                        log.info("【BRUSH】%s 达到删种条件，删除下载任务..." % torrent.get('name'))
                        Qbittorrent().delete_torrents(delete_file=True, ids=torrent_id)
                        delete_count += 1
            else:
                torrents = Transmission().get_torrents(ids=torrent_ids, status=["seeding", "seed_pending"])
                for torrent in torrents:
                    # ID
                    torrent_id = torrent.id
                    # 做种时间
                    date_done = torrent.date_done
                    if not date_done:
                        date_done = torrent.date_added
                    seeding_time = (datetime.now().astimezone() - date_done).seconds
                    # 分享率
                    ratio = torrent.ratio
                    # 上传量
                    uploaded = torrent.total_size * torrent.ratio
                    total_uploaded += uploaded
                    if self.__check_remove_rule(remove_rule=taskinfo.get("remove_rule"),
                                                seeding_time=seeding_time,
                                                ratio=ratio,
                                                uploaded=uploaded):
                        log.info("【BRUSH】%s 达到删种条件，删除下载任务..." % torrent.get('name'))
                        Transmission().delete_torrents(delete_file=True, ids=torrent_id)
                        delete_count += 1
            # 更新上传量和删除种子数
            add_brushtask_upload_count(brush_id=taskid, size=total_uploaded)
        if delete_count:
            log.info("【BRUSH】共删除 %s 个刷流下载任务" % delete_count)

    def __is_allow_new_torrent(self, taskid, size=0):
        """
        检查是否还能添加新的下载
        """
        if not taskid:
            return False
        total_size = get_brushtask_totalsize(taskid)
        allow_size = self.get_brushtask_info(taskid).get("seed_size")
        if allow_size:
            if int(allow_size) * 1024**3 <= total_size + size:
                return False
        return True

    def __download_torrent(self, client, title, enclosure, size, taskid, transfer):
        """
        添加下载任务，更新任务数据
        :param client: 客户端
        :param title: 种子名称
        :param enclosure: 种子地址
        :param size: 种子大小
        :param taskid: 任务ID
        :param transfer: 是否要转移，为False时直接添加已整理的标签
        """
        if not client:
            return
        tag = "已整理" if not transfer else None
        download_id = None
        # 添加下载，默认用电影的分类
        if client == self._qb_client:
            torrent_tag = str(round(datetime.now().timestamp()))
            if tag:
                tag = [tag, torrent_tag]
            else:
                tag = torrent_tag
            Qbittorrent().add_torrent(content=enclosure, mtype=MediaType.MOVIE, tag=tag)
            # QB添加下载后需要时间，重试5次每次等待5秒
            for i in range(1, 6):
                sleep(5)
                download_id = Qbittorrent().get_last_add_torrentid_by_tag(tag)
                if download_id is None:
                    continue
                else:
                    Qbittorrent().remove_torrents_tag(download_id, torrent_tag)
                    break
        else:
            ret = Transmission().add_torrent(content=enclosure, mtype=MediaType.MOVIE)
            if ret:
                download_id = ret.id
                if download_id and tag:
                    Transmission().set_torrent_tag(tid=download_id, tag=tag)
        if not download_id:
            log.warn("【BRUSH】%s 获取添加的下载任务信息出错" % title)
            return
        # 插入种子数据
        insert_brushtask_torrent(brush_id=taskid,
                                 title=title,
                                 enclosure=enclosure,
                                 downloader=client,
                                 download_id=download_id,
                                 size=size)
        # 更新下载大小和次数
        add_brushtask_download_count(brush_id=taskid, size=size)

    @staticmethod
    def __check_rss_rule(rss_rule, title, description, torrent_url, torrent_size, cookie):
        """
        检查种子是否符合刷流过滤条件
        :param rss_rule: 过滤条件字典
        :param title: 种子名称
        :param description: 种子副标题
        :param torrent_url: 种子页面地址
        :param torrent_size: 种子大小
        :param cookie: Cookie
        :return: 是否命中
        """
        if not rss_rule:
            return True
        # 检查种子大小
        try:
            if rss_rule.get("size"):
                rule_sizes = rss_rule.get("size").split("#")
                if rule_sizes[0]:
                    if len(rule_sizes) > 1 and rule_sizes[1]:
                        min_max_size = rule_sizes[1].split(',')
                        min_size = min_max_size[0]
                        if len(min_max_size) > 1:
                            max_size = min_max_size[1]
                        else:
                            max_size = 0
                        if rule_sizes[0] == "gt" and int(torrent_size) < int(min_size) * 1024**3:
                            return False
                        if rule_sizes[0] == "lt" and int(torrent_size) > int(min_size) * 1024**3:
                            return False
                        if rule_sizes[0] == "bw" and not int(min_size) * 1024**3 < int(torrent_size) < int(max_size) * 1024**3:
                            return False

            # 检查包含规则
            if rss_rule.get("include"):
                if not re.search(r"%s" % rss_rule.get("include"), "%s %s" % (title, description), re.IGNORECASE):
                    return False

            # 检查排除规则
            if rss_rule.get("exclude"):
                if re.search(r"%s" % rss_rule.get("exclude"), "%s %s" % (title, description), re.IGNORECASE):
                    return False

            # 检查免费状态
            if rss_rule.get("free"):
                free_type = Torrent.check_torrent_free(torrent_url=torrent_url, cookie=cookie)
                if not free_type or rss_rule.get("free") != free_type:
                    return False
        except Exception as err:
            print(str(err))

        return True

    @staticmethod
    def __check_remove_rule(remove_rule, seeding_time, ratio, uploaded):
        """
        检查是否符合删种规则
        :param remove_rule: 删种规则
        :param seeding_time: 做种时间
        :param ratio: 分享率
        :param uploaded: 上传量
        """
        if not remove_rule:
            return False
        match_flag = False
        try:
            if remove_rule.get("time"):
                rule_times = remove_rule.get("time").split("#")
                if rule_times[0]:
                    match_flag = True
                    if len(rule_times) > 1 and rule_times[1]:
                        if int(seeding_time) < float(rule_times[1]) * 3600:
                            return False

            if remove_rule.get("ratio"):
                rule_ratios = remove_rule.get("ratio").split("#")
                if rule_ratios[0]:
                    match_flag = True
                    if len(rule_ratios) > 1 and rule_ratios[1]:
                        if float(ratio) < float(rule_ratios[1]):
                            return False

            if remove_rule.get("uploadsize"):
                rule_uploadsizes = remove_rule.get("uploadsize").split("#")
                if rule_uploadsizes[0]:
                    match_flag = True
                    if len(rule_uploadsizes) > 1 and rule_uploadsizes[1]:
                        if int(uploaded) < float(rule_uploadsizes[1]) * 1024**3:
                            return False

        except Exception as err:
            print(str(err))

        # 没开任何条件时不删种
        if not match_flag:
            return False
        # 开了条件且均命中
        return True
