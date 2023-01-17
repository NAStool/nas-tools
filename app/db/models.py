# coding: utf-8
from sqlalchemy import Column, Float, Index, Integer, Text, text, Sequence
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
BaseMedia = declarative_base()


class CONFIGFILTERGROUP(Base):
    __tablename__ = 'CONFIG_FILTER_GROUP'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    GROUP_NAME = Column(Text)
    IS_DEFAULT = Column(Text)
    NOTE = Column(Text)


class CONFIGFILTERRULES(Base):
    __tablename__ = 'CONFIG_FILTER_RULES'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    GROUP_ID = Column(Text, index=True)
    ROLE_NAME = Column(Text)
    PRIORITY = Column(Text)
    INCLUDE = Column(Text)
    EXCLUDE = Column(Text)
    SIZE_LIMIT = Column(Text)
    NOTE = Column(Text)


class CONFIGRSSPARSER(Base):
    __tablename__ = 'CONFIG_RSS_PARSER'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    NAME = Column(Text, index=True)
    TYPE = Column(Text)
    FORMAT = Column(Text)
    PARAMS = Column(Text)
    NOTE = Column(Text)
    SYSDEF = Column(Text)


class CONFIGSITE(Base):
    __tablename__ = 'CONFIG_SITE'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    NAME = Column(Text)
    PRI = Column(Text)
    RSSURL = Column(Text)
    SIGNURL = Column(Text)
    COOKIE = Column(Text)
    INCLUDE = Column(Text)
    EXCLUDE = Column(Text)
    SIZE = Column(Text)
    NOTE = Column(Text)


class CONFIGSYNCPATHS(Base):
    __tablename__ = 'CONFIG_SYNC_PATHS'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    SOURCE = Column(Text)
    DEST = Column(Text)
    UNKNOWN = Column(Text)
    MODE = Column(Text)
    RENAME = Column(Integer)
    ENABLED = Column(Integer)
    NOTE = Column(Text)


class CONFIGUSERS(Base):
    __tablename__ = 'CONFIG_USERS'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    NAME = Column(Text, index=True)
    PASSWORD = Column(Text)
    PRIS = Column(Text)


class CONFIGUSERRSS(Base):
    __tablename__ = 'CONFIG_USER_RSS'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    NAME = Column(Text, index=True)
    ADDRESS = Column(Text)
    PARSER = Column(Text)
    INTERVAL = Column(Text)
    USES = Column(Text)
    INCLUDE = Column(Text)
    EXCLUDE = Column(Text)
    FILTER = Column(Text)
    UPDATE_TIME = Column(Text)
    PROCESS_COUNT = Column(Text)
    STATE = Column(Text)
    SAVE_PATH = Column(Text)
    DOWNLOAD_SETTING = Column(Integer)
    RECOGNIZATION = Column(Text)
    OVER_EDITION = Column(Integer)
    SITES = Column(Text)
    FILTER_ARGS = Column(Text)
    MEDIAINFOS = Column(Text)
    NOTE = Column(Text)


class CUSTOMWORDS(Base):
    __tablename__ = 'CUSTOM_WORDS'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    REPLACED = Column(Text)
    REPLACE = Column(Text)
    FRONT = Column(Text)
    BACK = Column(Text)
    OFFSET = Column(Text)
    TYPE = Column(Integer)
    GROUP_ID = Column(Integer)
    SEASON = Column(Integer)
    ENABLED = Column(Integer)
    REGEX = Column(Integer)
    HELP = Column(Text)
    NOTE = Column(Text)


class CUSTOMWORDGROUPS(Base):
    __tablename__ = 'CUSTOM_WORD_GROUPS'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    TITLE = Column(Text)
    YEAR = Column(Text)
    TYPE = Column(Integer)
    TMDBID = Column(Integer)
    SEASON_COUNT = Column(Integer)
    NOTE = Column(Text)


