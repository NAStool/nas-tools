import re
import json
from enum import Enum

import log
from config import Config, MESSAGE_SETTING
from app.helper import DbHelper
from app.message import Bark, IyuuMsg, PushPlus, ServerChan, Telegram, WeChat
from app.utils import StringUtils
from app.message.message_center import MessageCenter
from app.utils.types import SearchType, MediaType


class Message:
    __msg_channel = None
    __msg_switch = None
    __webhook_ignore = None
    __domain = None
    __client_configs = {}
    normal_clients = {}
    interactive_client = None
    interactive_type = ""
    dbhelper = None
    messagecenter = None

    def __init__(self):
        self.dbhelper = DbHelper()
        self.messagecenter = MessageCenter()
        self.__domain = Config().get_domain()
        self.__msg_channel = MESSAGE_SETTING.get('channel')
        self.__msg_switch = MESSAGE_SETTING.get('switch')
        self.init_config()

    def init_config(self):
        self.__client_configs = {}
        self.interactive_client = None
        self.interactive_type = ""
        self.normal_clients = {
            "11": [],
            "12": [],
            "21": [],
            "22": [],
            "31": [],
            "32": [],
            "41": [],
            "42": [],
            "51": [],
            "52": [],
            "61": []
        }
        client_configs = self.dbhelper.get_message_client()
        for client_config in client_configs:
            cid = client_config.ID
            name = client_config.NAME
            ctype = client_config.TYPE
            config = json.loads(client_config.CONFIG) if client_config.CONFIG else {}
            switchs = json.loads(client_config.SWITCHS) if client_config.SWITCHS else {}
            interactive = client_config.INTERACTIVE
            enabled = client_config.ENABLED
            self.__client_configs[str(client_config.ID)] = {
                "id": cid,
                "name": name,
                "type": ctype,
                "config": config,
                "switchs": switchs,
                "interactive": interactive,
                "enabled": enabled,
            }
            # 跳过不启用
            if not enabled:
                continue
            # 跳过不启用
            if not config:
                continue
            # 实例化
            exec(f"self.client_{cid} = {self.__msg_channel[str(ctype)].get('name')}(config={config}, name='{name}')")
            if interactive:
                self.interactive_type = self.__msg_channel[str(ctype)].get('name')
                self.interactive_client = eval(f"self.client_{cid}")
            if not switchs:
                for switch in self.normal_clients:
                    self.normal_clients[switch].append(eval(f"self.client_{cid}"))
            else:
                for switch in switchs:
                    self.normal_clients[switch].append(eval(f"self.client_{cid}"))

    def get_webhook_ignore(self):
        """
        获取Emby/Jellyfin不通知的设备清单
        """
        return self.__webhook_ignore or []

    def sendmsg(self, client, title, text="", image="", url="", user_id=""):
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
        if not client:
            return None
        log.info(f"【Message】发送{client.type}消息服务{client.name}：title={title}, text={text}")
        if self.__domain:
            if url:
                url = "%s?next=%s" % (self.__domain, url)
            else:
                url = self.__domain
        else:
            url = ""
        self.messagecenter.insert_system_message(level="INFO", title=title, content=text)
        state, ret_msg = client.send_msg(title, text, image, url, user_id)
        if not state:
            log.error("【Message】发送消息失败：%s" % ret_msg)
        return state

    def send_channel_msg(self, channel, title, text="", image="", url="", user_id=""):
        """
        按渠道发送消息
        :param channel: 消息渠道
        :param title: 消息标题
        :param text: 消息内容
        :param image: 图片URL
        :param url: 消息跳转地址
        :param user_id: 用户ID，如有则只发给这个用户
        :return: 发送状态、错误信息
        """
        if not self.interactive_client:
            return False
        if self.__domain:
            if url:
                url = "%s?next=%s" % (self.__domain, url)
            else:
                url = self.__domain
        else:
            url = ""
        if channel == SearchType.TG:
            if self.interactive_type != "Telegram":
                log.error("【Message】发送消息失败：搜索渠道为TG，但未启用TG消息服务")
                return False
            state, ret_msg = self.interactive_client.send_msg(title, text, image, url, user_id)
        elif channel == SearchType.WX:
            if self.interactive_type != "WeChat":
                log.error("【Message】发送消息失败：搜索渠道为TG，但未启用TG消息服务")
                return False
            state, ret_msg = self.interactive_client.send_msg(title, text, image, url, user_id)
        else:
            state, ret_msg = self.interactive_client.send_msg(title, text, image, url, user_id)
        if not state:
            log.error("【Message】发送消息失败：%s" % ret_msg)
        return state

    def send_channel_list_msg(self, channel, title, medias: list, user_id=""):
        """
        发送列表选择消息
        :param channel: 消息渠道
        :param title: 消息标题
        :param medias: 媒体信息列表
        :param user_id: 用户ID，如有则只发给这个用户
        :return: 发送状态、错误信息
        """
        if channel == SearchType.TG:
            state, ret_msg = Telegram().send_list_msg(title, medias, user_id)
        elif channel == SearchType.WX:
            WeChat().send_msg(title, user_id=user_id)
            state, ret_msg = WeChat().send_list_msg(medias, self.__domain, user_id)
        else:
            return False
        if not state:
            log.error("【Message】发送消息失败：%s" % ret_msg)
        return state

    def send_download_message(self, in_from: SearchType, can_item):
        """
        发送下载的消息
        :param in_from: 下载来源
        :param can_item: 下载的媒体信息
        :return: 发送状态、错误信息
        """
        # 获取消息端
        clients = self.normal_clients.get("11")
        if not clients:
            return
        msg_title = can_item.get_title_ep_vote_string()
        msg_text = f"{in_from.value}的{can_item.type.value} {can_item.get_title_string()} {can_item.get_season_episode_string()} 已开始下载"
        if can_item.site:
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
        for client in clients:
            self.sendmsg(
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
        # 获取消息端
        clients = self.normal_clients.get("21")
        if not clients:
            return
        msg_title = f"{media_info.get_title_string()} 转移完成"
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
        for client in clients:
            self.sendmsg(
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
        # 获取消息端
        clients = self.normal_clients.get("21")
        if not clients:
            return
        for item_info in message_medias.values():
            if item_info.total_episodes == 1:
                msg_title = f"{item_info.get_title_string()} {item_info.get_season_episode_string()} 转移完成"
            else:
                msg_title = f"{item_info.get_title_string()} {item_info.get_season_string()} 转移完成"
            if item_info.vote_average:
                msg_str = f"{item_info.get_vote_string()}，类型：{item_info.type.value}"
            else:
                msg_str = f"类型：{item_info.type.value}"
            if item_info.category:
                msg_str = f"{msg_str}，类别：{item_info.category}"
            if item_info.total_episodes == 1:
                msg_str = f"{msg_str}，大小：{StringUtils.str_filesize(item_info.size)}，来自：{in_from.value}"
            else:
                msg_str = f"{msg_str}，共{item_info.total_episodes}集，总大小：{StringUtils.str_filesize(item_info.size)}，来自：{in_from.value}"
            # 发送消息
            for client in clients:
                self.sendmsg(
                    client=client,
                    title=msg_title,
                    text=msg_str,
                    image=item_info.get_message_image(),
                    url='history')

    def send_download_fail_message(self, item, error_msg):
        """
        发送下载失败的消息
        """
        # 获取消息端
        clients = self.normal_clients.get("12")
        if not clients:
            return
        # 发送消息
        for client in clients:
            self.sendmsg(
                client=client,
                title="添加下载任务失败：%s %s" % (item.get_title_string(), item.get_season_episode_string()),
                text=f"种子：{item.org_string}\n错误信息：{error_msg}",
                image=item.get_message_image()
            )

    def send_rss_success_message(self, in_from: Enum, media_info, user_id=""):
        """
        发送订阅成功的消息
        """
        # 获取消息端
        if not self.interactive_client:
            return
        if media_info.type == MediaType.MOVIE:
            msg_title = f"{media_info.get_title_string()} 已添加订阅"
        else:
            msg_title = f"{media_info.get_title_string()} {media_info.get_season_string()} 已添加订阅"
        msg_str = f"类型：{media_info.type.value}"
        if media_info.vote_average:
            msg_str = f"{msg_str}，{media_info.get_vote_string()}"
        msg_str = f"{msg_str}，来自：{in_from.value}"
        # 发送消息
        self.send_channel_msg(
            channel=in_from,
            title=msg_title,
            text=msg_str,
            image=media_info.get_message_image(),
            url='movie_rss' if media_info.type == MediaType.MOVIE else 'tv_rss',
            user_id=user_id
        )

    def send_rss_finished_message(self, media_info):
        """
        发送订阅完成的消息，只针对电视剧
        """
        # 获取消息端
        clients = self.normal_clients.get("32")
        if not clients:
            return
        if media_info.type == MediaType.MOVIE:
            return
        else:
            msg_title = f"{media_info.get_title_string()} {media_info.get_season_string()} 已完成订阅"
        msg_str = f"类型：{media_info.type.value}"
        if media_info.vote_average:
            msg_str = f"{msg_str}，{media_info.get_vote_string()}"
        # 发送消息
        for client in clients:
            self.sendmsg(
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
        # 获取消息端
        clients = self.normal_clients.get("41")
        if not clients:
            return
        # 发送消息
        for client in clients:
            self.sendmsg(
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
        # 获取消息端
        clients = self.normal_clients.get("42")
        if not clients:
            return
        # 发送消息
        for client in clients:
            self.sendmsg(
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
        # 获取消息端
        clients = self.normal_clients.get("22")
        if not clients:
            return
        # 发送消息
        for client in clients:
            self.sendmsg(
                client=client,
                title=f"【{count} 个文件转移失败】",
                text=f"路径：{path}\n原因：{text}"
            )

    def send_brushtask_remove_message(self, title, text):
        """
        发送刷流删种的消息
        """
        if not title or not text:
            return
        # 获取消息端
        clients = self.normal_clients.get("51")
        if not clients:
            return
        # 发送消息
        for client in clients:
            self.sendmsg(
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
        # 获取消息端
        clients = self.normal_clients.get("52")
        if not clients:
            return
        # 发送消息
        for client in clients:
            self.sendmsg(
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
        # 获取消息端
        clients = self.normal_clients.get("61")
        if not clients:
            return
        # 发送消息
        for client in clients:
            self.sendmsg(
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
            return self.__client_configs.get(str(cid))
        return self.__client_configs

    def get_status(self, ctype=None, config=None):
        """
        测试消息设置状态
        """
        if not config or not ctype:
            return False
        client = eval(f"{self.__msg_channel[str(ctype)].get('name')}({config})")
        if client:
            return client.get_status()
        else:
            return False
    