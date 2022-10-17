import re
import sys
import time
import traceback
from datetime import datetime
from time import sleep

from apscheduler.schedulers.background import BackgroundScheduler

import log
from app.helper import SqlHelper, DictHelper
from app.sites import Sites
from config import BRUSH_REMOVE_TORRENTS_INTERVAL
from app.downloader import Qbittorrent, Transmission
from app.message import Message
from app.rss import Rss
from app.utils import StringUtils
from app.utils.types import BrushDeleteType, SystemDictType
from app.utils.commons import singleton


@singleton
class BrushTask(object):
    message = None
    sites = None
    _scheduler = None
    _brush_tasks = []
    _torrents_cache = []
    _qb_client = "qbittorrent"
    _tr_client = "transmission"

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.message = Message()
        self.sites = Sites()
        # 移除现有任务
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                self._scheduler.shutdown()
                self._scheduler = None
        except Exception as e:
            print(str(e))
        # 读取任务任务列表
        brushtasks = SqlHelper.get_brushtasks()
        self._brush_tasks = []
        for task in brushtasks:
            sendmessage_switch = DictHelper.get(SystemDictType.BrushMessageSwitch.value, task[2])
            forceupload_switch = DictHelper.get(SystemDictType.BrushForceUpSwitch.value, task[2])
            site_info = self.sites.get_sites(siteid=task[2])
            self._brush_tasks.append({
                "id": task[0],
                "name": task[1],
                "site": site_info.get("name"),
                "interval": task[4],
                "state": task[5],
                "downloader": task[6],
                "transfer": task[7],
                "free": task[8],
                "rss_rule": eval(task[9]),
                "remove_rule": eval(task[10]),
                "seed_size": task[11],
                "rss_url": site_info.get("rssurl"),
                "cookie": site_info.get("cookie"),
                "sendmessage": sendmessage_switch,
                "forceupload": forceupload_switch,
                "ua": site_info.get("ua")
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
            log_info("刷流服务启动")

    def get_brushtask_info(self, taskid):
        for task in self._brush_tasks:
            if task.get("id") == int(taskid):
                return task
        return None

    def check_task_rss(self, taskid):
        """
        检查RSS并添加下载，由定时服务调用
        :param taskid: 刷流任务的ID
        """
        if not taskid:
            return
        # 任务信息
        taskinfo = self.get_brushtask_info(taskid)
        if not taskinfo:
            return
        # 检索RSS
        seed_size = taskinfo.get("seed_size")
        task_name = taskinfo.get("name")
        site_name = taskinfo.get("site")
        rss_url = taskinfo.get("rss_url")
        rss_rule = taskinfo.get("rss_rule")
        cookie = taskinfo.get("cookie")
        rss_free = taskinfo.get("free")
        ua = taskinfo.get("ua")
        downloader_id = taskinfo.get("downloader")
        log_info("【Brush】开始站点 %s 的刷流任务：%s..." % (site_name, task_name))
        if not rss_url:
            log_warn("【Brush】站点 %s 未配置RSS订阅地址，无法刷流" % site_name)
            return
        if rss_free and not cookie:
            log_warn("【Brush】站点 %s 未配置Cookie，无法开启促销刷流" % site_name)
            return
        # 下载器参数
        downloader_cfg = self.get_downloader_config(downloader_id)
        if not downloader_cfg:
            log_warn("【Brush】任务 %s 下载器不存在，无法刷流" % task_name)
            return
        # 检查是否达到保种体积
        if not self.__is_allow_new_torrent(taskid=taskid,
                                           taskname=task_name,
                                           seedsize=seed_size,
                                           downloadercfg=downloader_cfg,
                                           dlcount=rss_rule.get("dlcount")):
            return
        rss_result = Rss.parse_rssxml(rss_url)
        if len(rss_result) == 0:
            log_warn("【Brush】%s RSS未下载到数据" % site_name)
            return
        else:
            log_info("【Brush】%s RSS获取数据：%s" % (site_name, len(rss_result)))
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
                # 发布时间
                pubdate = res.get('pubdate')

                if enclosure not in self._torrents_cache:
                    self._torrents_cache.append(enclosure)
                else:
                    log.debug("【Brush】%s 已处理过" % torrent_name)
                    continue

                # 检查种子是否符合选种规则
                if not self.__check_rss_rule(rss_rule=rss_rule,
                                             title=torrent_name,
                                             description=description,
                                             torrent_url=page_url,
                                             torrent_size=size,
                                             pubdate=pubdate,
                                             cookie=cookie,
                                             ua=ua):
                    continue
                # 开始下载
                log.debug("【Brush】%s 符合条件，开始下载..." % torrent_name)
                if self.__download_torrent(downloadercfg=downloader_cfg,
                                           title=torrent_name,
                                           enclosure=enclosure,
                                           size=size,
                                           taskid=taskid,
                                           transfer=True if taskinfo.get("transfer") == 'Y' else False,
                                           sendmessage=True if taskinfo.get("sendmessage") == 'Y' else False,
                                           forceupload=True if taskinfo.get("forceupload") == 'Y' else False,
                                           upspeed=rss_rule.get("upspeed"),
                                           downspeed=rss_rule.get("downspeed"),
                                           taskname=task_name):
                    # 计数
                    success_count += 1
                    # 再判断一次
                    if not self.__is_allow_new_torrent(taskid=taskid,
                                                       taskname=task_name,
                                                       seedsize=seed_size,
                                                       dlcount=rss_rule.get("dlcount"),
                                                       downloadercfg=downloader_cfg):
                        break
            except Exception as err:
                log.console(str(err) + " - " + traceback.format_exc())
                continue
        log_info("【Brush】任务 %s 本次添加了 %s 个下载" % (task_name, success_count))

    def remove_tasks_torrents(self):
        """
        根据条件检查所有任务下载完成的种子，按条件进行删除，并更新任务数据
        由定时服务调用
        """
        # 遍历所有任务
        for taskinfo in self._brush_tasks:
            if taskinfo.get("state") != "Y":
                continue
            try:
                # 总上传量
                total_uploaded = 0
                # 总下载量
                total_downloaded = 0
                # 可以删种的种子
                delete_ids = []
                # 需要更新状态的种子
                update_torrents = []
                # 任务信息
                taskid = taskinfo.get("id")
                task_name = taskinfo.get("name")
                download_id = taskinfo.get("downloader")
                remove_rule = taskinfo.get("remove_rule")
                sendmessage = True if taskinfo.get("sendmessage") == "Y" else False
                # 当前任务种子详情
                task_torrents = SqlHelper.get_brushtask_torrents(taskid)
                torrent_ids = [item[6] for item in task_torrents if item[6]]
                if not torrent_ids:
                    continue
                # 下载器参数
                downloader_cfg = self.get_downloader_config(download_id)
                if not downloader_cfg:
                    log_warn("【Brush】任务 %s 下载器不存在" % task_name)
                    continue
                # 下载器类型
                client_type = downloader_cfg.get("type")
                # qbittorrent
                if client_type == self._qb_client:
                    downloader = Qbittorrent(user_config=downloader_cfg)
                    # 检查完成状态的
                    torrents, has_err = downloader.get_torrents(ids=torrent_ids, status=["completed"])
                    # 看看是否有错误, 有错误的话就不处理了
                    if has_err:
                        log_warn("【BRUSH】任务 %s 获取种子状态失败" % task_name)
                        continue
                    remove_torrent_ids = list(
                        set(torrent_ids).difference(set([torrent.get("hash") for torrent in torrents])))
                    for torrent in torrents:
                        # ID
                        torrent_id = torrent.get("hash")
                        # 已开始时间 秒
                        dltime = int(time.time() - torrent.get("added_on"))
                        # 已做种时间 秒
                        seeding_time = torrent.get('seeding_time') or 0
                        # 分享率
                        ratio = torrent.get("ratio") or 0
                        # 上传量
                        uploaded = torrent.get("uploaded") or 0
                        total_uploaded += uploaded
                        # 平均上传速度 Byte/s
                        avg_upspeed = int(uploaded / dltime)
                        # 下载量
                        downloaded = torrent.get("downloaded")
                        total_downloaded += downloaded
                        need_delete, delete_type = self.__check_remove_rule(remove_rule=remove_rule,
                                                                            seeding_time=seeding_time,
                                                                            ratio=ratio,
                                                                            uploaded=uploaded,
                                                                            avg_upspeed=avg_upspeed)
                        if need_delete:
                            log_info("【Brush】%s 做种达到删种条件：%s，删除任务..." % (torrent.get('name'), delete_type.value))
                            if sendmessage:
                                msg_title = "【刷流任务 {} 删除做种】".format(task_name)
                                msg_text = "删除原因：{}\n种子名称：{}".format(delete_type.value, torrent.get('name'))
                                self.message.sendmsg(title=msg_title, text=msg_text)

                            if torrent_id not in delete_ids:
                                delete_ids.append(torrent_id)
                                update_torrents.append(("%s,%s" % (uploaded, downloaded), taskid, torrent_id))
                    # 检查下载中状态的
                    torrents, has_err = downloader.get_torrents(ids=torrent_ids, status=["downloading"])
                    # 看看是否有错误, 有错误的话就不处理了
                    if has_err:
                        log_warn("【BRUSH】任务 %s 获取种子状态失败" % task_name)
                        continue
                    remove_torrent_ids = list(
                        set(remove_torrent_ids).difference(set([torrent.get("hash") for torrent in torrents])))
                    for torrent in torrents:
                        # ID
                        torrent_id = torrent.get("hash")
                        # 下载耗时 秒
                        dltime = int(time.time() - torrent.get("added_on"))
                        # 上传量 Byte
                        uploaded = torrent.get("uploaded") or 0
                        total_uploaded += uploaded
                        # 平均上传速度 Byte/s
                        avg_upspeed = int(uploaded / dltime)
                        # 下载量
                        downloaded = torrent.get("downloaded")
                        total_downloaded += downloaded
                        need_delete, delete_type = self.__check_remove_rule(remove_rule=remove_rule,
                                                                            dltime=dltime,
                                                                            avg_upspeed=avg_upspeed)
                        if need_delete:
                            log_info("【Brush】%s 达到删种条件：%s，删除下载任务..." % (torrent.get('name'), delete_type.value))
                            if sendmessage:
                                msg_title = "【刷流任务 {} 删除做种】".format(task_name)
                                msg_text = "删除原因：{}\n种子名称：{}".format(delete_type.value, torrent.get('name'))
                                self.message.sendmsg(title=msg_title, text=msg_text)

                            if torrent_id not in delete_ids:
                                delete_ids.append(torrent_id)
                                update_torrents.append(("%s,%s" % (uploaded, downloaded), taskid, torrent_id))
                # transmission
                else:
                    # 将查询的torrent_ids转为数字型
                    torrent_ids = [int(x) for x in torrent_ids if str(x).isdigit()]
                    # 检查完成状态
                    downloader = Transmission(user_config=downloader_cfg)
                    torrents, has_err = downloader.get_torrents(ids=torrent_ids, status=["seeding", "seed_pending"])
                    # 看看是否有错误, 有错误的话就不处理了
                    if has_err:
                        log_warn("【BRUSH】任务 %s 获取种子状态失败" % task_name)
                        continue
                    remove_torrent_ids = list(set(torrent_ids).difference(set([torrent.id for torrent in torrents])))
                    for torrent in torrents:
                        # ID
                        torrent_id = torrent.id
                        # 做种时间
                        date_done = torrent.date_done if torrent.date_done else torrent.date_added
                        dltime = (datetime.now().astimezone() - torrent.date_added).seconds
                        seeding_time = (datetime.now().astimezone() - date_done).seconds
                        # 下载量
                        downloaded = int(torrent.total_size * torrent.progress / 100)
                        total_downloaded += downloaded
                        # 分享率
                        ratio = torrent.ratio or 0
                        # 上传量
                        uploaded = int(downloaded * torrent.ratio)
                        total_uploaded += uploaded
                        # 平均上传速度
                        avg_upspeed = int(uploaded / dltime)
                        need_delete, delete_type = self.__check_remove_rule(remove_rule=remove_rule,
                                                                            seeding_time=seeding_time,
                                                                            ratio=ratio,
                                                                            uploaded=uploaded,
                                                                            avg_upspeed=avg_upspeed)
                        if need_delete:
                            log_info("【Brush】%s 做种达到删种条件：%s，删除任务..." % (torrent.name, delete_type.value))
                            if sendmessage:
                                msg_title = "【刷流任务 {} 删除做种】".format(task_name)
                                msg_text = "删除原因：{}\n种子名称：{}".format(delete_type.value, torrent.name)
                                self.message.sendmsg(title=msg_title, text=msg_text)

                            if torrent_id not in delete_ids:
                                delete_ids.append(torrent_id)
                                update_torrents.append(("%s,%s" % (uploaded, downloaded), taskid, torrent_id))
                    # 检查下载状态
                    torrents, has_err = downloader.get_torrents(ids=torrent_ids,
                                                                status=["downloading", "download_pending", "stopped"])
                    # 看看是否有错误, 有错误的话就不处理了
                    if has_err:
                        log_warn("【BRUSH】任务 %s 获取种子状态失败" % task_name)
                        continue
                    remove_torrent_ids = list(
                        set(remove_torrent_ids).difference(set([torrent.id for torrent in torrents])))
                    for torrent in torrents:
                        # ID
                        torrent_id = torrent.id
                        # 下载耗时
                        dltime = (datetime.now().astimezone() - torrent.date_added).seconds
                        # 下载量
                        downloaded = int(torrent.total_size * torrent.progress / 100)
                        total_downloaded += downloaded
                        # 上传量
                        uploaded = int(downloaded * torrent.ratio)
                        total_uploaded += uploaded
                        # 平均上传速度
                        avg_upspeed = int(uploaded / dltime)
                        need_delete, delete_type = self.__check_remove_rule(remove_rule=remove_rule,
                                                                            dltime=dltime,
                                                                            avg_upspeed=avg_upspeed)
                        if need_delete:
                            log_info("【Brush】%s 达到删种条件：%s，删除下载任务..." % (torrent.name, delete_type.value))
                            if sendmessage:
                                msg_title = "【刷流任务 {} 删除做种】".format(task_name)
                                msg_text = "删除原因：{}\n种子名称：{}".format(delete_type.value, torrent.name)
                                self.message.sendmsg(title=msg_title, text=msg_text)

                            if torrent_id not in delete_ids:
                                delete_ids.append(torrent_id)
                                update_torrents.append(("%s,%s" % (uploaded, downloaded), taskid, torrent_id))
                # 手工删除的种子，清除对应记录
                if remove_torrent_ids:
                    log_info("【Brush】任务 %s 的这些下载任务在下载器中不存在，将删除任务记录：%s" % (task_name, remove_torrent_ids))
                    for remove_torrent_id in remove_torrent_ids:
                        SqlHelper.delete_brushtask_torrent(taskid, remove_torrent_id)
                # 更新种子状态为已删除
                SqlHelper.update_brushtask_torrent_state(update_torrents)
                # 删除下载器种子
                if delete_ids:
                    downloader.delete_torrents(delete_file=True, ids=delete_ids)
                    log_info("【Brush】任务 %s 共删除 %s 个刷流下载任务" % (task_name, len(delete_ids)))
                else:
                    log_info("【Brush】任务 %s 本次检查未删除下载任务" % task_name)
                # 更新上传下载量和删除种子数
                SqlHelper.add_brushtask_upload_count(brush_id=taskid,
                                                     upload_size=total_uploaded,
                                                     download_size=total_downloaded,
                                                     remove_count=len(delete_ids) + len(remove_torrent_ids))
            except Exception as e:
                log.console(str(e) + " - " + traceback.format_exc())

    def __is_allow_new_torrent(self, taskid, taskname, downloadercfg, seedsize, dlcount):
        """
        检查是否还能添加新的下载
        """
        if not taskid:
            return False
        # 判断大小
        total_size = SqlHelper.get_brushtask_totalsize(taskid)
        if seedsize:
            if float(seedsize) * 1024 ** 3 <= int(total_size):
                log_warn("【Brush】刷流任务 %s 当前保种体积 %sGB，不再新增下载"
                         % (taskname, round(int(total_size) / 1024 / 1024 / 1024, 1)))
                return False
        # 检查正在下载的任务数
        if dlcount:
            downloading_count = self.__get_downloading_count(downloadercfg)
            if downloading_count is None:
                log_error("【Brush】任务 %s 下载器 %s 无法连接" % (taskname, downloadercfg.get("name")))
                return False
            if int(downloading_count) >= int(dlcount):
                log_warn("【Brush】下载器 %s 正在下载任务数：%s，超过设定上限，暂不添加下载" % (downloadercfg.get("name"), downloading_count))
                return False
        return True

    @staticmethod
    def get_downloader_config(dlid):
        """
        获取下载器的参数
        """
        if not dlid:
            return {}
        downloader_info = SqlHelper.get_user_downloaders(dlid)
        if downloader_info:
            userconfig = {"id": downloader_info[0][0],
                          "name": downloader_info[0][1],
                          "type": downloader_info[0][2],
                          "host": downloader_info[0][3],
                          "port": downloader_info[0][4],
                          "username": downloader_info[0][5],
                          "password": downloader_info[0][6],
                          "save_dir": downloader_info[0][7]}
            return userconfig
        return {}

    def __get_downloading_count(self, downloadercfg):
        """
        查询当前正在下载的任务数
        """
        if not downloadercfg:
            return 0
        if downloadercfg.get("type") == self._qb_client:
            downloader = Qbittorrent(user_config=downloadercfg)
            if not downloader.qbc:
                return None
            dlitems = downloader.get_downloading_torrents()
            if dlitems is not None:
                return int(len(dlitems))
        else:
            downloader = Transmission(user_config=downloadercfg)
            if not downloader.trc:
                return None
            dlitems = downloader.get_downloading_torrents()
            if dlitems is not None:
                return int(len(dlitems))
        return None

    def __download_torrent(self,
                           downloadercfg,
                           title,
                           enclosure,
                           size,
                           taskid,
                           transfer,
                           sendmessage,
                           forceupload,
                           upspeed,
                           downspeed,
                           taskname):
        """
        添加下载任务，更新任务数据
        :param downloadercfg: 下载器的所有参数
        :param title: 种子名称
        :param enclosure: 种子地址
        :param size: 种子大小
        :param taskid: 任务ID
        :param transfer: 是否要转移，为False时直接添加已整理的标签
        :param sendmessage: 是否需要消息推送
        :param forceupload: 是否需要将添加的刷流任务设置为强制做种(仅针对qBittorrent)
        :param upspeed: 上传限速
        :param downspeed: 下载限速
        :param taskname: 任务名称
        """
        if not downloadercfg:
            return False
        # 标签
        tag = "已整理" if not transfer else None
        # 下载任务ID
        download_id = None
        # 添加下载
        if downloadercfg.get("type") == self._qb_client:
            # 初始化下载器
            downloader = Qbittorrent(user_config=downloadercfg)
            if not downloader.qbc:
                log_error("【Brush】任务 %s 下载器 %s 无法连接" % (taskname, downloadercfg.get("name")))
                return False
            torrent_tag = "NT" + StringUtils.generate_random_str(5)
            if tag:
                tag = [tag, torrent_tag]
            else:
                tag = torrent_tag
            ret = downloader.add_torrent(content=enclosure,
                                         tag=tag,
                                         download_dir=downloadercfg.get("save_dir"),
                                         upload_limit=upspeed,
                                         download_limit=downspeed)
            if ret:
                # QB添加下载后需要时间，重试5次每次等待5秒
                for i in range(1, 6):
                    sleep(5)
                    download_id = downloader.get_last_add_torrentid_by_tag(tag)
                    if download_id is None:
                        continue
                    else:
                        downloader.remove_torrents_tag(download_id, torrent_tag)
                        downloader.start_torrents(download_id)
                        # 强制做种
                        if forceupload:
                            downloader.torrents_set_force_start(download_id)
                        break
        else:
            # 初始化下载器
            downloader = Transmission(user_config=downloadercfg)
            if not downloader.trc:
                log_error("【Brush】任务 %s 下载器 %s 无法连接" % (taskname, downloadercfg.get("name")))
                return False
            ret = downloader.add_torrent(content=enclosure,
                                         download_dir=downloadercfg.get("save_dir"),
                                         upload_limit=upspeed,
                                         download_limit=downspeed
                                         )
            if ret:
                download_id = ret.id
                # 设置标签
                if download_id and tag:
                    downloader.set_torrent_tag(tid=download_id, tag=tag)
        if not download_id:
            log_warn("【Brush】%s 添加下载任务出错，可能原因：Cookie过期/任务已存在/触发了站点首次种子下载" % title)
            return False
        else:
            log_info("【Brush】成功添加下载：%s" % title)
            if sendmessage:
                msg_title = "【刷流任务 {} 新增下载】".format(taskname)
                msg_text = "种子名称：{}\n种子大小：{}".format(title, StringUtils.str_filesize(size))
                self.message.sendmsg(title=msg_title, text=msg_text)
        # 插入种子数据
        if SqlHelper.insert_brushtask_torrent(brush_id=taskid,
                                              title=title,
                                              enclosure=enclosure,
                                              downloader=downloadercfg.get("id"),
                                              download_id=download_id,
                                              size=size):
            # 更新下载次数
            SqlHelper.add_brushtask_download_count(brush_id=taskid)
        else:
            log_info("【Brush】%s 已下载过" % title)

        return True

    def __check_rss_rule(self,
                         rss_rule,
                         title,
                         description,
                         torrent_url,
                         torrent_size,
                         pubdate,
                         cookie,
                         ua):
        """
        检查种子是否符合刷流过滤条件
        :param rss_rule: 过滤条件字典
        :param title: 种子名称
        :param description: 种子副标题
        :param torrent_url: 种子页面地址
        :param torrent_size: 种子大小
        :param pubdate: 发布时间
        :param cookie: Cookie
        :param ua: User-Agent
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
                        if rule_sizes[0] == "gt" and float(torrent_size) < float(min_size) * 1024 ** 3:
                            return False
                        if rule_sizes[0] == "lt" and float(torrent_size) > float(min_size) * 1024 ** 3:
                            return False
                        if rule_sizes[0] == "bw" and not float(min_size) * 1024 ** 3 < float(torrent_size) < float(
                                max_size) * 1024 ** 3:
                            return False

            # 检查包含规则
            if rss_rule.get("include"):
                if not re.search(r"%s" % rss_rule.get("include"), "%s %s" % (title, description), re.IGNORECASE):
                    return False

            # 检查排除规则
            if rss_rule.get("exclude"):
                if re.search(r"%s" % rss_rule.get("exclude"), "%s %s" % (title, description), re.IGNORECASE):
                    return False

            attr_type = self.sites.check_torrent_attr(torrent_url=torrent_url, cookie=cookie, ua=ua)

            log.debug("【Brush】%s 解析详情, %s" % (title, attr_type))

            # 检查免费状态
            if rss_rule.get("free") == "FREE":
                if not attr_type.is_free():
                    return False
            elif rss_rule.get("free") == "2XFREE":
                if not attr_type.is_free2x():
                    return False

            # 检查HR状态
            if rss_rule.get("hr"):
                if attr_type.is_hr():
                    return False

            # 检查做种人数
            if rss_rule.get("peercount"):
                # 兼容旧版本
                peercount_str = rss_rule.get("peercount")
                if not peercount_str:
                    peercount_str = "#"
                elif "#" not in peercount_str:
                    peercount_str = "lt#" + peercount_str
                else:
                    pass
                peer_counts = peercount_str.split("#")
                if len(peer_counts) >= 2 and peer_counts[1]:
                    min_max_count = peer_counts[1].split(',')
                    min_count = int(min_max_count[0])
                    if len(min_max_count) > 1:
                        max_count = int(min_max_count[1])
                    else:
                        max_count = sys.maxsize
                    if peer_counts[0] == "gt" and attr_type.peer_count <= min_count:
                        log.debug("【Brush】%s `判断做种数, 判断条件: peer_count:%d %s threshold:%d" % (
                            title, attr_type.peer_count, peer_counts[0], min_count))
                        return False
                    if peer_counts[0] == "lt" and attr_type.peer_count >= min_count:
                        log.debug("【Brush】%s `判断做种数, 判断条件: peer_count:%d %s threshold:%d" % (
                            title, attr_type.peer_count, peer_counts[0], min_count))
                        return False
                    if peer_counts[0] == "bw" and not (min_count <= attr_type.peer_count <= max_count):
                        log.debug("【Brush】%s `判断做种数, 判断条件: left:%d %s peer_count:%d %s right:%d" % (
                            title, min_count, peer_counts[0], attr_type.peer_count, peer_counts[0], max_count))
                        return False

            # 检查发布时间
            if rss_rule.get("pubdate") and pubdate:
                rule_pubdates = rss_rule.get("pubdate").split("#")
                if len(rule_pubdates) >= 2 and rule_pubdates[1]:
                    if (datetime.now() - pubdate).seconds / 3600 > int(rule_pubdates[1]):
                        return False

        except Exception as err:
            log_error(str(err) + " - " + traceback.format_exc())

        return True

    @staticmethod
    def __check_remove_rule(remove_rule, seeding_time=None, ratio=None, uploaded=None, dltime=None, avg_upspeed=None):
        """
        检查是否符合删种规则
        :param remove_rule: 删种规则
        :param seeding_time: 做种时间
        :param ratio: 分享率
        :param uploaded: 上传量
        :param dltime: 下载耗时
        :param avg_upspeed: 上传平均速度
        """
        if not remove_rule:
            return False
        try:
            if remove_rule.get("time") and seeding_time:
                rule_times = remove_rule.get("time").split("#")
                if rule_times[0]:
                    if len(rule_times) > 1 and rule_times[1]:
                        if int(seeding_time) > float(rule_times[1]) * 3600:
                            return True, BrushDeleteType.SEEDTIME
            if remove_rule.get("ratio") and ratio:
                rule_ratios = remove_rule.get("ratio").split("#")
                if rule_ratios[0]:
                    if len(rule_ratios) > 1 and rule_ratios[1]:
                        if float(ratio) > float(rule_ratios[1]):
                            return True, BrushDeleteType.RATIO
            if remove_rule.get("uploadsize") and uploaded:
                rule_uploadsizes = remove_rule.get("uploadsize").split("#")
                if rule_uploadsizes[0]:
                    if len(rule_uploadsizes) > 1 and rule_uploadsizes[1]:
                        if int(uploaded) > float(rule_uploadsizes[1]) * 1024 ** 3:
                            return True, BrushDeleteType.UPLOADSIZE
            if remove_rule.get("dltime") and dltime:
                rule_times = remove_rule.get("dltime").split("#")
                if rule_times[0]:
                    if len(rule_times) > 1 and rule_times[1]:
                        if int(dltime) > float(rule_times[1]) * 3600:
                            return True, BrushDeleteType.DLTIME
            if remove_rule.get("avg_upspeed") and avg_upspeed:
                rule_avg_upspeeds = remove_rule.get("avg_upspeed").split("#")
                if rule_avg_upspeeds[0]:
                    if len(rule_avg_upspeeds) > 1 and rule_avg_upspeeds[1]:
                        if int(avg_upspeed) < float(rule_avg_upspeeds[1]) * 1024:
                            return True, BrushDeleteType.AVGUPSPEED
        except Exception as err:
            log.console(str(err) + " - " + traceback.format_exc())
        return False, BrushDeleteType.NOTDELETE


def log_info(text):
    log.info(text, module="brushtask")


def log_warn(text):
    log.warn(text, module="brushtask")


def log_error(text):
    log.error(text, module="brushtask")
