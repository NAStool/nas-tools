import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.plugins.modules._base import _IPluginModule
from config import Config
from web.action import WebAction
from web.backend.web_utils import WebUtils


class ScheduledTasks(_IPluginModule):
    # 插件名称
    module_name = "定时任务"
    # 插件描述
    module_desc = "定时重启、更新、备份nas-tools。"
    # 插件图标
    module_icon = "scheduledtasks.png"
    # 主题色
    module_color = "#2e7eff"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "thsrite"
    # 作者主页
    author_url = "https://github.com/thsrite"
    # 插件配置项ID前缀
    module_config_prefix = "scheduledtasks_"
    # 加载顺序
    module_order = 22
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _scheduler = None

    # 设置开关
    _reboot_enabled = False
    _update_enabled = False
    _backup_enabled = False
    # 任务执行间隔
    _reboot_cron = None
    _update_cron = None
    _backup_cron = None

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
                            'title': '定时重启',
                            'required': "",
                            'tooltip': '开启后会根据周期定时重启nas-tools',
                            'type': 'switch',
                            'id': 'reboot_enabled',
                        },
                        {
                            'title': '定时更新',
                            'required': "",
                            'tooltip': '开启后会根据周期定时更新nas-tools，检测本地版本和远程版本不一致时更新',
                            'type': 'switch',
                            'id': 'update_enabled',
                        },
                        {
                            'title': '定时备份',
                            'required': "",
                            'tooltip': '开启后会根据周期定时备份nas-tools，默认备份路径/config/backup_file',
                            'type': 'switch',
                            'id': 'backup_enabled',
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
                            'title': '重启周期',
                            'required': "",
                            'tooltip': '设置自动重启时间周期，支持5位cron表达式',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'reboot_cron',
                                    'placeholder': '0 0 0 ? *',
                                }
                            ]
                        },
                        {
                            'title': '更新周期',
                            'required': "",
                            'tooltip': '设置自动更新时间周期，支持5位cron表达式',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'update_cron',
                                    'placeholder': '0 0 0 ? *',
                                }
                            ]
                        },
                        {
                            'title': '备份周期',
                            'required': "",
                            'tooltip': '设置自动备份时间周期，支持5位cron表达式',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'backup_cron',
                                    'placeholder': '0 0 0 ? *',
                                }
                            ]
                        },
                    ]
                ]
            }
        ]

    def init_config(self, config=None):
        # 读取配置
        if config:
            self._reboot_enabled = config.get("reboot_enabled")
            self._update_enabled = config.get("update_enabled")
            self._backup_enabled = config.get("backup_enabled")
            self._reboot_cron = config.get("reboot_cron")
            self._update_cron = config.get("update_cron")
            self._backup_cron = config.get("backup_cron")

        self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())

        # 启动服务
        if self._reboot_enabled and self._reboot_cron:
            self.info(f"定时重启服务启动，周期：{self._reboot_cron}")
            self._scheduler.add_job(self.__reboot,
                                    CronTrigger.from_crontab(self._reboot_cron))

        # 启动服务
        if self._update_enabled and self._update_cron:
            self.info(f"定时更新服务启动，周期：{self._update_cron}")
            self._scheduler.add_job(self.__update,
                                    CronTrigger.from_crontab(self._update_cron))

        # 启动服务
        if self._backup_enabled and self._backup_cron:
            self.info(f"定时备份服务启动，周期：{self._backup_cron}")
            self._scheduler.add_job(self.__backup,
                                    CronTrigger.from_crontab(self._backup_cron))

        # 启动任务
        if self._scheduler.get_jobs():
            self._scheduler.print_jobs()
            self._scheduler.start()

    def __reboot(self):
        self.info(f"当前时间 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))} 开始重启")
        WebAction().restart_server()

    def __update(self):
        # 判断是否有新版本
        current_version = WebUtils.get_current_version()
        version, _, _ = WebUtils.get_latest_version()
        releases_update_only = Config().get_config("app").get("releases_update_only") or False

        if releases_update_only and current_version and version and current_version.split()[0] == version:
            self.info(f"本地版本 {current_version.split()[0]} 线上版本 {version} 无需更新")
            return

        if not releases_update_only and current_version and version and current_version == version:
            self.info(f"本地版本 {current_version} 线上版本 {version} 无需更新")
            return

        self.info(f"当前时间 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))} 开始更新")
        WebAction().update_system()

    def __backup(self):
        self.info(f"当前时间 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))} 开始备份")
        zip_file = WebAction().backup()
        if zip_file:
            self.info(f"备份完成 备份文件 {zip_file} ")
        else:
            self.error("创建备份失败")

    def stop_service(self):
        pass

    def get_state(self):
        return (self._reboot_enabled and self._reboot_cron) or (
                self._update_enabled and self._update_cron) or (
                self._backup_enabled and self._backup_cron)
