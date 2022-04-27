from enum import Enum


class MediaType(Enum):
    TV = '电视剧'
    MOVIE = '电影'
    ANIME = '动漫'
    UNKNOWN = '未知'


class DownloaderType(Enum):
    QB = 'Qbittorrent'
    TR = 'Transmission'


class SyncType(Enum):
    MAN = "手动整理"
    MON = "目录同步"


class SearchType(Enum):
    WX = "微信搜索"
    WEB = "WEB搜索"
    DB = "豆瓣收藏"
    RSS = "RSS订阅"
    OT = "手动下载"
    TG = "Telegram搜索"


class RmtMode(Enum):
    LINK = "硬链接"
    SOFTLINK = "软链接"
    COPY = "复制"


class MatchMode(Enum):
    NORMAL = "正常模式"
    STRICT = "严格模式"


class OsType(Enum):
    WINDOWS = "Windows"
    LINUX = "Linux"


class IndexerType(Enum):
    JACKETT = "Jackett"
    PROWLARR = "Prowlarr"


class MediaServerType(Enum):
    JELLYFIN = "Jellyfin"
    EMBY = "Emby"
