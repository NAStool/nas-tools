import datetime
import os.path
import time
import json
from enum import Enum
from sqlalchemy import cast, func, and_, case

from app.db import MainDb, DbPersist
from app.db.models import *
from app.utils import StringUtils
from app.utils.types import MediaType, RmtMode


class DbHelper:
    _db = MainDb()

    @DbPersist(_db)
    def insert_search_results(self, media_items: list, title=None, ident_flag=True):
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
            data_list.append(
                SEARCHRESULTINFO(
                    TORRENT_NAME=media_item.org_string,
                    ENCLOSURE=media_item.enclosure,
                    DESCRIPTION=media_item.description,
                    TYPE=mtype if ident_flag else '',
                    TITLE=media_item.title if ident_flag else title,
                    YEAR=media_item.year if ident_flag else '',
                    SEASON=media_item.get_season_string() if ident_flag else '',
                    EPISODE=media_item.get_episode_string() if ident_flag else '',
                    ES_STRING=media_item.get_season_episode_string() if ident_flag else '',
                    VOTE=media_item.vote_average or "0",
                    IMAGE=media_item.get_backdrop_image(default=False, original=True),
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
                    DOWNLOAD_VOLUME_FACTOR=media_item.download_volume_factor,
                    NOTE=media_item.labels
                ))
        self._db.insert(data_list)

    def get_search_result_by_id(self, dl_id):
        """
        根据ID从数据库中查询搜索结果的一条记录
        """
        return self._db.query(SEARCHRESULTINFO).filter(SEARCHRESULTINFO.ID == dl_id).all()

    def get_search_results(self):
        """
        查询搜索结果的所有记录
        """
        return self._db.query(SEARCHRESULTINFO).all()

    @DbPersist(_db)
    def delete_all_search_torrents(self):
        """
        删除所有搜索的记录
        """
        self._db.query(SEARCHRESULTINFO).delete()

    def is_transfer_history_exists(self, source_path, source_filename, dest_path, dest_filename):
        """
        查询识别转移记录
        """
        if not source_path or not source_filename or not dest_path or not dest_filename:
            return False
        ret = self._db.query(TRANSFERHISTORY).filter(TRANSFERHISTORY.SOURCE_PATH == source_path,
                                                     TRANSFERHISTORY.SOURCE_FILENAME == source_filename,
                                                     TRANSFERHISTORY.DEST_PATH == dest_path,
                                                     TRANSFERHISTORY.DEST_FILENAME == dest_filename).count()
        return True if ret > 0 else False

    def update_transfer_history_date(self, source_path, source_filename, dest_path, dest_filename, date):
        """
        更新历史转移记录时间
        """
        self._db.query(TRANSFERHISTORY).filter(TRANSFERHISTORY.SOURCE_PATH == source_path,
                                               TRANSFERHISTORY.SOURCE_FILENAME == source_filename,
                                               TRANSFERHISTORY.DEST_PATH == dest_path,
                                               TRANSFERHISTORY.DEST_FILENAME == dest_filename).update(
            {
                "DATE": date
            }
        )

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
        timestr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        if self.is_transfer_history_exists(source_path, source_filename, dest_path, dest_filename):
            # 更新历史转移记录的时间
            self.update_transfer_history_date(source_path, source_filename, dest_path, dest_filename, timestr)
            return
        dest = dest or ""
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

    def get_transfer_info_by_id(self, logid):
        """
        据logid查询PATH
        """
        return self._db.query(TRANSFERHISTORY).filter(TRANSFERHISTORY.ID == int(logid)).first()

    def get_transfer_info_by(self, tmdbid, season=None, season_episode=None):
        """
        据tmdbid、season、season_episode查询转移记录
        """
        # 电视剧所有季集｜电影
        if tmdbid and not season and not season_episode:
            return self._db.query(TRANSFERHISTORY).filter(TRANSFERHISTORY.TMDBID == int(tmdbid)).all()
        # 电视剧某季
        if tmdbid and season:
            season = f"%{season}%"
            return self._db.query(TRANSFERHISTORY).filter(TRANSFERHISTORY.TMDBID == int(tmdbid),
                                                          TRANSFERHISTORY.SEASON_EPISODE.like(season)).all()
        # 电视剧某季某集
        if tmdbid and season_episode:
            return self._db.query(TRANSFERHISTORY).filter(TRANSFERHISTORY.TMDBID == int(tmdbid),
                                                          TRANSFERHISTORY.SEASON_EPISODE == season_episode).all()

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

    def get_transfer_unknown_paths(self):
        """
        查询未识别的记录列表
        """
        return self._db.query(TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.STATE == 'N').all()

    def get_transfer_unknown_paths_by_page(self, search, page, rownum):
        """
        按页查询未识别的记录列表
        """
        if int(page) == 1:
            begin_pos = 0
        else:
            begin_pos = (int(page) - 1) * int(rownum)
        if search:
            search = f"%{search}%"
            count = self._db.query(TRANSFERUNKNOWN).filter((TRANSFERUNKNOWN.STATE == 'N')
                                                           & (TRANSFERUNKNOWN.PATH.like(search))).count()
            data = self._db.query(TRANSFERUNKNOWN).filter((TRANSFERUNKNOWN.STATE == 'N')
                                                          & (TRANSFERUNKNOWN.PATH.like(search))).order_by(
                TRANSFERUNKNOWN.ID.desc()).limit(int(rownum)).offset(begin_pos).all()
            return count, data
        else:
            return self._db.query(TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.STATE == 'N').count(), self._db.query(
                TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.STATE == 'N').order_by(
                TRANSFERUNKNOWN.ID.desc()).limit(int(rownum)).offset(begin_pos).all()

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

    def get_unknown_info_by_id(self, tid):
        """
        查询未识别记录
        """
        if not tid:
            return []
        return self._db.query(TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.ID == int(tid)).first()

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
    def insert_transfer_unknown(self, path, dest, rmt_mode):
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
                STATE='N',
                MODE=str(rmt_mode.value)
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
    def delete_transfer_blacklist(self, path):
        """
        删除黑名单记录
        """
        self._db.query(TRANSFERBLACKLIST).filter(TRANSFERBLACKLIST.PATH == str(path)).delete()
        self._db.query(SYNCHISTORY).filter(SYNCHISTORY.PATH == str(path)).delete()

    @DbPersist(_db)
    def truncate_transfer_blacklist(self):
        """
        清空黑名单记录
        """
        self._db.query(TRANSFERBLACKLIST).delete()
        self._db.query(SYNCHISTORY).delete()

    @DbPersist(_db)
    def truncate_rss_episodes(self):
        """
        清空RSS历史记录
        """
        self._db.query(RSSTVEPISODES).delete()

    def get_config_site(self):
        """
        查询所有站点信息
        """
        return self._db.query(CONFIGSITE).order_by(cast(CONFIGSITE.PRI, Integer).asc())

    def get_site_by_id(self, tid):
        """
        查询1个站点信息
        """
        return self._db.query(CONFIGSITE).filter(CONFIGSITE.ID == int(tid)).all()

    @DbPersist(_db)
    def insert_config_site(self, name, site_pri,
                           rssurl=None, signurl=None, cookie=None, note=None, rss_uses=None):
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
    def update_site_cookie_ua(self, tid, cookie, ua=None):
        """
        更新站点Cookie和ua
        """
        if not tid:
            return
        rec = self._db.query(CONFIGSITE).filter(CONFIGSITE.ID == int(tid)).first()
        if rec.NOTE:
            note = json.loads(rec.NOTE)
            if ua:
                note['ua'] = ua
        else:
            note = {}
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

    def get_rss_movie_id(self, title, year=None, tmdbid=None):
        """
        获取订阅电影ID
        """
        if not title:
            return ""
        if tmdbid:
            ret = self._db.query(RSSMOVIES.ID).filter(RSSMOVIES.TMDBID == str(tmdbid)).first()
            if ret:
                return ret[0]
        if not year:
            items = self._db.query(RSSMOVIES).filter(RSSMOVIES.NAME == title).all()
        else:
            items = self._db.query(RSSMOVIES).filter(RSSMOVIES.NAME == title,
                                                     RSSMOVIES.YEAR == str(year)).all()
        if items:
            if tmdbid:
                for item in items:
                    if not item.TMDBID or item.TMDBID == str(tmdbid):
                        return item.ID
            else:
                return items[0].ID
        else:
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

    @DbPersist(_db)
    def update_rss_filter_order(self, rtype, rssid, res_order):
        """
        更新订阅命中的过滤规则优先级
        """
        if rtype == MediaType.MOVIE:
            self._db.query(RSSMOVIES).filter(RSSMOVIES.ID == int(rssid)).update({
                "FILTER_ORDER": res_order
            })
        else:
            self._db.query(RSSTVS).filter(RSSTVS.ID == int(rssid)).update({
                "FILTER_ORDER": res_order
            })

    def get_rss_overedition_order(self, rtype, rssid):
        """
        查询当前订阅的过滤优先级
        """
        if rtype == MediaType.MOVIE:
            res = self._db.query(RSSMOVIES.FILTER_ORDER).filter(RSSMOVIES.ID == int(rssid)).first()
        else:
            res = self._db.query(RSSTVS.FILTER_ORDER).filter(RSSTVS.ID == int(rssid)).first()
        if res and res[0]:
            return int(res[0])
        else:
            return 0

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
                         filter_include=None,
                         filter_exclude=None,
                         save_path=None,
                         download_setting=-1,
                         fuzzy_match=0,
                         desc=None,
                         note=None,
                         keyword=None):
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
            FILTER_INCLUDE=filter_include,
            FILTER_EXCLUDE=filter_exclude,
            SAVE_PATH=save_path,
            DOWNLOAD_SETTING=download_setting,
            FUZZY_MATCH=fuzzy_match,
            STATE=state,
            DESC=desc,
            NOTE=note,
            KEYWORD=keyword
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
            self._db.query(RSSMOVIES).filter(RSSMOVIES.NAME == title,
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

    def get_rss_tv_id(self, title, year=None, season=None, tmdbid=None):
        """
        获取订阅电视剧ID
        """
        if not title:
            return ""
        if tmdbid:
            if season:
                ret = self._db.query(RSSTVS.ID).filter(RSSTVS.TMDBID == tmdbid,
                                                       RSSTVS.SEASON == season).first()
            else:
                ret = self._db.query(RSSTVS.ID).filter(RSSTVS.TMDBID == tmdbid).first()
            if ret:
                return ret[0]
        if season and year:
            items = self._db.query(RSSTVS).filter(RSSTVS.NAME == title,
                                                  RSSTVS.SEASON == str(season),
                                                  RSSTVS.YEAR == str(year)).all()
        elif season and not year:
            items = self._db.query(RSSTVS).filter(RSSTVS.NAME == title,
                                                  RSSTVS.SEASON == str(season)).all()
        elif not season and year:
            items = self._db.query(RSSTVS).filter(RSSTVS.NAME == title,
                                                  RSSTVS.YEAR == str(year)).all()
        else:
            items = self._db.query(RSSTVS).filter(RSSTVS.NAME == title).all()
        if items:
            if tmdbid:
                for item in items:
                    if not item.TMDBID or item.TMDBID == str(tmdbid):
                        return item.ID
            else:
                return items[0].ID
        else:
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
                      filter_include=None,
                      filter_exclude=None,
                      save_path=None,
                      download_setting=-1,
                      total_ep=None,
                      current_ep=None,
                      fuzzy_match=0,
                      desc=None,
                      note=None,
                      keyword=None):
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
            FILTER_INCLUDE=filter_include,
            FILTER_EXCLUDE=filter_exclude,
            SAVE_PATH=save_path,
            DOWNLOAD_SETTING=download_setting,
            FUZZY_MATCH=fuzzy_match,
            TOTAL_EP=total_ep,
            CURRENT_EP=current_ep,
            TOTAL=total,
            LACK=lack,
            STATE=state,
            DESC=desc,
            NOTE=note,
            KEYWORD=keyword
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

    def get_users(self, uid=None, name=None):
        """
        查询用户列表
        """
        if uid:
            return self._db.query(CONFIGUSERS).filter(CONFIGUSERS.ID == uid).first()
        elif name:
            return self._db.query(CONFIGUSERS).filter(CONFIGUSERS.NAME == name).first()
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
            TRANSFERHISTORY.TYPE, func.substr(TRANSFERHISTORY.DATE, 1, 10)
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
            # 根据站点优先级排序
            return self._db.query(SITEUSERINFOSTATS) \
                .join(CONFIGSITE, SITEUSERINFOSTATS.SITE == CONFIGSITE.NAME) \
                .filter(SITEUSERINFOSTATS.URL.in_(tuple(strict_urls + ["__DUMMY__"]))) \
                .order_by(cast(CONFIGSITE.PRI, Integer).asc()).limit(num).all()
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

    def get_site_statistics_recent_sites(self, days=7, end_day=None, strict_urls=None):
        """
        查询近期上传下载量
        :param days 需要前几天的数据,传入7实际上会返回6天的数据?
        :param end_day 开始时间
        :param strict_urls 需要的站点URL的列表
        传入 7,"2020-01-01" 表示需要从2020-01-01之前6天的数据
        """
        # 查询最大最小日期
        if strict_urls is None:
            strict_urls = []
        end = datetime.datetime.now()
        if end_day:
            try:
                end = datetime.datetime.strptime(end_day, "%Y-%m-%d")
            except Exception as e:
                pass

        # 开始时间
        b_date = (end - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        # 结束时间
        e_date = end.strftime("%Y-%m-%d")
        # 大于开始时间范围里的最大日期与最小日期
        date_ret = self._db.query(func.max(SITESTATISTICSHISTORY.DATE),
                                  func.MIN(SITESTATISTICSHISTORY.DATE)).filter(
            SITESTATISTICSHISTORY.DATE > b_date, SITESTATISTICSHISTORY.DATE <= e_date).all()
        if date_ret and date_ret[0][0]:
            total_upload = 0
            total_download = 0
            ret_site_uploads = []
            ret_site_downloads = []
            min_date = date_ret[0][1]
            max_date = date_ret[0][0]
            # 查询开始值
            if strict_urls:
                subquery = self._db.query(SITESTATISTICSHISTORY.SITE.label("SITE"),
                                          SITESTATISTICSHISTORY.DATE.label("DATE"),
                                          func.sum(SITESTATISTICSHISTORY.UPLOAD).label("UPLOAD"),
                                          func.sum(SITESTATISTICSHISTORY.DOWNLOAD).label("DOWNLOAD")).filter(
                    SITESTATISTICSHISTORY.DATE >= min_date,
                    SITESTATISTICSHISTORY.DATE <= max_date,
                    SITESTATISTICSHISTORY.URL.in_(tuple(strict_urls + ["__DUMMY__"]))
                ).group_by(SITESTATISTICSHISTORY.SITE, SITESTATISTICSHISTORY.DATE).subquery()
            else:
                subquery = self._db.query(SITESTATISTICSHISTORY.SITE.label("SITE"),
                                          SITESTATISTICSHISTORY.DATE.label("DATE"),
                                          func.sum(SITESTATISTICSHISTORY.UPLOAD).label("UPLOAD"),
                                          func.sum(SITESTATISTICSHISTORY.DOWNLOAD).label("DOWNLOAD")).filter(
                    SITESTATISTICSHISTORY.DATE >= min_date,
                    SITESTATISTICSHISTORY.DATE <= max_date
                ).group_by(SITESTATISTICSHISTORY.SITE, SITESTATISTICSHISTORY.DATE).subquery()
            # 查询大于开始时间范围里的单日,单站点 最大值与最小值
            rets = self._db.query(subquery.c.SITE,
                                  func.min(subquery.c.UPLOAD),
                                  func.min(subquery.c.DOWNLOAD),
                                  func.max(subquery.c.UPLOAD),
                                  func.max(subquery.c.DOWNLOAD)).group_by(subquery.c.SITE).all()
            ret_sites = []
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

    def is_exists_download_history(self, enclosure, downloader, download_id):
        """
        查询下载历史是否存在
        """
        if enclosure:
            count = self._db.query(DOWNLOADHISTORY).filter(
                DOWNLOADHISTORY.ENCLOSURE == enclosure
            ).count()
        else:
            count = self._db.query(DOWNLOADHISTORY).filter(
                DOWNLOADHISTORY.DOWNLOADER == downloader,
                DOWNLOADHISTORY.DOWNLOAD_ID == download_id
            ).count()
        if count > 0:
            return True
        else:
            return False

    @DbPersist(_db)
    def insert_download_history(self, media_info, downloader, download_id, save_dir):
        """
        新增下载历史
        """
        if not media_info:
            return
        if not media_info.title or not media_info.tmdb_id:
            return
        if self.is_exists_download_history(enclosure=media_info.enclosure,
                                           downloader=downloader,
                                           download_id=download_id):
            self._db.query(DOWNLOADHISTORY).filter(DOWNLOADHISTORY.ENCLOSURE == media_info.enclosure,
                                                   DOWNLOADHISTORY.DOWNLOADER == downloader,
                                                   DOWNLOADHISTORY.DOWNLOAD_ID == download_id).update(
                {
                    "TORRENT": media_info.org_string,
                    "ENCLOSURE": media_info.enclosure,
                    "DESC": media_info.description,
                    "SITE": media_info.site,
                    "DOWNLOADER": downloader,
                    "DOWNLOAD_ID": download_id,
                    "SAVE_PATH": save_dir,
                    "SE": media_info.get_season_episode_string(),
                    "DATE": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
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
                SITE=media_info.site,
                DOWNLOADER=downloader,
                DOWNLOAD_ID=download_id,
                SAVE_PATH=save_dir,
                SE=media_info.get_season_episode_string()
            ))

    def get_download_history(self, date=None, hid=None, num=30, page=1):
        """
        查询下载历史
        """
        if hid:
            return self._db.query(DOWNLOADHISTORY).filter(DOWNLOADHISTORY.ID == int(hid)).all()
        sub_query = self._db.query(DOWNLOADHISTORY,
                                   func.max(DOWNLOADHISTORY.DATE)
                                   ).group_by(DOWNLOADHISTORY.TITLE).subquery()
        if date:
            return self._db.query(DOWNLOADHISTORY).filter(
                DOWNLOADHISTORY.DATE > date).join(
                sub_query,
                and_(sub_query.c.ID == DOWNLOADHISTORY.ID)
            ).order_by(DOWNLOADHISTORY.DATE.desc()).all()
        else:
            offset = (int(page) - 1) * int(num)
            return self._db.query(DOWNLOADHISTORY).join(
                sub_query,
                and_(sub_query.c.ID == DOWNLOADHISTORY.ID)
            ).order_by(
                DOWNLOADHISTORY.DATE.desc()
            ).limit(num).offset(offset).all()

    def get_download_history_by_title(self, title):
        """
        根据标题查找下载历史
        """
        return self._db.query(DOWNLOADHISTORY).filter(DOWNLOADHISTORY.TITLE == title).all()

    def get_download_history_by_path(self, path):
        """
        根据路径查找下载历史
        """
        return self._db.query(DOWNLOADHISTORY).filter(
            DOWNLOADHISTORY.SAVE_PATH == os.path.normpath(path)
        ).order_by(DOWNLOADHISTORY.DATE.desc()).first()

    def get_download_history_by_downloader(self, downloader, download_id):
        """
        根据下载器查找下载历史
        """
        return self._db.query(DOWNLOADHISTORY).filter(
            DOWNLOADHISTORY.DOWNLOADER == downloader,
            DOWNLOADHISTORY.DOWNLOAD_ID == download_id
        ).order_by(DOWNLOADHISTORY.DATE.desc()).first()

    @DbPersist(_db)
    def update_brushtask(self, brush_id, item):
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
                RSSURL=item.get('rssurl'),
                INTEVAL=item.get('interval'),
                DOWNLOADER=item.get('downloader'),
                LABEL=item.get('label'),
                SAVEPATH=item.get('savepath'),
                TRANSFER=item.get('transfer'),
                DOWNLOAD_COUNT=0,
                REMOVE_COUNT=0,
                DOWNLOAD_SIZE=0,
                UPLOAD_SIZE=0,
                STATE=item.get('state'),
                LST_MOD_DATE=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                SENDMESSAGE=item.get('sendmessage')
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
                    "RSSURL": item.get('rssurl'),
                    "INTEVAL": item.get('interval'),
                    "DOWNLOADER": item.get('downloader'),
                    "LABEL": item.get('label'),
                    "SAVEPATH": item.get('savepath'),
                    "TRANSFER": item.get('transfer'),
                    "STATE": item.get('state'),
                    "LST_MOD_DATE": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                    "SENDMESSAGE": item.get('sendmessage')
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
            # 根据站点优先级排序
            return self._db.query(SITEBRUSHTASK) \
                .join(CONFIGSITE, SITEBRUSHTASK.SITE == CONFIGSITE.ID) \
                .order_by(cast(CONFIGSITE.PRI, Integer).asc()).all()

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
    def update_brushtask_state(self, state, tid=None):
        """
        改变所有刷流任务的状态
        """
        if tid:
            self._db.query(SITEBRUSHTASK).filter(SITEBRUSHTASK.ID == int(tid)).update(
                {
                    "STATE": "Y" if state == "Y" else "N"
                }
            )
        else:
            self._db.query(SITEBRUSHTASK).update(
                {
                    "STATE": "Y" if state == "Y" else "N"
                }
            )

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

    def get_brushtask_torrent_by_enclosure(self, enclosure):
        """
        根据URL查询刷流任务种子
        """
        if not enclosure:
            return None
        return self._db.query(SITEBRUSHTORRENTS).filter(SITEBRUSHTORRENTS.ENCLOSURE == enclosure).first()

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

    def get_userrss_tasks(self, tid=None):
        if tid:
            return self._db.query(CONFIGUSERRSS).filter(CONFIGUSERRSS.ID == int(tid)).all()
        else:
            return self._db.query(CONFIGUSERRSS).order_by(CONFIGUSERRSS.STATE.desc()).all()

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
                    "ADDRESS": json.dumps(item.get("address")),
                    "PARSER": json.dumps(item.get("parser")),
                    "INTERVAL": item.get("interval"),
                    "USES": item.get("uses"),
                    "INCLUDE": item.get("include"),
                    "EXCLUDE": item.get("exclude"),
                    "FILTER": item.get("filter_rule"),
                    "UPDATE_TIME": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                    "STATE": item.get("state"),
                    "SAVE_PATH": item.get("save_path"),
                    "DOWNLOAD_SETTING": item.get("download_setting"),
                    "RECOGNIZATION": item.get("recognization"),
                    "OVER_EDITION": int(item.get("over_edition")) if str(item.get("over_edition")).isdigit() else 0,
                    "SITES": json.dumps(item.get("sites")),
                    "FILTER_ARGS": json.dumps(item.get("filter_args")),
                    "NOTE": json.dumps(item.get("note"))
                }
            )
        else:
            self._db.insert(CONFIGUSERRSS(
                NAME=item.get("name"),
                ADDRESS=json.dumps(item.get("address")),
                PARSER=json.dumps(item.get("parser")),
                INTERVAL=item.get("interval"),
                USES=item.get("uses"),
                INCLUDE=item.get("include"),
                EXCLUDE=item.get("exclude"),
                FILTER=item.get("filter_rule"),
                UPDATE_TIME=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                STATE=item.get("state"),
                SAVE_PATH=item.get("save_path"),
                DOWNLOAD_SETTING=item.get("download_setting"),
                RECOGNIZATION=item.get("recognization"),
                OVER_EDITION=item.get("over_edition"),
                SITES=json.dumps(item.get("sites")),
                FILTER_ARGS=json.dumps(item.get("filter_args")),
                NOTE=json.dumps(item.get("note")),
                PROCESS_COUNT='0'
            ))

    @DbPersist(_db)
    def check_userrss_task(self, tid=None, state=None):
        if state is None:
            return
        if tid:
            self._db.query(CONFIGUSERRSS).filter(CONFIGUSERRSS.ID == int(tid)).update(
                {
                    "STATE": state
                }
            )
        else:
            self._db.query(CONFIGUSERRSS).update(
                {
                    "STATE": state
                }
            )

    @DbPersist(_db)
    def insert_userrss_mediainfos(self, tid=None, mediainfo=None):
        if not tid or not mediainfo:
            return
        taskinfo = self._db.query(CONFIGUSERRSS).filter(CONFIGUSERRSS.ID == int(tid)).all()
        if not taskinfo:
            return
        mediainfos = json.loads(taskinfo[0].MEDIAINFOS) if taskinfo[0].MEDIAINFOS else []
        tmdbid = str(mediainfo.tmdb_id)
        season = int(mediainfo.get_season_seq())
        for media in mediainfos:
            if media.get("id") == tmdbid and media.get("season") == season:
                return
        mediainfos.append({
            "id": tmdbid,
            "rssid": "",
            "season": season,
            "name": mediainfo.title
        })
        self._db.query(CONFIGUSERRSS).filter(CONFIGUSERRSS.ID == int(tid)).update(
            {
                "MEDIAINFOS": json.dumps(mediainfos)
            })

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

    @DbPersist(_db)
    def excute(self, sql):
        return self._db.excute(sql)

    @DbPersist(_db)
    def drop_table(self, table_name):
        return self._db.excute(f"""DROP TABLE IF EXISTS {table_name}""")

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
        return self._db.query(USERRSSTASKHISTORY).filter(USERRSSTASKHISTORY.TASK_ID == task_id) \
            .order_by(USERRSSTASKHISTORY.DATE.desc()).all()

    def get_rss_history(self, rtype=None, rid=None):
        """
        查询RSS历史
        """
        if rid:
            return self._db.query(RSSHISTORY).filter(RSSHISTORY.ID == int(rid)).all()
        elif rtype:
            return self._db.query(RSSHISTORY).filter(RSSHISTORY.TYPE == rtype) \
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

    def check_rss_history(self, type_str, name, year, season):
        """
        检查RSS历史是否存在
        """
        count = self._db.query(RSSHISTORY).filter(
            RSSHISTORY.TYPE == type_str,
            RSSHISTORY.NAME == name,
            RSSHISTORY.YEAR == year,
            RSSHISTORY.SEASON == season
        ).count()
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
    def delete_custom_word(self, wid=None):
        """
        删除自定义识别词
        """
        if not wid:
            self._db.query(CUSTOMWORDS).delete()
        self._db.query(CUSTOMWORDS).filter(CUSTOMWORDS.ID == int(wid)).delete()

    @DbPersist(_db)
    def check_custom_word(self, wid=None, enabled=None):
        """
        设置自定义识别词状态
        """
        if enabled is None:
            return
        if wid:
            self._db.query(CUSTOMWORDS).filter(CUSTOMWORDS.ID == int(wid)).update(
                {
                    "ENABLED": int(enabled)
                }
            )
        else:
            self._db.query(CUSTOMWORDS).update(
                {
                    "ENABLED": int(enabled)
                }
            )

    def get_custom_words(self, wid=None, gid=None, enabled=None):
        """
        查询自定义识别词
        """
        if wid:
            return self._db.query(CUSTOMWORDS).filter(CUSTOMWORDS.ID == int(wid)).all()
        elif gid:
            return self._db.query(CUSTOMWORDS).filter(CUSTOMWORDS.GROUP_ID == int(gid)) \
                .order_by(CUSTOMWORDS.ENABLED.desc(), CUSTOMWORDS.TYPE, CUSTOMWORDS.REGEX, CUSTOMWORDS.ID).all()
        elif enabled is not None:
            return self._db.query(CUSTOMWORDS).filter(CUSTOMWORDS.ENABLED == int(enabled)) \
                .order_by(CUSTOMWORDS.GROUP_ID, CUSTOMWORDS.TYPE, CUSTOMWORDS.REGEX, CUSTOMWORDS.ID).all()
        return self._db.query(CUSTOMWORDS) \
            .order_by(CUSTOMWORDS.GROUP_ID,
                      CUSTOMWORDS.ENABLED.desc(),
                      CUSTOMWORDS.TYPE,
                      CUSTOMWORDS.REGEX,
                      CUSTOMWORDS.ID) \
            .all()

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
    def insert_config_sync_path(self, source, dest, unknown, mode, compatibility, rename, enabled, note=None):
        """
        增加目录同步
        """
        return self._db.insert(CONFIGSYNCPATHS(
            SOURCE=source,
            DEST=dest,
            UNKNOWN=unknown,
            MODE=mode,
            COMPATIBILITY=int(compatibility),
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
        return self._db.query(CONFIGSYNCPATHS).order_by(CONFIGSYNCPATHS.SOURCE).all()

    @DbPersist(_db)
    def check_config_sync_paths(self, sid=None, compatibility=None, rename=None, enabled=None):
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
        elif sid and compatibility is not None:
            self._db.query(CONFIGSYNCPATHS).filter(CONFIGSYNCPATHS.ID == int(sid)).update(
                {
                    "COMPATIBILITY": int(compatibility)
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
        return self._db.query(MESSAGECLIENT).all()

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
    def update_downloader(self,
                          did,
                          name,
                          enabled,
                          dtype,
                          transfer,
                          only_nastool,
                          match_path,
                          rmt_mode,
                          config,
                          download_dir):
        """
        更新下载器
        """
        if did:
            self._db.query(DOWNLOADER).filter(DOWNLOADER.ID == int(did)).update(
                {
                    "NAME": name,
                    "ENABLED": int(enabled),
                    "TYPE": dtype,
                    "TRANSFER": int(transfer),
                    "ONLY_NASTOOL": int(only_nastool),
                    "MATCH_PATH": int(match_path),
                    "RMT_MODE": rmt_mode,
                    "CONFIG": config,
                    "DOWNLOAD_DIR": download_dir
                }
            )
        else:
            self._db.insert(DOWNLOADER(
                NAME=name,
                ENABLED=int(enabled),
                TYPE=dtype,
                TRANSFER=int(transfer),
                ONLY_NASTOOL=int(only_nastool),
                MATCH_PATH=int(match_path),
                RMT_MODE=rmt_mode,
                CONFIG=config,
                DOWNLOAD_DIR=download_dir
            ))

    @DbPersist(_db)
    def delete_downloader(self, did):
        """
        删除下载器
        """
        if not did:
            return
        self._db.query(DOWNLOADER).filter(DOWNLOADER.ID == int(did)).delete()

    @DbPersist(_db)
    def check_downloader(self, did=None, transfer=None, only_nastool=None, enabled=None, match_path=None):
        """
        设置下载器状态
        """
        if not did:
            return
        if transfer is not None:
            self._db.query(DOWNLOADER).filter(DOWNLOADER.ID == int(did)).update(
                {
                    "TRANSFER": int(transfer)
                }
            )
        elif only_nastool is not None:
            self._db.query(DOWNLOADER).filter(DOWNLOADER.ID == int(did)).update(
                {
                    "ONLY_NASTOOL": int(only_nastool)
                }
            )
        elif match_path is not None:
            self._db.query(DOWNLOADER).filter(DOWNLOADER.ID == int(did)).update(
                {
                    "MATCH_PATH": int(match_path)
                }
            )
        elif enabled is not None:
            self._db.query(DOWNLOADER).filter(DOWNLOADER.ID == int(did)).update(
                {
                    "ENABLED": int(enabled)
                }
            )

    def get_downloaders(self):
        """
        查询下载器
        """
        return self._db.query(DOWNLOADER).all()

    @DbPersist(_db)
    def insert_indexer_statistics(self,
                                  indexer,
                                  itype,
                                  seconds,
                                  result):
        """
        插入索引器统计
        """
        self._db.insert(INDEXERSTATISTICS(
            INDEXER=indexer,
            TYPE=itype,
            SECONDS=seconds,
            RESULT=result,
            DATE=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        ))

    def get_indexer_statistics(self):
        """
        查询索引器统计
        """
        return self._db.query(
            INDEXERSTATISTICS.INDEXER,
            func.count(INDEXERSTATISTICS.ID).label("TOTAL"),
            func.sum(case((INDEXERSTATISTICS.RESULT == 'N', 1),
                          else_=0)).label("FAIL"),
            func.sum(case((INDEXERSTATISTICS.RESULT == 'Y', 1),
                          else_=0)).label("SUCCESS"),
            func.avg(INDEXERSTATISTICS.SECONDS).label("AVG"),
        ).group_by(INDEXERSTATISTICS.INDEXER).all()

    @DbPersist(_db)
    def insert_plugin_history(self, plugin_id, key, value):
        """
        新增插件运行记录
        """
        self._db.insert(PLUGINHISTORY(
            PLUGIN_ID=plugin_id,
            KEY=key,
            VALUE=value,
            DATE=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        ))

    def get_plugin_history(self, plugin_id, key):
        """
        查询插件运行记录
        """
        if not plugin_id:
            return None
        if key:
            return self._db.query(PLUGINHISTORY).filter(PLUGINHISTORY.PLUGIN_ID == plugin_id,
                                                        PLUGINHISTORY.KEY == key).first()
        else:
            return self._db.query(PLUGINHISTORY).filter(PLUGINHISTORY.PLUGIN_ID == plugin_id).all()

    @DbPersist(_db)
    def update_plugin_history(self, plugin_id, key, value):
        """
        更新插件运行记录
        """
        self._db.query(PLUGINHISTORY).filter(PLUGINHISTORY.PLUGIN_ID == plugin_id,
                                             PLUGINHISTORY.KEY == key).update(
            {
                "VALUE": value
            }
        )

    @DbPersist(_db)
    def delete_plugin_history(self, plugin_id, key):
        """
        删除插件运行记录
        """
        self._db.query(PLUGINHISTORY).filter(PLUGINHISTORY.PLUGIN_ID == plugin_id,
                                             PLUGINHISTORY.KEY == key).delete()