class DOUBANMEDIAS(Base):
    __tablename__ = 'DOUBAN_MEDIAS'
    __table_args__ = (
        Index('INDX_DOUBAN_MEDIAS_NAME', 'NAME', 'YEAR'),
    )

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    NAME = Column(Text)
    YEAR = Column(Text)
    TYPE = Column(Text)
    RATING = Column(Text)
    IMAGE = Column(Text)
    STATE = Column(Text)
    ADD_TIME = Column(Text)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class DOWNLOADHISTORY(Base):
    __tablename__ = 'DOWNLOAD_HISTORY'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    TITLE = Column(Text, index=True)
    YEAR = Column(Text)
    TYPE = Column(Text)
    TMDBID = Column(Text)
    VOTE = Column(Text)
    POSTER = Column(Text)
    OVERVIEW = Column(Text)
    TORRENT = Column(Text)
    ENCLOSURE = Column(Text)
    SITE = Column(Text)
    DESC = Column(Text)
    DATE = Column(Text, index=True)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class DOWNLOADSETTING(Base):
    __tablename__ = 'DOWNLOAD_SETTING'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    NAME = Column(Text)
    CATEGORY = Column(Text)
    TAGS = Column(Text)
    CONTENT_LAYOUT = Column(Integer)
    IS_PAUSED = Column(Integer)
    UPLOAD_LIMIT = Column(Integer)
    DOWNLOAD_LIMIT = Column(Integer)
    RATIO_LIMIT = Column(Integer)
    SEEDING_TIME_LIMIT = Column(Integer)
    DOWNLOADER = Column(Text)
    NOTE = Column(Text)


class MESSAGECLIENT(Base):
    __tablename__ = 'MESSAGE_CLIENT'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    NAME = Column(Text)
    TYPE = Column(Text)
    CONFIG = Column(Text)
    SWITCHS = Column(Text)
    INTERACTIVE = Column(Integer)
    ENABLED = Column(Integer)
    NOTE = Column(Text)


class RSSHISTORY(Base):
    __tablename__ = 'RSS_HISTORY'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    TYPE = Column(Text)
    RSSID = Column(Text, index=True)
    NAME = Column(Text)
    YEAR = Column(Text)
    TMDBID = Column(Text)
    SEASON = Column(Text)
    IMAGE = Column(Text)
    DESC = Column(Text)
    TOTAL = Column(Integer)
    START = Column(Integer)
    FINISH_TIME = Column(Text)
    NOTE = Column(Text)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class RSSMOVIES(Base):
    __tablename__ = 'RSS_MOVIES'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    NAME = Column(Text, index=True)
    YEAR = Column(Text)
    TMDBID = Column(Text)
    IMAGE = Column(Text)
    RSS_SITES = Column(Text)
    SEARCH_SITES = Column(Text)
    OVER_EDITION = Column(Integer)
    FILTER_RESTYPE = Column(Text)
    FILTER_PIX = Column(Text)
    FILTER_RULE = Column(Integer)
    FILTER_TEAM = Column(Text)
    SAVE_PATH = Column(Text)
    DOWNLOAD_SETTING = Column(Integer)
    FUZZY_MATCH = Column(Integer)
    STATE = Column(Text)
    DESC = Column(Text)
    NOTE = Column(Text)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class RSSTORRENTS(Base):
    __tablename__ = 'RSS_TORRENTS'
    __table_args__ = (
        Index('INDX_RSS_TORRENTS_NAME', 'TITLE', 'YEAR', 'SEASON', 'EPISODE'),
    )

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    TORRENT_NAME = Column(Text)
    ENCLOSURE = Column(Text, index=True)
    TYPE = Column(Text)
    TITLE = Column(Text)
    YEAR = Column(Text)
    SEASON = Column(Text)
    EPISODE = Column(Text)


class RSSTVS(Base):
    __tablename__ = 'RSS_TVS'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    NAME = Column(Text, index=True)
    YEAR = Column(Text)
    SEASON = Column(Text)
    TMDBID = Column(Text)
    IMAGE = Column(Text)
    RSS_SITES = Column(Text)
    SEARCH_SITES = Column(Text)
    OVER_EDITION = Column(Integer)
    FILTER_RESTYPE = Column(Text)
    FILTER_PIX = Column(Text)
    FILTER_RULE = Column(Integer)
    FILTER_TEAM = Column(Text)
    SAVE_PATH = Column(Text)
    DOWNLOAD_SETTING = Column(Integer)
    FUZZY_MATCH = Column(Integer)
    TOTAL_EP = Column(Integer)
    CURRENT_EP = Column(Integer)
    TOTAL = Column(Integer)
    LACK = Column(Integer)
    STATE = Column(Text)
    DESC = Column(Text)
    NOTE = Column(Text)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class RSSTVEPISODES(Base):
    __tablename__ = 'RSS_TV_EPISODES'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    RSSID = Column(Text, index=True)
    EPISODES = Column(Text)


