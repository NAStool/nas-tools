from enum import Enum


class MediaType(Enum):
    TV = '电视剧'
    MOVIE = '电影'
    ANIME = '动漫'
    UNKNOWN = '未知'


class DownloaderType(Enum):
    QB = 'Qbittorrent'
    TR = 'Transmission'
    Client115 = '115网盘'
    Aria2 = 'Aria2'


class SyncType(Enum):
    MAN = "手动整理"
    MON = "目录同步"


class SearchType(Enum):
    WX = "微信"
    WEB = "WEB"
    DB = "豆瓣"
    RSS = "电影/电视剧订阅"
    USERRSS = "自定义订阅"
    OT = "手动下载"
    TG = "Telegram"
    API = "第三方API请求"
    SLACK = "Slack"


class RmtMode(Enum):
    LINK = "硬链接"
    SOFTLINK = "软链接"
    COPY = "复制"
    MOVE = "移动"
    RCLONECOPY = "Rclone复制"
    RCLONE = "Rclone移动"
    MINIOCOPY = "Minio复制"
    MINIO = "Minio移动"


class MatchMode(Enum):
    NORMAL = "正常模式"
    STRICT = "严格模式"


class OsType(Enum):
    WINDOWS = "Windows"
    LINUX = "Linux"
    SYNOLOGY = "Synology"
    MACOS = "MacOS"
    DOCKER = "Docker"


class IndexerType(Enum):
    JACKETT = "Jackett"
    PROWLARR = "Prowlarr"
    BUILTIN = "Indexer"


class MediaServerType(Enum):
    JELLYFIN = "Jellyfin"
    EMBY = "Emby"
    PLEX = "Plex"


class BrushDeleteType(Enum):
    NOTDELETE = "不删除"
    SEEDTIME = "做种时间"
    RATIO = "分享率"
    UPLOADSIZE = "上传量"
    DLTIME = "下载耗时"
    AVGUPSPEED = "平均上传速度"


class SystemDictType(Enum):
    BrushMessageSwitch = "刷流消息开关"
    BrushForceUpSwitch = "刷流强制做种开关"


# 站点框架
class SiteSchema(Enum):
    DiscuzX = "Discuz!"
    Gazelle = "Gazelle"
    Ipt = "IPTorrents"
    NexusPhp = "NexusPhp"
    NexusProject = "NexusProject"
    NexusRabbit = "NexusRabbit"
    SmallHorse = "Small Horse"
    Unit3d = "Unit3d"
    TorrentLeech = "TorrentLeech"
    FileList = "FileList"


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
