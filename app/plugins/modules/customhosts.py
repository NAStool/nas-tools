import os

from python_hosts import Hosts, HostsEntry

import log
from app.plugins.modules._base import _IPluginModule
from app.utils import SystemUtils
from app.utils.ip_utils import IpUtils


class CustomHosts(_IPluginModule):
    # 插件名称
    module_name = "Hosts"
    # 插件描述
    module_desc = "自定义hosts"
    # 插件图标
    module_icon = "hosts.png"
    # 主题色
    module_color = "bg-yellow"
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
                            'required': '',
                            'tooltip': '',
                            'type': 'textarea',
                            'content':
                                {
                                    'id': 'hosts',
                                    'placeholder': '读取hosts文件，修改会覆盖hosts文件',
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

        flush_config = False

        if config:
            self._hosts = config.get("hosts")
            # 读取hosts
            hosts = Hosts(path=hosts_path)

            # 清空hosts
            hosts.entries = []

            new_hosts = []
            # 写入hosts
            for host in str(config.get("hosts")).split("\n"):
                if host:
                    host_arr = str(host).split()
                    try:
                        new_entry = HostsEntry(entry_type='ipv4' if IpUtils.is_ipv4(str(host_arr[0])) else 'ipv6',
                                               address=host_arr[0], names=[host_arr[1]])
                        new_hosts.append(new_entry)
                    except:
                        flush_config = True
                        log.error("[%s]hosts输入不标准，请检查ip和域名是否规范" % str(host))

            # 没有错误再写入hosts
            if not flush_config:
                hosts.add(new_hosts)
                hosts.write()
                log.info("更新系统hosts文件成功")

        if not config or flush_config:
            _hosts = []
            # 读取hosts
            hosts = Hosts(path=hosts_path)
            for entry in hosts.entries:
                if not entry.is_real_entry():
                    continue
                _hosts.append(str(entry.address) + " " + str(entry.names[0]) + "\n")

            self._hosts = _hosts

            # 更新配置
            self.update_config({
                "hosts": _hosts
            })
            log.info("数据库与hosts文件版本不一致，获取系统hosts更新入数据库")

    def get_state(self):
        return self._hosts

    def stop_service(self):
        """
        退出插件
        """
        pass