class TORRENTREMOVETASK(Base):
    __tablename__ = 'TORRENT_REMOVE_TASK'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    NAME = Column(Text)
    ACTION = Column(Integer)
    INTERVAL = Column(Integer)
    ENABLED = Column(Integer)
    SAMEDATA = Column(Integer)
    ONLYNASTOOL = Column(Integer)
    DOWNLOADER = Column(Text)
    CONFIG = Column(Text)
    NOTE = Column(Text)


class SEARCHRESULTINFO(Base):
    __tablename__ = 'SEARCH_RESULT_INFO'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    TORRENT_NAME = Column(Text)
    ENCLOSURE = Column(Text)
    DESCRIPTION = Column(Text)
    TYPE = Column(Text)
    TITLE = Column(Text)
    YEAR = Column(Text)
    SEASON = Column(Text)
    EPISODE = Column(Text)
    ES_STRING = Column(Text)
    VOTE = Column(Text)
    IMAGE = Column(Text)
    POSTER = Column(Text)
    TMDBID = Column(Text)
    OVERVIEW = Column(Text)
    RES_TYPE = Column(Text)
    RES_ORDER = Column(Text)
    SIZE = Column(Integer)
    SEEDERS = Column(Integer)
    PEERS = Column(Integer)
    SITE = Column(Text)
    SITE_ORDER = Column(Text)
    PAGEURL = Column(Text)
    OTHERINFO = Column(Text)
    UPLOAD_VOLUME_FACTOR = Column(Float)
    DOWNLOAD_VOLUME_FACTOR = Column(Float)
    NOTE = Column(Text)


class SITEBRUSHDOWNLOADERS(Base):
    __tablename__ = 'SITE_BRUSH_DOWNLOADERS'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    NAME = Column(Text)
    TYPE = Column(Text)
    HOST = Column(Text)
    PORT = Column(Text)
    USERNAME = Column(Text)
    PASSWORD = Column(Text)
    SAVE_DIR = Column(Text)
    NOTE = Column(Text)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SITEBRUSHTASK(Base):
    __tablename__ = 'SITE_BRUSH_TASK'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    NAME = Column(Text, index=True)
    SITE = Column(Text)
    FREELEECH = Column(Text)
    RSS_RULE = Column(Text)
    REMOVE_RULE = Column(Text)
    SEED_SIZE = Column(Text)
    INTEVAL = Column(Text)
    DOWNLOADER = Column(Text)
    TRANSFER = Column(Text)
    DOWNLOAD_COUNT = Column(Text)
    REMOVE_COUNT = Column(Text)
    DOWNLOAD_SIZE = Column(Text)
    UPLOAD_SIZE = Column(Text)
    SENDMESSAGE = Column(Text)
    FORCEUPLOAD = Column(Text)
    STATE = Column(Text)
    LST_MOD_DATE = Column(Text)


class SITEBRUSHTORRENTS(Base):
    __tablename__ = 'SITE_BRUSH_TORRENTS'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    TASK_ID = Column(Text, index=True)
    TORRENT_NAME = Column(Text)
    TORRENT_SIZE = Column(Text)
    ENCLOSURE = Column(Text)
    DOWNLOADER = Column(Text)
    DOWNLOAD_ID = Column(Text)
    LST_MOD_DATE = Column(Text)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class SITESTATISTICSHISTORY(Base):
    __tablename__ = 'SITE_STATISTICS_HISTORY'
    __table_args__ = (
        Index('INDX_SITE_STATISTICS_HISTORY_DS', 'DATE', 'URL'),
        Index('UN_INDX_SITE_STATISTICS_HISTORY_DS', 'DATE', 'URL', unique=True)
    )

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    SITE = Column(Text)
    DATE = Column(Text)
    USER_LEVEL = Column(Text)
    UPLOAD = Column(Text)
    DOWNLOAD = Column(Text)
    RATIO = Column(Text)
    SEEDING = Column(Integer, server_default=text("0"))
    LEECHING = Column(Integer, server_default=text("0"))
    SEEDING_SIZE = Column(Integer, server_default=text("0"))
    BONUS = Column(Float, server_default=text("0.0"))
    URL = Column(Text)


