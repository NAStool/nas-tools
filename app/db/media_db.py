import os
import threading
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import SingletonThreadPool
from app.db.models import BaseMedia, MEDIASYNCITEMS
from app.utils.commons import singleton
from config import Config

lock = threading.Lock()


@singleton
class MediaDb:
    __engine = None
    __session = None

    def __init__(self):
        self.__engine = create_engine(
            f"sqlite:///{os.path.join(Config().get_config_path(), 'media.db')}?check_same_thread=False",
            echo=False,
            poolclass=SingletonThreadPool,
            pool_size=5,
            pool_recycle=60 * 30
        )
        self.__session = scoped_session(sessionmaker(bind=self.__engine, autocommit=True))()
        self.__init_db()

    def __init_db(self):
        with lock:
            BaseMedia.metadata.create_all(self.__engine)

    def insert(self, server_type, iteminfo):
        if not server_type or not iteminfo:
            return False
        self.delete(server_type, iteminfo.get("id"))
        return self.__session.add(MEDIASYNCITEMS(
            SERVER=server_type,
            LIBRARY=iteminfo.get("library"),
            ITEM_ID=iteminfo.get("id"),
            ITEM_TYPE=iteminfo.get("type"),
            TITLE=iteminfo.get("title"),
            ORGIN_TITLE=iteminfo.get("originalTitle"),
            YEAR=iteminfo.get("year"),
            TMDBID=iteminfo.get("tmdbid"),
            IMDBID=iteminfo.get("imdbid"),
            PATH=iteminfo.get("path"),
            JSON=iteminfo.get("json")
        ))

    def delete(self, server_type, itemid):
        if not server_type or not itemid:
            return False
        return self.__session.query(MEDIASYNCITEMS).filter(MEDIASYNCITEMS.SERVER == server_type,
                                                           MEDIASYNCITEMS.ITEM_ID == itemid).delete()

    def empty(self, server_type=None, library=None):
        if server_type and library:
            return self.__session.query(MEDIASYNCITEMS).filter(MEDIASYNCITEMS.SERVER == server_type,
                                                               MEDIASYNCITEMS.LIBRARY == library).delete()
        else:
            return self.__session.query(MEDIASYNCITEMS).delete()

    def statistics(self, server_type, total_count, movie_count, tv_count):
        if not server_type:
            return False
        self.__session.query(MEDIASYNCITEMS).filter(MEDIASYNCITEMS.SERVER == server_type).delete()
        return self.__session.add(MEDIASYNCITEMS(
            SERVER=server_type,
            TOTAL_COUNT=total_count,
            MOVIE_COUNT=movie_count,
            TV_COUNT=tv_count,
            UPDATE_TIME=time.strftime('%Y-%m-%d %H:%M:%S',
                                      time.localtime(time.time()))
        ))

    def exists(self, server_type, title, year, tmdbid):
        if not server_type or not title:
            return False
        if title and year:
            count = self.__session.query(MEDIASYNCITEMS).filter(MEDIASYNCITEMS.SERVER == server_type,
                                                                MEDIASYNCITEMS.TITLE == title,
                                                                MEDIASYNCITEMS.YEAR == year).count()
        else:
            count = self.__session.query(MEDIASYNCITEMS).filter(MEDIASYNCITEMS.SERVER == server_type,
                                                                MEDIASYNCITEMS.TITLE == title).count()
        if count > 0:
            return True
        elif tmdbid:
            count = self.__session.query(MEDIASYNCITEMS).filter(MEDIASYNCITEMS.TMDBID == tmdbid).count()
            if count > 0:
                return True
        return False

    def get_statistics(self, server_type):
        if not server_type:
            return None
        return self.__session.query(MEDIASYNCITEMS).filter(MEDIASYNCITEMS.SERVER == server_type).all()
