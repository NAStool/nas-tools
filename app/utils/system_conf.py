# coding: utf-8
from app.utils.types import *


class SystemConf(object):
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

    # 转移模式
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
                "search_type": SearchType.TG
            },
            "wechat": {
                "name": "微信",
                "img_url": "../static/img/wechat.png",
                "search_type": SearchType.WX
            },
            "serverchan": {
                "name": "Server酱",
                "img_url": "../static/img/serverchan.png"
            },
            "bark": {
                "name": "Bark",
                "img_url": "../static/img/bark.webp"
            },
            "pushdeer": {
                "name": "PushDeer",
                "img_url": "../static/img/pushdeer.png"
            },
            "pushplus": {
                "name": "PushPlus",
                "img_url": "../static/img/pushplus.jpg"
            },
            "iyuu": {
                "name": "爱语飞飞",
                "img_url": "../static/img/iyuu.png"
            },
            "slack": {
                "name": "Slack",
                "img_url": "../static/img/slack.png",
                "search_type": SearchType.SLACK
            },
            "gotify": {
                "name": "Gotify",
                "img_url": "../static/img/gotify.png"
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
