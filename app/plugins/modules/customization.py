from app.media.meta.customization import CustomizationMatcher
from app.plugins.modules._base import _IPluginModule


class Customization(_IPluginModule):
    # 插件名称
    module_name = "自定义占位符"
    # 插件描述
    module_desc = "添加自定义占位符识别正则，重命名格式中添加{customization}使用，自定义多个结果间分隔符"
    # 插件图标
    module_icon = "regex.png"
    # 主题色
    module_color = "#E64D1C"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "Shurelol"
    # 作者主页
    author_url = "https://github.com/Shurelol"
    # 插件配置项ID前缀
    module_config_prefix = "customization_"
    # 加载顺序
    module_order = 6
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _customization = None
    _custom_separator = None
    _customization_matcher = None

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
                                    'id': 'customization',
                                    'placeholder': '多个匹配对象请用;或换行分隔，支持正则表达式，特殊字符注意转义',
                                    'rows': 5
                                }
                        },
                    ],
                    [
                        {
                            'title': '自定义分隔符',
                            'required': "",
                            'tooltip': '当匹配到多个结果时，使用此分隔符按添加自定义占位符的顺序进行合成，留空使用@（同一正则表达式内的多个对象按名称中出现的顺序合成）',
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
        self._customization_matcher = CustomizationMatcher()

        # 读取配置
        if config:
            customization = config.get('customization')
            custom_separator = config.get('separator')
            if customization:
                customization = customization.replace("\n", ";").strip(";").split(";")
                customization = "|".join([f"({item})" for item in customization])
                if customization:
                    self.info("自定义占位符已加载")
                    if custom_separator:
                        self.info(f"自定义分隔符 {custom_separator} 已加载")
                    self._customization_matcher.update_custom(customization, custom_separator)
                    self._customization = customization
                    self._custom_separator = custom_separator

    def get_state(self):
        return True if self._customization or self._custom_separator else False

    def stop_service(self):
        """
        退出插件
        """
        pass
