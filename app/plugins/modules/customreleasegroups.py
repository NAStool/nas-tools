from app.media.meta.release_groups import ReleaseGroupsMatcher
from app.plugins.modules._base import _IPluginModule


class CustomReleaseGroups(_IPluginModule):
    # 插件名称
    module_name = "自定义制作组/字幕组"
    # 插件描述
    module_desc = "添加无法识别的制作组/字幕组，自定义多个组间分隔符"
    # 插件图标
    module_icon = "teamwork.png"
    # 主题色
    module_color = "#00ADEF"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "Shurelol"
    # 作者主页
    author_url = "https://github.com/Shurelol"
    # 插件配置项ID前缀
    module_config_prefix = "customreleasegroups_"
    # 加载顺序
    module_order = 6
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _custom_release_groups = None
    _custom_separator = None
    _release_groups_matcher = None

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
                                    'id': 'release_groups',
                                    'placeholder': '多个制作组/字幕组请用;或换行分隔，支持正则表达式，特殊字符注意转义',
                                    'rows': 5
                                }
                        },
                    ],
                    [
                        {
                            'title': '自定义分隔符',
                            'required': "",
                            'tooltip': '当匹配到多个制作组/字幕组时，使用此分隔符进行分隔，留空使用@；如名称中识别出A组和B组，分隔符为@，则结果为A@B',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'separator',
                                    'placeholder': '请不要使用文件名中禁止使用的符号！',
                                }
                            ]
                        },
                    ]
                ]
            }
        ]

    def init_config(self, config=None):
        self._release_groups_matcher = ReleaseGroupsMatcher()

        # 读取配置
        if config:
            custom_release_groups = config.get('release_groups')
            custom_separator = config.get('separator')
            if custom_release_groups:
                if custom_release_groups.startswith(';'):
                    custom_release_groups = custom_release_groups[1:]
                if custom_release_groups.endswith(';'):
                    custom_release_groups = custom_release_groups[:-1]
                custom_release_groups = custom_release_groups.replace(";", "|").replace("\n", "|")
            if custom_release_groups or custom_separator:
                if custom_release_groups:
                    self.info("自定义制作组/字幕组已加载")
                if custom_separator:
                    self.info(f"自定义分隔符 {custom_separator} 已加载")
                self._release_groups_matcher.update_custom(custom_release_groups, custom_separator)
                self._custom_release_groups = custom_release_groups
                self._custom_separator = custom_separator

    def get_state(self):
        return True if self._custom_release_groups or self._custom_separator else False

    def stop_service(self):
        """
        退出插件
        """
        pass
