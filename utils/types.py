from enum import Enum


class MediaType(Enum):
    TV = '电视剧'
    MOVIE = '电影'


class DownloaderType(Enum):
    QB = 'Qbittorrent'
    TR = 'Transmission'
