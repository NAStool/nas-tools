import glob
import os
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.plugins.modules._base import _IPluginModule
from config import Config
from web.action import WebAction
from web.backend.web_utils import WebUtils


class AutoBackup(_IPluginModule):
    # 插件名称
    module_name = "自动备份"
    # 插件描述
    module_desc = "自动备份NAStool数据和配置文件。"
    # 插件图标
    module_icon = "backup.png"
    # 主题色
    module_color = "bg-green"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "thsrite"
    # 作者主页
    author_url = "https://github.com/thsrite"
    # 插件配置项ID前缀
    module_config_prefix = "autobackup_"
    # 加载顺序
    module_order = 22
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _scheduler = None

    # 设置开关
    _enabled = False
    # 任务执行间隔
    _cron = None
    _cnt = None
    _config_path = "/config/backup_file"

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
                            'title': '开启定时备份',
                            'required': "",
                            'tooltip': '开启后会根据周期定时备份nas-tools，默认备份路径/config/backup_file',
                            'type': 'switch',
                            'id': 'enabled',
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
                            'title': '备份周期',
                            'required': "",
                            'tooltip': '设置自动备份时间周期，支持5位cron表达式',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'cron',
                                    'placeholder': '0 0 0 ? *',
                                }
                            ]
                        },
                        {
                            'title': '最大保留备份数',
                            'required': "",
                            'tooltip': '最大保留备份数量，优先删除较早备份',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'cnt',
                                    'placeholder': '10',
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
            self._enabled = config.get("enabled")
            self._cron = config.get("cron")
            self._cnt = config.get("cnt")

        # 启动服务
        if self._enabled and self._cron:
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())
            self.info(f"定时备份服务启动，周期：{self._cron}")
            self._scheduler.add_job(self.__backup,
                                    CronTrigger.from_crontab(self._cron))

            # 启动任务
            if self._scheduler.get_jobs():
                self._scheduler.print_jobs()
                self._scheduler.start()

    def __backup(self):
        """
        自动备份、删除备份
        """
        self.info(f"当前时间 {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))} 开始备份")
        zip_file = WebAction().backup()
        if zip_file:
            self.info(f"备份完成 备份文件 {zip_file} ")
        else:
            self.error("创建备份失败")

        if self._cnt:
            # 获取指定路径下所有以"bk"开头的文件，按照创建时间从旧到新排序
            files = sorted(glob.glob(self._config_path), key=os.path.getctime)
            # 计算需要删除的文件数
            del_cnt = len(files) - self._cnt
            self.info(f"获取到 {self._config_path} 路径下备份文件数量 {len(files)} 需要删除备份文件数量 {del_cnt}")

            # 遍历并删除最旧的几个备份
            if del_cnt > 0:
                for i in range(del_cnt):
                    os.remove(files[i])
                    self.debug(f"删除备份文件 {files[i]} 成功")

    def stop_service(self):
        pass

    def get_state(self):
        return self._enabled and self._cron
