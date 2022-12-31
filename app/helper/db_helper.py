import datetime
import os.path
import time
import json
from enum import Enum
from sqlalchemy import cast, func

from app.db import MainDb, DbPersist
from app.db.models import *
from app.utils import StringUtils
from app.utils.types import MediaType, RmtMode


class DbHelper:
    _db = MainDb()

    @DbPersist(_db)
    def insert_search_results(self, media_items: list):
        """
        将返回信息插入数据库
        """
        if not media_items:
            return
        data_list = []
        for media_item in media_items:
            if media_item.type == MediaType.TV:
                mtype = "TV"
            elif media_item.type == MediaType.MOVIE:
                mtype = "MOV"
            else:
                mtype = "ANI"
            data_list.append(SEARCHRESULTINFO(
                TORRENT_NAME=media_item.org_string,
                ENCLOSURE=media_item.enclosure,
                DESCRIPTION=media_item.description,
                TYPE=mtype,
                TITLE=media_item.title or media_item.get_name(),
                YEAR=media_item.year,
                SEASON=media_item.get_season_string(),
                EPISODE=media_item.get_episode_string(),
                ES_STRING=media_item.get_season_episode_string(),
                VOTE=media_item.vote_average or "0",
                IMAGE=media_item.get_backdrop_image(default=False),
                POSTER=media_item.get_poster_image(),
                TMDBID=media_item.tmdb_id,
                OVERVIEW=media_item.overview,
                RES_TYPE=json.dumps({
                    "respix": media_item.resource_pix,
                    "restype": media_item.resource_type,
                    "reseffect": media_item.resource_effect,
                    "video_encode": media_item.video_encode
                }),
                RES_ORDER=media_item.res_order,
                SIZE=StringUtils.str_filesize(int(media_item.size)),
                SEEDERS=media_item.seeders,
                PEERS=media_item.peers,
                SITE=media_item.site,
                SITE_ORDER=media_item.site_order,
                PAGEURL=media_item.page_url,
                OTHERINFO=media_item.resource_team,
                UPLOAD_VOLUME_FACTOR=media_item.upload_volume_factor,
                DOWNLOAD_VOLUME_FACTOR=media_item.download_volume_factor
            ))
        self._db.insert(data_list)

    def get_search_result_by_id(self, dl_id):
        """
        根据ID从数据库中查询检索结果的一条记录
        """
        return self._db.query(SEARCHRESULTINFO).filter(SEARCHRESULTINFO.ID == dl_id).all()

    def get_search_results(self, ):
        """
        查询检索结果的所有记录
        """
        return self._db.query(SEARCHRESULTINFO).all()

    def is_torrent_rssd(self, enclosure):
        """
        查询RSS是否处理过，根据下载链接
        """
        if not enclosure:
            return True
        if self._db.query(RSSTORRENTS).filter(RSSTORRENTS.ENCLOSURE == enclosure).count() > 0:
            return True
        else:
            return False

    def is_userrss_finished(self, torrent_name, enclosure):
        """
        查询RSS是否处理过，根据名称
        """
        if not torrent_name and not enclosure:
            return True
        if enclosure:
            ret = self._db.query(RSSTORRENTS).filter(RSSTORRENTS.ENCLOSURE == enclosure).count()
        else:
            ret = self._db.query(RSSTORRENTS).filter(RSSTORRENTS.TORRENT_NAME == torrent_name).count()
        return True if ret > 0 else False

    @DbPersist(_db)
    def delete_all_search_torrents(self, ):
        """
        删除所有搜索的记录
        """
        self._db.query(SEARCHRESULTINFO).delete()

    @DbPersist(_db)
    def insert_rss_torrents(self, media_info):
        """
        将RSS的记录插入数据库
        """
        self._db.insert(
            RSSTORRENTS(
                TORRENT_NAME=media_info.org_string,
                ENCLOSURE=media_info.enclosure,
                TYPE=media_info.type.value,
                TITLE=media_info.title,
                YEAR=media_info.year,
                SEASON=media_info.get_season_string(),
                EPISODE=media_info.get_episode_string()
            ))

    @DbPersist(_db)
    def simple_insert_rss_torrents(self, title, enclosure):
        """
        将RSS的记录插入数据库
        """
        self._db.insert(
            RSSTORRENTS(
                TORRENT_NAME=title,
                ENCLOSURE=enclosure
            ))

    @DbPersist(_db)
    def simple_delete_rss_torrents(self, title, enclosure):
        """
        删除RSS的记录
        """
        self._db.query(RSSTORRENTS).filter(RSSTORRENTS.TORRENT_NAME == title,
                                           RSSTORRENTS.ENCLOSURE == enclosure).delete()

    @DbPersist(_db)
    def insert_douban_media_state(self, media, state):
        """
        将豆瓣的数据插入数据库
        """
        if not media.year:
            self._db.query(DOUBANMEDIAS).filter(DOUBANMEDIAS.NAME == media.get_name()).delete()
        else:
            self._db.query(DOUBANMEDIAS).filter(DOUBANMEDIAS.NAME == media.get_name(),
                                                DOUBANMEDIAS.YEAR == media.year).delete()

        # 再插入
        self._db.insert(
            DOUBANMEDIAS(
                NAME=media.get_name(),
                YEAR=media.year,
                TYPE=media.type.value,
                RATING=media.vote_average,
                IMAGE=media.get_poster_image(),
                STATE=state,
                ADD_TIME=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            )
        )

    @DbPersist(_db)
    def update_douban_media_state(self, media, state):
        """
        标记豆瓣数据的状态
        """
        self._db.query(DOUBANMEDIAS).filter(DOUBANMEDIAS.NAME == media.title,
                                            DOUBANMEDIAS.YEAR == media.year).update(
            {
                "STATE": state
            }
        )

    def get_douban_search_state(self, title, year):
        """
        查询未检索的豆瓣数据
        """
        return self._db.query(DOUBANMEDIAS.STATE).filter(DOUBANMEDIAS.NAME == title,
                                                         DOUBANMEDIAS.YEAR == str(year)).all()

    def is_transfer_history_exists(self, file_path, file_name, title, se):
        """
        查询识别转移记录
        """
        if not file_path:
            return False
        ret = self._db.query(TRANSFERHISTORY).filter(TRANSFERHISTORY.SOURCE_PATH == file_path,
                                                     TRANSFERHISTORY.SOURCE_FILENAME == file_name,
                                                     TRANSFERHISTORY.TITLE == title,
                                                     TRANSFERHISTORY.SEASON_EPISODE == se).count()
        return True if ret > 0 else False

    @DbPersist(_db)
    def insert_transfer_history(self, in_from: Enum, rmt_mode: RmtMode, in_path, out_path, dest, media_info):
        """
        插入识别转移记录
        """
        if not media_info or not media_info.tmdb_info:
            return
        if in_path:
            in_path = os.path.normpath(in_path)
            source_path = os.path.dirname(in_path)
            source_filename = os.path.basename(in_path)
        else:
            return
        if out_path:
            outpath = os.path.normpath(out_path)
            dest_path = os.path.dirname(outpath)
            dest_filename = os.path.basename(outpath)
            season_episode = media_info.get_season_episode_string()
        else:
            dest_path = ""
            dest_filename = ""
            season_episode = media_info.get_season_string()
        title = media_info.title
        if self.is_transfer_history_exists(source_path, source_filename, title, season_episode):
            return
        dest = dest or ""
        timestr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        self._db.insert(
            TRANSFERHISTORY(
                MODE=str(rmt_mode.value),
                TYPE=media_info.type.value,
                CATEGORY=media_info.category,
                TMDBID=int(media_info.tmdb_id),
                TITLE=title,
                YEAR=media_info.year,
                SEASON_EPISODE=season_episode,
                SOURCE=str(in_from.value),
                SOURCE_PATH=source_path,
                SOURCE_FILENAME=source_filename,
                DEST=dest,
                DEST_PATH=dest_path,
                DEST_FILENAME=dest_filename,
                DATE=timestr
            )
        )

    def get_transfer_history(self, search, page, rownum):
        """
        查询识别转移记录
        """
        if int(page) == 1:
            begin_pos = 0
        else:
            begin_pos = (int(page) - 1) * int(rownum)

        if search:
            search = f"%{search}%"
            count = self._db.query(TRANSFERHISTORY).filter((TRANSFERHISTORY.SOURCE_FILENAME.like(search))
                                                           | (TRANSFERHISTORY.TITLE.like(search))).count()
            data = self._db.query(TRANSFERHISTORY).filter((TRANSFERHISTORY.SOURCE_FILENAME.like(search))
                                                          | (TRANSFERHISTORY.TITLE.like(search))).order_by(
                TRANSFERHISTORY.DATE.desc()).limit(int(rownum)).offset(begin_pos).all()
            return count, data
        else:
            return self._db.query(TRANSFERHISTORY).count(), self._db.query(TRANSFERHISTORY).order_by(
                TRANSFERHISTORY.DATE.desc()).limit(int(rownum)).offset(begin_pos).all()

    def get_transfer_path_by_id(self, logid):
        """
        据logid查询PATH
        """
        return self._db.query(TRANSFERHISTORY).filter(TRANSFERHISTORY.ID == int(logid)).all()

    def is_transfer_history_exists_by_source_full_path(self, source_full_path):
        """
        据源文件的全路径查询识别转移记录
        """

        path = os.path.dirname(source_full_path)
        filename = os.path.basename(source_full_path)
        ret = self._db.query(TRANSFERHISTORY).filter(TRANSFERHISTORY.SOURCE_PATH == path,
                                                     TRANSFERHISTORY.SOURCE_FILENAME == filename).count()
        if ret > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def delete_transfer_log_by_id(self, logid):
        """
        根据logid删除记录
        """
        self._db.query(TRANSFERHISTORY).filter(TRANSFERHISTORY.ID == int(logid)).delete()

    def get_transfer_unknown_paths(self, ):
        """
        查询未识别的记录列表
        """
        return self._db.query(TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.STATE == 'N').all()

    @DbPersist(_db)
    def update_transfer_unknown_state(self, path):
        """
        更新未识别记录为识别
        """
        if not path:
            return
        self._db.query(TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.PATH == os.path.normpath(path)).update(
            {
                "STATE": "Y"
            }
        )

    @DbPersist(_db)
    def delete_transfer_unknown(self, tid):
        """
        删除未识别记录
        """
        if not tid:
            return []
        self._db.query(TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.ID == int(tid)).delete()

    def get_unknown_path_by_id(self, tid):
        """
        查询未识别记录
        """
        if not tid:
            return []
        return self._db.query(TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.ID == int(tid)).all()

    def get_transfer_unknown_by_path(self, path):
        """
        根据路径查询未识别记录
        """
        if not path:
            return []
        return self._db.query(TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.PATH == path).all()

    def is_transfer_unknown_exists(self, path):
        """
        查询未识别记录是否存在
        """
        if not path:
            return False
        ret = self._db.query(TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.PATH == os.path.normpath(path)).count()
        if ret > 0:
            return True
        else:
            return False

    def is_need_insert_transfer_unknown(self, path):
        """
        检查是否需要插入未识别记录
        """
        if not path:
            return False

        """
        1) 如果不存在未识别，则插入
        2) 如果存在未处理的未识别，则插入（并不会真正的插入，insert_transfer_unknown里会挡住，主要是标记进行消息推送）
        3) 如果未识别已经全部处理完并且存在转移记录，则不插入
        4) 如果未识别已经全部处理完并且不存在转移记录，则删除并重新插入
        """
        unknowns = self.get_transfer_unknown_by_path(path)
        if unknowns:
            is_all_proceed = True
            for unknown in unknowns:
                if unknown.STATE == 'N':
                    is_all_proceed = False
                    break

            if is_all_proceed:
                is_transfer_history_exists = self.is_transfer_history_exists_by_source_full_path(path)
                if is_transfer_history_exists:
                    # 对应 3)
                    return False
                else:
                    # 对应 4)
                    for unknown in unknowns:
                        self.delete_transfer_unknown(unknown.ID)
                    return True
            else:
                # 对应 2)
                return True
        else:
            # 对应 1)
            return True

    @DbPersist(_db)
    def insert_transfer_unknown(self, path, dest):
        """
        插入未识别记录
        """
        if not path:
            return
        if self.is_transfer_unknown_exists(path):
            return
        else:
            path = os.path.normpath(path)
            if dest:
                dest = os.path.normpath(dest)
            else:
                dest = ""
            self._db.insert(TRANSFERUNKNOWN(
                PATH=path,
                DEST=dest,
                STATE='N'
            ))

    def is_transfer_in_blacklist(self, path):
        """
        查询是否为黑名单
        """
        if not path:
            return False
        ret = self._db.query(TRANSFERBLACKLIST).filter(TRANSFERBLACKLIST.PATH == os.path.normpath(path)).count()
        if ret > 0:
            return True
        else:
            return False

    def is_transfer_notin_blacklist(self, path):
        """
        查询是否为黑名单
        """
        return not self.is_transfer_in_blacklist(path)

    @DbPersist(_db)
    def insert_transfer_blacklist(self, path):
        """
        插入黑名单记录
        """
        if not path:
            return
        if self.is_transfer_in_blacklist(path):
            return
        else:
            self._db.insert(TRANSFERBLACKLIST(
                PATH=os.path.normpath(path)
            ))

    @DbPersist(_db)
    def truncate_transfer_blacklist(self, ):
        """
        清空黑名单记录
        """
        self._db.query(TRANSFERBLACKLIST).delete()
        self._db.query(SYNCHISTORY).delete()

    @DbPersist(_db)
    def truncate_rss_history(self, ):
        """
        清空RSS历史记录
        """
        self._db.query(RSSTORRENTS).delete()

    @DbPersist(_db)
    def truncate_rss_episodes(self, ):
        """
        清空RSS历史记录
        """
        self._db.query(RSSTVEPISODES).delete()

    def get_config_site(self, ):
        """
        查询所有站点信息
        """
        return self._db.query(CONFIGSITE).order_by(cast(CONFIGSITE.PRI, Integer).asc())

    def get_site_by_id(self, tid):
        """
        查询1个站点信息
        """
        return self._db.query(CONFIGSITE).filter(CONFIGSITE.ID == int(tid)).all()

    def get_site_by_name(self, name):
        """
        基于站点名称查询站点信息
        :return:
        """
        return self._db.query(CONFIGSITE).filter(CONFIGSITE.NAME == name).all()

    @DbPersist(_db)
    def insert_config_site(self, name, site_pri, rssurl, signurl, cookie, note, rss_uses):
        """
        插入站点信息
        """
        if not name:
            return
        self._db.insert(CONFIGSITE(
            NAME=name,
            PRI=site_pri,
            RSSURL=rssurl,
            SIGNURL=signurl,
            COOKIE=cookie,
            NOTE=note,
            INCLUDE=rss_uses
        ))

    @DbPersist(_db)
    def delete_config_site(self, tid):
        """
        删除站点信息
        """
        if not tid:
            return
        self._db.query(CONFIGSITE).filter(CONFIGSITE.ID == int(tid)).delete()

    @DbPersist(_db)
    def update_config_site(self, tid, name, site_pri, rssurl, signurl, cookie, note, rss_uses):
        """
        更新站点信息
        """
        if not tid:
            return
        self._db.query(CONFIGSITE).filter(CONFIGSITE.ID == int(tid)).update(
            {
                "NAME": name,
                "PRI": site_pri,
                "RSSURL": rssurl,
                "SIGNURL": signurl,
                "COOKIE": cookie,
                "NOTE": note,
                "INCLUDE": rss_uses
            }
        )

    @DbPersist(_db)
    def update_config_site_note(self, tid, note):
        """
        更新站点属性
        """
        if not tid:
            return
        self._db.query(CONFIGSITE).filter(CONFIGSITE.ID == int(tid)).update(
            {
                "NOTE": note
            }
        )

    @DbPersist(_db)
    def update_site_cookie_ua(self, tid, cookie, ua):
        """
        更新站点Cookie和ua
        """
        if not tid:
            return
        rec = self._db.query(CONFIGSITE).filter(CONFIGSITE.ID == int(tid)).first()
        if not rec.NOTE:
            return
        note = json.loads(rec.NOTE)
        note['ua'] = ua
        self._db.query(CONFIGSITE).filter(CONFIGSITE.ID == int(tid)).update(
            {
                "COOKIE": cookie,
                "NOTE": json.dumps(note)
            }
        )

    def get_config_filter_group(self, gid=None):
        """
        查询过滤规则组
        """
        if gid:
            return self._db.query(CONFIGFILTERGROUP).filter(CONFIGFILTERGROUP.ID == int(gid)).all()
        return self._db.query(CONFIGFILTERGROUP).all()

    def get_config_filter_rule(self, groupid=None):
        """
        查询过滤规则
        """
        if not groupid:
            return self._db.query(CONFIGFILTERRULES).order_by(CONFIGFILTERRULES.GROUP_ID,
                                                              cast(CONFIGFILTERRULES.PRIORITY,
                                                                   Integer)).all()
        else:
            return self._db.query(CONFIGFILTERRULES).filter(
                CONFIGFILTERRULES.GROUP_ID == int(groupid)).order_by(CONFIGFILTERRULES.GROUP_ID,
                                                                     cast(CONFIGFILTERRULES.PRIORITY,
                                                                          Integer)).all()

    def get_rss_movies(self, state=None, rssid=None):
        """
        查询订阅电影信息
        """
        if rssid:
            return self._db.query(RSSMOVIES).filter(RSSMOVIES.ID == int(rssid)).all()
        else:
            if not state:
                return self._db.query(RSSMOVIES).all()
            else:
                return self._db.query(RSSMOVIES).filter(RSSMOVIES.STATE == state).all()

    def get_rss_movie_id(self, title, tmdbid=None):
        """
        获取订阅电影ID
        """
        if not title:
            return ""
        ret = self._db.query(RSSMOVIES.ID).filter(RSSMOVIES.NAME == title).first()
        if ret:
            return ret[0]
        else:
            if tmdbid:
                ret = self._db.query(RSSMOVIES.ID).filter(RSSMOVIES.TMDBID == tmdbid).first()
                if ret:
                    return ret[0]
        return ""

    def get_rss_movie_sites(self, rssid):
        """
        获取订阅电影站点
        """
        if not rssid:
            return ""
        ret = self._db.query(RSSMOVIES.DESC).filter(RSSMOVIES.ID == int(rssid)).first()
        if ret:
            return ret[0]
        return ""

    @DbPersist(_db)
    def update_rss_movie_tmdb(self, rid, tmdbid, title, year, image, desc, note):
        """
        更新订阅电影的部分信息
        """
        if not tmdbid:
            return
        self._db.query(RSSMOVIES).filter(RSSMOVIES.ID == int(rid)).update({
            "TMDBID": tmdbid,
            "NAME": title,
            "YEAR": year,
            "IMAGE": image,
            "NOTE": note,
            "DESC": desc
        })

    @DbPersist(_db)
    def update_rss_movie_desc(self, rid, desc):
        """
        更新订阅电影的DESC
        """
        self._db.query(RSSMOVIES).filter(RSSMOVIES.ID == int(rid)).update({
            "DESC": desc
        })

    def is_exists_rss_movie(self, title, year):
        """
        判断RSS电影是否存在
        """
        if not title:
            return False
        count = self._db.query(RSSMOVIES).filter(RSSMOVIES.NAME == title,
                                                 RSSMOVIES.YEAR == str(year)).count()
        if count > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def insert_rss_movie(self, media_info,
                         state='D',
                         rss_sites=None,
                         search_sites=None,
                         over_edition=0,
                         filter_restype=None,
                         filter_pix=None,
                         filter_team=None,
                         filter_rule=None,
                         save_path=None,
                         download_setting=-1,
                         fuzzy_match=0,
                         desc=None,
                         note=None):
        """
        新增RSS电影
        """
        if search_sites is None:
            search_sites = []
        if rss_sites is None:
            rss_sites = []
        if not media_info:
            return -1
        if not media_info.title:
            return -1
        if self.is_exists_rss_movie(media_info.title, media_info.year):
            return 9
        self._db.insert(RSSMOVIES(
            NAME=media_info.title,
            YEAR=media_info.year,
            TMDBID=media_info.tmdb_id,
            IMAGE=media_info.get_message_image(),
            RSS_SITES=json.dumps(rss_sites),
            SEARCH_SITES=json.dumps(search_sites),
            OVER_EDITION=over_edition,
            FILTER_RESTYPE=filter_restype,
            FILTER_PIX=filter_pix,
            FILTER_RULE=filter_rule,
            FILTER_TEAM=filter_team,
            SAVE_PATH=save_path,
            DOWNLOAD_SETTING=download_setting,
            FUZZY_MATCH=fuzzy_match,
            STATE=state,
            DESC=desc,
            NOTE=note
        ))
        return 0

    @DbPersist(_db)
    def delete_rss_movie(self, title=None, year=None, rssid=None, tmdbid=None):
        """
        删除RSS电影
        """
        if not title and not rssid:
            return
        if rssid:
            self._db.query(RSSMOVIES).filter(RSSMOVIES.ID == int(rssid)).delete()
        else:
            if tmdbid:
                self._db.query(RSSMOVIES).filter(RSSMOVIES.TMDBID == tmdbid).delete()
            self._db.query(RSSMOVIES).filter(RSSMOVIES.NAME == title,
                                             RSSMOVIES.YEAR == str(year)).delete()

    @DbPersist(_db)
    def update_rss_movie_state(self, title=None, year=None, rssid=None, state='R'):
        """
        更新电影订阅状态
        """
        if not title and not rssid:
            return
        if rssid:
            self._db.query(RSSMOVIES).filter(RSSMOVIES.ID == int(rssid)).update(
                {
                    "STATE": state
                })
        else:
            self._db.query(RSSMOVIES).filter(
                RSSMOVIES.NAME == title,
                RSSMOVIES.YEAR == str(year)).update(
                {
                    "STATE": state
                })

    def get_rss_tvs(self, state=None, rssid=None):
        """
        查询订阅电视剧信息
        """
        if rssid:
            return self._db.query(RSSTVS).filter(RSSTVS.ID == int(rssid)).all()
        else:
            if not state:
                return self._db.query(RSSTVS).all()
            else:
                return self._db.query(RSSTVS).filter(RSSTVS.STATE == state).all()

    def get_rss_tv_id(self, title, season=None, tmdbid=None):
        """
        获取订阅电影ID
        """
        if not title:
            return ""
        if season:
            ret = self._db.query(RSSTVS.ID).filter(RSSTVS.NAME == title,
                                                   RSSTVS.SEASON == season).first()
            if ret:
                return ret[0]
            else:
                if tmdbid:
                    ret = self._db.query(RSSTVS.ID).filter(RSSTVS.TMDBID == tmdbid,
                                                           RSSTVS.SEASON == season).first()
                    if ret:
                        return ret[0]
        else:
            ret = self._db.query(RSSTVS.ID).filter(RSSTVS.NAME == title).first()
            if ret:
                return ret[0]
            else:
                if tmdbid:
                    ret = self._db.query(RSSTVS.ID).filter(RSSTVS.TMDBID == tmdbid).first()
                    if ret:
                        return ret[0]
        return ""

    def get_rss_tv_sites(self, rssid):
        """
        获取订阅电视剧站点
        """
        if not rssid:
            return ""
        ret = self._db.query(RSSTVS).filter(RSSTVS.ID == int(rssid)).first()
        if ret:
            return ret
        return ""

    @DbPersist(_db)
    def update_rss_tv_tmdb(self, rid, tmdbid, title, year, total, lack, image, desc, note):
        """
        更新订阅电影的TMDBID
        """
        if not tmdbid:
            return
        self._db.query(RSSTVS).filter(RSSTVS.ID == int(rid)).update(
            {
                "TMDBID": tmdbid,
                "NAME": title,
                "YEAR": year,
                "TOTAL": total,
                "LACK": lack,
                "IMAGE": image,
                "DESC": desc,
                "NOTE": note
            }
        )

    @DbPersist(_db)
    def update_rss_tv_desc(self, rid, desc):
        """
        更新订阅电视剧的DESC
        """
        self._db.query(RSSTVS).filter(RSSTVS.ID == int(rid)).update(
            {
                "DESC": desc
            }
        )

    def is_exists_rss_tv(self, title, year, season=None):
        """
        判断RSS电视剧是否存在
        """
        if not title:
            return False
        if season:
            count = self._db.query(RSSTVS).filter(RSSTVS.NAME == title,
                                                  RSSTVS.YEAR == str(year),
                                                  RSSTVS.SEASON == season).count()
        else:
            count = self._db.query(RSSTVS).filter(RSSTVS.NAME == title,
                                                  RSSTVS.YEAR == str(year)).count()
        if count > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def insert_rss_tv(self,
                      media_info,
                      total,
                      lack=0,
                      state="D",
                      rss_sites=None,
                      search_sites=None,
                      over_edition=0,
                      filter_restype=None,
                      filter_pix=None,
                      filter_team=None,
                      filter_rule=None,
                      save_path=None,
                      download_setting=-1,
                      total_ep=None,
                      current_ep=None,
                      fuzzy_match=0,
                      desc=None,
                      note=None):
        """
        新增RSS电视剧
        """
        if search_sites is None:
            search_sites = []
        if rss_sites is None:
            rss_sites = []
        if not media_info:
            return -1
        if not media_info.title:
            return -1
        if fuzzy_match and media_info.begin_season is None:
            season_str = ""
        else:
            season_str = media_info.get_season_string()
        if self.is_exists_rss_tv(media_info.title, media_info.year, season_str):
            return 9
        self._db.insert(RSSTVS(
            NAME=media_info.title,
            YEAR=media_info.year,
            SEASON=season_str,
            TMDBID=media_info.tmdb_id,
            IMAGE=media_info.get_message_image(),
            RSS_SITES=json.dumps(rss_sites),
            SEARCH_SITES=json.dumps(search_sites),
            OVER_EDITION=over_edition,
            FILTER_RESTYPE=filter_restype,
            FILTER_PIX=filter_pix,
            FILTER_RULE=filter_rule,
            FILTER_TEAM=filter_team,
            SAVE_PATH=save_path,
            DOWNLOAD_SETTING=download_setting,
            FUZZY_MATCH=fuzzy_match,
            TOTAL_EP=total_ep,
            CURRENT_EP=current_ep,
            TOTAL=total,
            LACK=lack,
            STATE=state,
            DESC=desc,
            NOTE=note
        ))
        return 0

    @DbPersist(_db)
    def update_rss_tv_lack(self, title=None, year=None, season=None, rssid=None, lack_episodes: list = None):
        """
        更新电视剧缺失的集数
        """
        if not title and not rssid:
            return
        if not lack_episodes:
            lack = 0
        else:
            lack = len(lack_episodes)
        if rssid:
            self.update_rss_tv_episodes(rssid, lack_episodes)
            self._db.query(RSSTVS).filter(RSSTVS.ID == int(rssid)).update(
                {
                    "LACK": lack
                }
            )
        else:
            self._db.query(RSSTVS).filter(RSSTVS.NAME == title,
                                          RSSTVS.YEAR == str(year),
                                          RSSTVS.SEASON == season).update(
                {
                    "LACK": lack
                }
            )

    @DbPersist(_db)
    def delete_rss_tv(self, title=None, season=None, rssid=None, tmdbid=None):
        """
        删除RSS电视剧
        """
        if not title and not rssid:
            return
        if not rssid:
            rssid = self.get_rss_tv_id(title=title, tmdbid=tmdbid, season=season)
        if rssid:
            self.delete_rss_tv_episodes(rssid)
            self._db.query(RSSTVS).filter(RSSTVS.ID == int(rssid)).delete()

    def is_exists_rss_tv_episodes(self, rid):
        """
        判断RSS电视剧是否存在
        """
        if not rid:
            return False
        count = self._db.query(RSSTVEPISODES).filter(RSSTVEPISODES.RSSID == int(rid)).count()
        if count > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def update_rss_tv_episodes(self, rid, episodes):
        """
        插入或更新电视剧订阅缺失剧集
        """
        if not rid:
            return
        if not episodes:
            episodes = []
        else:
            episodes = [str(epi) for epi in episodes]
        if self.is_exists_rss_tv_episodes(rid):
            self._db.query(RSSTVEPISODES).filter(RSSTVEPISODES.RSSID == int(rid)).update(
                {
                    "EPISODES": ",".join(episodes)
                }
            )
        else:
            self._db.insert(RSSTVEPISODES(
                RSSID=rid,
                EPISODES=",".join(episodes)
            ))

    def get_rss_tv_episodes(self, rid):
        """
        查询电视剧订阅缺失剧集
        """
        if not rid:
            return []
        ret = self._db.query(RSSTVEPISODES.EPISODES).filter(RSSTVEPISODES.RSSID == rid).first()
        if ret:
            return [int(epi) for epi in str(ret[0]).split(',')]
        else:
            return None

    @DbPersist(_db)
    def delete_rss_tv_episodes(self, rid):
        """
        删除电视剧订阅缺失剧集
        """
        if not rid:
            return
        self._db.query(RSSTVEPISODES).filter(RSSTVEPISODES.RSSID == int(rid)).delete()

    @DbPersist(_db)
    def update_rss_tv_state(self, title=None, year=None, season=None, rssid=None, state='R'):
        """
        更新电视剧订阅状态
        """
        if not title and not rssid:
            return
        if rssid:
            self._db.query(RSSTVS).filter(RSSTVS.ID == int(rssid)).update(
                {
                    "STATE": state
                })
        else:
            self._db.query(RSSTVS).filter(RSSTVS.NAME == title,
                                          RSSTVS.YEAR == str(year),
                                          RSSTVS.SEASON == season).update(
                {
                    "STATE": state
                })

    def is_sync_in_history(self, path, dest):
        """
        查询是否存在同步历史记录
        """
        if not path:
            return False
        count = self._db.query(SYNCHISTORY).filter(SYNCHISTORY.PATH == os.path.normpath(path),
                                                   SYNCHISTORY.DEST == os.path.normpath(dest)).count()
        if count > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def insert_sync_history(self, path, src, dest):
        """
        插入黑名单记录
        """
        if not path or not dest:
            return
        if self.is_sync_in_history(path, dest):
            return
        else:
            self._db.insert(SYNCHISTORY(
                PATH=os.path.normpath(path),
                SRC=os.path.normpath(src),
                DEST=os.path.normpath(dest)
            ))

    def get_users(self, ):
        """
        查询用户列表
        """
        return self._db.query(CONFIGUSERS).all()

    def is_user_exists(self, name):
        """
        判断用户是否存在
        """
        if not name:
            return False
        count = self._db.query(CONFIGUSERS).filter(CONFIGUSERS.NAME == name).count()
        if count > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def insert_user(self, name, password, pris):
        """
        新增用户
        """
        if not name or not password:
            return
        if self.is_user_exists(name):
            return
        else:
            self._db.insert(CONFIGUSERS(
                NAME=name,
                PASSWORD=password,
                PRIS=pris
            ))

    @DbPersist(_db)
    def delete_user(self, name):
        """
        删除用户
        """
        self._db.query(CONFIGUSERS).filter(CONFIGUSERS.NAME == name).delete()

    def get_transfer_statistics(self, days=30):
        """
        查询历史记录统计
        """
        begin_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        return self._db.query(TRANSFERHISTORY.TYPE,
                              func.substr(TRANSFERHISTORY.DATE, 1, 10),
                              func.count('*')
                              ).filter(TRANSFERHISTORY.DATE > begin_date).group_by(
            func.substr(TRANSFERHISTORY.DATE, 1, 10)
        ).order_by(TRANSFERHISTORY.DATE).all()

    @DbPersist(_db)
    def update_site_user_statistics_site_name(self, new_name, old_name):
        """
        更新站点用户数据中站点名称
        """
        self._db.query(SITEUSERINFOSTATS).filter(SITEUSERINFOSTATS.SITE == old_name).update(
            {
                "SITE": new_name
            }
        )

    @DbPersist(_db)
    def update_site_user_statistics(self, site_user_infos: list):
        """
        更新站点用户粒度数据
        """
        if not site_user_infos:
            return
        update_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        for site_user_info in site_user_infos:
            site = site_user_info.site_name
            username = site_user_info.username
            user_level = site_user_info.user_level
            join_at = site_user_info.join_at
            upload = site_user_info.upload
            download = site_user_info.download
            ratio = site_user_info.ratio
            seeding = site_user_info.seeding
            seeding_size = site_user_info.seeding_size
            leeching = site_user_info.leeching
            bonus = site_user_info.bonus
            url = site_user_info.site_url
            msg_unread = site_user_info.message_unread
            if not self.is_exists_site_user_statistics(url):
                self._db.insert(SITEUSERINFOSTATS(
                    SITE=site,
                    USERNAME=username,
                    USER_LEVEL=user_level,
                    JOIN_AT=join_at,
                    UPDATE_AT=update_at,
                    UPLOAD=upload,
                    DOWNLOAD=download,
                    RATIO=ratio,
                    SEEDING=seeding,
                    LEECHING=leeching,
                    SEEDING_SIZE=seeding_size,
                    BONUS=bonus,
                    URL=url,
                    MSG_UNREAD=msg_unread
                ))
            else:
                self._db.query(SITEUSERINFOSTATS).filter(SITEUSERINFOSTATS.URL == url).update(
                    {
                        "SITE": site,
                        "USERNAME": username,
                        "USER_LEVEL": user_level,
                        "JOIN_AT": join_at,
                        "UPDATE_AT": update_at,
                        "UPLOAD": upload,
                        "DOWNLOAD": download,
                        "RATIO": ratio,
                        "SEEDING": seeding,
                        "LEECHING": leeching,
                        "SEEDING_SIZE": seeding_size,
                        "BONUS": bonus,
                        "MSG_UNREAD": msg_unread
                    }
                )

    def is_exists_site_user_statistics(self, url):
        """
        判断站点数据是滞存在
        """
        count = self._db.query(SITEUSERINFOSTATS).filter(SITEUSERINFOSTATS.URL == url).count()
        if count > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def update_site_favicon(self, site_user_infos: list):
        """
        更新站点图标数据
        """
        if not site_user_infos:
            return
        for site_user_info in site_user_infos:
            site_icon = "data:image/ico;base64," + \
                        site_user_info.site_favicon if site_user_info.site_favicon else site_user_info.site_url \
                                                                                        + "/favicon.ico"
            if not self.is_exists_site_favicon(site_user_info.site_name):
                self._db.insert(SITEFAVICON(
                    SITE=site_user_info.site_name,
                    URL=site_user_info.site_url,
                    FAVICON=site_icon
                ))
            elif site_user_info.site_favicon:
                self._db.query(SITEFAVICON).filter(SITEFAVICON.SITE == site_user_info.site_name).update(
                    {
                        "URL": site_user_info.site_url,
                        "FAVICON": site_icon
                    }
                )

    def is_exists_site_favicon(self, site):
        """
        判断站点图标是否存在
        """
        count = self._db.query(SITEFAVICON).filter(SITEFAVICON.SITE == site).count()
        if count > 0:
            return True
        else:
            return False

    def get_site_favicons(self, site=None):
        """
        查询站点数据历史
        """
        if site:
            return self._db.query(SITEFAVICON).filter(SITEFAVICON.SITE == site).all()
        else:
            return self._db.query(SITEFAVICON).all()

    @DbPersist(_db)
    def update_site_seed_info_site_name(self, new_name, old_name):
        """
        更新站点做种数据中站点名称
        :param new_name: 新的站点名称
        :param old_name: 原始站点名称
        :return:
        """
        self._db.query(SITEUSERSEEDINGINFO).filter(SITEUSERSEEDINGINFO.SITE == old_name).update(
            {
                "SITE": new_name
            }
        )

    @DbPersist(_db)
    def update_site_seed_info(self, site_user_infos: list):
        """
        更新站点做种数据
        """
        if not site_user_infos:
            return
        update_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        for site_user_info in site_user_infos:
            if not self.is_site_seeding_info_exist(url=site_user_info.site_url):
                self._db.insert(SITEUSERSEEDINGINFO(
                    SITE=site_user_info.site_name,
                    UPDATE_AT=update_at,
                    SEEDING_INFO=site_user_info.seeding_info,
                    URL=site_user_info.site_url
                ))
            else:
                self._db.query(SITEUSERSEEDINGINFO).filter(SITEUSERSEEDINGINFO.URL == site_user_info.site_url).update(
                    {
                        "SITE": site_user_info.site_name,
                        "UPDATE_AT": update_at,
                        "SEEDING_INFO": site_user_info.seeding_info
                    }
                )

    def is_site_user_statistics_exists(self, url):
        """
        判断站点用户数据是否存在
        """
        if not url:
            return False
        count = self._db.query(SITEUSERINFOSTATS).filter(SITEUSERINFOSTATS.URL == url).count()
        if count > 0:
            return True
        else:
            return False

    def get_site_user_statistics(self, num=100, strict_urls=None):
        """
        查询站点数据历史
        """
        if strict_urls:
            return self._db.query(SITEUSERINFOSTATS).filter(
                SITEUSERINFOSTATS.URL.in_(tuple(strict_urls + ["__DUMMY__"]))).limit(num).all()
        else:
            return self._db.query(SITEUSERINFOSTATS).limit(num).all()

    def is_site_statistics_history_exists(self, url, date):
        """
        判断站点历史数据是否存在
        """
        if not url or not date:
            return False
        count = self._db.query(SITESTATISTICSHISTORY).filter(SITESTATISTICSHISTORY.URL == url,
                                                             SITESTATISTICSHISTORY.DATE == date).count()
        if count > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def update_site_statistics_site_name(self, new_name, old_name):
        """
        更新站点做种数据中站点名称
        :param new_name: 新站点名称
        :param old_name: 原始站点名称
        :return:
        """
        self._db.query(SITESTATISTICSHISTORY).filter(SITESTATISTICSHISTORY.SITE == old_name).update(
            {
                "SITE": new_name
            }
        )

    @DbPersist(_db)
    def insert_site_statistics_history(self, site_user_infos: list):
        """
        插入站点数据
        """
        if not site_user_infos:
            return
        date_now = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        for site_user_info in site_user_infos:
            site = site_user_info.site_name
            upload = site_user_info.upload
            user_level = site_user_info.user_level
            download = site_user_info.download
            ratio = site_user_info.ratio
            seeding = site_user_info.seeding
            seeding_size = site_user_info.seeding_size
            leeching = site_user_info.leeching
            bonus = site_user_info.bonus
            url = site_user_info.site_url
            if not self.is_site_statistics_history_exists(date=date_now, url=url):
                self._db.insert(SITESTATISTICSHISTORY(
                    SITE=site,
                    USER_LEVEL=user_level,
                    DATE=date_now,
                    UPLOAD=upload,
                    DOWNLOAD=download,
                    RATIO=ratio,
                    SEEDING=seeding,
                    LEECHING=leeching,
                    SEEDING_SIZE=seeding_size,
                    BONUS=bonus,
                    URL=url
                ))
            else:
                self._db.query(SITESTATISTICSHISTORY).filter(SITESTATISTICSHISTORY.DATE == date_now,
                                                             SITESTATISTICSHISTORY.URL == url).update(
                    {
                        "SITE": site,
                        "USER_LEVEL": user_level,
                        "UPLOAD": upload,
                        "DOWNLOAD": download,
                        "RATIO": ratio,
                        "SEEDING": seeding,
                        "LEECHING": leeching,
                        "SEEDING_SIZE": seeding_size,
                        "BONUS": bonus
                    }
                )

    def get_site_statistics_history(self, site, days=30):
        """
        查询站点数据历史
        """
        return self._db.query(SITESTATISTICSHISTORY).filter(
            SITESTATISTICSHISTORY.SITE == site).order_by(
            SITESTATISTICSHISTORY.DATE.asc()
        ).limit(days)

    def get_site_seeding_info(self, site):
        """
        查询站点做种信息
        """
        return self._db.query(SITEUSERSEEDINGINFO.SEEDING_INFO).filter(
            SITEUSERSEEDINGINFO.SITE == site).first()

    def is_site_seeding_info_exist(self, url):
        """
        判断做种数据是否已存在
        """
        count = self._db.query(SITEUSERSEEDINGINFO).filter(
            SITEUSERSEEDINGINFO.URL == url).count()
        if count > 0:
            return True
        else:
            return False

    def get_site_statistics_recent_sites(self, days=7, strict_urls=None):
        """
        查询近期上传下载量
        """
        # 查询最大最小日期
        if strict_urls is None:
            strict_urls = []

        b_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        date_ret = self._db.query(func.max(SITESTATISTICSHISTORY.DATE),
                                  func.MIN(SITESTATISTICSHISTORY.DATE)).filter(
            SITESTATISTICSHISTORY.DATE > b_date).all()
        if date_ret:
            total_upload = 0
            total_download = 0
            ret_sites = []
            ret_site_uploads = []
            ret_site_downloads = []
            min_date = date_ret[0][1]
            # 查询开始值
            if strict_urls:
                subquery = self._db.query(SITESTATISTICSHISTORY.SITE.label("SITE"),
                                          SITESTATISTICSHISTORY.DATE.label("DATE"),
                                          func.sum(SITESTATISTICSHISTORY.UPLOAD).label("UPLOAD"),
                                          func.sum(SITESTATISTICSHISTORY.DOWNLOAD).label("DOWNLOAD")).filter(
                    SITESTATISTICSHISTORY.DATE >= min_date,
                    SITESTATISTICSHISTORY.URL.in_(tuple(strict_urls + ["__DUMMY__"]))).group_by(
                    SITESTATISTICSHISTORY.SITE, SITESTATISTICSHISTORY.DATE).subquery()
            else:
                subquery = self._db.query(SITESTATISTICSHISTORY.SITE.label("SITE"),
                                          SITESTATISTICSHISTORY.DATE.label("DATE"),
                                          func.sum(SITESTATISTICSHISTORY.UPLOAD).label("UPLOAD"),
                                          func.sum(SITESTATISTICSHISTORY.DOWNLOAD).label("DOWNLOAD")).filter(
                    SITESTATISTICSHISTORY.DATE >= min_date).group_by(
                    SITESTATISTICSHISTORY.SITE, SITESTATISTICSHISTORY.DATE).subquery()
            rets = self._db.query(subquery.c.SITE,
                                  func.min(subquery.c.UPLOAD),
                                  func.min(subquery.c.DOWNLOAD),
                                  func.max(subquery.c.UPLOAD),
                                  func.max(subquery.c.DOWNLOAD)).group_by(subquery.c.SITE).all()
            for ret_b in rets:
                # 如果最小值都是0，可能时由于近几日没有更新数据，或者cookie过期，正常有数据的话，第二天能正常
                ret_b = list(ret_b)
                if ret_b[1] == 0 and ret_b[2] == 0:
                    ret_b[1] = ret_b[3]
                    ret_b[2] = ret_b[4]
                ret_sites.append(ret_b[0])
                if int(ret_b[1]) < int(ret_b[3]):
                    total_upload += int(ret_b[3]) - int(ret_b[1])
                    ret_site_uploads.append(int(ret_b[3]) - int(ret_b[1]))
                else:
                    ret_site_uploads.append(0)
                if int(ret_b[2]) < int(ret_b[4]):
                    total_download += int(ret_b[4]) - int(ret_b[2])
                    ret_site_downloads.append(int(ret_b[4]) - int(ret_b[2]))
                else:
                    ret_site_downloads.append(0)
            return total_upload, total_download, ret_sites, ret_site_uploads, ret_site_downloads
        else:
            return 0, 0, [], [], []

    def is_exists_download_history(self, title, tmdbid, mtype=None):
        """
        查询下载历史是否存在
        """
        if not title or not tmdbid:
            return False
        if mtype:
            count = self._db.query(DOWNLOADHISTORY).filter(
                (DOWNLOADHISTORY.TITLE == title) | (DOWNLOADHISTORY.TMDBID == tmdbid),
                DOWNLOADHISTORY.TYPE == mtype).count()
        else:
            count = self._db.query(DOWNLOADHISTORY).filter(
                (DOWNLOADHISTORY.TITLE == title) | (DOWNLOADHISTORY.TMDBID == tmdbid)).count()
        if count > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def insert_download_history(self, media_info):
        """
        新增下载历史
        """
        if not media_info:
            return
        if not media_info.title or not media_info.tmdb_id:
            return
        if self.is_exists_download_history(media_info.title, media_info.tmdb_id, media_info.type.value):
            self._db.query(DOWNLOADHISTORY).filter(DOWNLOADHISTORY.TITLE == media_info.title,
                                                   DOWNLOADHISTORY.TMDBID == media_info.tmdb_id,
                                                   DOWNLOADHISTORY.TYPE == media_info.type.value).update(
                {
                    "TORRENT": media_info.org_string,
                    "ENCLOSURE": media_info.enclosure,
                    "DESC": media_info.description,
                    "DATE": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                    "SITE": media_info.site
                }
            )
        else:
            self._db.insert(DOWNLOADHISTORY(
                TITLE=media_info.title,
                YEAR=media_info.year,
                TYPE=media_info.type.value,
                TMDBID=media_info.tmdb_id,
                VOTE=media_info.vote_average,
                POSTER=media_info.get_poster_image(),
                OVERVIEW=media_info.overview,
                TORRENT=media_info.org_string,
                ENCLOSURE=media_info.enclosure,
                DESC=media_info.description,
                DATE=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                SITE=media_info.site
            ))

    def get_download_history(self, date=None, hid=None, num=30, page=1):
        """
        查询下载历史
        """
        if hid:
            return self._db.query(DOWNLOADHISTORY).filter(DOWNLOADHISTORY.ID == int(hid)).all()
        elif date:
            return self._db.query(DOWNLOADHISTORY).filter(
                DOWNLOADHISTORY.DATE > date).order_by(DOWNLOADHISTORY.DATE.desc()).all()
        else:
            offset = (int(page) - 1) * int(num)
            return self._db.query(DOWNLOADHISTORY).order_by(
                DOWNLOADHISTORY.DATE.desc()).limit(num).offset(offset).all()

    def is_media_downloaded(self, title, tmdbid):
        """
        根据标题和年份检查是否下载过
        """
        if self.is_exists_download_history(title, tmdbid):
            return True
        count = self._db.query(TRANSFERHISTORY).filter(TRANSFERHISTORY.TITLE == title).count()
        if count > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def insert_brushtask(self, brush_id, item):
        """
        新增刷流任务
        """
        if not brush_id:
            self._db.insert(SITEBRUSHTASK(
                NAME=item.get('name'),
                SITE=item.get('site'),
                FREELEECH=item.get('free'),
                RSS_RULE=str(item.get('rss_rule')),
                REMOVE_RULE=str(item.get('remove_rule')),
                SEED_SIZE=item.get('seed_size'),
                INTEVAL=item.get('interval'),
                DOWNLOADER=item.get('downloader'),
                TRANSFER=item.get('transfer'),
                DOWNLOAD_COUNT='0',
                REMOVE_COUNT='0',
                DOWNLOAD_SIZE='0',
                UPLOAD_SIZE='0',
                STATE=item.get('state'),
                LST_MOD_DATE=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            ))
        else:
            self._db.query(SITEBRUSHTASK).filter(SITEBRUSHTASK.ID == int(brush_id)).update(
                {
                    "NAME": item.get('name'),
                    "SITE": item.get('site'),
                    "FREELEECH": item.get('free'),
                    "RSS_RULE": str(item.get('rss_rule')),
                    "REMOVE_RULE": str(item.get('remove_rule')),
                    "SEED_SIZE": item.get('seed_size'),
                    "INTEVAL": item.get('interval'),
                    "DOWNLOADER": item.get('downloader'),
                    "TRANSFER": item.get('transfer'),
                    "STATE": item.get('state'),
                    "LST_MOD_DATE": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                }
            )

    @DbPersist(_db)
    def delete_brushtask(self, brush_id):
        """
        删除刷流任务
        """
        self._db.query(SITEBRUSHTASK).filter(SITEBRUSHTASK.ID == int(brush_id)).delete()
        self._db.query(SITEBRUSHTORRENTS).filter(SITEBRUSHTORRENTS.TASK_ID == brush_id).delete()

    def get_brushtasks(self, brush_id=None):
        """
        查询刷流任务
        """
        if brush_id:
            return self._db.query(SITEBRUSHTASK).filter(SITEBRUSHTASK.ID == int(brush_id)).first()
        else:
            return self._db.query(SITEBRUSHTASK).all()

    def get_brushtask_totalsize(self, brush_id):
        """
        查询刷流任务总体积
        """
        if not brush_id:
            return 0
        ret = self._db.query(func.sum(cast(SITEBRUSHTORRENTS.TORRENT_SIZE,
                                           Integer))).filter(SITEBRUSHTORRENTS.TASK_ID == brush_id,
                                                             SITEBRUSHTORRENTS.DOWNLOAD_ID != '0').first()
        if ret:
            return ret[0] or 0
        else:
            return 0

    @DbPersist(_db)
    def add_brushtask_download_count(self, brush_id):
        """
        增加刷流下载数
        """
        if not brush_id:
            return
        self._db.query(SITEBRUSHTASK).filter(SITEBRUSHTASK.ID == int(brush_id)).update(
            {
                "DOWNLOAD_COUNT": SITEBRUSHTASK.DOWNLOAD_COUNT + 1,
                "LST_MOD_DATE": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            }
        )

    def get_brushtask_remove_size(self, brush_id):
        """
        获取已删除种子的上传量
        """
        if not brush_id:
            return 0
        return self._db.query(SITEBRUSHTORRENTS.TORRENT_SIZE).filter(SITEBRUSHTORRENTS.TASK_ID == brush_id,
                                                                     SITEBRUSHTORRENTS.DOWNLOAD_ID == '0').all()

    @DbPersist(_db)
    def add_brushtask_upload_count(self, brush_id, upload_size, download_size, remove_count):
        """
        更新上传下载量和删除种子数
        """
        if not brush_id:
            return
        delete_upsize = 0
        delete_dlsize = 0
        remove_sizes = self.get_brushtask_remove_size(brush_id)
        for remove_size in remove_sizes:
            if not remove_size[0]:
                continue
            if str(remove_size[0]).find(",") != -1:
                sizes = str(remove_size[0]).split(",")
                delete_upsize += int(sizes[0] or 0)
                if len(sizes) > 1:
                    delete_dlsize += int(sizes[1] or 0)
            else:
                delete_upsize += int(remove_size[0])
        self._db.query(SITEBRUSHTASK).filter(SITEBRUSHTASK.ID == int(brush_id)).update({
            "REMOVE_COUNT": SITEBRUSHTASK.REMOVE_COUNT + remove_count,
            "UPLOAD_SIZE": int(upload_size) + delete_upsize,
            "DOWNLOAD_SIZE": int(download_size) + delete_dlsize,
        })

    @DbPersist(_db)
    def insert_brushtask_torrent(self, brush_id, title, enclosure, downloader, download_id, size):
        """
        增加刷流下载的种子信息
        """
        if not brush_id:
            return
        if self.is_brushtask_torrent_exists(brush_id, title, enclosure):
            return
        self._db.insert(SITEBRUSHTORRENTS(
            TASK_ID=brush_id,
            TORRENT_NAME=title,
            TORRENT_SIZE=size,
            ENCLOSURE=enclosure,
            DOWNLOADER=downloader,
            DOWNLOAD_ID=download_id,
            LST_MOD_DATE=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        ))

    def get_brushtask_torrents(self, brush_id, active=True):
        """
        查询刷流任务所有种子
        """
        if not brush_id:
            return []
        if active:
            return self._db.query(SITEBRUSHTORRENTS).filter(
                SITEBRUSHTORRENTS.TASK_ID == int(brush_id),
                SITEBRUSHTORRENTS.DOWNLOAD_ID != '0').all()
        else:
            return self._db.query(SITEBRUSHTORRENTS).filter(
                SITEBRUSHTORRENTS.TASK_ID == int(brush_id)
            ).order_by(SITEBRUSHTORRENTS.LST_MOD_DATE.desc()).all()

    def is_brushtask_torrent_exists(self, brush_id, title, enclosure):
        """
        查询刷流任务种子是否已存在
        """
        if not brush_id:
            return False
        count = self._db.query(SITEBRUSHTORRENTS).filter(SITEBRUSHTORRENTS.TASK_ID == brush_id,
                                                         SITEBRUSHTORRENTS.TORRENT_NAME == title,
                                                         SITEBRUSHTORRENTS.ENCLOSURE == enclosure).count()
        if count > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def update_brushtask_torrent_state(self, ids: list):
        """
        更新刷流种子的状态
        """
        if not ids:
            return
        for _id in ids:
            self._db.query(SITEBRUSHTORRENTS).filter(SITEBRUSHTORRENTS.TASK_ID == _id[1],
                                                     SITEBRUSHTORRENTS.DOWNLOAD_ID == _id[2]).update(
                {
                    "TORRENT_SIZE": _id[0],
                    "DOWNLOAD_ID": '0'
                }
            )

    @DbPersist(_db)
    def delete_brushtask_torrent(self, brush_id, download_id):
        """
        删除刷流种子记录
        """
        if not download_id or not brush_id:
            return
        self._db.query(SITEBRUSHTORRENTS).filter(SITEBRUSHTORRENTS.TASK_ID == brush_id,
                                                 SITEBRUSHTORRENTS.DOWNLOAD_ID == download_id).delete()

    def get_user_downloaders(self, did=None):
        """
        查询自定义下载器
        """
        if did:
            return self._db.query(SITEBRUSHDOWNLOADERS).filter(SITEBRUSHDOWNLOADERS.ID == int(did)).first()
        else:
            return self._db.query(SITEBRUSHDOWNLOADERS).all()

    @DbPersist(_db)
    def update_user_downloader(self, did, name, dtype, user_config, note):
        """
        新增自定义下载器
        """
        if did:
            self._db.query(SITEBRUSHDOWNLOADERS).filter(SITEBRUSHDOWNLOADERS.ID == int(did)).update(
                {
                    "NAME": name,
                    "TYPE": dtype,
                    "HOST": user_config.get("host"),
                    "PORT": user_config.get("port"),
                    "USERNAME": user_config.get("username"),
                    "PASSWORD": user_config.get("password"),
                    "SAVE_DIR": user_config.get("save_dir"),
                    "NOTE": note
                }
            )
        else:
            self._db.insert(SITEBRUSHDOWNLOADERS(
                NAME=name,
                TYPE=dtype,
                HOST=user_config.get("host"),
                PORT=user_config.get("port"),
                USERNAME=user_config.get("username"),
                PASSWORD=user_config.get("password"),
                SAVE_DIR=user_config.get("save_dir"),
                NOTE=note
            ))

    @DbPersist(_db)
    def delete_user_downloader(self, did):
        """
        删除自定义下载器
        """
        self._db.query(SITEBRUSHDOWNLOADERS).filter(SITEBRUSHDOWNLOADERS.ID == int(did)).delete()

    @DbPersist(_db)
    def add_filter_group(self, name, default='N'):
        """
        新增规则组
        """
        if default == 'Y':
            self.set_default_filtergroup(0)
        group_id = self.get_filter_groupid_by_name(name)
        if group_id:
            self._db.query(CONFIGFILTERGROUP).filter(CONFIGFILTERGROUP.ID == int(group_id)).update({
                "IS_DEFAULT": default
            })
        else:
            self._db.insert(CONFIGFILTERGROUP(
                GROUP_NAME=name,
                IS_DEFAULT=default
            ))

    def get_filter_groupid_by_name(self, name):
        ret = self._db.query(CONFIGFILTERGROUP.ID).filter(CONFIGFILTERGROUP.GROUP_NAME == name).first()
        if ret:
            return ret[0]
        else:
            return ""

    @DbPersist(_db)
    def set_default_filtergroup(self, groupid):
        """
        设置默认的规则组
        """
        self._db.query(CONFIGFILTERGROUP).filter(CONFIGFILTERGROUP.ID == int(groupid)).update({
            "IS_DEFAULT": 'Y'
        })
        self._db.query(CONFIGFILTERGROUP).filter(CONFIGFILTERGROUP.ID != int(groupid)).update({
            "IS_DEFAULT": 'N'
        })

    @DbPersist(_db)
    def delete_filtergroup(self, groupid):
        """
        删除规则组
        """
        self._db.query(CONFIGFILTERRULES).filter(CONFIGFILTERRULES.GROUP_ID == groupid).delete()
        self._db.query(CONFIGFILTERGROUP).filter(CONFIGFILTERGROUP.ID == int(groupid)).delete()

    @DbPersist(_db)
    def delete_filterrule(self, ruleid):
        """
        删除规则
        """
        self._db.query(CONFIGFILTERRULES).filter(CONFIGFILTERRULES.ID == int(ruleid)).delete()

    @DbPersist(_db)
    def insert_filter_rule(self, item, ruleid=None):
        """
        新增规则
        """
        if ruleid:
            self._db.query(CONFIGFILTERRULES).filter(CONFIGFILTERRULES.ID == int(ruleid)).update(
                {
                    "ROLE_NAME": item.get("name"),
                    "PRIORITY": item.get("pri"),
                    "INCLUDE": item.get("include"),
                    "EXCLUDE": item.get("exclude"),
                    "SIZE_LIMIT": item.get("size"),
                    "NOTE": item.get("free")
                }
            )
        else:
            self._db.insert(CONFIGFILTERRULES(
                GROUP_ID=item.get("group"),
                ROLE_NAME=item.get("name"),
                PRIORITY=item.get("pri"),
                INCLUDE=item.get("include"),
                EXCLUDE=item.get("exclude"),
                SIZE_LIMIT=item.get("size"),
                NOTE=item.get("free")
            ))

    def get_userrss_tasks(self, taskid=None):
        if taskid:
            return self._db.query(CONFIGUSERRSS).filter(CONFIGUSERRSS.ID == int(taskid)).all()
        else:
            return self._db.query(CONFIGUSERRSS).all()

    @DbPersist(_db)
    def delete_userrss_task(self, tid):
        if not tid:
            return
        self._db.query(CONFIGUSERRSS).filter(CONFIGUSERRSS.ID == int(tid)).delete()

    @DbPersist(_db)
    def update_userrss_task_info(self, tid, count):
        if not tid:
            return
        self._db.query(CONFIGUSERRSS).filter(CONFIGUSERRSS.ID == int(tid)).update(
            {
                "PROCESS_COUNT": CONFIGUSERRSS.PROCESS_COUNT + count,
                "UPDATE_TIME": time.strftime('%Y-%m-%d %H:%M:%S',
                                             time.localtime(time.time()))
            }
        )

    @DbPersist(_db)
    def update_userrss_task(self, item):
        if item.get("id") and self.get_userrss_tasks(item.get("id")):
            self._db.query(CONFIGUSERRSS).filter(CONFIGUSERRSS.ID == int(item.get("id"))).update(
                {
                    "NAME": item.get("name"),
                    "ADDRESS": item.get("address"),
                    "PARSER": item.get("parser"),
                    "INTERVAL": item.get("interval"),
                    "USES": item.get("uses"),
                    "INCLUDE": item.get("include"),
                    "EXCLUDE": item.get("exclude"),
                    "FILTER": item.get("filterrule"),
                    "UPDATE_TIME": time.strftime('%Y-%m-%d %H:%M:%S',
                                                 time.localtime(time.time())),
                    "STATE": item.get("state"),
                    "SAVE_PATH": item.get("save_path"),
                    "DOWNLOAD_SETTING": item.get("download_setting"),
                    "NOTE": item.get("note")
                }
            )
        else:
            self._db.insert(CONFIGUSERRSS(
                NAME=item.get("name"),
                ADDRESS=item.get("address"),
                PARSER=item.get("parser"),
                INTERVAL=item.get("interval"),
                USES=item.get("uses"),
                INCLUDE=item.get("include"),
                EXCLUDE=item.get("exclude"),
                FILTER=item.get("filterrule"),
                UPDATE_TIME=time.strftime('%Y-%m-%d %H:%M:%S',
                                          time.localtime(time.time())),
                STATE=item.get("state"),
                SAVE_PATH=item.get("save_path"),
                DOWNLOAD_SETTING=item.get("download_setting"),
            ))

    def get_userrss_parser(self, pid=None):
        if pid:
            return self._db.query(CONFIGRSSPARSER).filter(CONFIGRSSPARSER.ID == int(pid)).first()
        else:
            return self._db.query(CONFIGRSSPARSER).all()

    @DbPersist(_db)
    def delete_userrss_parser(self, pid):
        if not pid:
            return
        self._db.query(CONFIGRSSPARSER).filter(CONFIGRSSPARSER.ID == int(pid)).delete()

    @DbPersist(_db)
    def update_userrss_parser(self, item):
        if not item:
            return
        if item.get("id") and self.get_userrss_parser(item.get("id")):
            self._db.query(CONFIGRSSPARSER).filter(CONFIGRSSPARSER.ID == int(item.get("id"))).update(
                {
                    "NAME": item.get("name"),
                    "TYPE": item.get("type"),
                    "FORMAT": item.get("format"),
                    "PARAMS": item.get("params")
                }
            )
        else:
            self._db.insert(CONFIGRSSPARSER(
                NAME=item.get("name"),
                TYPE=item.get("type"),
                FORMAT=item.get("format"),
                PARAMS=item.get("params")
            ))

    def excute(self, sql):
        return self._db.excute(sql)

    @DbPersist(_db)
    def insert_userrss_task_history(self, task_id, title, downloader):
        """
        增加自定义RSS订阅任务的下载记录
        """
        self._db.insert(USERRSSTASKHISTORY(
            TASK_ID=task_id,
            TITLE=title,
            DOWNLOADER=downloader,
            DATE=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        ))

    def get_userrss_task_history(self, task_id):
        """
        查询自定义RSS订阅任务的下载记录
        """
        if not task_id:
            return []
        return self._db.query(USERRSSTASKHISTORY).filter(USERRSSTASKHISTORY.TASK_ID == task_id)\
            .order_by(USERRSSTASKHISTORY.DATE.desc()).all()

    def get_rss_history(self, rtype=None, rid=None):
        """
        查询RSS历史
        """
        if rid:
            return self._db.query(RSSHISTORY).filter(RSSHISTORY.ID == int(rid)).all()
        elif rtype:
            return self._db.query(RSSHISTORY).filter(RSSHISTORY.TYPE == rtype)\
                .order_by(RSSHISTORY.FINISH_TIME.desc()).all()
        return self._db.query(RSSHISTORY).order_by(RSSHISTORY.FINISH_TIME.desc()).all()

    def is_exists_rss_history(self, rssid):
        """
        判断RSS历史是否存在
        """
        if not rssid:
            return False
        count = self._db.query(RSSHISTORY).filter(RSSHISTORY.RSSID == rssid).count()
        if count > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def insert_rss_history(self, rssid, rtype, name, year, tmdbid, image, desc, season=None, total=None, start=None):
        """
        登记RSS历史
        """
        if not self.is_exists_rss_history(rssid):
            self._db.insert(RSSHISTORY(
                TYPE=rtype,
                RSSID=rssid,
                NAME=name,
                YEAR=year,
                TMDBID=tmdbid,
                SEASON=season,
                IMAGE=image,
                DESC=desc,
                TOTAL=total,
                START=start,
                FINISH_TIME=time.strftime('%Y-%m-%d %H:%M:%S',
                                          time.localtime(time.time()))
            ))

    @DbPersist(_db)
    def delete_rss_history(self, rssid):
        """
        删除RSS历史
        """
        if not rssid:
            return
        self._db.query(RSSHISTORY).filter(RSSHISTORY.ID == int(rssid)).delete()

    @DbPersist(_db)
    def insert_custom_word(self, replaced, replace, front, back, offset, wtype, gid, season, enabled, regex, whelp,
                           note=None):
        """
        增加自定义识别词
        """
        self._db.insert(CUSTOMWORDS(
            REPLACED=replaced,
            REPLACE=replace,
            FRONT=front,
            BACK=back,
            OFFSET=offset,
            TYPE=int(wtype),
            GROUP_ID=int(gid),
            SEASON=int(season),
            ENABLED=int(enabled),
            REGEX=int(regex),
            HELP=whelp,
            NOTE=note
        ))

    @DbPersist(_db)
    def delete_custom_word(self, wid):
        """
        删除自定义识别词
        """
        self._db.query(CUSTOMWORDS).filter(CUSTOMWORDS.ID == int(wid)).delete()

    @DbPersist(_db)
    def check_custom_word(self, wid, enabled):
        """
        设置自定义识别词状态
        """
        self._db.query(CUSTOMWORDS).filter(CUSTOMWORDS.ID == int(wid)).update(
            {
                "ENABLED": int(enabled)
            }
        )

    def get_custom_words(self, wid=None, gid=None, enabled=None, wtype=None, regex=None):
        """
        查询自定义识别词
        """
        if wid:
            return self._db.query(CUSTOMWORDS).filter(CUSTOMWORDS.ID == int(wid))\
                .order_by(CUSTOMWORDS.GROUP_ID).all()
        elif gid:
            return self._db.query(CUSTOMWORDS).filter(CUSTOMWORDS.GROUP_ID == int(gid))\
                .order_by(CUSTOMWORDS.GROUP_ID).all()
        elif wtype and enabled is not None and regex is not None:
            return self._db.query(CUSTOMWORDS).filter(CUSTOMWORDS.ENABLED == int(enabled),
                                                      CUSTOMWORDS.TYPE == int(wtype),
                                                      CUSTOMWORDS.REGEX == int(regex))\
                .order_by(CUSTOMWORDS.GROUP_ID).all()
        return self._db.query(CUSTOMWORDS).all().order_by(CUSTOMWORDS.GROUP_ID)

    def is_custom_words_existed(self, replaced=None, front=None, back=None):
        """
        查询自定义识别词
        """
        if replaced:
            count = self._db.query(CUSTOMWORDS).filter(CUSTOMWORDS.REPLACED == replaced).count()
        elif front and back:
            count = self._db.query(CUSTOMWORDS).filter(CUSTOMWORDS.FRONT == front,
                                                       CUSTOMWORDS.BACK == back).count()
        else:
            return False
        if count > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def insert_custom_word_groups(self, title, year, gtype, tmdbid, season_count, note=None):
        """
        增加自定义识别词组
        """
        self._db.insert(CUSTOMWORDGROUPS(
            TITLE=title,
            YEAR=year,
            TYPE=int(gtype),
            TMDBID=int(tmdbid),
            SEASON_COUNT=int(season_count),
            NOTE=note
        ))

    @DbPersist(_db)
    def delete_custom_word_group(self, gid):
        """
        删除自定义识别词组
        """
        if not gid:
            return
        self._db.query(CUSTOMWORDS).filter(CUSTOMWORDS.GROUP_ID == int(gid)).delete()
        self._db.query(CUSTOMWORDGROUPS).filter(CUSTOMWORDGROUPS.ID == int(gid)).delete()

    def get_custom_word_groups(self, gid=None, tmdbid=None, gtype=None):
        """
        查询自定义识别词组
        """
        if gid:
            return self._db.query(CUSTOMWORDGROUPS).filter(CUSTOMWORDGROUPS.ID == int(gid)).all()
        if tmdbid and gtype:
            return self._db.query(CUSTOMWORDGROUPS).filter(CUSTOMWORDGROUPS.TMDBID == int(tmdbid),
                                                           CUSTOMWORDGROUPS.TYPE == int(gtype)).all()
        return self._db.query(CUSTOMWORDGROUPS).all()

    def is_custom_word_group_existed(self, tmdbid=None, gtype=None):
        """
        查询自定义识别词组
        """
        if not gtype or not tmdbid:
            return False
        count = self._db.query(CUSTOMWORDGROUPS).filter(CUSTOMWORDGROUPS.TMDBID == int(tmdbid),
                                                        CUSTOMWORDGROUPS.TYPE == int(gtype)).count()
        if count > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def insert_config_sync_path(self, source, dest, unknown, mode, rename, enabled, note=None):
        """
        增加目录同步
        """
        return self._db.insert(CONFIGSYNCPATHS(
            SOURCE=source,
            DEST=dest,
            UNKNOWN=unknown,
            MODE=mode,
            RENAME=int(rename),
            ENABLED=int(enabled),
            NOTE=note
        ))

    @DbPersist(_db)
    def delete_config_sync_path(self, sid):
        """
        删除目录同步
        """
        if not sid:
            return
        self._db.query(CONFIGSYNCPATHS).filter(CONFIGSYNCPATHS.ID == int(sid)).delete()

    def get_config_sync_paths(self, sid=None):
        """
        查询目录同步
        """
        if sid:
            return self._db.query(CONFIGSYNCPATHS).filter(CONFIGSYNCPATHS.ID == int(sid)).all()
        return self._db.query(CONFIGSYNCPATHS).all()

    @DbPersist(_db)
    def check_config_sync_paths(self, sid=None, source=None, rename=None, enabled=None):
        """
        设置目录同步状态
        """
        if sid and rename is not None:
            self._db.query(CONFIGSYNCPATHS).filter(CONFIGSYNCPATHS.ID == int(sid)).update(
                {
                    "RENAME": int(rename)
                }
            )
        elif sid and enabled is not None:
            self._db.query(CONFIGSYNCPATHS).filter(CONFIGSYNCPATHS.ID == int(sid)).update(
                {
                    "ENABLED": int(enabled)
                }
            )
        elif source and enabled is not None:
            self._db.query(CONFIGSYNCPATHS).filter(CONFIGSYNCPATHS.SOURCE == source).update(
                {
                    "ENABLED": int(enabled)
                }
            )

    @DbPersist(_db)
    def delete_download_setting(self, sid):
        """
        删除下载设置
        """
        if not sid:
            return
        self._db.query(DOWNLOADSETTING).filter(DOWNLOADSETTING.ID == int(sid)).delete()

    def get_download_setting(self, sid=None):
        """
        查询下载设置
        """
        if sid:
            return self._db.query(DOWNLOADSETTING).filter(DOWNLOADSETTING.ID == int(sid)).all()
        return self._db.query(DOWNLOADSETTING).all()

    @DbPersist(_db)
    def update_download_setting(self,
                                sid,
                                name,
                                category,
                                tags,
                                content_layout,
                                is_paused,
                                upload_limit,
                                download_limit,
                                ratio_limit,
                                seeding_time_limit,
                                downloader):
        """
        设置下载设置
        """
        if sid:
            self._db.query(DOWNLOADSETTING).filter(DOWNLOADSETTING.ID == int(sid)).update(
                {
                    "NAME": name,
                    "CATEGORY": category,
                    "TAGS": tags,
                    "CONTENT_LAYOUT": int(content_layout),
                    "IS_PAUSED": int(is_paused),
                    "UPLOAD_LIMIT": int(float(upload_limit)),
                    "DOWNLOAD_LIMIT": int(float(download_limit)),
                    "RATIO_LIMIT": int(round(float(ratio_limit), 2) * 100),
                    "SEEDING_TIME_LIMIT": int(float(seeding_time_limit)),
                    "DOWNLOADER": downloader
                }
            )
        else:
            self._db.insert(DOWNLOADSETTING(
                NAME=name,
                CATEGORY=category,
                TAGS=tags,
                CONTENT_LAYOUT=int(content_layout),
                IS_PAUSED=int(is_paused),
                UPLOAD_LIMIT=int(float(upload_limit)),
                DOWNLOAD_LIMIT=int(float(download_limit)),
                RATIO_LIMIT=int(round(float(ratio_limit), 2) * 100),
                SEEDING_TIME_LIMIT=int(float(seeding_time_limit)),
                DOWNLOADER=downloader
            ))

    @DbPersist(_db)
    def delete_message_client(self, cid):
        """
        删除消息服务器
        """
        if not cid:
            return
        self._db.query(MESSAGECLIENT).filter(MESSAGECLIENT.ID == int(cid)).delete()

    def get_message_client(self, cid=None):
        """
        查询消息服务器
        """
        if cid:
            return self._db.query(MESSAGECLIENT).filter(MESSAGECLIENT.ID == int(cid)).all()
        return self._db.query(MESSAGECLIENT).order_by(MESSAGECLIENT.TYPE).all()

    @DbPersist(_db)
    def insert_message_client(self,
                              name,
                              ctype,
                              config,
                              switchs: list,
                              interactive,
                              enabled,
                              note=''):
        """
        设置消息服务器
        """
        self._db.insert(MESSAGECLIENT(
            NAME=name,
            TYPE=ctype,
            CONFIG=config,
            SWITCHS=json.dumps(switchs),
            INTERACTIVE=int(interactive),
            ENABLED=int(enabled),
            NOTE=note
        ))

    @DbPersist(_db)
    def check_message_client(self, cid=None, interactive=None, enabled=None, ctype=None):
        """
        设置目录同步状态
        """
        if cid and interactive is not None:
            self._db.query(MESSAGECLIENT).filter(MESSAGECLIENT.ID == int(cid)).update(
                {
                    "INTERACTIVE": int(interactive)
                }
            )
        elif cid and enabled is not None:
            self._db.query(MESSAGECLIENT).filter(MESSAGECLIENT.ID == int(cid)).update(
                {
                    "ENABLED": int(enabled)
                }
            )
        elif not cid and int(interactive) == 0 and ctype:
            self._db.query(MESSAGECLIENT).filter(MESSAGECLIENT.INTERACTIVE == 1,
                                                 MESSAGECLIENT.TYPE == ctype).update(
                {
                    "INTERACTIVE": 0
                }
            )

    @DbPersist(_db)
    def delete_torrent_remove_task(self, tid):
        """
        删除自动删种策略
        """
        if not tid:
            return
        self._db.query(TORRENTREMOVETASK).filter(TORRENTREMOVETASK.ID == int(tid)).delete()

    def get_torrent_remove_tasks(self, tid=None):
        """
        查询自动删种策略
        """
        if tid:
            return self._db.query(TORRENTREMOVETASK).filter(TORRENTREMOVETASK.ID == int(tid)).all()
        return self._db.query(TORRENTREMOVETASK).order_by(TORRENTREMOVETASK.NAME).all()

    @DbPersist(_db)
    def insert_torrent_remove_task(self,
                                   name,
                                   action,
                                   interval,
                                   enabled,
                                   samedata,
                                   onlynastool,
                                   downloader,
                                   config: dict,
                                   note=None):
        """
        设置自动删种策略
        """
        self._db.insert(TORRENTREMOVETASK(
            NAME=name,
            ACTION=int(action),
            INTERVAL=int(interval),
            ENABLED=int(enabled),
            SAMEDATA=int(samedata),
            ONLYNASTOOL=int(onlynastool),
            DOWNLOADER=downloader,
            CONFIG=json.dumps(config),
            NOTE=note
        ))

    @DbPersist(_db)
    def delete_douban_history(self, hid):
        """
        删除豆瓣同步记录
        """
        if not hid:
            return
        self._db.query(DOUBANMEDIAS).filter(DOUBANMEDIAS.ID == int(hid)).delete()

    def get_douban_history(self):
        """
        查询豆瓣同步记录
        """
        return self._db.query(DOUBANMEDIAS).order_by(DOUBANMEDIAS.ADD_TIME.desc()).all()
