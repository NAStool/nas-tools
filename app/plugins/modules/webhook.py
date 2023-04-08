from app.plugins import EventHandler
from app.plugins.modules._base import _IPluginModule
from app.utils import RequestUtils
from app.utils.types import EventType


class Webhook(_IPluginModule):
    # 插件名称
    module_name = "Webhook"
    # 插件描述
    module_desc = "事件发生时向第三方地址发送请求。"
    # 插件图标
    module_icon = "webhook.png"
    # 主题色
    module_color = "#C73A63"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    module_config_prefix = "webhook_"
    # 加载顺序
    module_order = 4
    # 可使用的用户级别
    user_level = 2

    # 私有属性
    _save_tmp_path = None
    _webhook_url = None
    _method = None

    def init_config(self, config: dict = None):
        if config:
            self._webhook_url = config.get("webhook_url")
            self._method = config.get('method')

    def get_state(self):
        return self._webhook_url and self._method

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
                            'title': '请求方式',
                            'required': "required",
                            'tooltip': 'GET方式通过URL传递数据，POST方式通过JSON报文传递数据',
                            'type': 'select',
                            'content': [
                                {
                                    'id': 'method',
                                    'default': 'post',
                                    'options': {
                                        "get": "GET",
                                        "post": "POST"
                                    },
                                }
                            ]

                        },
                        {
                            'title': 'Webhook地址',
                            'required': "required",
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'webhook_url',
                                    'placeholder': 'http://127.0.0.1/webhook'
                                }
                            ]
                        }
                    ]
                ]
            }
        ]

    def stop_service(self):
        pass

    @EventHandler.register(EventType)
    def send(self, event):
        """
        向第三方Webhook发送请求
        """
        if not self._webhook_url:
            return
        event_info = {
            "type": event.event_type,
            "data": event.event_data
        }
        if self._method == 'post':
            ret = RequestUtils(content_type="application/json").post_res(self._webhook_url, json=event_info)
        else:
            ret = RequestUtils().get_res(self._webhook_url, params=event_info)

        if ret:
            self.info(f"发送成功：{self._webhook_url}")
        elif ret is not None:
            self.error(f"发送失败，状态码：{ret.status_code}，返回信息：{ret.text} {ret.reason}")
        else:
            self.error(f"发送失败，未获取到返回信息")
