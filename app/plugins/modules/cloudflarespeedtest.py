import os
from datetime import datetime
from pathlib import Path

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from threading import Event

import log
from app.plugins import EventManager
from app.plugins.modules._base import _IPluginModule
from app.utils import SystemUtils, RequestUtils
from app.utils.types import EventType
from config import Config
from app.utils.ip_utils import IpUtils


class CloudflareSpeedTest(_IPluginModule):
    # 插件名称
    module_name = "Cloudflare IP优选"
    # 插件描述
    module_desc = "🌩 测试 Cloudflare CDN 延迟和速度，自动优选IP。"
    # 插件图标
    module_icon = "cloudflare.jpg"
    # 主题色
    module_color = "bg-orange"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "thsrite"
    # 插件配置项ID前缀
    module_config_prefix = "cloudflarespeedtest_"
    # 加载顺序
    module_order = 12
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    eventmanager = None
    _customhosts = False
    _cf_ip = None
    _scheduler = None
    _cron = None
    _onlyonce = False
    _ipv4 = False
    _ipv6 = False
    _version = None
    _cf_path = 'cloudflarespeedtest'
    _cf_ipv4 = 'cloudflarespeedtest/ip.txt'
    _cf_ipv6 = 'cloudflarespeedtest/ipv6.txt'
    _release_prefix = 'https://github.com/XIU2/CloudflareSpeedTest/releases/download'
    _binary_name = 'CloudflareST'
    _result_file = 'cloudflarespeedtest/result_hosts.txt'

    # 退出事件
    _event = Event()

    @staticmethod
    def get_fields():
        return [
            # 同一板块
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': '优选IP',
                            'required': "required",
                            'tooltip': '第一次使用，请先将 自定义Hosts插件 中所有 Cloudflare CDN IP 统一改为一个 IP。后续会自动变更。需搭配[自定义Hosts]插件使用！',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'cf_ip',
                                    'placeholder': '121.121.121.121',
                                }
                            ]
                        },
                        {
                            'title': '优选周期',
                            'required': "required",
                            'tooltip': 'Cloudflare CDN优选周期。',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'cron',
                                    'placeholder': '0 0 0 ? *',
                                }
                            ]
                        },
                    ],
                    [
                        {
                            'title': 'IPv4',
                            'required': "",
                            'tooltip': '优选测速ipv4；v4和v6必须其一，都不选择则默认ipv4',
                            'type': 'switch',
                            'id': 'ipv4',
                        },
                        {
                            'title': 'IPv6',
                            'required': "",
                            'tooltip': '优选测速ipv6；v4和v6必须其一，都不选择则默认ipv4。选择ipv6会大大加长测速时间。',
                            'type': 'switch',
                            'id': 'ipv6',
                        }
                    ],
                    [
                        {
                            'title': '立即运行一次',
                            'required': "",
                            'tooltip': '打开后立即运行一次（点击此对话框的确定按钮后即会运行，周期未设置也会运行），关闭后将仅按照优选周期运行（同时上次触发运行的任务如果在运行中也会停止）',
                            'type': 'switch',
                            'id': 'onlyonce',
                        },
                        {
                            'title': '',
                            'required': "",
                            'tooltip': '',
                            'type': 'text',
                            'hidden': True,
                            'content': [
                                {
                                    'id': 'version',
                                    'placeholder': 'CloudflareSpeedTest版本',
                                }
                            ]
                        }
                    ]
                ]
            }
        ]

    def init_config(self, config=None):
        self.eventmanager = EventManager()

        # 停止现有任务
        self.stop_service()

        # 读取配置
        if config:
            self._onlyonce = config.get("onlyonce")
            self._cron = config.get("cron")
            self._cf_ip = config.get("cf_ip")
            self._version = config.get("version")
            self._ipv4 = config.get("ipv4")
            self._ipv6 = config.get("ipv6")

        # 自定义插件hosts配置
        customHosts = self.get_config("CustomHosts")
        self._customhosts = customHosts and customHosts.get("enable")

        # 启动定时任务 & 立即运行一次
        if self._cron or self._onlyonce:
            # 获取自定义Hosts插件，若无设置则停止
            if self._cf_ip and not customHosts or not customHosts.get("hosts"):
                log.error(f"【Plugin】Cloudflare CDN优选依赖于自定义Hosts，请先维护hosts")
                self._onlyonce = False
                self.__update_config()
                return

            if not self._cf_ip:
                log.error("【Plugin】CloudflareSpeedTest加载成功，首次运行，需要配置优选ip")
                self._onlyonce = False
                self.__update_config()
                return

            # ipv4和ipv6必须其一
            if not self._ipv4 and not self._ipv6:
                self._ipv4 = True
                self.__update_config()
                log.warn(f"【Plugin】Cloudflare CDN优选未指定ip类型，默认ipv4")

            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            if self._cron:
                self._scheduler.add_job(self.__cloudflareSpeedTest, CronTrigger.from_crontab(self._cron))
            if self._onlyonce:
                self._scheduler.add_job(self.__cloudflareSpeedTest, 'date',
                                        run_date=datetime.now(tz=pytz.timezone(Config().get_timezone())))
            self._scheduler.print_jobs()
            self._scheduler.start()

            if self._onlyonce:
                log.info(f"【Plugin】Cloudflare CDN优选服务启动，立即运行一次")
            if self._cron:
                log.info(f"【Plugin】Cloudflare CDN优选服务启动，周期：{self._cron}")

            # 关闭一次性开关
            self._onlyonce = False
            self.__update_config()

    def __cloudflareSpeedTest(self):
        """
        CloudflareSpeedTest优选
        """
        customHosts = self.get_config("CustomHosts")
        err_flag, release_version = self.__check_envirment()
        if err_flag and release_version:
            # 更新版本
            self._version = release_version
            self.__update_config()

        # 开始优选
        if err_flag:
            log.info("【Plugin】正在进行CLoudflare CDN优选，请耐心等待")
            # 执行优选命令，-dd不测速
            cf_command = f'./{self._cf_path}/{self._binary_name} -dd -o {self._result_file}' + (
                f' -f {self._cf_ipv4}' if self._ipv4 else '') + (f' -f {self._cf_ipv6}' if self._ipv6 else '')
            log.info(f'正在执行优选命令 {cf_command}')
            os.system(cf_command)

            # 获取优选后最优ip
            best_ip = SystemUtils.execute("sed -n '2,1p' " + self._result_file + " | awk -F, '{print $1}'")
            log.info(f"\n【Plugin】获取到最优ip==>[{best_ip}]")

            # 替换自定义Hosts插件数据库hosts
            if IpUtils.is_ipv4(best_ip) or IpUtils.is_ipv6(best_ip):
                if best_ip == self._cf_ip:
                    log.info(f"【Plugin】CloudflareSpeedTest CDN优选ip未变，不做处理")
                else:
                    # 替换优选ip
                    hosts = customHosts.get("hosts")
                    if isinstance(hosts, str):
                        hosts = str(hosts).split('\n')
                    err_hosts = customHosts.get("err_hosts")
                    enable = customHosts.get("enable")

                    # 处理ip
                    new_hosts = []
                    for host in hosts:
                        if host and host != '\n':
                            host_arr = str(host).split()
                            if host_arr[0] == self._cf_ip:
                                new_hosts.append(host.replace(self._cf_ip, best_ip))
                            else:
                                new_hosts.append(host)

                    # 更新自定义Hosts
                    self.update_config({
                        "hosts": new_hosts,
                        "err_hosts": err_hosts,
                        "enable": enable
                    }, "CustomHosts")

                    # 更新优选ip
                    self._cf_ip = best_ip
                    self.__update_config()
                    log.info(f"【Plugin】CLoudflare CDN优选ip [{best_ip}] 已替换自定义Hosts插件")

                    # 解发自定义hosts插件重载
                    self.eventmanager.send_event(EventType.CustomHostsReload,
                                                 self.get_config("CustomHosts"))
                    log.info("【Plugin】CustomHosts插件重载成功")
        else:
            log.error("【Plugin】获取到最优ip格式错误，请重试")
            self._onlyonce = False
            self.__update_config()
            self.stop_service()

    def __check_envirment(self):
        """
        环境检查
        """
        # 判断目录是否存在
        cf_path = Path(self._cf_path)
        if not cf_path.exists():
            os.mkdir(self._cf_path)

        # 获取CloudflareSpeedTest最新版本
        release_version = self.__get_release_version()
        if not release_version:
            # 如果升级失败但是有可执行文件CloudflareST，则可继续运行，反之停止
            if Path(f'{self._cf_path}/{self._binary_name}').exists():
                log.warn(f"【Plugin】获取CloudflareSpeedTest版本失败，存在可执行版本，继续运行")
                return True, None
            else:
                log.error(f"【Plugin】获取CloudflareSpeedTest版本失败，无可用版本，停止运行")
                return False, None

        # 是否安装标识
        install_flag = False

        # 有更新
        if release_version and release_version != self._version:
            log.info(f"【Plugin】检测到CloudflareSpeedTest有版本[{release_version}]更新，开始安装")
            install_flag = True

        # 重装后数据库有版本数据，但是本地没有则重装
        if release_version == self._version and not Path(f'{self._cf_path}/{self._binary_name}').exists():
            log.warn(f"【Plugin】未检测到CloudflareSpeedTest本地版本，重新安装")
            install_flag = True

        if not install_flag:
            log.info(f"【Plugin】CloudflareSpeedTest无新版本，存在可执行版本，继续运行")
            return True, None

        # 检查环境、安装
        if SystemUtils.is_windows():
            # todo
            log.error(f"【Plugin】CloudflareSpeedTest暂不支持windows平台")
            return False, None
        elif SystemUtils.is_macos():
            # mac
            uname = SystemUtils.execute('uname -m')
            arch = 'amd64' if uname == 'x86_64' else 'arm64'
            cf_file_name = f'CloudflareST_darwin_{arch}.zip'
            download_url = f'{self._release_prefix}/{release_version}/{cf_file_name}'
            return self.__os_install(download_url, cf_file_name, release_version,
                                     f"ditto -V -x -k --sequesterRsrc {self._cf_path}/{cf_file_name} {self._cf_path}")
        else:
            # docker
            uname = SystemUtils.execute('uname -m')
            arch = 'amd64' if uname == 'x86_64' else 'arm64'
            cf_file_name = f'CloudflareST_linux_{arch}.tar.gz'
            download_url = f'{self._release_prefix}/{release_version}/"{cf_file_name}"'
            return self.__os_install(download_url, cf_file_name, release_version,
                                     f"tar -zxf {self._cf_path}/{cf_file_name} -C {self._cf_path}")

    def __os_install(self, download_url, cf_file_name, release_version, unzip_command):
        """
        macos docker安装cloudflare
        """
        # 首次下载或下载新版压缩包
        proxies = Config().get_proxies()
        os.system('wget -P ' + ('-e http_proxy = ' + proxies.get("http") if proxies and proxies.get(
            "http") else '') + f' {self._cf_path} {download_url}')

        # 判断是否下载好安装包
        if Path(f'{self._cf_path}/{cf_file_name}').exists():
            try:
                # 解压
                os.system(f'{unzip_command}')
                # 赋权
                os.system(f'chmod +x {self._cf_path}/{self._binary_name}')
                # 删除压缩包
                os.system(f'rm -rf {self._cf_path}/{cf_file_name}')
                if Path(f'{self._cf_path}/{self._binary_name}').exists():
                    log.info(f"【Plugin】CloudflareSpeedTest安装成功，当前版本：{release_version}")
                    return True, release_version
                else:
                    log.error(f"【Plugin】CloudflareSpeedTest安装失败，请检查")
                    os.removedirs(self._cf_path)
                    return False, None
            except Exception as err:
                # 如果升级失败但是有可执行文件CloudflareST，则可继续运行，反之停止
                if Path(f'{self._cf_path}/{self._binary_name}').exists():
                    log.error(f"【Plugin】CloudflareSpeedTest安装失败：{str(err)}，继续使用现版本运行")
                    return True, None
                else:
                    log.error(f"【Plugin】CloudflareSpeedTest安装失败：{str(err)}，无可用版本，停止运行")
                    os.removedirs(self._cf_path)
                    return False, None
        else:
            # 如果升级失败但是有可执行文件CloudflareST，则可继续运行，反之停止
            if Path(f'{self._cf_path}/{self._binary_name}').exists():
                log.warn(f"【Plugin】CloudflareSpeedTest安装失败，存在可执行版本，继续运行")
                return True, None
            else:
                log.error(f"【Plugin】CloudflareSpeedTest安装失败，无可用版本，停止运行")
                os.removedirs(self._cf_path)
                return False, None

    def __update_config(self):
        """
        更新优选插件配置
        """
        self.update_config({
            "onlyonce": False,
            "cron": self._cron,
            "cf_ip": self._cf_ip,
            "version": self._version,
            "ipv4": self._ipv4,
            "ipv6": self._ipv6,
        })

    @staticmethod
    def __get_release_version():
        """
        获取CloudflareSpeedTest最新版本
        """
        version_res = RequestUtils(proxies=Config().get_proxies()).get_res(
            "https://api.github.com/repos/XIU2/CloudflareSpeedTest/releases/latest")

        if version_res:
            ver_json = version_res.json()
            version = f"{ver_json['tag_name']}"
            return version
        else:
            return None

    def get_state(self):
        return self._customhosts and self._cf_ip and True if self._cron else False

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
