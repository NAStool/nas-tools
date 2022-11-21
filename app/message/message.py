import re
import json
from enum import Enum

import log
from app.utils.commons import singleton
from config import Config
from app.helper import DbHelper
from app.message import Bark, IyuuMsg, PushPlus, ServerChan, Telegram, WeChat
from app.utils import StringUtils
from app.message.message_center import MessageCenter
from app.utils.types import SearchType, MediaType


@singleton
class Message:
    _active_clients = []
    _client_configs = {}
    _webhook_ignore = None
    _domain = None
    dbhelper = None
    messagecenter = None

    # 消息通知类型
    MESSAGE_DICT = {
        "channel": {
            "telegram": {"name": "Telegram", "img_url": "../static/img/telegram.png", "search_type": SearchType.TG},
            "wechat": {"name": "WeChat", "img_url": "../static/img/wechat.png", "search_type": SearchType.WX},
            "serverchan": {"name": "ServerChan", "img_url": "../static/img/serverchan.png"},
            "bark": {"name": "Bark", "img_url": "../static/img/bark.webp"},
            "pushplus": {"name": "PushPlus", "img_url": "../static/img/pushplus.jpg"},
            "iyuu": {"name": "IyuuMsg", "img_url": "../static/img/iyuu.png"}
        },
        "switch": {
            "download_start": {"name": "新增下载", "fuc_name": "download_start"},
            "download_fail": {"name": "下载失败", "fuc_name": "download_fail"},
            "transfer_finished": {"name": "入库完成", "fuc_name": "transfer_finished"},
            "transfer_fail": {"name": "入库失败", "fuc_name": "transfer_fail"},
            "rss_added": {"name": "新增订阅", "fuc_name": "rss_added"},
            "rss_finished": {"name": "订阅完成", "fuc_name": "rss_finished"},
            "site_signin": {"name": "站点签到", "fuc_name": "site_signin"},
            "site_message": {"name": "站点消息", "fuc_name": "site_message"},
            "brushtask_added": {"name": "刷流下种", "fuc_name": "brushtask_added"},
            "brushtask_remove": {"name": "刷流删种", "fuc_name": "brushtask_remove"},
            "mediaserver_message": {"name": "媒体服务", "fuc_name": "mediaserver_message"},
        }
    }

    def __init__(self):
        self.dbhelper = DbHelper()
        self.messagecenter = MessageCenter()
        self._domain = Config().get_domain()
        self.init_config()

    def init_config(self):
        # 初始化消息客户端
        self._active_clients = []
        self._client_configs = {}
        for client_config in self.dbhelper.get_message_client() or []:
            cid = client_config.ID
            name = client_config.NAME
            enabled = client_config.ENABLED
            config = json.loads(client_config.CONFIG) if client_config.CONFIG else {}
            ctype = client_config.TYPE
            switchs = json.loads(client_config.SWITCHS) if client_config.SWITCHS else []
            interactive = client_config.INTERACTIVE
            self._client_configs[str(cid)] = {
                "id": cid,
                "name": name,
                "type": ctype,
                "config": config,
                "switchs": switchs,
                "interactive": interactive,
                "enabled": enabled,
            }
            if not enabled or not config:
                continue
            self._active_clients.append({
                "name": name,
                "type": ctype,
                "search_type": self.MESSAGE_DICT.get('channel').get(ctype, {}).get('search_type'),
                "client": self.__build_client(ctype, config, interactive),
                "config": config,
                "switchs": switchs,
                "interactive": interactive
            })

    @staticmethod
    def __build_client(ctype, conf, interactive=False):
        """
        构造客户端实例
        """
        if ctype == "wechat":
            return WeChat(conf, interactive)
        elif ctype == "telegram":
            return Telegram(conf, interactive)
        elif ctype == "serverchan":
            return ServerChan(conf)
        elif ctype == "bark":
            return Bark(conf)
        elif ctype == "pushpush":
            return PushPlus(conf)
        elif ctype == "iyuu":
            return IyuuMsg(conf)
        else:
            return None

    def get_webhook_ignore(self):
        """
        获取Emby/Jellyfin不通知的设备清单
        """
        return self.__webhook_ignore or []

    def __sendmsg(self, client, title, text="", image="", url="", user_id=""):
        """
        通用消息发送
        :param client: 消息端
        :param title: 消息标题
        :param text: 消息内容
        :param image: 图片URL
        :param url: 消息跳转地址
        :param user_id: 用户ID，如有则只发给这个用户
        :return: 发送状态、错误信息
        """
        if not client or not client.get('client'):
            return None
        log.info(f"【Message】发送{client.get('type')}消息服务{client.get('name')}：title={title}, text={text}")
        if self._domain:
            if url:
                url = "%s?next=%s" % (self._domain, url)
            else:
                url = self._domain
        else:
            url = ""
        self.messagecenter.insert_system_message(level="INFO", title=title, content=text)
        state, ret_msg = client.get('client').send_msg(title=title,
                                                       text=text,
                                                       image=image,
                                                       url=url,
                                                       user_id=user_id)
        if not state:
            log.error("【Message】发送消息失败：%s" % ret_msg)
        return state

    def send_channel_msg(self, channel, title, text="", image="", url="", user_id=""):
        """
        按渠道发送消息，用于消息交互
        :param channel: 消息渠道
        :param title: 消息标题
        :param text: 消息内容
        :param image: 图片URL
        :param url: 消息跳转地址
        :param user_id: 用户ID，如有则只发给这个用户
        :return: 发送状态、错误信息
        """
        if self._domain:
            if url:
                url = "%s?next=%s" % (self._domain, url)
            else:
                url = self._domain
        else:
            url = ""
        for client in self._active_clients:
            if client.get("search_type") == channel:
                state = self.__sendmsg(client=client,
                                       title=title,
                                       text=text,
                                       image=image,
                                       url=url,
                                       user_id=user_id)
                return state
        return False

    def __send_list_msg(self, client, medias, user_id, title):
        """
        发送选择类消息
        """
        if not client or not client.get('client'):
            return False, ""
        return client.get('client').send_list_msg(medias=medias,
                                                  user_id=user_id,
                                                  title=title,
                                                  url=self._domain)

    def send_channel_list_msg(self, channel, title, medias: list, user_id=""):
        """
        发送列表选择消息，用于消息交互
        :param channel: 消息渠道
        :param title: 消息标题
        :param medias: 媒体信息列表
        :param user_id: 用户ID，如有则只发给这个用户
        :return: 发送状态、错误信息
        """
        for client in self._active_clients:
            if client.get("search_type") == channel:
                state, ret_msg = self.__send_list_msg(client=client,
                                                      title=title,
                                                      medias=medias,
                                                      user_id=user_id)
                if not state:
                    log.error("【Message】发送消息失败：%s" % ret_msg)
                return state
        return False

    def send_download_message(self, in_from: SearchType, can_item):
        """
        发送下载的消息
        :param in_from: 下载来源
        :param can_item: 下载的媒体信息
        :return: 发送状态、错误信息
        """
        msg_title = f"{can_item.get_title_ep_string()} 开始下载"
        msg_text = f"{can_item.get_vote_string()}"
        msg_text = f"{msg_text}\n来自：{in_from.value}"
        if can_item.user_name:
            msg_text = f"{msg_text}\n用户：{can_item.user_name}"
        if can_item.site:
            if in_from == SearchType.USERRSS:
                msg_text = f"{msg_text}\n任务：{can_item.site}"
            else:
                msg_text = f"{msg_text}\n站点：{can_item.site}"
        if can_item.get_resource_type_string():
            msg_text = f"{msg_text}\n质量：{can_item.get_resource_type_string()}"
        if can_item.size:
            if str(can_item.size).isdigit():
                size = StringUtils.str_filesize(can_item.size)
            else:
                size = can_item.size
            msg_text = f"{msg_text}\n大小：{size}"
        if can_item.org_string:
            msg_text = f"{msg_text}\n种子：{can_item.org_string}"
        if can_item.seeders:
            msg_text = f"{msg_text}\n做种数：{can_item.seeders}"
        msg_text = f"{msg_text}\n促销：{can_item.get_volume_factor_string()}"
        if can_item.hit_and_run:
            msg_text = f"{msg_text}\nHit&Run：是"
        if can_item.description:
            html_re = re.compile(r'<[^>]+>', re.S)
            description = html_re.sub('', can_item.description)
            can_item.description = re.sub(r'<[^>]+>', '', description)
            msg_text = f"{msg_text}\n描述：{can_item.description}"
        # 发送消息
        for client in self._active_clients:
            if "download_start" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=msg_title,
                    text=msg_text,
                    image=can_item.get_message_image(),
                    url='downloading'
                )

    def send_transfer_movie_message(self, in_from: Enum, media_info, exist_filenum, category_flag):
        """
        发送转移电影的消息
        :param in_from: 转移来源
        :param media_info: 转移的媒体信息
        :param exist_filenum: 已存在的文件数
        :param category_flag: 二级分类开关
        :return: 发送状态、错误信息
        """
        msg_title = f"{media_info.get_title_string()} 已入库"
        if media_info.vote_average:
            msg_str = f"{media_info.get_vote_string()}，类型：电影"
        else:
            msg_str = "类型：电影"
        if media_info.category:
            if category_flag:
                msg_str = f"{msg_str}，类别：{media_info.category}"
        if media_info.get_resource_type_string():
            msg_str = f"{msg_str}，质量：{media_info.get_resource_type_string()}"
        msg_str = f"{msg_str}，大小：{StringUtils.str_filesize(media_info.size)}，来自：{in_from.value}"
        if exist_filenum != 0:
            msg_str = f"{msg_str}，{exist_filenum}个文件已存在"
        # 发送消息
        for client in self._active_clients:
            if "transfer_finished" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=msg_title,
                    text=msg_str,
                    image=media_info.get_message_image(),
                    url='history'
                )

    def send_transfer_tv_message(self, message_medias: dict, in_from: Enum):
        """
        发送转移电视剧/动漫的消息
        """
        for item_info in message_medias.values():
            if item_info.total_episodes == 1:
                msg_title = f"{item_info.get_title_string()} {item_info.get_season_episode_string()} 已入库"
            else:
                msg_title = f"{item_info.get_title_string()} {item_info.get_season_string()} 共{item_info.total_episodes}集 已入库"
            if item_info.vote_average:
                msg_str = f"{item_info.get_vote_string()}，类型：{item_info.type.value}"
            else:
                msg_str = f"类型：{item_info.type.value}"
            if item_info.category:
                msg_str = f"{msg_str}，类别：{item_info.category}"
            if item_info.total_episodes == 1:
                msg_str = f"{msg_str}，大小：{StringUtils.str_filesize(item_info.size)}，来自：{in_from.value}"
            else:
                msg_str = f"{msg_str}，总大小：{StringUtils.str_filesize(item_info.size)}，来自：{in_from.value}"
            # 发送消息
            for client in self._active_clients:
                if "transfer_finished" in client.get("switchs"):
                    self.__sendmsg(
                        client=client,
                        title=msg_title,
                        text=msg_str,
                        image=item_info.get_message_image(),
                        url='history')

    def send_download_fail_message(self, item, error_msg):
        """
        发送下载失败的消息
        """
        # 发送消息
        for client in self._active_clients:
            if "download_fail" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title="添加下载任务失败：%s %s" % (item.get_title_string(), item.get_season_episode_string()),
                    text=f"种子：{item.org_string}\n错误信息：{error_msg}",
                    image=item.get_message_image()
                )

    def send_rss_success_message(self, in_from: Enum, media_info):
        """
        发送订阅成功的消息
        """
        if media_info.type == MediaType.MOVIE:
            msg_title = f"{media_info.get_title_string()} 已添加订阅"
        else:
            msg_title = f"{media_info.get_title_string()} {media_info.get_season_string()} 已添加订阅"
        msg_str = f"类型：{media_info.type.value}"
        if media_info.vote_average:
            msg_str = f"{msg_str}，{media_info.get_vote_string()}"
        msg_str = f"{msg_str}，来自：{in_from.value}"
        if media_info.user_name:
            msg_str = f"{msg_str}，用户：{media_info.user_name}"
        # 发送消息
        for client in self._active_clients:
            if "rss_added" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=msg_title,
                    text=msg_str,
                    image=media_info.get_message_image(),
                    url='movie_rss' if media_info.type == MediaType.MOVIE else 'tv_rss'
                )

    def send_rss_finished_message(self, media_info):
        """
        发送订阅完成的消息，只针对电视剧
        """
        if media_info.type == MediaType.MOVIE:
            return
        else:
            msg_title = f"{media_info.get_title_string()} {media_info.get_season_string()} 已完成订阅"
        msg_str = f"类型：{media_info.type.value}"
        if media_info.vote_average:
            msg_str = f"{msg_str}，{media_info.get_vote_string()}"
        # 发送消息
        for client in self._active_clients:
            if "rss_finished" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=msg_title,
                    text=msg_str,
                    image=media_info.get_message_image(),
                    url='downloaded'
                )

    def send_site_signin_message(self, msgs: list):
        """
        发送站点签到消息
        """
        if not msgs:
            return
        # 发送消息
        for client in self._active_clients:
            if "site_signin" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title="站点签到",
                    text="\n".join(msgs)
                )

    def send_site_message(self, title=None, text=None):
        """
        发送站点消息
        """
        if not title:
            return
        if not text:
            text = ""
        # 发送消息
        for client in self._active_clients:
            if "site_message" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=title,
                    text=text
                )

    def send_transfer_fail_message(self, path, count, text):
        """
        发送转移失败的消息
        """
        if not path or not count:
            return
        # 发送消息
        for client in self._active_clients:
            if "transfer_fail" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=f"【{count} 个文件转移失败】",
                    text=f"源路径：{path}\n原因：{text}"
                )

    def send_brushtask_remove_message(self, title, text):
        """
        发送刷流删种的消息
        """
        if not title or not text:
            return
        # 发送消息
        for client in self._active_clients:
            if "brushtask_remove" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=title,
                    text=text
                )

    def send_brushtask_added_message(self, title, text):
        """
        发送刷流下种的消息
        """
        if not title or not text:
            return
        # 发送消息
        for client in self._active_clients:
            if "brushtask_added" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=title,
                    text=text
                )

    def send_mediaserver_message(self, title, text, image):
        """
        发送媒体服务器的消息
        """
        if not title or not text or image:
            return
        # 发送消息
        for client in self._active_clients:
            if "mediaserver_message" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=title,
                    text=text,
                    image=image
                )

    def get_message_client_info(self, cid=None):
        """
        获取消息端信息
        """
        if cid:
            return self._client_configs.get(str(cid))
        return self._client_configs

    def get_interactive_client(self):
        """
        查询当前可以交互的渠道
        """
        for client in self._active_clients:
            if client.get('interactive'):
                return client
        return {}

    def get_status(self, ctype=None, config=None):
        """
        测试消息设置状态
        """
        if not config or not ctype:
            return False
        return self.__build_client(ctype, config).get_status()
