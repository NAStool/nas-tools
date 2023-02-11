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
    PikPak = 'PikPak'


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
    SYNOLOGY = "Synology Chat"


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
    IATIME = "未活动时间"


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
    TNode = "TNode"


MovieTypes = ['MOV', '电影']
TvTypes = ['TV', '电视剧']
