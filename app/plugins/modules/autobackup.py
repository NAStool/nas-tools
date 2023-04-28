import glob
import os
import time
from datetime import datetime

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from threading import Event
from app.plugins.modules._base import _IPluginModule
from app.utils import SystemUtils
from config import Config
from web.action import WebAction


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
    _full = None
    _bk_path = None
    _onlyonce = False
    _notify = False
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
                            'title': '开启定时备份',
                            'required': "",
                            'tooltip': '开启后会根据周期定时备份NAStool',
                            'type': 'switch',
                            'id': 'enabled',
                        },
                        {
                            'title': '是否完整版备份',
                            'required': "",
                            'tooltip': '开启后会备份完整数据库，保留有历史记录',
                            'type': 'switch',
                            'id': 'full',
                        },
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
                            'tooltip': '打开后立即运行一次',
                            'type': 'switch',
                            'id': 'onlyonce',
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
                        {
                            'title': '自定义备份路径',
                            'required': "",
                            'tooltip': '自定义备份路径（默认备份路径/config/backup_file/）',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'bk_path',
                                    'placeholder': '/config/backup_file',
                                }
                            ]
                        } if not SystemUtils.is_docker() else {}
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
            self._full = config.get("full")
            self._bk_path = config.get("bk_path")
            self._notify = config.get("notify")
            self._onlyonce = config.get("onlyonce")

        # 停止现有任务
        self.stop_service()

        # 启动服务
        if self._enabled or self._onlyonce:
            self._scheduler = BackgroundScheduler(timezone=Config().get_timezone())

            # 运行一次
            if self._onlyonce:
                self.info(f"备份服务启动，立即运行一次")
                self._scheduler.add_job(self.__backup, 'date',
                                        run_date=datetime.now(tz=pytz.timezone(Config().get_timezone())))
                # 关闭一次性开关
                self._onlyonce = False
                self.update_config({
                    "enabled": self._enabled,
                    "cron": self._cron,
                    "cnt": self._cnt,
                    "full": self._full,
                    "bk_path": self._bk_path,
                    "notify": self._notify,
                    "onlyonce": self._onlyonce,
                })

            # 周期运行
            if self._cron:
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

        # docker用默认路径
        if SystemUtils.is_docker():
            bk_path = os.path.join(Config().get_config_path(), "backup_file")
        else:
            # 无自定义路径则用默认
            bk_path = self._bk_path or os.path.join(Config().get_config_path(), "backup_file")

        # 备份
        zip_file = WebAction().backup(bk_path=bk_path,
                                      full_backup=self._full)

        if zip_file:
            self.info(f"备份完成 备份文件 {zip_file} ")
        else:
            self.error("创建备份失败")

        # 清理备份
        bk_cnt = 0
        del_cnt = 0
        if self._cnt:
            # 获取指定路径下所有以"bk"开头的文件，按照创建时间从旧到新排序
            files = sorted(glob.glob(bk_path + "/bk**"), key=os.path.getctime)
            bk_cnt = len(files)
            # 计算需要删除的文件数
            del_cnt = bk_cnt - int(self._cnt)
            if del_cnt > 0:
                self.info(
                    f"获取到 {bk_path} 路径下备份文件数量 {bk_cnt} 保留数量 {int(self._cnt)} 需要删除备份文件数量 {del_cnt}")

                # 遍历并删除最旧的几个备份
                for i in range(del_cnt):
                    os.remove(files[i])
                    self.debug(f"删除备份文件 {files[i]} 成功")
            else:
                self.info(
                    f"获取到 {bk_path} 路径下备份文件数量 {bk_cnt} 保留数量 {int(self._cnt)} 无需删除")

        # 发送通知
        if self._notify:
            next_run_time = self._scheduler.get_jobs()[0].next_run_time.strftime('%Y-%m-%d %H:%M:%S')
            self.send_message(title="【自动备份任务完成】",
                              text=f"创建备份{'成功' if zip_file else '失败'}\n"
                                   f"清理备份数量 {del_cnt}\n"
                                   f"剩余备份数量 {bk_cnt - del_cnt} \n"
                                   f"下次备份时间: {next_run_time}")

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

    def get_state(self):
        return self._enabled and self._cron
