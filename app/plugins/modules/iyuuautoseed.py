import re
from copy import deepcopy
from datetime import datetime
from threading import Event

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from lxml import etree

from app.downloader import Downloader
from app.helper import IyuuHelper
from app.media.meta import MetaInfo
from app.message import Message
from app.plugins.modules._base import _IPluginModule
from app.sites import Sites
from app.utils import RequestUtils
from app.utils.types import DownloaderType
from config import Config


class IYUUAutoSeed(_IPluginModule):
    # 插件名称
    module_name = "IYUU自动辅种"
    # 插件描述
    module_desc = "基于IYUU官方Api实现自动辅种。"
    # 插件图标
    module_icon = "iyuu.png"
    # 主题色
    module_color = "#F3B70B"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "iyuuautoseed_"
    # 加载顺序
    module_order = 20
    # 可使用的用户级别
    user_level = 2

    # 私有属性
    _scheduler = None
    downloader = None
    iyuuhelper = None
    sites = None
    message = None
    # 限速开关
    _enable = False
    _cron = None
    _onlyonce = False
    _token = None
    _downloaders = []
    _sites = []
    _notify = False
    _nolabels = None
    _clearcache = False
    # 退出事件
    _event = Event()
    # 种子链接xpaths
    _torrent_xpaths = [
        "//form[contains(@action, 'download.php?id=')]/@action",
        "//a[contains(@href, 'download.php?hash=')]/@href",
        "//a[contains(@href, 'download.php?id=')]/@href",
        "//a[@class='index'][contains(@href, '/dl/')]/@href",
    ]
    _torrent_tags = ["已整理", "辅种"]
    # 待校全种子hash清单
    _recheck_torrents = {}
    _is_recheck_running = False
    # 辅种缓存，出错的种子不再重复辅种，可清除
    _error_caches = []
    # 辅种缓存，辅种成功的种子，可清除
    _success_caches = []
    # 辅种缓存，出错的种子不再重复辅种，且无法清除。种子被删除404等情况
    _permanent_error_caches = []
    # 辅种计数
    total = 0
    realtotal = 0
    success = 0
    exist = 0
    fail = 0
    cached = 0

    @staticmethod
    def get_fields():
        downloaders = {k: v for k, v in Downloader().get_downloader_conf_simple().items()
                       if v.get("type") in ["qbittorrent", "transmission"] and v.get("enabled")}
        sites = {site.get("id"): site for site in Sites().get_site_dict()}
        return [
            # 同一板块
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '开启自动辅种',
                            'required': "",
                            'tooltip': '开启后，自动监控下载器，对下载完成的任务根据执行周期自动辅种，辅种任务会自动暂停，校验通过且完整后才开始做种。',
                            'type': 'switch',
                            'id': 'enable',
                        }
                    ],
                    [
                        {
                            'title': 'IYUU Token',
                            'required': "required",
                            'tooltip': '登录IYUU使用的Token，用于调用IYUU官方Api',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'token',
                                    'placeholder': 'IYUUxxx',
                                }
                            ]
                        },
                        {
                            'title': '执行周期',
                            'required': "required",
                            'tooltip': '辅种任务执行的时间周期，支持5位cron表达式；应避免任务执行过于频繁',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'cron',
                                    'placeholder': '0 0 0 ? *',
                                }
                            ]
                        }
                    ],
                    [
                        {
                            'title': '不辅种标签',
                            'required': "",
                            'tooltip': '下载器中的种子有以下标签时不进行辅种，多个标签使用英文,分隔',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'nolabels',
                                    'placeholder': '使用,分隔多个标签',
                                }
                            ]
                        }
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '辅种下载器',
                'tooltip': '只有选中的下载器才会执行辅种任务',
                'content': [
                    # 同一行
                    [
                        {
                            'id': 'downloaders',
                            'type': 'form-selectgroup',
                            'content': downloaders
                        },
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '辅种站点',
                'tooltip': '只有选中的站点才会执行辅种任务，不选则默认为全选',
                'content': [
                    # 同一行
                    [
                        {
                            'id': 'sites',
                            'type': 'form-selectgroup',
                            'content': sites
                        },
                    ]
                ]
            },
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '运行时通知',
                            'required': "",
                            'tooltip': '运行辅助任务后会发送通知（需要打开自定义消息通知）',
                            'type': 'switch',
                            'id': 'notify',
                        },
                        {
                            'title': '立即运行一次',
                            'required': "",
                            'tooltip': '打开后立即运行一次（点击此对话框的确定按钮后即会运行，周期未设置也会运行），关闭后将仅按照刮削周期运行（同时上次触发运行的任务如果在运行中也会停止）',
                            'type': 'switch',
                            'id': 'onlyonce',
                        },
                        {
                            'title': '下一次运行时清除缓存',
                            'required': "",
                            'tooltip': '打开后下一次运行前会先清除辅种缓存，辅种出错的种子会重新尝试辅种，此开关仅生效一次',
                            'type': 'switch',
                            'id': 'clearcache',
                        }
                    ]
                ]
            }
        ]

    def init_config(self, config=None):
        self.downloader = Downloader()
        self.sites = Sites()
        self.message = Message()
        # 读取配置
        if config:
            self._enable = config.get("enable")
            self._onlyonce = config.get("onlyonce")
            self._cron = config.get("cron")
            self._token = config.get("token")
            self._downloaders = config.get("downloaders")
            self._sites = config.get("sites")
            self._notify = config.get("notify")
            self._nolabels = config.get("nolabels")
            self._clearcache = config.get("clearcache")
            self._permanent_error_caches = config.get("permanent_error_caches") or []
            self._error_caches = [] if self._clearcache else config.get("error_caches") or []
            self._success_caches = [] if self._clearcache else config.get("success_caches") or []
        # 停止现有任务
        self.stop_service()

        # 启动定时任务 & 立即运行一次
        if self.get_state() or self._onlyonce:
            self.iyuuhelper = IyuuHelper(token=self._token)
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            if self._cron:
                self.info(f"辅种服务启动，周期：{self._cron}")
                self._scheduler.add_job(self.auto_seed,
                                        CronTrigger.from_crontab(self._cron))
            if self._onlyonce:
                self.info(f"辅种服务启动，立即运行一次")
                self._scheduler.add_job(self.auto_seed, 'date',
                                        run_date=datetime.now(tz=pytz.timezone(Config().get_timezone())))
                # 关闭一次性开关
                self._onlyonce = False
            if self._clearcache:
                # 关闭清除缓存开关
                self._clearcache = False

            if self._clearcache or self._onlyonce:
                # 保存配置
                self.__update_config()

            if self._scheduler.get_jobs():
                # 追加种子校验服务
                self._scheduler.add_job(self.check_recheck, 'interval', minutes=3)
                # 启动服务
                self._scheduler.print_jobs()
                self._scheduler.start()

    def get_state(self):
        return True if self._enable and self._cron and self._token and self._downloaders else False

    def __update_config(self):
        self.update_config({
            "enable": self._enable,
            "onlyonce": self._onlyonce,
            "clearcache": self._clearcache,
            "cron": self._cron,
            "token": self._token,
            "downloaders": self._downloaders,
            "sites": self._sites,
            "notify": self._notify,
            "nolabels": self._nolabels,
            "success_caches": self._success_caches,
            "error_caches": self._error_caches,
            "permanent_error_caches": self._permanent_error_caches
        })

    def auto_seed(self):
        """
        开始辅种
        """
        if not self._enable or not self._token or not self._downloaders:
            self.warn("辅种服务未启用或未配置")
            return
        if not self.iyuuhelper:
            return
        self.info("开始辅种任务 ...")
        # 计数器初始化
        self.total = 0
        self.realtotal = 0
        self.success = 0
        self.exist = 0
        self.fail = 0
        self.cached = 0
        # 扫描下载器辅种
        for downloader in self._downloaders:
            self.info(f"开始扫描下载器 {downloader} ...")
            # 下载器类型
            downloader_type = self.downloader.get_downloader_type(downloader_id=downloader)
            # 获取下载器中已完成的种子
            torrents = self.downloader.get_completed_torrents(downloader_id=downloader)
            if torrents:
                self.info(f"下载器 {downloader} 已完成种子数：{len(torrents)}")
            else:
                self.info(f"下载器 {downloader} 没有已完成种子")
                continue
            hash_strs = []
            for torrent in torrents:
                if self._event.is_set():
                    self.info(f"辅种服务停止")
                    return
                # 获取种子hash
                hash_str = self.__get_hash(torrent, downloader_type)
                if hash_str in self._error_caches or hash_str in self._permanent_error_caches:
                    self.info(f"种子 {hash_str} 辅种失败且已缓存，跳过 ...")
                    continue
                save_path = self.__get_save_path(torrent, downloader_type)
                # 获取种子标签
                torrent_labels = self.__get_label(torrent, downloader_type)
                if torrent_labels and self._nolabels:
                    is_skip = False
                    for label in self._nolabels.split(','):
                        if label in torrent_labels:
                            self.info(f"种子 {hash_str} 含有不转移标签 {label}，跳过 ...")
                            is_skip = True
                            break
                    if is_skip:
                        continue
                hash_strs.append({
                    "hash": hash_str,
                    "save_path": save_path
                })
            if hash_strs:
                self.info(f"总共需要辅种的种子数：{len(hash_strs)}")
                # 分组处理，减少IYUU Api请求次数
                chunk_size = 200
                for i in range(0, len(hash_strs), chunk_size):
                    # 切片操作
                    chunk = hash_strs[i:i + chunk_size]
                    # 处理分组
                    self.__seed_torrents(hash_strs=chunk,
                                         downloader=downloader)
                # 触发校验检查
                self.check_recheck()
            else:
                self.info(f"没有需要辅种的种子")
        # 保存缓存
        self.__update_config()
        # 发送消息
        if self._notify:
            self.message.send_custom_message(
                title="【IYUU自动辅种任务完成】",
                text=f"服务器返回可辅种总数：{self.total}\n"
                     f"实际可辅种数：{self.realtotal}\n"
                     f"已存在：{self.exist}\n"
                     f"成功：{self.success}\n"
                     f"失败：{self.fail}\n"
                     f"{self.cached} 条失败记录已加入缓存"
            )
        self.info("辅种任务执行完成")

    def check_recheck(self):
        """
        定时检查下载器中种子是否校验完成，校验完成且完整的自动开始辅种
        """
        if not self._recheck_torrents:
            return
        if self._is_recheck_running:
            return
        self._is_recheck_running = True
        for downloader in self._downloaders:
            # 需要检查的种子
            recheck_torrents = self._recheck_torrents.get(downloader) or []
            if not recheck_torrents:
                continue
            self.info(f"开始检查下载器 {downloader} 的校验任务 ...")
            # 下载器类型
            downloader_type = self.downloader.get_downloader_type(downloader_id=downloader)
            # 获取下载器中的种子
            torrents = self.downloader.get_torrents(downloader_id=downloader,
                                                    ids=recheck_torrents)
            if torrents:
                can_seeding_torrents = []
                for torrent in torrents:
                    # 获取种子hash
                    hash_str = self.__get_hash(torrent, downloader_type)
                    if self.__can_seeding(torrent, downloader_type):
                        can_seeding_torrents.append(hash_str)
                if can_seeding_torrents:
                    self.info(f"共 {len(can_seeding_torrents)} 个任务校验完成，开始辅种 ...")
                    self.downloader.start_torrents(downloader_id=downloader, ids=can_seeding_torrents)
                    # 去除已经处理过的种子
                    self._recheck_torrents[downloader] = list(
                        set(recheck_torrents).difference(set(can_seeding_torrents)))
            elif torrents is None:
                self.info(f"下载器 {downloader} 查询校验任务失败，将在下次继续查询 ...")
                continue
            else:
                self.info(f"下载器 {downloader} 中没有需要检查的校验任务，清空待处理列表 ...")
                self._recheck_torrents[downloader] = []
        self._is_recheck_running = False

    def __seed_torrents(self, hash_strs: list, downloader):
        """
        执行一批种子的辅种
        """
        if not hash_strs:
            return
        self.info(f"下载器 {downloader} 开始查询辅种，数量：{len(hash_strs)} ...")
        # 下载器中的Hashs
        hashs = [item.get("hash") for item in hash_strs]
        # 每个Hash的保存目录
        save_paths = {}
        for item in hash_strs:
            save_paths[item.get("hash")] = item.get("save_path")
        # 查询可辅种数据
        seed_list, msg = self.iyuuhelper.get_seed_info(hashs)
        if not isinstance(seed_list, dict):
            self.warn(f"当前种子列表没有可辅种的站点：{msg}")
            return
        else:
            self.info(f"IYUU返回可辅种数：{len(seed_list)}")
        # 遍历
        for current_hash, seed_info in seed_list.items():
            if not seed_info:
                continue
            seed_torrents = seed_info.get("torrent")
            if not isinstance(seed_torrents, list):
                seed_torrents = [seed_torrents]

            # 本次辅种成功的种子
            success_torrents = []

            for seed in seed_torrents:
                if not seed:
                    continue
                if not isinstance(seed, dict):
                    continue
                if not seed.get("sid") or not seed.get("info_hash"):
                    continue
                if seed.get("info_hash") in hashs:
                    self.info(f"{seed.get('info_hash')} 已在下载器中，跳过 ...")
                    continue
                if seed.get("info_hash") in self._success_caches:
                    self.info(f"{seed.get('info_hash')} 已处理过辅种，跳过 ...")
                    continue
                if seed.get("info_hash") in self._error_caches or seed.get("info_hash") in self._permanent_error_caches:
                    self.info(f"种子 {seed.get('info_hash')} 辅种失败且已缓存，跳过 ...")
                    continue
                # 添加任务
                success = self.__download_torrent(seed=seed,
                                                  downloader=downloader,
                                                  save_path=save_paths.get(current_hash))
                if success:
                    success_torrents.append(seed.get("info_hash"))

            # 辅种成功的去重放入历史
            if len(success_torrents) > 0:
                self.__save_history(current_hash=current_hash,
                                    downloader=downloader,
                                    success_torrents=success_torrents)

        self.info(f"下载器 {downloader} 辅种完成")

    def __save_history(self, current_hash, downloader, success_torrents):
        """
        [
            {
                "downloader":"2",
                "torrents":[
                    "248103a801762a66c201f39df7ea325f8eda521b",
                    "bd13835c16a5865b01490962a90b3ec48889c1f0"
                ]
            },
            {
                "downloader":"3",
                "torrents":[
                    "248103a801762a66c201f39df7ea325f8eda521b",
                    "bd13835c16a5865b01490962a90b3ec48889c1f0"
                ]
            }
        ]
        """
        try:
            # 查询当前Hash的辅种历史
            seed_history = self.get_history(key=current_hash) or []

            new_history = True
            if len(seed_history) > 0:
                for history in seed_history:
                    if not history:
                        continue
                    if not isinstance(history, dict):
                        continue
                    if not history.get("downloader"):
                        continue
                    # 如果本次辅种下载器之前有过记录则继续添加
                    if int(history.get("downloader")) == downloader:
                        history_torrents = history.get("torrents") or []
                        history["torrents"] = list(set(history_torrents + success_torrents))
                        new_history = False
                        break

            # 本次辅种下载器之前没有成功记录则新增
            if new_history:
                seed_history.append({
                    "downloader": downloader,
                    "torrents": list(set(success_torrents))
                })

            # 保存历史
            self.history(key=current_hash,
                         value=seed_history)
        except Exception as e:
            print(str(e))

    def __download_torrent(self, seed, downloader, save_path):
        """
        下载种子
        torrent: {
                    "sid": 3,
                    "torrent_id": 377467,
                    "info_hash": "a444850638e7a6f6220e2efdde94099c53358159"
                }
        """
        self.total += 1
        # 获取种子站点及下载地址模板
        site_url, download_page = self.iyuuhelper.get_torrent_url(seed.get("sid"))
        if not site_url or not download_page:
            # 加入缓存
            self._error_caches.append(seed.get("info_hash"))
            self.fail += 1
            self.cached += 1
            return False
        # 查询站点
        site_info = self.sites.get_sites(siteurl=site_url)
        if not site_info:
            self.debug(f"没有维护种子对应的站点：{site_url}")
            return False
        if self._sites and str(site_info.get("id")) not in self._sites:
            self.info("当前站点不在选择的辅助站点范围，跳过 ...")
            return False
        self.realtotal += 1
        # 查询hash值是否已经在下载器中
        torrent_info = self.downloader.get_torrents(downloader_id=downloader,
                                                    ids=[seed.get("info_hash")])
        if torrent_info:
            self.debug(f"{seed.get('info_hash')} 已在下载器中，跳过 ...")
            self.exist += 1
            return False
        # 站点流控
        if self.sites.check_ratelimit(site_info.get("id")):
            self.fail += 1
            return False
        # 下载种子
        torrent_url = self.__get_download_url(seed=seed,
                                              site=site_info,
                                              base_url=download_page)
        if not torrent_url:
            # 加入失败缓存
            self._error_caches.append(seed.get("info_hash"))
            self.fail += 1
            self.cached += 1
            return False
        meta_info = MetaInfo(title="IYUU自动辅种")
        meta_info.set_torrent_info(site=site_info.get("name"),
                                   enclosure=torrent_url)
        # 辅种任务默认暂停，关闭自动管理模式
        _, download_id, retmsg = self.downloader.download(
            media_info=meta_info,
            is_paused=True,
            tag=deepcopy(self._torrent_tags),
            downloader_id=downloader,
            download_dir=save_path,
            download_setting="-2",
            is_auto=False
        )
        if not download_id:
            # 下载失败
            self.warn(f"添加下载任务出错，"
                      f"错误原因：{retmsg or '下载器添加任务失败'}，"
                      f"种子链接：{torrent_url}")
            self.fail += 1
            # 加入失败缓存
            if retmsg and ('无法打开链接' in retmsg or '触发站点流控' in retmsg):
                self._error_caches.append(seed.get("info_hash"))
            else:
                # 种子不存在的情况
                self._permanent_error_caches.append(seed.get("info_hash"))
            return False
        else:
            self.success += 1
            # 追加校验任务
            self.info(f"添加校验检查任务：{download_id} ...")
            if not self._recheck_torrents.get(downloader):
                self._recheck_torrents[downloader] = []
            self._recheck_torrents[downloader].append(download_id)
            # 下载成功
            self.info(f"成功添加辅种下载，站点：{site_info.get('name')}，种子链接：{torrent_url}")
            # TR会自动校验
            downloader_type = self.downloader.get_downloader_type(downloader_id=downloader)
            if downloader_type == DownloaderType.QB:
                # 开始校验种子
                self.downloader.recheck_torrents(downloader_id=downloader, ids=[download_id])

            # 成功也加入缓存，有一些改了路径校验不通过的，手动删除后，下一次又会辅上
            self._success_caches.append(seed.get("info_hash"))
            return True

    @staticmethod
    def __get_hash(torrent, dl_type):
        """
        获取种子hash
        """
        try:
            return torrent.get("hash") if dl_type == DownloaderType.QB else torrent.hashString
        except Exception as e:
            print(str(e))
            return ""

    @staticmethod
    def __get_label(torrent, dl_type):
        """
        获取种子标签
        """
        try:
            return torrent.get("tags") or [] if dl_type == DownloaderType.QB else torrent.labels or []
        except Exception as e:
            print(str(e))
            return []

    @staticmethod
    def __can_seeding(torrent, dl_type):
        """
        判断种子是否可以做种并处于暂停状态
        """
        try:
            return torrent.get("state") == "pausedUP" if dl_type == DownloaderType.QB \
                else (torrent.status.stopped and torrent.percent_done == 1)
        except Exception as e:
            print(str(e))
            return False

    @staticmethod
    def __get_save_path(torrent, dl_type):
        """
        获取种子保存路径
        """
        try:
            return torrent.get("save_path") if dl_type == DownloaderType.QB else torrent.download_dir
        except Exception as e:
            print(str(e))
            return ""

    def __get_download_url(self, seed, site, base_url):
        """
        拼装种子下载链接
        """

        def __is_special_site(url):
            """
            判断是否为特殊站点
            """
            if "hdchina.org" in url:
                return True
            if "hdsky.me" in url:
                return True
            if "hdcity.in" in url:
                return True
            if "totheglory.im" in url:
                return True
            return False

        try:
            if __is_special_site(site.get('strict_url')):
                # 从详情页面获取下载链接
                return self.__get_torrent_url_from_page(seed=seed, site=site)
            else:
                download_url = base_url.replace(
                    "id={}",
                    "id={id}"
                ).replace(
                    "/{}",
                    "/{id}"
                ).replace(
                    "/{torrent_key}",
                    ""
                ).format(
                    **{
                        "id": seed.get("torrent_id"),
                        "passkey": site.get("passkey") or '',
                        "uid": site.get("uid") or '',
                    }
                )
                if download_url.count("{"):
                    self.warn(f"当前不支持该站点的辅助任务，Url转换失败：{seed}")
                    return None
                download_url = re.sub(r"[&?]passkey=", "",
                                      re.sub(r"[&?]uid=", "",
                                             download_url,
                                             flags=re.IGNORECASE),
                                      flags=re.IGNORECASE)
                return f"{site.get('strict_url')}/{download_url}"
        except Exception as e:
            self.warn(f"当前不支持该站点的辅助任务，Url转换失败：{str(e)}")
            return None

    def __get_torrent_url_from_page(self, seed, site):
        """
        从详情页面获取下载链接
        """
        try:
            page_url = f"{site.get('strict_url')}/details.php?id={seed.get('torrent_id')}&hit=1"
            self.info(f"正在获取种子下载链接：{page_url} ...")
            res = RequestUtils(
                cookies=site.get("cookie"),
                headers=site.get("ua"),
                proxies=Config().get_proxies() if site.get("proxy") else None
            ).get_res(url=page_url)
            if res is not None and res.status_code in (200, 500):
                if "charset=utf-8" in res.text or "charset=UTF-8" in res.text:
                    res.encoding = "UTF-8"
                else:
                    res.encoding = res.apparent_encoding
                if not res.text:
                    self.warn(f"获取种子下载链接失败，页面内容为空：{page_url}")
                    return None
                # 使用xpath从页面中获取下载链接
                html = etree.HTML(res.text)
                for xpath in self._torrent_xpaths:
                    download_url = html.xpath(xpath)
                    if download_url:
                        download_url = download_url[0]
                        self.info(f"获取种子下载链接成功：{download_url}")
                        if not download_url.startswith("http"):
                            if download_url.startswith("/"):
                                download_url = f"{site.get('strict_url')}{download_url}"
                            else:
                                download_url = f"{site.get('strict_url')}/{download_url}"
                        return download_url
                self.warn(f"获取种子下载链接失败，未找到下载链接：{page_url}")
                return None
            else:
                return None
        except Exception as e:
            self.warn(f"获取种子下载链接失败：{str(e)}")
            return None

    def stop_service(self):
        """
        退出插件
        """
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._event.set()
                    self._scheduler.shutdown()
                    self._event.clear()
                self._scheduler = None
        except Exception as e:
            print(str(e))
