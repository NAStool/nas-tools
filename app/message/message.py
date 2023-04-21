import json
import re
import time
from enum import Enum

import log
from app.conf import ModuleConf
from app.helper import DbHelper, SubmoduleHelper
from app.message.message_center import MessageCenter
from app.utils import StringUtils, ExceptionUtils
from app.utils.commons import singleton
from app.utils.types import SearchType, MediaType
from config import Config
from web.backend.web_utils import WebUtils


@singleton
class Message(object):
    dbhelper = None
    messagecenter = None
    _message_schemas = []
    _active_clients = []
    _active_interactive_clients = {}
    _client_configs = {}
    _domain = None

    def __init__(self):
        self._message_schemas = SubmoduleHelper.import_submodules(
            'app.message.client',
            filter_func=lambda _, obj: hasattr(obj, 'schema')
        )
        log.debug(f"【Message】加载消息服务：{self._message_schemas}")
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()
        self.messagecenter = MessageCenter()

        self._domain = Config().get_domain()
        # 停止旧服务
        if self._active_clients:
            for active_client in self._active_clients:
                if active_client.get("search_type") in self.get_search_types():
                    client = active_client.get("client")
                    if client and hasattr(client, "stop_service"):
                        client.stop_service()
        # 活跃的客户端
        self._active_clients = []
        # 活跃的交互客户端
        self._active_interactive_clients = {}
        # 全量客户端配置
        self._client_configs = {}
        for client_config in self.dbhelper.get_message_client() or []:
            config = json.loads(client_config.CONFIG) if client_config.CONFIG else {}
            config.update({
                "interactive": client_config.INTERACTIVE
            })
            client_conf = {
                "id": client_config.ID,
                "name": client_config.NAME,
                "type": client_config.TYPE,
                "config": config,
                "switchs": json.loads(client_config.SWITCHS) if client_config.SWITCHS else [],
                "interactive": client_config.INTERACTIVE,
                "enabled": client_config.ENABLED
            }
            self._client_configs[str(client_config.ID)] = client_conf
            if not client_config.ENABLED or not config:
                continue
            client = {
                "search_type": ModuleConf.MESSAGE_CONF.get('client').get(client_config.TYPE, {}).get('search_type'),
                "max_length": ModuleConf.MESSAGE_CONF.get('client').get(client_config.TYPE, {}).get('max_length'),
                "client": self.__build_class(ctype=client_config.TYPE, conf=config)
            }
            client.update(client_conf)
            self._active_clients.append(client)
            if client.get("interactive"):
                self._active_interactive_clients[client.get("search_type")] = client

    def __build_class(self, ctype, conf):
        for message_schema in self._message_schemas:
            try:
                if message_schema.match(ctype):
                    return message_schema(conf)
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
        return None

    def get_status(self, ctype=None, config=None):
        """
        测试消息设置状态
        """
        if not config or not ctype:
            return False
        # 测试状态不启动监听服务
        state, ret_msg = self.__build_class(ctype=ctype,
                                            conf=config).send_msg(title="测试",
                                                                  text="这是一条测试消息",
                                                                  url="https://github.com/NAStool/nas-tools")
        if not state:
            log.error(f"【Message】{ctype} 发送测试消息失败：%s" % ret_msg)
        return state

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
        cname = client.get('name')
        log.info(f"【Message】发送消息 {cname}：title={title}, text={text}")
        if self._domain:
            if url:
                if not url.startswith("http"):
                    url = "%s?next=%s" % (self._domain, url)
            else:
                url = ""
        else:
            url = ""
        # 消息内容分段
        max_length = client.get("max_length")
        if max_length:
            texts = StringUtils.split_text(text, max_length)
        else:
            texts = [text]
        # 循环发送
        for txt in texts:
            if not title:
                title = txt
                txt = ""
            state, ret_msg = client.get('client').send_msg(title=title,
                                                           text=txt,
                                                           image=image,
                                                           url=url,
                                                           user_id=user_id)
            title = None
            if not state:
                log.error(f"【Message】{cname} 消息发送失败：%s" % ret_msg)
                return state
        return True

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
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=title, content=text)
        # 发送消息
        client = self._active_interactive_clients.get(channel)
        if client:
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
            return None
        cname = client.get('name')
        log.info(f"【Message】发送消息 {cname}：title={title}")
        state, ret_msg = client.get('client').send_list_msg(medias=medias,
                                                            user_id=user_id,
                                                            title=title,
                                                            url=self._domain)
        if not state:
            log.error(f"【Message】{cname} 发送消息失败：%s" % ret_msg)
        return state

    def send_channel_list_msg(self, channel, title, medias: list, user_id=""):
        """
        发送列表选择消息，用于消息交互
        :param channel: 消息渠道
        :param title: 消息标题
        :param medias: 媒体信息列表
        :param user_id: 用户ID，如有则只发给这个用户
        :return: 发送状态、错误信息
        """
        client = self._active_interactive_clients.get(channel)
        if client:
            state = self.__send_list_msg(client=client,
                                         title=title,
                                         medias=medias,
                                         user_id=user_id)
            return state
        return False

    def send_download_message(self, in_from: SearchType, can_item, download_setting_name=None, downloader_name=None):
        """
        发送下载的消息
        :param in_from: 下载来源
        :param can_item: 下载的媒体信息
        :param download_setting_name: 下载设置名称
        :param downloader_name: 下载器名称
        :return: 发送状态、错误信息
        """
        msg_title = f"{can_item.get_title_ep_string()} 开始下载"
        msg_text = f"{can_item.get_star_string()}"
        msg_text = f"{msg_text}\n来自：{in_from.value}"
        if download_setting_name:
            msg_text = f"{msg_text}\n下载设置：{download_setting_name}"
        if downloader_name:
            msg_text = f"{msg_text}\n下载器：{downloader_name}"
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
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=msg_title, content=msg_text)
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
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=msg_title, content=msg_str)
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
            # 插入消息中心
            self.messagecenter.insert_system_message(level="INFO", title=msg_title, content=msg_str)
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
        title = "添加下载任务失败：%s %s" % (item.get_title_string(), item.get_season_episode_string())
        text = f"站点：{item.site}\n种子名称：{item.org_string}\n种子链接：{item.enclosure}\n错误信息：{error_msg}"
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=title, content=text)
        # 发送消息
        for client in self._active_clients:
            if "download_fail" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=title,
                    text=text,
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
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=msg_title, content=msg_str)
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
            if media_info.over_edition:
                msg_title = f"{media_info.get_title_string()} {media_info.get_season_string()} 已完成洗版"
            else:
                msg_title = f"{media_info.get_title_string()} {media_info.get_season_string()} 已完成订阅"
        msg_str = f"类型：{media_info.type.value}"
        if media_info.vote_average:
            msg_str = f"{msg_str}，{media_info.get_vote_string()}"
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=msg_title, content=msg_str)
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
        title = "站点签到"
        # 按照结果分组，失败的放在前面
        success_sites = [x for x in msgs if "失败" not in x]
        failed_sites = [x for x in msgs if "失败" in x]

        # 统计信息
        text = f"共 {len(success_sites) + len(failed_sites)} ，成功 {len(success_sites)} 个，失败 {len(failed_sites)} 个\n"
        text += "\n-----失败-----\n"
        text += "\n".join(failed_sites)
        text += "\n-----成功-----\n"
        text += "\n".join(success_sites)
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=title, content=text)
        # 发送消息
        for client in self._active_clients:
            if "site_signin" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=title,
                    text=text
                )

    def send_site_message(self, title=None, text=None):
        """
        发送站点消息
        """
        if not title:
            return
        if not text:
            text = ""
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=title, content=text)
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
        title = f"【{count} 个文件入库失败】"
        text = f"源路径：{path}\n原因：{text}"
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=title, content=text)
        # 发送消息
        for client in self._active_clients:
            if "transfer_fail" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=title,
                    text=text,
                    url="unidentification"
                )

    def send_auto_remove_torrents_message(self, title, text):
        """
        发送自动删种的消息
        """
        if not title or not text:
            return
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=title, content=text)
        # 发送消息
        for client in self._active_clients:
            if "auto_remove_torrents" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=title,
                    text=text,
                    url="torrent_remove"
                )

    def send_brushtask_remove_message(self, title, text):
        """
        发送刷流删种的消息
        """
        if not title or not text:
            return
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=title, content=text)
        # 发送消息
        for client in self._active_clients:
            if "brushtask_remove" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=title,
                    text=text,
                    url="brushtask"
                )

    def send_brushtask_added_message(self, title, text):
        """
        发送刷流下种的消息
        """
        if not title or not text:
            return
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=title, content=text)
        # 发送消息
        for client in self._active_clients:
            if "brushtask_added" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=title,
                    text=text,
                    url="brushtask"
                )

    def send_mediaserver_message(self, event_info: dict, channel, image_url):
        """
        发送媒体服务器的消息
        :param event_info: 事件信息
        :param channel: 服务器类型:
        :param image_url: 图片
        """
        if not event_info or not channel:
            return
        # 拼装消息内容
        _webhook_actions = {
            "system.webhooktest": "测试",
            "playback.start": "开始播放",
            "playback.stop": "停止播放",
            "user.authenticated": "登录成功",
            "user.authenticationfailed": "登录失败",
            "media.play": "开始播放",
            "media.stop": "停止播放",
            "PlaybackStart": "开始播放",
            "PlaybackStop": "停止播放",
            "item.rate": "标记了"
        }
        _webhook_images = {
            "Emby": "https://emby.media/notificationicon.png",
            "Plex": "https://www.plex.tv/wp-content/uploads/2022/04/new-logo-process-lines-gray.png",
            "Jellyfin": "https://play-lh.googleusercontent.com/SCsUK3hCCRqkJbmLDctNYCfehLxsS4ggD1ZPHIFrrAN1Tn9yhjmGMPep2D9lMaaa9eQi"
        }

        if not _webhook_actions.get(event_info.get('event')):
            return

        # 消息标题
        if event_info.get('item_type') == "TV":
            message_title = f"{_webhook_actions.get(event_info.get('event'))}剧集 {event_info.get('item_name')}"
        elif event_info.get('item_type') == "MOV":
            message_title = f"{_webhook_actions.get(event_info.get('event'))}电影 {event_info.get('item_name')}"
        elif event_info.get('item_type') == "AUD":
            message_title = f"{_webhook_actions.get(event_info.get('event'))}有声书 {event_info.get('item_name')}"
        else:
            message_title = f"{_webhook_actions.get(event_info.get('event'))}"

        # 消息内容
        message_texts = []
        if event_info.get('user_name'):
            message_texts.append(f"用户：{event_info.get('user_name')}")
        if event_info.get('device_name'):
            message_texts.append(f"设备：{event_info.get('client')} {event_info.get('device_name')}")
        if event_info.get('ip'):
            message_texts.append(f"位置：{event_info.get('ip')} {WebUtils.get_location(event_info.get('ip'))}")
        if event_info.get('percentage'):
            percentage = round(float(event_info.get('percentage')), 2)
            message_texts.append(f"进度：{percentage}%")
        if event_info.get('overview'):
            message_texts.append(f"剧情：{event_info.get('overview')}")
        message_texts.append(f"时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}")

        # 消息图片
        if not image_url:
            image_url = _webhook_images.get(channel)

        # 插入消息中心
        message_content = "\n".join(message_texts)
        self.messagecenter.insert_system_message(level="INFO", title=message_title, content=message_content)

        # 发送消息
        for client in self._active_clients:
            if "mediaserver_message" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=message_title,
                    text=message_content,
                    image=image_url
                )

    def send_plugin_message(self, title, text="", image=""):
        """
        发送插件消息
        """
        if not title:
            return
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=title, content=text)
        # 发送消息
        for client in self._active_clients:
            if "custom_message" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=title,
                    text=text,
                    image=image
                )

    def send_custom_message(self, clients, title, text="", image=""):
        """
        发送自定义消息
        """
        if not title:
            return
        if not clients:
            return
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=title, content=text)
        # 发送消息
        for client in self._active_clients:
            if str(client.get("id")) in clients:
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

    def get_interactive_client(self, client_type=None):
        """
        查询当前可以交互的渠道
        """
        if client_type:
            return self._active_interactive_clients.get(client_type)
        else:
            return [client for client in self._active_interactive_clients.values()]

    @staticmethod
    def get_search_types():
        """
        查询可交互的渠道
        """
        return [info.get("search_type")
                for info in ModuleConf.MESSAGE_CONF.get('client').values()
                if info.get('search_type')]

    def send_user_statistics_message(self, msgs: list):
        """
        发送数据统计消息
        """
        if not msgs:
            return
        title = "站点数据统计"
        text = "\n".join(msgs)
        # 插入消息中心
        self.messagecenter.insert_system_message(level="INFO", title=title, content=text)
        # 发送消息
        for client in self._active_clients:
            if "ptrefresh_date_message" in client.get("switchs"):
                self.__sendmsg(
                    client=client,
                    title=title,
                    text=text
                )
