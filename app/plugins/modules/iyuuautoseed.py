from datetime import datetime
from threading import Event

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.downloader import Downloader
from app.helper import IyuuHelper
from app.media.meta import MetaInfo
from app.message import Message
from app.plugins.modules._base import _IPluginModule
from app.sites import Sites
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
    module_order = 10
    # 可使用的用户级别
    user_level = 1

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
    # 退出事件
    _event = Event()

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
                            'tooltip': '开启后，自动监控下载器，对下载完成的任务根据执行周期自动辅种。',
                            'type': 'switch',
                            'id': 'enable',
                        }
                    ],
                    [
                        {
                            'title': '立即运行一次',
                            'required': "",
                            'tooltip': '打开后立即运行一次（点击此对话框的确定按钮后即会运行，周期未设置也会运行），关闭后将仅按照刮削周期运行（同时上次触发运行的任务如果在运行中也会停止）',
                            'type': 'switch',
                            'id': 'onlyonce',
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
        # 停止现有任务
        self.stop_service()

        # 启动定时任务 & 立即运行一次
        if self.get_state() or self._onlyonce:
            self.iyuuhelper = IyuuHelper(token=self._token)
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            if self._cron:
                self._scheduler.add_job(self.auto_seed, CronTrigger.from_crontab(self._cron))
            if self._onlyonce:
                self._scheduler.add_job(self.auto_seed, 'date',
                                        run_date=datetime.now(tz=pytz.timezone(Config().get_timezone())))
            if self._cron or self._onlyonce:
                self._scheduler.print_jobs()
                self._scheduler.start()

                if self._onlyonce:
                    self.info(f"辅种服务启动，立即运行一次")
                if self._cron:
                    self.info(f"辅种服务启动，周期：{self._cron}")

            # 关闭一次性开关
            if self._onlyonce:
                self._onlyonce = False
                self.update_config({
                    "enable": self._enable,
                    "onlyonce": False,
                    "cron": self._cron,
                    "token": self._token,
                    "downloaders": self._downloaders,
                    "sites": self._sites,
                    "notify": self._notify
                })

    def get_state(self):
        return True if self._enable and self._token and self._downloaders else False

    def auto_seed(self):
        """
        开始辅种
        """
        if not self.get_state():
            return
        if not self.iyuuhelper:
            return
        self.info("开始辅种任务 ...")
        # 扫描下载器辅种
        for downloader in self._downloaders:
            self.info(f"开始扫描下载器：{downloader} ...")
            # 下载器类型
            downloader_type = self.downloader.get_downloader_type(downloader_id=downloader)
            # 获取下载器中已完成的种子
            torrents = self.downloader.get_completed_torrents(downloader_id=downloader)
            if torrents:
                self.info(f"下载器：{downloader}，已完成种子数：{len(torrents)}")
            else:
                self.info(f"下载器：{downloader}，没有已完成种子")
                continue
            hash_strs = []
            for torrent in torrents:
                if self._event.is_set():
                    self.info(f"辅种服务停止")
                    return
                # 获取种子hash
                hash_str = self.__get_hash(torrent, downloader_type)
                save_path = self.__get_save_path(torrent, downloader_type)
                # FIXME 需要控制单次提交条数
                hash_strs.append({
                    "hash": hash_str,
                    "save_path": save_path
                })
            if hash_strs:
                self.__seed_torrent(hash_strs=hash_strs,
                                    downloader=downloader)
        self.info("辅种任务执行完成")

    def __seed_torrent(self, hash_strs: list, downloader):
        """
        执行一个种子的辅种
        """
        if not hash_strs:
            return
        self.info(f"下载器 {downloader} 开始查询辅种 ...")
        # 获取当前hash可辅助的站点和种子信息列表
        hashs = [hash_str.get("hash") for hash_str in hash_strs]
        # 每个Hash的保存目录
        save_paths = {}
        for hash_str in hash_strs:
            save_paths[hash_str.get("hash")] = hash_str.get("save_path")
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
            for seed in seed_torrents:
                if not seed:
                    continue
                if not isinstance(seed, dict):
                    continue
                if not seed.get("sid"):
                    continue
                if seed.get("info_hash") == current_hash:
                    self.info(f"跳过站点自身种子：{current_hash} ...")
                    continue
                # 添加任务
                self.__download_torrent(torrent=seed,
                                        downloader=downloader,
                                        save_path=save_paths.get(current_hash))
        # 针对每一个站点的种子，拼装下载链接下载种子，发送至下载器
        self.info(f"下载器 {downloader} 辅种完成")

    def __download_torrent(self, torrent, downloader, save_path):
        """
        下载种子
        """
        site_url, download_page = self.iyuuhelper.get_torrent_url(torrent.get("sid"))
        if not site_url or not download_page:
            return
        # 查询站点
        site_info = self.sites.get_sites(siteurl=site_url)
        if not site_info:
            self.warn(f"没有维护种子对应的站点：{site_url}")
            return
        if self._sites and str(site_info.get("id")) not in self._sites:
            self.info("当前站点不在选择的辅助站点范围，跳过 ...")
            return
        # 下载种子
        torrent_url = self.__get_download_url(torrent=torrent,
                                              site=site_info,
                                              base_url=download_page)
        if not torrent_url:
            return
        meta_info = MetaInfo(title="IYUU自动辅种")
        meta_info.set_torrent_info(site=site_info.get("name"),
                                   enclosure=torrent_url)
        _, download_id, retmsg = self.downloader.download(
            media_info=meta_info,
            tag=["已整理", "辅种"],
            downloader_id=downloader,
            download_dir=save_path,
            download_setting="-2"
        )
        if not download_id:
            # 下载失败
            self.warn(f"添加下载任务出错，"
                      f"错误原因：{retmsg or '下载器添加任务失败'}，"
                      f"种子链接：{torrent_url}")
            return
        else:
            # 下载成功
            self.info(f"成功添加辅种下载：站点：{site_info.get('name')}，种子链接：{torrent_url}")
            if self._notify:
                msg_title = "【IYUU自动辅种新增任务】"
                msg_text = f"站点：{site_info.get('name')}\n种子链接：{torrent_url}"
                self.message.send_custom_message(title=msg_title, text=msg_text)

    @staticmethod
    def __get_hash(torrent, dl_type):
        """
        获取种子hash
        """
        return torrent.get("hash") if dl_type == DownloaderType.QB else torrent.hashString

    @staticmethod
    def __get_save_path(torrent, dl_type):
        """
        获取种子保存路径
        """
        return torrent.get("save_path") if dl_type == DownloaderType.QB else torrent.download_dir

    def __get_download_url(self, torrent, site, base_url):
        """
        拼装种子下载链接
        """
        download_url = base_url.replace("id={}",
                                        "id={id}"
                                        ).format(
            **{"id": torrent.get("torrent_id"),
               "passkey": site.get("passkey"),
               "uid": site.get("uid")
               })
        if download_url.find("{") != -1:
            self.warn(f"当前不支持该站点的辅助任务，Url转换失败：{download_url}")
            return None
        return f"{site.get('strict_url')}/{download_url}"

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
