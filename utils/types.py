from enum import Enum


class MediaType(Enum):
    TV = '电视剧'
    MOVIE = '电影'


class DownloaderType(Enum):
    QB = 'Qbittorrent'
    TR = 'Transmission'


class SyncType(Enum):
    MAN = "手动整理"
    MON = "目录监控"
