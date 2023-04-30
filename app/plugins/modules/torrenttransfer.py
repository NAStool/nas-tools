import os.path
from copy import deepcopy
from datetime import datetime
from threading import Event

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from bencode import bdecode, bencode

from app.downloader import Downloader
from app.media.meta import MetaInfo
from app.plugins.modules._base import _IPluginModule
from app.utils import Torrent
from app.utils.types import DownloaderType
from config import Config


class TorrentTransfer(_IPluginModule):
    # 插件名称
    module_name = "自动转移做种"
    # 插件描述
    module_desc = "定期转移下载器中的做种任务到另一个下载器。"
    # 插件图标
    module_icon = "torrenttransfer.jpg"
    # 主题色
    module_color = "#272636"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "torrenttransfer_"
    # 加载顺序
    module_order = 20
    # 可使用的用户级别
    user_level = 2

    # 私有属性
    _scheduler = None
    downloader = None
    sites = None
    # 限速开关
    _enable = False
    _cron = None
    _onlyonce = False
    _fromdownloader = None
    _todownloader = None
    _frompath = None
    _topath = None
    _notify = False
    _nolabels = None
    _nopaths = None
    _deletesource = False
    _fromtorrentpath = None
    _autostart = False
    # 退出事件
    _event = Event()
    # 待检查种子清单
    _recheck_torrents = {}
    _is_recheck_running = False
    # 任务标签
    _torrent_tags = ["已整理", "转移做种"]

    @staticmethod
    def get_fields():
        downloaders = {k: v for k, v in Downloader().get_downloader_conf_simple().items()
                       if v.get("type") in ["qbittorrent", "transmission"] and v.get("enabled")}
        return [
            # 同一板块
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '开启自动转移做种',
                            'required': "",
                            'tooltip': '开启后，定期将源下载器中已完成的种子任务迁移至目的下载器，任务转移后会自动暂停，校验通过且完整后才开始做种。',
                            'type': 'switch',
                            'id': 'enable',
                        }
                    ],
                    [
                        {
                            'title': '执行周期',
                            'required': "required",
                            'tooltip': '设置移转做种任务执行的时间周期，支持5位cron表达式；应避免任务执行过于频繁',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'cron',
                                    'placeholder': '0 0 0 ? *',
                                }
                            ]
                        },
                        {
                            'title': '不转移种子标签',
                            'required': "",
                            'tooltip': '下载器中的种子有以下标签时不进行移转做种，多个标签使用英文,分隔',
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
                'summary': '源下载器',
                'tooltip': '只有选中的下载器才会执行转移任务，只能选择一个',
                'content': [
                    # 同一行
                    [
                        {
                            'id': 'fromdownloader',
                            'type': 'form-selectgroup',
                            'radio': True,
                            'onclick': 'torrenttransfer_check(this);',
                            'content': downloaders
                        },
                    ],
                    [
                        {
                            'title': '种子文件路径',
                            'required': "required",
                            'tooltip': '源下载器保存种子文件的路径，需要是NAStool可访问的路径，QB一般为BT_backup，TR一般为torrents',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'fromtorrentpath',
                                    'placeholder': 'xxx/BT_backup、xxx/torrents',
                                }
                            ]
                        },
                        {
                            'title': '数据文件根路径',
                            'required': "required",
                            'tooltip': '源下载器中的种子数据文件保存根目录路径，必须是下载器能访问的路径，用于转移时转换种子数据文件路径使用；留空不进行路径转换，使用种子的数据文件保存目录',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'frompath',
                                    'placeholder': '根路径，留空不进行路径转换',
                                }
                            ]
                        }
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '目的下载器',
                'tooltip': '将做种任务转移到这个下载器，只能选择一个',
                'content': [
                    # 同一行
                    [
                        {
                            'id': 'todownloader',
                            'type': 'form-selectgroup',
                            'radio': True,
                            'onclick': 'torrenttransfer_check(this);',
                            'content': downloaders
                        },
                    ],
                    [
                        {
                            'title': '数据文件根路径',
                            'required': "required",
                            'tooltip': '目的下载器的种子数据文件保存目录根路径，必须是下载器能访问的路径，将会使用该路径替换源下载器中种子数据文件保存路径中的源目录根路径，替换后的新路径做为目的下载器种子数据文件的保存路径，需要准确填写，否则可能导致移转做种后找不到数据文件无法做种；留空不进行路径转换，使用种子的数据文件保存路径',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'topath',
                                    'placeholder': '根路径，留空不进行路径转换',
                                }
                            ]
                        }
                    ]
                ]
            },
            {
                'type': 'div',
                'content': [
                    [
                        {
                            'title': '不转移数据文件目录',
                            'required': "",
                            'tooltip': '以下数据文件目录的任务不进行转移，指下载器可访问的目录，每一行一个目录',
                            'type': 'textarea',
                            'content': {
                                'id': 'nopaths',
                                'placeholder': '每一行一个目录',
                                'rows': 3
                            }
                        }
                    ]
                ]
            },
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '校验完成后自动开始',
                            'required': "",
                            'tooltip': '自动开始目的下载器中校验完成且100%完整的种子，校验不完整的不会处理',
                            'type': 'switch',
                            'default': True,
                            'id': 'autostart',
                        },
                        {
                            'title': '删除源种子',
                            'required': "",
                            'tooltip': '转移成功后删除源下载器中的种子，首次运行请不要打开，避免种子丢失',
                            'type': 'switch',
                            'id': 'deletesource',
                        }

                    ],
                    [
                        {
                            'title': '运行时通知',
                            'required': "",
                            'tooltip': '运行任务后会发送通知（需要打开插件消息通知）',
                            'type': 'switch',
                            'id': 'notify',
                        },
                        {
                            'title': '立即运行一次',
                            'required': "",
                            'tooltip': '打开后立即运行一次（点击此对话框的确定按钮后即会运行，周期未设置也会运行），关闭后将仅按照周期运行（同时上次触发运行的任务如果在运行中也会停止）',
                            'type': 'switch',
                            'id': 'onlyonce',
                        }
                    ]
                ]
            }
        ]

    @staticmethod
    def get_script():
        """
        返回插件额外的JS代码
        """
        return """
        function torrenttransfer_check(obj) {
            let val = $(obj).val();
            let name = $(obj).attr("name") === "torrenttransfer_fromdownloader" ? "torrenttransfer_todownloader" : "torrenttransfer_fromdownloader";
            if ($(obj).prop("checked")) {
                $(`input[name^=${name}][type=checkbox]`).each(function () {
                    if ($(this).val() === val) {
                        $(this).prop('checked',false).prop('disabled', true);
                    } else {
                        $(this).prop('disabled', false);
                    }
                });
            } else {
                $(`input[name^=${name}][type=checkbox]`).each(function () {
                    if ($(this).val() === val) {
                        $(this).prop('disabled', false);
                    }
                });
            }
        }
        """

    def init_config(self, config=None):
        self.downloader = Downloader()
        # 读取配置
        if config:
            self._enable = config.get("enable")
            self._onlyonce = config.get("onlyonce")
            self._cron = config.get("cron")
            self._notify = config.get("notify")
            self._nolabels = config.get("nolabels")
            self._frompath = config.get("frompath")
            self._topath = config.get("topath")
            self._fromdownloader = config.get("fromdownloader")
            self._todownloader = config.get("todownloader")
            self._deletesource = config.get("deletesource")
            self._fromtorrentpath = config.get("fromtorrentpath")
            self._nopaths = config.get("nopaths")
            self._autostart = config.get("autostart")

        # 停止现有任务
        self.stop_service()

        # 启动定时任务 & 立即运行一次
        if self.get_state() or self._onlyonce:
            # 检查配置
            if self._fromtorrentpath and not os.path.exists(self._fromtorrentpath):
                self.error(f"源下载器种子文件保存路径不存在：{self._fromtorrentpath}")
                return
            if isinstance(self._fromdownloader, list) and len(self._fromdownloader) > 1:
                self.error(f"源下载器只能选择一个")
                return
            if isinstance(self._todownloader, list) and len(self._todownloader) > 1:
                self.error(f"目的下载器只能选择一个")
                return
            if self._fromdownloader == self._todownloader:
                self.error(f"源下载器和目的下载器不能相同")
                return
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            if self._cron:
                self.info(f"移转做种服务启动，周期：{self._cron}")
                self._scheduler.add_job(self.transfer,
                                        CronTrigger.from_crontab(self._cron))
            if self._onlyonce:
                self.info(f"移转做种服务启动，立即运行一次")
                self._scheduler.add_job(self.transfer, 'date',
                                        run_date=datetime.now(tz=pytz.timezone(Config().get_timezone())))
                # 关闭一次性开关
                self._onlyonce = False
                self.update_config({
                    "enable": self._enable,
                    "onlyonce": self._onlyonce,
                    "cron": self._cron,
                    "notify": self._notify,
                    "nolabels": self._nolabels,
                    "frompath": self._frompath,
                    "topath": self._topath,
                    "fromdownloader": self._fromdownloader,
                    "todownloader": self._todownloader,
                    "deletesource": self._deletesource,
                    "fromtorrentpath": self._fromtorrentpath,
                    "nopaths": self._nopaths,
                    "autostart": self._autostart
                })
            if self._scheduler.get_jobs():
                if self._autostart:
                    # 追加种子校验服务
                    self._scheduler.add_job(self.check_recheck, 'interval', minutes=3)
                # 启动服务
                self._scheduler.print_jobs()
                self._scheduler.start()

    def get_state(self):
        return True if self._enable \
                       and self._cron \
                       and self._fromdownloader \
                       and self._todownloader \
                       and self._fromtorrentpath else False

    def transfer(self):
        """
        开始移转做种
        """
        if not self._enable \
                or not self._fromdownloader \
                or not self._todownloader \
                or not self._fromtorrentpath:
            self.warn("移转做种服务未启用或未配置")
            return
        self.info("开始移转做种任务 ...")
        # 源下载器
        downloader = self._fromdownloader[0]
        # 源下载器类型
        downloader_type = self.downloader.get_downloader_type(downloader_id=downloader)
        # 目的下载器
        todownloader = self._todownloader[0]
        # 目的下载器类型
        to_downloader_type = self.downloader.get_downloader_type(downloader_id=todownloader)
        # 获取下载器中已完成的种子
        torrents = self.downloader.get_completed_torrents(downloader_id=downloader)
        if torrents:
            self.info(f"下载器 {downloader} 已完成种子数：{len(torrents)}")
        else:
            self.info(f"下载器 {downloader} 没有已完成种子")
            return
        # 过滤种子，记录保存目录
        hash_strs = []
        for torrent in torrents:
            if self._event.is_set():
                self.info(f"移转服务停止")
                return
            # 获取种子hash
            hash_str = self.__get_hash(torrent, downloader_type)
            # 获取保存路径
            save_path = self.__get_save_path(torrent, downloader_type)
            if self._nopaths and save_path:
                # 过滤不需要移转的路径
                nopath_skip = False
                for nopath in self._nopaths.split('\n'):
                    if os.path.normpath(save_path).startswith(os.path.normpath(nopath)):
                        self.info(f"种子 {hash_str} 保存路径 {save_path} 不需要移转，跳过 ...")
                        nopath_skip = True
                        break
                if nopath_skip:
                    continue
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
        # 开始转移任务
        if hash_strs:
            self.info(f"需要移转的种子数：{len(hash_strs)}")
            # 记数
            total = len(hash_strs)
            success = 0
            fail = 0
            for hash_item in hash_strs:
                # 检查种子文件是否存在
                torrent_file = os.path.join(self._fromtorrentpath,
                                            f"{hash_item.get('hash')}.torrent")
                if not os.path.exists(torrent_file):
                    self.error(f"种子文件不存在：{torrent_file}")
                    fail += 1
                    continue
                # 查询hash值是否已经在目的下载器中
                torrent_info = self.downloader.get_torrents(downloader_id=todownloader,
                                                            ids=[hash_item.get('hash')])
                if torrent_info:
                    self.debug(f"{hash_item.get('hash')} 已在目的下载器中，跳过 ...")
                    continue
                # 转换保存路径
                download_dir = self.__convert_save_path(hash_item.get('save_path'),
                                                        self._frompath,
                                                        self._topath)
                if not download_dir:
                    self.error(f"转换保存路径失败：{hash_item.get('save_path')}")
                    fail += 1
                    continue

                # 如果是QB检查是否有Tracker，没有的话补充解析
                if downloader_type == DownloaderType.QB:
                    # 读取种子内容、解析种子文件
                    content, _, _, retmsg = Torrent().read_torrent_content(torrent_file)
                    if not content:
                        self.error(f"读取种子文件失败：{retmsg}")
                        fail += 1
                        continue
                    # 读取trackers
                    try:
                        torrent_main = bdecode(content)
                        main_announce = torrent_main.get('announce')
                    except Exception as err:
                        self.error(f"解析种子文件 {torrent_file} 失败：{err}")
                        fail += 1
                        continue

                    if not main_announce:
                        self.info(f"{hash_item.get('hash')} 未发现tracker信息，尝试补充tracker信息...")
                        # 读取fastresume文件
                        fastresume_file = os.path.join(self._fromtorrentpath,
                                                       f"{hash_item.get('hash')}.fastresume")
                        if not os.path.exists(fastresume_file):
                            self.error(f"fastresume文件不存在：{fastresume_file}")
                            fail += 1
                            continue
                        # 尝试补充trackers
                        try:
                            with open(fastresume_file, 'rb') as f:
                                fastresume = f.read()
                            # 解析fastresume文件
                            torrent_fastresume = bdecode(fastresume)
                            # 读取trackers
                            fastresume_trackers = torrent_fastresume.get('trackers')
                            if isinstance(fastresume_trackers, list) \
                                    and len(fastresume_trackers) > 0 \
                                    and fastresume_trackers[0]:
                                # 重新赋值
                                torrent_main['announce'] = fastresume_trackers[0][0]
                                # 替换种子文件路径
                                torrent_file = os.path.join(Config().get_temp_path(),
                                                            f"{hash_item.get('hash')}.torrent")
                                # 编码并保存到临时文件
                                with open(torrent_file, 'wb') as f:
                                    f.write(bencode(torrent_main))
                        except Exception as err:
                            self.error(f"解析fastresume文件 {fastresume_file} 失败：{err}")
                            fail += 1
                            continue

                # 发送到另一个下载器中下载：默认暂停、传输下载路径、关闭自动管理模式
                _, download_id, retmsg = self.downloader.download(
                    media_info=MetaInfo("自动转移做种"),
                    torrent_file=torrent_file,
                    is_paused=True,
                    tag=deepcopy(self._torrent_tags),
                    downloader_id=todownloader,
                    download_dir=download_dir,
                    download_setting="-2",
                )
                if not download_id:
                    # 下载失败
                    self.warn(f"添加转移任务出错，"
                              f"错误原因：{retmsg or '下载器添加任务失败'}，"
                              f"种子文件：{torrent_file}")
                    fail += 1
                    continue
                else:
                    # 追加校验任务
                    self.info(f"添加校验检查任务：{download_id} ...")
                    if not self._recheck_torrents.get(todownloader):
                        self._recheck_torrents[todownloader] = []
                    self._recheck_torrents[todownloader].append(download_id)
                    # 下载成功
                    self.info(f"成功添加转移做种任务，种子文件：{torrent_file}")
                    # TR会自动校验
                    if to_downloader_type == DownloaderType.QB:
                        # 开始校验种子
                        self.downloader.recheck_torrents(downloader_id=todownloader, ids=[download_id])
                    # 删除源种子，不能删除文件！
                    if self._deletesource:
                        self.downloader.delete_torrents(downloader_id=downloader,
                                                        ids=[download_id],
                                                        delete_file=False)
                    success += 1
                    # 插入转种记录
                    history_key = "%s-%s" % (int(self._fromdownloader[0]), hash_item.get('hash'))
                    self.history(key=history_key,
                                 value={
                                     "to_download": int(self._todownloader[0]),
                                     "to_download_id": download_id,
                                     "delete_source": self._deletesource,
                                 })
            # 触发校验任务
            if success > 0 and self._autostart:
                self.check_recheck()
            # 发送通知
            if self._notify:
                self.send_message(
                    title="【移转做种任务执行完成】",
                    text=f"总数：{total}，成功：{success}，失败：{fail}"
                )
        else:
            self.info(f"没有需要移转的种子")
        self.info("移转做种任务执行完成")

    def check_recheck(self):
        """
        定时检查下载器中种子是否校验完成，校验完成且完整的自动开始辅种
        """
        if not self._recheck_torrents:
            return
        if not self._todownloader:
            return
        if self._is_recheck_running:
            return
        downloader = self._todownloader[0]
        # 需要检查的种子
        recheck_torrents = self._recheck_torrents.get(downloader, [])
        if not recheck_torrents:
            return
        self.info(f"开始检查下载器 {downloader} 的校验任务 ...")
        self._is_recheck_running = True
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
        else:
            self.info(f"下载器 {downloader} 中没有需要检查的校验任务，清空待处理列表 ...")
            self._recheck_torrents[downloader] = []
        self._is_recheck_running = False

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
    def __get_save_path(torrent, dl_type):
        """
        获取种子保存路径
        """
        try:
            return torrent.get("save_path") if dl_type == DownloaderType.QB else torrent.download_dir
        except Exception as e:
            print(str(e))
            return ""

    @staticmethod
    def __can_seeding(torrent, dl_type):
        """
        判断种子是否可以做种并处于暂停状态
        """
        try:
            return torrent.get("state") == "pausedUP" and torrent.get("tracker") if dl_type == DownloaderType.QB \
                else (torrent.status.stopped and torrent.percent_done == 1 and torrent.trackers)
        except Exception as e:
            print(str(e))
            return False

    @staticmethod
    def __convert_save_path(save_path, from_root, to_root):
        """
        转换保存路径
        """
        try:
            # 没有保存目录，以目的根目录为准
            if not save_path:
                return to_root
            # 没有设置根目录时返回save_path
            if not to_root or not from_root:
                return save_path
            # 统一目录格式
            save_path = os.path.normpath(save_path).replace("\\", "/")
            from_root = os.path.normpath(from_root).replace("\\", "/")
            to_root = os.path.normpath(to_root).replace("\\", "/")
            # 替换根目录
            if save_path.startswith(from_root):
                return save_path.replace(from_root, to_root, 1)
        except Exception as e:
            print(str(e))
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
