# coding: utf-8
from app.utils.types import *


class ModuleConf(object):
    # 菜单对应关系，配置WeChat应用中配置的菜单ID与执行命令的对应关系，需要手工修改
    # 菜单序号在https://work.weixin.qq.com/wework_admin/frame#apps 应用自定义菜单中维护，然后看日志输出的菜单序号是啥（按顺利能猜到的）....
    # 命令对应关系：/ptt 下载文件转移；/ptr 删种；/pts 站点签到；/rst 目录同步；/rss RSS下载
    WECHAT_MENU = {
        '_0_0': '/ptt',
        '_0_1': '/ptr',
        '_0_2': '/rss',
        '_1_0': '/rst',
        '_1_1': '/db',
        '_2_0': '/pts'
    }

    # 全量转移模式
    RMT_MODES = {
        "copy": RmtMode.COPY,
        "link": RmtMode.LINK,
        "softlink": RmtMode.SOFTLINK,
        "move": RmtMode.MOVE,
        "rclone": RmtMode.RCLONE,
        "rclonecopy": RmtMode.RCLONECOPY,
        "minio": RmtMode.MINIO,
        "miniocopy": RmtMode.MINIOCOPY
    }

    # 精简版转移模式
    RMT_MODES_LITE = {
        "copy": RmtMode.COPY,
        "link": RmtMode.LINK,
        "softlink": RmtMode.SOFTLINK,
        "move": RmtMode.MOVE
    }

    # 下载器
    DOWNLOADER_DICT = {
        "qbittorrent": DownloaderType.QB,
        "transmission": DownloaderType.TR,
        "client115": DownloaderType.Client115,
        "aria2": DownloaderType.Aria2
    }

    # 索引器
    INDEXER_DICT = {
        "prowlarr": IndexerType.PROWLARR,
        "jackett": IndexerType.JACKETT,
        "builtin": IndexerType.BUILTIN
    }

    # 媒体服务器
    MEDIASERVER_DICT = {
        "emby": MediaServerType.EMBY,
        "jellyfin": MediaServerType.JELLYFIN,
        "plex": MediaServerType.PLEX
    }

    # 消息通知类型
    MESSAGE_DICT = {
        "client": {
            "telegram": {
                "name": "Telegram",
                "img_url": "../static/img/telegram.png",
                "search_type": SearchType.TG,
                "config": {
                    "token": {
                        "id": "telegram_token",
                        "required": True,
                        "title": "Bot Token",
                        "tooltip": "telegram机器人的Token，关注BotFather创建机器人",
                        "type": "text"
                    },
                    "chat_id": {
                        "id": "telegram_chat_id",
                        "required": True,
                        "title": "Chat ID",
                        "tooltip": "接受消息通知的用户、群组或频道Chat ID，关注@getidsbot获取",
                        "type": "text"
                    },
                    "user_ids": {
                        "id": "telegram_user_ids",
                        "required": False,
                        "title": "User IDs",
                        "tooltip": "允许使用交互的用户Chat ID，留空则只允许管理用户使用，关注@getidsbot获取",
                        "type": "text",
                        "placeholder": "使用,分隔多个Id"
                    },
                    "admin_ids": {
                        "id": "telegram_admin_ids",
                        "required": False,
                        "title": "Admin IDs",
                        "tooltip": "允许使用管理命令的用户Chat ID，关注@getidsbot获取",
                        "type": "text",
                        "placeholder": "使用,分隔多个Id"
                    },
                    "webhook": {
                        "id": "telegram_webhook",
                        "required": False,
                        "title": "Webhook",
                        "tooltip": "Telegram机器人消息有两种模式：Webhook或消息轮循；开启后将使用Webhook方式，需要在基础设置中正确配置好外网访问地址，同时受Telegram官方限制，外网访问地址需要设置为以下端口之一：443, 80, 88, 8443，且需要有公网认证的可信SSL证书；关闭后将使用消息轮循方式，使用该方式时，需要在基础设置->安全处将Telegram ipv4源地址设置为127.0.0.1，推荐关闭Webhook",
                        "type": "switch"
                    }
                }
            },
            "wechat": {
                "name": "微信",
                "img_url": "../static/img/wechat.png",
                "search_type": SearchType.WX,
                "config": {
                    "corpid": {
                        "id": "wechat_corpid",
                        "required": True,
                        "title": "企业ID",
                        "tooltip": "每个企业都拥有唯一的corpid，获取此信息可在管理后台“我的企业”－“企业信息”下查看“企业ID”（需要有管理员权限）",
                        "type": "text"
                    },
                    "corpsecret": {
                        "id": "wechat_corpsecret",
                        "required": True,
                        "title": "应用Secret",
                        "tooltip": "每个应用都拥有唯一的secret，获取此信息可在管理后台“应用与小程序”－“自建”下查看“Secret”（需要有管理员权限）",
                        "type": "text",
                        "placeholder": "Secret"
                    },
                    "agentid": {
                        "id": "wechat_agentid",
                        "required": True,
                        "title": "应用ID",
                        "tooltip": "每个应用都拥有唯一的agentid，获取此信息可在管理后台“应用与小程序”－“自建”下查看“AgentId”（需要有管理员权限）",
                        "type": "text",
                        "placeholder": "AgentId",
                    },
                    "default_proxy": {
                        "id": "wechat_default_proxy",
                        "required": False,
                        "title": "消息推送代理",
                        "tooltip": "由于微信官方限制，2022年6月20日后创建的企业微信应用需要有固定的公网IP地址并加入IP白名单后才能发送消息，使用有固定公网IP的代理服务器转发可解决该问题；代理服务器需自行搭建，搭建方法可参考项目主页说明",
                        "type": "text",
                        "placeholder": "https://wechat.nastool.cn"
                    },
                    "token": {
                        "id": "wechat_token",
                        "required": False,
                        "title": "Token",
                        "tooltip": "需要交互功能时才需要填写，在微信企业应用管理后台-接收消息设置页面生成，填入完成后重启本应用，然后再在微信页面输入地址确定",
                        "type": "text",
                        "placeholder": "API接收消息Token"
                    },
                    "encodingAESKey": {
                        "id": "wechat_encodingAESKey",
                        "required": False,
                        "title": "EncodingAESKey",
                        "tooltip": "需要交互功能时才需要填写，在微信企业应用管理后台-接收消息设置页面生成，填入完成后重启本应用，然后再在微信页面输入地址确定",
                        "type": "text",
                        "placeholder": "API接收消息EncodingAESKey"
                    }
                }
            },
            "serverchan": {
                "name": "Server酱",
                "img_url": "../static/img/serverchan.png",
                "config": {
                    "sckey": {
                        "id": "serverchan_sckey",
                        "required": True,
                        "title": "SCKEY",
                        "tooltip": "填写ServerChan的API Key，SCT类型，在https://sct.ftqq.com/中申请",
                        "type": "text",
                        "placeholder": "SCT..."
                    }
                }
            },
            "bark": {
                "name": "Bark",
                "img_url": "../static/img/bark.webp",
                "config": {
                    "server": {
                        "id": "bark_server",
                        "required": True,
                        "title": "Bark服务器地址",
                        "tooltip": "自己搭建Bark服务端请实际配置，否则可使用：https://api.day.app",
                        "type": "text",
                        "placeholder": "https://api.day.app",
                        "default": "https://api.day.app"
                    },
                    "apikey": {
                        "id": "bark_apikey",
                        "required": True,
                        "title": "API Key",
                        "tooltip": "在Bark客户端中点击右上角的“...”按钮，选择“生成Bark Key”，然后将生成的KEY填入此处",
                        "type": "text"
                    }
                }
            },
            "pushdeer": {
                "name": "PushDeer",
                "img_url": "../static/img/pushdeer.png",
                "config": {
                    "server": {
                        "id": "pushdeer_server",
                        "required": True,
                        "title": "PushDeer服务器地址",
                        "tooltip": "自己搭建pushdeer服务端请实际配置，否则可使用：https://api2.pushdeer.com",
                        "type": "text",
                        "placeholder": "https://api2.pushdeer.com",
                        "default": "https://api2.pushdeer.com"
                    },
                    "apikey": {
                        "id": "pushdeer_apikey",
                        "required": True,
                        "title": "API Key",
                        "tooltip": "pushdeer客户端生成的KEY",
                        "type": "text"
                    }
                }
            },
            "pushplus": {
                "name": "PushPlus",
                "img_url": "../static/img/pushplus.jpg",
                "config": {
                    "token": {
                        "id": "pushplus_token",
                        "required": True,
                        "title": "Token",
                        "tooltip": "在PushPlus官网中申请，申请地址：http://pushplus.plus/",
                        "type": "text"
                    },
                    "channel": {
                        "id": "pushplus_channel",
                        "required": True,
                        "title": "推送渠道",
                        "tooltip": "使用PushPlus中配置的发送渠道，具体参考pushplus.plus官网文档说明，支持第三方webhook、钉钉、飞书、邮箱等",
                        "type": "select",
                        "options": {
                            "wechat": "微信",
                            "mail": "邮箱",
                            "webhook": "第三方Webhook"
                        },
                        "default": "wechat"
                    },
                    "topic": {
                        "id": "pushplus_topic",
                        "required": False,
                        "title": "群组编码",
                        "tooltip": "PushPlus中创建的群组，如未设置可为空",
                        "type": "text"
                    },
                    "webhook": {
                        "id": "pushplus_webhook",
                        "required": False,
                        "title": "Webhook编码",
                        "tooltip": "PushPlus中创建的webhook编码，发送渠道为第三方webhook时需要填入",
                    }
                }
            },
            "iyuu": {
                "name": "爱语飞飞",
                "img_url": "../static/img/iyuu.png",
                "config": {
                    "token": {
                        "id": "iyuumsg_token",
                        "required": True,
                        "title": "令牌Token",
                        "tooltip": "在爱语飞飞官网中申请，申请地址：https://iyuu.cn/",
                        "type": "text",
                        "placeholder": "登录https://iyuu.cn获取"
                    }
                }
            },
            "slack": {
                "name": "Slack",
                "img_url": "../static/img/slack.png",
                "search_type": SearchType.SLACK,
                "config": {
                    "bot_token": {
                        "id": "slack_bot_token",
                        "required": True,
                        "title": "Bot User OAuth Token",
                        "tooltip": "在Slack中创建应用，获取Bot User OAuth Token",
                        "type": "text",
                        "placeholder": "xoxb-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx"
                    },
                    "app_token": {
                        "id": "slack_app_token",
                        "required": True,
                        "title": "App-Level Token",
                        "tooltip": "在Slack中创建应用，获取App-Level Token",
                        "type": "text",
                        "placeholder": "xapp-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx"
                    }
                }
            },
            "gotify": {
                "name": "Gotify",
                "img_url": "../static/img/gotify.png",
                "config": {
                    "server": {
                        "id": "gotify_server",
                        "required": True,
                        "title": "Gotify服务器地址",
                        "tooltip": "自己搭建gotify服务端地址",
                        "type": "text",
                        "placeholder": "http://localhost:8800"
                    },
                    "token": {
                        "id": "gotify_token",
                        "required": True,
                        "title": "令牌Token",
                        "tooltip": "Gotify服务端APPS下创建的token",
                        "type": "text"
                    },
                    "priority": {
                        "id": "gotify_priority",
                        "required": False,
                        "title": "消息Priority",
                        "tooltip": "消息通知优先级, 请填写数字(1-8), 默认: 8",
                        "type": "text",
                        "placeholder": "8"
                    }
                }
            },
        },
        "switch": {
            "download_start": {
                "name": "新增下载",
                "fuc_name": "download_start"
            },
            "download_fail": {
                "name": "下载失败",
                "fuc_name": "download_fail"
            },
            "transfer_finished": {
                "name": "入库完成",
                "fuc_name": "transfer_finished"
            },
            "transfer_fail": {
                "name": "入库失败",
                "fuc_name": "transfer_fail"
            },
            "rss_added": {
                "name": "新增订阅",
                "fuc_name": "rss_added"
            },
            "rss_finished": {
                "name": "订阅完成",
                "fuc_name": "rss_finished"
            },
            "site_signin": {
                "name": "站点签到",
                "fuc_name": "site_signin"
            },
            "site_message": {
                "name": "站点消息",
                "fuc_name": "site_message"
            },
            "brushtask_added": {
                "name": "刷流下种",
                "fuc_name": "brushtask_added"
            },
            "brushtask_remove": {
                "name": "刷流删种",
                "fuc_name": "brushtask_remove"
            },
            "mediaserver_message": {
                "name": "媒体服务",
                "fuc_name": "mediaserver_message"
            },
            "custom_message": {
                "name": "自定义消息",
                "fuc_name": "custom_message"
            }
        }
    }

    # 自动删种配置
    TORRENTREMOVER_DICT = {
        "Qb": {
            "name": "Qbittorrent",
            "img_url": "../static/img/qbittorrent.png",
            "downloader_type": DownloaderType.QB,
            "torrent_state": {
                "downloading": "正在下载_传输数据",
                "stalledDL": "正在下载_未建立连接",
                "uploading": "正在上传_传输数据",
                "stalledUP": "正在上传_未建立连接",
                "error": "暂停_发生错误",
                "pausedDL": "暂停_下载未完成",
                "pausedUP": "暂停_下载完成",
                "missingFiles": "暂停_文件丢失",
                "checkingDL": "检查中_下载未完成",
                "checkingUP": "检查中_下载完成",
                "checkingResumeData": "检查中_启动时恢复数据",
                "forcedDL": "强制下载_忽略队列",
                "queuedDL": "等待下载_排队",
                "forcedUP": "强制上传_忽略队列",
                "queuedUP": "等待上传_排队",
                "allocating": "分配磁盘空间",
                "metaDL": "获取元数据",
                "moving": "移动文件",
                "unknown": "未知状态",
            }
        },
        "Tr": {
            "name": "Transmission",
            "img_url": "../static/img/transmission.png",
            "downloader_type": DownloaderType.TR,
            "torrent_state": {
                "downloading": "正在下载",
                "seeding": "正在上传",
                "download_pending": "等待下载_排队",
                "seed_pending": "等待上传_排队",
                "checking": "正在检查",
                "check_pending": "等待检查_排队",
                "stopped": "暂停",
            }
        }
    }

    # 搜索种子过滤属性
    TORRENT_SEARCH_PARAMS = {
        "restype": {
            "BLURAY": r"Blu-?Ray|BD|BDRIP",
            "REMUX": r"REMUX",
            "DOLBY": r"DOLBY|DOVI|\s+DV$|\s+DV\s+",
            "WEB": r"WEB-?DL|WEBRIP",
            "HDTV": r"U?HDTV",
            "UHD": r"UHD",
            "HDR": r"HDR",
            "3D": r"3D"
        },
        "pix": {
            "8k": r"8K",
            "4k": r"4K|2160P|X2160",
            "1080p": r"1080[PIX]|X1080",
            "720p": r"720P"
        }
    }

    # 网络测试对象
    NETTEST_TARGETS = [
        "www.themoviedb.org",
        "api.themoviedb.org",
        "api.tmdb.org",
        "image.tmdb.org",
        "webservice.fanart.tv",
        "api.telegram.org",
        "qyapi.weixin.qq.com",
        "www.opensubtitles.org"
    ]

    @staticmethod
    def get_enum_name(enum, value):
        """
        根据Enum的value查询name
        :param enum: 枚举
        :param value: 枚举值
        :return: 枚举名或None
        """
        for e in enum:
            if e.value == value:
                return e.name
        return None

    @staticmethod
    def get_enum_item(enum, value):
        """
        根据Enum的value查询name
        :param enum: 枚举
        :param value: 枚举值
        :return: 枚举项
        """
        for e in enum:
            if e.value == value:
                return e
        return None

    @staticmethod
    def get_dictenum_key(dictenum, value):
        """
        根据Enum dict的value查询key
        :param dictenum: 枚举字典
        :param value: 枚举类（字典值）的值
        :return: 字典键或None
        """
        for k, v in dictenum.items():
            if v.value == value:
                return k
        return None
