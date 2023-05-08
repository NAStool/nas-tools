import random

from app.downloader import Downloader
from app.plugins.modules._base import _IPluginModule
from app.sites import Sites
from app.utils import Torrent, StringUtils


class AutoUnPack(_IPluginModule):
    # 插件名称
    module_name = "种子自动拆包"
    # 插件描述
    module_desc = "自动拆包种子、添加下载任务。"
    # 插件图标
    module_icon = "unpack.png"
    # 主题色
    module_color = "#4179F4"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "thsrite"
    # 作者主页
    author_url = "https://github.com/thsrite"
    # 插件配置项ID前缀
    module_config_prefix = "autounpack_"
    # 加载顺序
    module_order = 24
    # 可使用的用户级别
    auth_level = 2

    # 设置开关
    _size = None
    _type = None
    _torrents = None
    _downloader = None
    _onlyonce = False
    _notify = False
    _autostart = False
    _path = None
    _unpack_tag = "auto_unpacking"

    downloader = None
    torrent = None
    sites = None

    @staticmethod
    def get_fields():
        downloaders = {k: v.get('name') for k, v in Downloader().get_downloader_conf_simple().items()
                       if v.get("type") == "qbittorrent" and v.get("enabled")}
        return [
            # 同一板块
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '拆包方式',
                            'required': "required",
                            'tooltip': '选择拆包类型，从前部、中部、后部、均匀拆包（有误差请手动更正）',
                            'type': 'select',
                            'content': [
                                {
                                    'id': 'type',
                                    'options': {
                                        '0': '前部',
                                        '1': '中部',
                                        '2': '后部',
                                        '3': '均匀'
                                    },
                                    'default': '3',
                                }
                            ]
                        },
                        {
                            'title': '保留大小',
                            'required': "required",
                            'tooltip': '拆包后保留大小（单位GB）',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'size',
                                    'placeholder': '10',
                                }
                            ]
                        },
                        {
                            'title': '下载器',
                            'required': "required",
                            'tooltip': '添加任务的下载器（只支持Qbittorrent）',
                            'type': 'select',
                            'content': [
                                {
                                    'id': 'downloader',
                                    'options': downloaders,
                                },
                            ]
                        },
                        {
                            'title': '保存路径',
                            'required': "required",
                            'tooltip': '下载器保存路径（必须是所选下载器可访问的路径）',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'path',
                                    'placeholder': '下载器可访问路径',
                                }
                            ]
                        },
                    ],
                    [
                        {
                            'title': '种子链接',
                            'required': 'required',
                            'tooltip': '每一行一个种子链接',
                            'type': 'textarea',
                            'content':
                                {
                                    'id': 'torrents',
                                    'placeholder': 'https://xxxx',
                                    'rows': 5
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
                            'title': '立即运行一次',
                            'required': "",
                            'tooltip': '打开后立即运行一次',
                            'type': 'switch',
                            'id': 'onlyonce',
                        },
                        {
                            'title': '自动开始',
                            'required': "",
                            'tooltip': '打开后拆包完成会自动开始任务（不建议开启，建议拆包完成确认后手动开启任务）',
                            'type': 'switch',
                            'id': 'autostart',
                        },
                        {
                            'title': '运行时通知',
                            'required': "",
                            'tooltip': '运行签到任务后会发送通知（需要打开插件消息通知）',
                            'type': 'switch',
                            'id': 'notify',
                        }
                    ]
                ]
            },
        ]

    def init_config(self, config=None):
        self.sites = Sites()
        self.torrent = Torrent()
        self.downloader = Downloader()
        # 读取配置
        if config:
            self._size = config.get("size")
            self._type = config.get("type")
            self._torrents = config.get("torrents").split() if config.get("torrents") else []
            self._downloader = config.get("downloader")
            self._onlyonce = config.get("onlyonce")
            self._notify = config.get("notify")
            self._autostart = config.get("autostart")
            self._path = config.get("path")

        if self._onlyonce:
            if len(self._torrents) == 0:
                self.error("请添加需要拆包的种子链接")
                return

            if not self._downloader:
                self.error("请选择需要添加任务的下载器")
                return

            if not self._path:
                self.error("请指定下载器保存路径")
                return

            # 拆包
            success_cnt = 0
            for torrent in self._torrents:
                success = self.__unpacking(torrent=torrent)
                if success:
                    success_cnt += 1

            if self._notify:
                self.send_message(title="【自动拆包任务完成】",
                                  text=f"拆包成功数量 {success_cnt} \n"
                                       f"拆包失败数量 {len(self._torrents) - success_cnt}")
            # 更新状态
            self._onlyonce = False
            self._autostart = False
            self.update_config({
                "size": self._size,
                "type": self._type,
                "torrents": [],
                "downloader": self._downloader,
                "onlyonce": self._onlyonce,
                "notify": self._notify,
                "autostart": self._autostart,
                "path": self._path
            })

    def __unpacking(self, torrent):
        """
        自动拆包
        """
        # 1、添加下载器任务、暂停状态
        # 查询站点
        site_info = self.sites.get_sites(siteurl=torrent)
        if not site_info:
            self.error("根据链接地址未匹配到站点")
            return False

        # 下载种子文件，并读取信息
        file_path, content, _, files, retmsg = self.torrent.get_torrent_info(
            url=torrent,
            cookie=site_info.get("cookie"),
            ua=site_info.get("ua"),
            proxy=site_info.get("proxy")
        )
        if not file_path:
            self.error(f"下载种子文件失败： {retmsg}")

        # 添加下载、暂停
        downloader = self.downloader.get_downloader(downloader_id=self._downloader)
        ret = downloader.add_torrent(content,
                                     is_paused=True,
                                     tag=self._unpack_tag,
                                     download_dir=self._path,
                                     cookie=site_info.get("cookie"))
        if ret:
            self.info("添加下载任务成功，已暂停")
            # 2、任务拆包
            # 获取刚添加的种子id
            torrent_id = downloader.get_torrent_id_by_tag(tag=self._unpack_tag)
            if not torrent_id:
                self.error("未获取到刚新增的任务")
                return False
            self.debug(f"获取到刚添加的任务id {torrent_id}")

            # 获取种子文件
            torrent_files = downloader.get_files(tid=torrent_id)
            if not torrent_files:
                self.error("未获取到任务文件列表")
                return False

            # 拆包
            no_downloads_files_ids = self.__get_file_ids(files=torrent_files)
            self.debug(f"获取到任务 {torrent_id} 不下载文件id {no_downloads_files_ids}")
            # 设置任务哪些文件不下载
            if len(no_downloads_files_ids) > 0:
                success = downloader.set_files(torrent_hash=torrent_id,
                                               file_ids=no_downloads_files_ids,
                                               priority=0)
                if not success:
                    self.error("设置任务文件下载状态失败")
                    return False

            # 3、开始任务
            if self._autostart:
                success = downloader.start_torrents(ids=[torrent_id])
                if not success:
                    self.error("任务开启失败")
                    return False
                self.info("任务已自动开启")
            self.info("任务拆包完成")
            return True
        else:
            self.error("添加下载任务失败")
            return False

    def __get_file_ids(self, files):
        """
        根据所选拆包类型拆包
        """
        total_size = float(self._size) * 1024 ** 3
        # 按照文件大小排序
        sorted_file_lst = sorted(files, key=lambda x: x['size'])
        file_ids = []  # 存储文件id
        n = len(sorted_file_lst)
        size_sum = 0
        if self._type == '0':  # 从前开始获取文件
            self.info("开始从前部开始拆包")
            for i in range(n):
                if size_sum + sorted_file_lst[i]['size'] > total_size:
                    break
                file_ids.append(sorted_file_lst[i]['id'])
                size_sum += sorted_file_lst[i]['size']
        elif self._type == '1':  # 从中间获取文件
            self.info("开始从中间开始拆包")
            middle = n // 2
            left, right = middle, middle + 1
            while left >= 0 and right < n and size_sum < total_size:
                if sorted_file_lst[left]['size'] > sorted_file_lst[right]['size']:
                    file_id = sorted_file_lst[left]['id']
                    file_size = sorted_file_lst[left]['size']
                    left -= 1
                else:
                    file_id = sorted_file_lst[right]['id']
                    file_size = sorted_file_lst[right]['size']
                    right += 1
                if size_sum + file_size <= total_size:
                    file_ids.append(file_id)
                    size_sum += file_size
        elif self._type == '2':  # 从后开始获取文件
            self.info("开始从后部开始拆包")
            for i in range(n - 1, -1, -1):
                if size_sum + sorted_file_lst[i]['size'] > total_size:
                    break
                file_ids.append(sorted_file_lst[i]['id'])
                size_sum += sorted_file_lst[i]['size']
        elif self._type == '3':  # 均匀获取文件
            self.info("开始均匀拆包")
            while size_sum < total_size and len(sorted_file_lst) > 0:
                random_file = sorted_file_lst[random.randint(0, len(sorted_file_lst) - 1)]
                if total_size > float(random_file['size']):
                    size_sum += random_file['size']
                    file_ids.append(random_file['id'])
                sorted_file_lst.remove(random_file)

        # 反选不下载的文件id
        no_downloads_files_ids = [file['id'] for file in files if file['id'] not in file_ids]
        self.info(f"拆包完成，设置拆包大小 {self._size}GB 拆包后大小 {StringUtils.str_filesize(size_sum)}")
        return no_downloads_files_ids

    def stop_service(self):
        pass

    def get_state(self):
        return False
