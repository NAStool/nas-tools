import json
import os

from python_hosts import Hosts, HostsEntry

import log
from app.plugins.modules._base import _IPluginModule
from app.utils import SystemUtils
from app.utils.ip_utils import IpUtils


class CustomHosts(_IPluginModule):
    # 插件名称
    module_name = "自定义Hosts"
    # 插件描述
    module_desc = "修改系统hosts文件，加速网络访问。"
    # 插件图标
    module_icon = "hosts.png"
    # 主题色
    module_color = "bg-azure"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "thsrite"
    # 插件配置项ID前缀
    module_config_prefix = "customhosts_"
    # 加载顺序
    module_order = 11
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _hosts = None

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
                            'title': '',
                            'required': False,
                            'tooltip': '',
                            'type': 'textarea',
                            'content':
                                {
                                    'id': 'hosts',
                                    'placeholder': '默认读取系统原有hosts文件，修改会覆盖系统hosts设置',
                                    'rows': 20,
                                }
                        }
                    ]
                ]
            }
        ]

    def init_config(self, config=None):
        # 获取本机hosts路径
        if SystemUtils.is_windows():
            hosts_path = r"c:\windows\system32\drivers\etc\hosts"
        else:
            hosts_path = '/etc/hosts'

        # 读取配置
        if config:
            # 读取系统hosts
            system_hosts = Hosts(path=hosts_path)

            # 读取设置
            self._hosts = config.get("hosts")
            if self._hosts:
                if not isinstance(self._hosts, list):
                    self._hosts = str(self._hosts).split('\n')
                # 改写系统hosts开关
                flush_config = True
                # 新的hosts
                new_hosts = []
                for host in self._hosts:
                    if not host:
                        continue
                    host_arr = str(host).split()
                    try:
                        new_entry = HostsEntry(entry_type='ipv4' if IpUtils.is_ipv4(str(host_arr[0])) else 'ipv6',
                                               address=host_arr[0],
                                               names=[host_arr[1]])
                        new_hosts.append(new_entry)
                    except Exception as err:
                        flush_config = False
                        log.error(f"【Plugin】{host} 格式转换错误：{str(err)}")

                # 没有错误再写入hosts
                if flush_config:
                    # 清空系统hosts
                    system_hosts.entries = []
                    # 改写hosts
                    system_hosts.add(new_hosts)
                    system_hosts.write()
                    log.info("【Plugin】更新系统hosts文件成功")
        # 没有配置
        else:
            self._hosts = []
            # 读取系统hosts
            system_hosts = Hosts(path=hosts_path)
            for entry in system_hosts.entries:
                if not entry.is_real_entry():
                    continue
                self._hosts.append(str(entry.address) + " " + str(entry.names[0]) + "\n")

            # 更新配置
            self.update_config({
                "hosts": self._hosts
            })
            log.info("【Plugin】数据库与hosts文件版本不一致，获取系统hosts更新入数据库")

    def get_state(self):
        return self._hosts

    def stop_service(self):
        """
        退出插件
        """
        pass