class SITEUSERINFOSTATS(Base):
    __tablename__ = 'SITE_USER_INFO_STATS'
    __table_args__ = (
        Index('INDX_SITE_USER_INFO_STATS_URL', 'URL'),
    )

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    SITE = Column(Text, index=True)
    USERNAME = Column(Text)
    USER_LEVEL = Column(Text)
    JOIN_AT = Column(Text)
    UPDATE_AT = Column(Text)
    UPLOAD = Column(Integer)
    DOWNLOAD = Column(Integer)
    RATIO = Column(Float)
    SEEDING = Column(Integer)
    LEECHING = Column(Integer)
    SEEDING_SIZE = Column(Integer)
    BONUS = Column(Float)
    URL = Column(Text, unique=True)
    MSG_UNREAD = Column(Integer)
    EXT_INFO = Column(Text)


class SITEFAVICON(Base):
    __tablename__ = 'SITE_FAVICON'

    SITE = Column(Text, primary_key=True)
    URL = Column(Text)
    FAVICON = Column(Text)


class SITEUSERSEEDINGINFO(Base):
    __tablename__ = 'SITE_USER_SEEDING_INFO'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    SITE = Column(Text, index=True)
    SEEDING_INFO = Column(Text, server_default=text("'[]'"))
    UPDATE_AT = Column(Text)
    URL = Column(Text, unique=True)


class SYNCHISTORY(Base):
    __tablename__ = 'SYNC_HISTORY'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    PATH = Column(Text, index=True)
    SRC = Column(Text)
    DEST = Column(Text)


class SYSTEMDICT(Base):
    __tablename__ = 'SYSTEM_DICT'
    __table_args__ = (
        Index('INDX_SYSTEM_DICT', 'TYPE', 'KEY'),
    )

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    TYPE = Column(Text)
    KEY = Column(Text)
    VALUE = Column(Text)
    NOTE = Column(Text)


class TRANSFERBLACKLIST(Base):
    __tablename__ = 'TRANSFER_BLACKLIST'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    PATH = Column(Text, index=True)


class TRANSFERHISTORY(Base):
    __tablename__ = 'TRANSFER_HISTORY'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    MODE = Column(Text)
    TYPE = Column(Text)
    CATEGORY = Column(Text)
    TMDBID = Column(Integer)
    TITLE = Column(Text, index=True)
    YEAR = Column(Text)
    SEASON_EPISODE = Column(Text)
    SOURCE = Column(Text)
    SOURCE_PATH = Column(Text, index=True)
    SOURCE_FILENAME = Column(Text, index=True)
    DEST = Column(Text)
    DEST_PATH = Column(Text)
    DEST_FILENAME = Column(Text)
    DATE = Column(Text)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class TRANSFERUNKNOWN(Base):
    __tablename__ = 'TRANSFER_UNKNOWN'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    PATH = Column(Text, index=True)
    DEST = Column(Text)
    MODE = Column(Text)
    STATE = Column(Text, index=True)


class USERRSSTASKHISTORY(Base):
    __tablename__ = 'USERRSS_TASK_HISTORY'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    TASK_ID = Column(Text, index=True)
    TITLE = Column(Text)
    DOWNLOADER = Column(Text)
    DATE = Column(Text)


class MEDIASYNCITEMS(BaseMedia):
    __tablename__ = 'MEDIASYNC_ITEMS'
    __table_args__ = (
        Index('INDX_MEDIASYNC_ITEMS_SL', 'SERVER', 'LIBRARY'),
    )

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    SERVER = Column(Text)
    LIBRARY = Column(Text)
    ITEM_ID = Column(Text, index=True)
    ITEM_TYPE = Column(Text)
    TITLE = Column(Text, index=True)
    ORGIN_TITLE = Column(Text, index=True)
    YEAR = Column(Text)
    TMDBID = Column(Text, index=True)
    IMDBID = Column(Text)
    PATH = Column(Text)
    NOTE = Column(Text)
    JSON = Column(Text)


class MEDIASYNCSTATISTIC(BaseMedia):
    __tablename__ = 'MEDIASYNC_STATISTICS'

    ID = Column(Integer, Sequence('ID'), primary_key=True)
    SERVER = Column(Text, index=True)
    TOTAL_COUNT = Column(Text)
    MOVIE_COUNT = Column(Text)
    TV_COUNT = Column(Text)
    UPDATE_TIME = Column(Text)
