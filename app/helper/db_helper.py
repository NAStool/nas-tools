import datetime
import os.path
import time
from enum import Enum

from sqlalchemy import cast, func

from app.db.main_db import MainDb
from app.db.models import *
from app.utils import StringUtils
from app.utils.types import MediaType, RmtMode


class DbHelper:

    @staticmethod
    def insert_search_results(media_items: list):
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
                RES_TYPE=media_item.get_resource_type_string(),
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
        return MainDb().insert(data_list)

    @staticmethod
    def get_search_result_by_id(dl_id):
        """
        根据ID从数据库中查询检索结果的一条记录
        """
        return MainDb().query(SEARCHRESULTINFO).filter(SEARCHRESULTINFO.ID == dl_id).all()

    @staticmethod
    def get_search_results():
        """
        查询检索结果的所有记录
        """
        return MainDb().query(SEARCHRESULTINFO).all()

    @staticmethod
    def is_torrent_rssd(enclosure):
        """
        查询RSS是否处理过，根据下载链接
        """
        if not enclosure:
            return True
        if MainDb().query(RSSTORRENTS).filter(RSSTORRENTS.ENCLOSURE == enclosure).count() > 0:
            return True
        else:
            return False

    @staticmethod
    def is_userrss_finished(torrent_name, enclosure):
        """
        查询RSS是否处理过，根据名称
        """
        if not torrent_name and not enclosure:
            return True
        if enclosure:
            ret = MainDb().query(RSSTORRENTS).filter(RSSTORRENTS.ENCLOSURE == enclosure).count()
        else:
            ret = MainDb().query(RSSTORRENTS).filter(RSSTORRENTS.TORRENT_NAME == torrent_name).count()
        return True if ret > 0 else False

    @staticmethod
    def delete_all_search_torrents():
        """
        删除所有搜索的记录
        """
        return MainDb().query(SEARCHRESULTINFO).delete()

    @staticmethod
    def insert_rss_torrents(media_info):
        """
        将RSS的记录插入数据库
        """
        return MainDb().insert(
            RSSTORRENTS(
                TORRENT_NAME=media_info.org_string,
                ENCLOSURE=media_info.enclosure,
                TYPE=media_info.type.value,
                TITLE=media_info.title,
                YEAR=media_info.year,
                SEASON=media_info.get_season_string(),
                EPISODE=media_info.get_episode_string()
            ))

    @staticmethod
    def simple_insert_rss_torrents(title, enclosure):
        """
        将RSS的记录插入数据库
        """
        return MainDb().insert(
            RSSTORRENTS(
                TORRENT_NAME=title,
                ENCLOSURE=enclosure
            ))

    @staticmethod
    def simple_delete_rss_torrents(title, enclosure):
        """
        删除RSS的记录
        """
        return MainDb().query(RSSTORRENTS).filter(RSSTORRENTS.TORRENT_NAME == title,
                                                  RSSTORRENTS.ENCLOSURE == enclosure).delete()

    @staticmethod
    def insert_douban_media_state(media, state):
        """
        将豆瓣的数据插入数据库
        """
        if not media.year:
            MainDb().query(DOUBANMEDIAS).filter(DOUBANMEDIAS.NAME == media.get_name()).delete()
        else:
            MainDb().query(DOUBANMEDIAS).filter(DOUBANMEDIAS.NAME == media.get_name(),
                                                DOUBANMEDIAS.YEAR == media.year).delete()

        # 再插入
        return MainDb().insert(
            DOUBANMEDIAS(
                NAME=media.get_name(),
                YEAR=media.year,
                TYPE=media.type.value,
                RATING=media.vote_average,
                IMAGE=media.get_poster_image(),
                STATE=state
            )
        )

    @staticmethod
    def update_douban_media_state(media, state):
        """
        标记豆瓣数据的状态
        """
        return MainDb().query(DOUBANMEDIAS).filter(DOUBANMEDIAS.NAME == media.title,
                                                   DOUBANMEDIAS.YEAR == media.year).update(
            {
                "STATE": state
            }
        )

    @staticmethod
    def get_douban_search_state(title, year):
        """
        查询未检索的豆瓣数据
        """
        return MainDb().query(DOUBANMEDIAS.STATE).filter(DOUBANMEDIAS.NAME == title,
                                                         DOUBANMEDIAS.YEAR == str(year)).all()

    @staticmethod
    def is_transfer_history_exists(file_path, file_name, title, se):
        """
        查询识别转移记录
        """
        if not file_path:
            return False
        ret = MainDb().query(TRANSFERHISTORY).filter(TRANSFERHISTORY.FILE_PATH == file_path,
                                                     TRANSFERHISTORY.FILE_NAME == file_name,
                                                     TRANSFERHISTORY.TITLE == title,
                                                     TRANSFERHISTORY.SE == se).count()
        return True if ret > 0 else False

    @staticmethod
    def insert_transfer_history(in_from: Enum, rmt_mode: RmtMode, in_path, dest, media_info):
        """
        插入识别转移记录
        """
        if not media_info or not media_info.tmdb_info:
            return
        if in_path:
            in_path = os.path.normpath(in_path)
        else:
            return False
        if not dest:
            dest = ""
        file_path = os.path.dirname(in_path)
        file_name = os.path.basename(in_path)
        if DbHelper.is_transfer_history_exists(file_path, file_name, media_info.title, media_info.get_season_string()):
            return True
        timestr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        return MainDb().insert(
            TRANSFERHISTORY(
                SOURCE=in_from.value,
                MODE=rmt_mode.value,
                TYPE=media_info.type.value,
                FILE_PATH=file_path,
                FILE_NAME=file_name,
                TITLE=media_info.title,
                CATEGORY=media_info.category,
                YEAR=media_info.year,
                SE=media_info.get_season_string(),
                DEST=dest,
                DATE=timestr
            )
        )

    @staticmethod
    def get_transfer_history(search, page, rownum):
        """
        查询识别转移记录
        """
        if page == 1:
            begin_pos = 0
        else:
            begin_pos = (page - 1) * rownum

        if search:
            search = f"%{search}%"
            count = MainDb().query(TRANSFERHISTORY).filter((TRANSFERHISTORY.FILE_NAME.like(search))
                                                           | (TRANSFERHISTORY.TITLE.like(search))).count()
            data = MainDb().query(TRANSFERHISTORY).filter((TRANSFERHISTORY.FILE_NAME.like(search))
                                                          | (TRANSFERHISTORY.TITLE.like(search))).order_by(
                TRANSFERHISTORY.DATE.desc()).limit(rownum).offset(begin_pos).all()
            return count, data
        else:
            return MainDb().query(TRANSFERHISTORY).count(), MainDb().query(TRANSFERHISTORY).order_by(
                TRANSFERHISTORY.DATE.desc()).limit(rownum).offset(begin_pos).all()

    @staticmethod
    def get_transfer_path_by_id(logid):
        """
        据logid查询PATH
        """
        return MainDb().query(TRANSFERHISTORY).filter(TRANSFERHISTORY.ID == int(logid)).all()

    @staticmethod
    def delete_transfer_log_by_id(logid):
        """
        根据logid删除记录
        """
        return MainDb().query(TRANSFERHISTORY).filter(TRANSFERHISTORY.ID == int(logid)).delete()

    @staticmethod
    def get_transfer_unknown_paths():
        """
        查询未识别的记录列表
        """
        return MainDb().query(TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.STATE == 'N').all()

    @staticmethod
    def update_transfer_unknown_state(path):
        """
        更新未识别记录为识别
        """
        if not path:
            return False
        return MainDb().query(TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.PATH == os.path.normpath(path)).update(
            {
                "STATE": "Y"
            }
        )

    @staticmethod
    def delete_transfer_unknown(tid):
        """
        删除未识别记录
        """
        if not tid:
            return False
        return MainDb().query(TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.ID == int(tid)).delete()

    @staticmethod
    def get_unknown_path_by_id(tid):
        """
        查询未识别记录
        """
        if not tid:
            return False
        return MainDb().query(TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.ID == int(tid)).all()

    @staticmethod
    def is_transfer_unknown_exists(path):
        """
        查询未识别记录是否存在
        """
        if not path:
            return False
        ret = MainDb().query(TRANSFERUNKNOWN).filter(TRANSFERUNKNOWN.PATH == os.path.normpath(path)).count()
        if ret > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_transfer_unknown(path, dest):
        """
        插入未识别记录
        """
        if not path:
            return False
        if DbHelper.is_transfer_unknown_exists(path):
            return False
        else:
            path = os.path.normpath(path)
            if dest:
                dest = os.path.normpath(dest)
            else:
                dest = ""
            return MainDb().insert(TRANSFERUNKNOWN(
                PATH=path,
                DEST=dest,
                STATE='N'
            ))

    @staticmethod
    def is_transfer_in_blacklist(path):
        """
        查询是否为黑名单
        """
        if not path:
            return False
        ret = MainDb().query(TRANSFERBLACKLIST).filter(TRANSFERBLACKLIST.PATH == os.path.normpath(path)).count()
        if ret > 0:
            return True
        else:
            return False

    @staticmethod
    def is_transfer_notin_blacklist(path):
        """
        查询是否为黑名单
        """
        return not DbHelper.is_transfer_in_blacklist(path)

    @staticmethod
    def insert_transfer_blacklist(path):
        """
        插入黑名单记录
        """
        if not path:
            return False
        if DbHelper.is_transfer_in_blacklist(path):
            return False
        else:
            return MainDb().insert(TRANSFERBLACKLIST(
                PATH=os.path.normpath(path)
            ))

    @staticmethod
    def truncate_transfer_blacklist():
        """
        清空黑名单记录
        """
        MainDb().query(TRANSFERBLACKLIST).delete()
        MainDb().query(SYNCHISTORY).delete()

    @staticmethod
    def truncate_rss_history():
        """
        清空RSS历史记录
        """
        MainDb().query(RSSTORRENTS).delete()

    @staticmethod
    def truncate_rss_episodes():
        """
        清空RSS历史记录
        """
        MainDb().query(RSSTVEPISODES).delete()

    @staticmethod
    def get_config_site():
        """
        查询所有站点信息
        """
        return MainDb().query(CONFIGSITE).order_by(cast(CONFIGSITE.PRI, Integer).asc())

    @staticmethod
    def get_site_by_id(tid):
        """
        查询1个站点信息
        """
        return MainDb().query(CONFIGSITE).filter(CONFIGSITE.ID == int(tid)).all()

    @staticmethod
    def get_site_by_name(name):
        """
        基于站点名称查询站点信息
        :return:
        """
        return MainDb().query(CONFIGSITE).filter(CONFIGSITE.NAME == name).all()

    @staticmethod
    def insert_config_site(name, site_pri, rssurl, signurl, cookie, note, rss_uses):
        """
        插入站点信息
        """
        if not name:
            return
        return MainDb().insert(CONFIGSITE(
            NAME=name,
            PRI=site_pri,
            RSSURL=rssurl,
            SIGNURL=signurl,
            COOKIE=cookie,
            NOTE=note,
            INCLUDE=rss_uses
        ))

    @staticmethod
    def delete_config_site(tid):
        """
        删除站点信息
        """
        if not tid:
            return False
        return MainDb().query(CONFIGSITE).filter(CONFIGSITE.ID == int(tid)).delete()

    @staticmethod
    def update_config_site(tid, name, site_pri, rssurl, signurl, cookie, note, rss_uses):
        """
        更新站点信息
        """
        if not tid:
            return
        return MainDb().query(CONFIGSITE).filter(CONFIGSITE.ID == int(tid)).update(
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

    @staticmethod
    def get_config_filter_group(gid=None):
        """
        查询过滤规则组
        """
        if gid:
            return MainDb().query(CONFIGFILTERGROUP).filter(CONFIGFILTERGROUP.ID == int(gid)).all()
        return MainDb().query(CONFIGFILTERGROUP).all()

    @staticmethod
    def get_config_filter_rule(groupid=None):
        """
        查询过滤规则
        """
        if not groupid:
            return MainDb().query(CONFIGFILTERRULES).group_by(CONFIGFILTERRULES.GROUP_ID,
                                                              cast(CONFIGFILTERRULES.PRIORITY,
                                                                   Integer)).all()
        else:
            return MainDb().query(CONFIGFILTERRULES).filter(
                CONFIGFILTERRULES.GROUP_ID == int(groupid)).group_by(CONFIGFILTERRULES.GROUP_ID,
                                                                     cast(CONFIGFILTERRULES.PRIORITY,
                                                                          Integer)).all()

    @staticmethod
    def get_rss_movies(state=None, rssid=None):
        """
        查询订阅电影信息
        """
        if rssid:
            return MainDb().query(RSSMOVIES).filter(RSSMOVIES.ID == int(rssid)).all()
        else:
            if not state:
                return MainDb().query(RSSMOVIES).all()
            else:
                return MainDb().query(RSSMOVIES).filter(RSSMOVIES.STATE == state).all()

    @staticmethod
    def get_rss_movie_id(title, tmdbid=None):
        """
        获取订阅电影ID
        """
        if not title:
            return ""
        ret = MainDb().query(RSSMOVIES.ID).filter(RSSMOVIES.NAME == title).first()
        if ret:
            return ret[0]
        else:
            if tmdbid:
                ret = MainDb().query(RSSMOVIES.ID).filter(RSSMOVIES.TMDBID == tmdbid).first()
                if ret:
                    return ret[0]
        return ""

    @staticmethod
    def get_rss_movie_sites(rssid):
        """
        获取订阅电影站点
        """
        if not rssid:
            return ""
        ret = MainDb().query(RSSMOVIES.DESC).filter(RSSMOVIES.ID == int(rssid)).first()
        if ret:
            return ret[0]
        return ""

    @staticmethod
    def update_rss_movie_tmdb(rid, tmdbid, title, year, image):
        """
        更新订阅电影的TMDBID
        """
        if not tmdbid:
            return False
        return MainDb().query(RSSMOVIES).filter(RSSMOVIES.ID == int(rid)).update({
            "TMDBID": tmdbid,
            "NAME": title,
            "YEAR": year,
            "IMAGE": image
        })

    @staticmethod
    def is_exists_rss_movie(title, year):
        """
        判断RSS电影是否存在
        """
        if not title:
            return False
        count = MainDb().query(RSSMOVIES).filter(RSSMOVIES.NAME == title,
                                                 RSSMOVIES.YEAR == str(year)).count()
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_rss_movie(media_info,
                         state='D',
                         sites: list = None,
                         search_sites: list = None,
                         over_edition=False,
                         rss_restype=None,
                         rss_pix=None,
                         rss_team=None,
                         rss_rule=None):
        """
        新增RSS电影
        """
        if not media_info:
            return False
        if not media_info.title:
            return False
        if DbHelper.is_exists_rss_movie(media_info.title, media_info.year):
            return True
        desc = "#".join(["|".join(sites or []),
                         "|".join(search_sites or []),
                         "Y" if over_edition else "N",
                         "@".join([StringUtils.str_sql(rss_restype),
                                   StringUtils.str_sql(rss_pix),
                                   StringUtils.str_sql(rss_rule),
                                   StringUtils.str_sql(rss_team)])])
        return MainDb().insert(RSSMOVIES(
            NAME=media_info.title,
            YEAR=media_info.year,
            TMDBID=media_info.tmdb_id,
            IMAGE=media_info.get_message_image(),
            DESC=desc,
            STATE=state
        ))

    @staticmethod
    def delete_rss_movie(title=None, year=None, rssid=None, tmdbid=None):
        """
        删除RSS电影
        """
        if not title and not rssid:
            return False
        if rssid:
            return MainDb().query(RSSMOVIES).filter(RSSMOVIES.ID == int(rssid)).delete()
        else:
            if tmdbid:
                return MainDb().query(RSSMOVIES).filter(RSSMOVIES.TMDBID == tmdbid).delete()
            return MainDb().query(RSSMOVIES).filter(RSSMOVIES.NAME == title,
                                                    RSSMOVIES.YEAR == str(year)).delete()

    @staticmethod
    def update_rss_movie_state(title=None, year=None, rssid=None, state='R'):
        """
        更新电影订阅状态
        """
        if not title and not rssid:
            return False
        if rssid:
            return MainDb().query(RSSMOVIES).filter(RSSMOVIES.ID == int(rssid)).update(
                {
                    "STATE": state
                })
        else:
            return MainDb().query(RSSMOVIES).filter(
                RSSMOVIES.NAME == title,
                RSSMOVIES.YEAR == str(year)).update(
                {
                    "STATE": state
                })

    @staticmethod
    def get_rss_tvs(state=None, rssid=None):
        """
        查询订阅电视剧信息
        """
        if rssid:
            return MainDb().query(RSSTVS).filter(RSSTVS.ID == int(rssid)).all()
        else:
            if not state:
                return MainDb().query(RSSTVS).all()
            else:
                return MainDb().query(RSSTVS).filter(RSSTVS.STATE == state).all()

    @staticmethod
    def get_rss_tv_id(title, season=None, tmdbid=None):
        """
        获取订阅电影ID
        """
        if not title:
            return ""
        if season:
            ret = MainDb().query(RSSTVS.ID).filter(RSSTVS.NAME == title,
                                                   RSSTVS.SEASON == season).first()
            if ret:
                return ret[0]
            else:
                if tmdbid:
                    ret = MainDb().query(RSSTVS.ID).filter(RSSTVS.TMDBID == tmdbid,
                                                           RSSTVS.SEASON == season).first()
                    if ret:
                        return ret[0]
        else:
            ret = MainDb().query(RSSTVS.ID).filter(RSSTVS.NAME == title).first()
            if ret:
                return ret[0]
            else:
                if tmdbid:
                    ret = MainDb().query(RSSTVS.ID).filter(RSSTVS.TMDBID == tmdbid).first()
                    if ret:
                        return ret[0]
        return ""

    @staticmethod
    def get_rss_tv_sites(rssid):
        """
        获取订阅电视剧站点
        """
        if not rssid:
            return ""
        ret = MainDb().query(RSSTVS).filter(RSSTVS.ID == int(rssid)).first()
        if ret:
            return ret[0]
        return ""

    @staticmethod
    def update_rss_tv_tmdb(rid, tmdbid, title, year, total, lack, image):
        """
        更新订阅电影的TMDBID
        """
        if not tmdbid:
            return False
        return MainDb().query(RSSTVS).filter(RSSTVS.ID == int(rid)).update(
            {
                "TMDBID": tmdbid,
                "NAME": title,
                "YEAR": year,
                "TOTAL": total,
                "LACK": lack,
                "IMAGE": image
            }
        )

    @staticmethod
    def is_exists_rss_tv(title, year, season=None):
        """
        判断RSS电视剧是否存在
        """
        if not title:
            return False
        if season:
            count = MainDb().query(RSSTVS).filter(RSSTVS.NAME == title,
                                                  RSSTVS.YEAR == str(year),
                                                  RSSTVS.SEASON == season).count()
        else:
            count = MainDb().query(RSSTVS).filter(RSSTVS.NAME == title,
                                                  RSSTVS.YEAR == str(year)).count()
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_rss_tv(media_info, total, lack=0, state="D",
                      sites: list = None,
                      search_sites: list = None,
                      over_edition=False,
                      rss_restype=None,
                      rss_pix=None,
                      rss_team=None,
                      rss_rule=None,
                      match=False,
                      total_ep=None,
                      current_ep=None
                      ):
        """
        新增RSS电视剧
        """
        if not media_info:
            return False
        if not media_info.title:
            return False
        if match and media_info.begin_season is None:
            season_str = ""
        else:
            season_str = media_info.get_season_string()
        if DbHelper.is_exists_rss_tv(media_info.title, media_info.year, season_str):
            return True
        # 插入订阅数据
        desc = "#".join(["|".join(sites or []),
                         "|".join(search_sites or []),
                         "Y" if over_edition else "N",
                         "@".join([StringUtils.str_sql(rss_restype),
                                   StringUtils.str_sql(rss_pix),
                                   StringUtils.str_sql(rss_rule),
                                   StringUtils.str_sql(rss_team)]),
                         "@".join([StringUtils.str_sql(total_ep),
                                   StringUtils.str_sql(current_ep)])])
        return MainDb().insert(RSSTVS(
            NAME=media_info.title,
            YEAR=media_info.year,
            SEASON=season_str,
            TMDBID=media_info.tmdb_id,
            IMAGE=media_info.get_message_image(),
            DESC=desc,
            TOTAL=total,
            LACK=lack,
            STATE=state
        ))

    @staticmethod
    def update_rss_tv_lack(title=None, year=None, season=None, rssid=None, lack_episodes: list = None):
        """
        更新电视剧缺失的集数
        """
        if not title and not rssid:
            return False
        if not lack_episodes:
            lack = 0
        else:
            lack = len(lack_episodes)
        if rssid:
            DbHelper.update_rss_tv_episodes(rssid, lack_episodes)
            return MainDb().query(RSSTVS).filter(RSSTVS.ID == int(rssid)).update(
                {
                    "LACK": lack
                }
            )
        else:
            return MainDb().query(RSSTVS).filter(RSSTVS.NAME == title,
                                                 RSSTVS.YEAR == str(year),
                                                 RSSTVS.SEASON == season).update(
                {
                    "LACK": lack
                }
            )

    @staticmethod
    def delete_rss_tv(title=None, season=None, rssid=None, tmdbid=None):
        """
        删除RSS电视剧
        """
        if not title and not rssid:
            return False
        if not rssid:
            rssid = DbHelper.get_rss_tv_id(title=title, tmdbid=tmdbid, season=season)
        if rssid:
            DbHelper.delete_rss_tv_episodes(rssid)
            return MainDb().query(RSSTVS).filter(RSSTVS.ID == int(rssid)).delete()
        return False

    @staticmethod
    def is_exists_rss_tv_episodes(rid):
        """
        判断RSS电视剧是否存在
        """
        if not rid:
            return False
        count = MainDb().query(RSSTVEPISODES).filter(RSSTVEPISODES.RSSID == int(rid)).count()
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def update_rss_tv_episodes(rid, episodes):
        """
        插入或更新电视剧订阅缺失剧集
        """
        if not rid:
            return
        if not episodes:
            episodes = []
        else:
            episodes = [str(epi) for epi in episodes]
        if DbHelper.is_exists_rss_tv_episodes(rid):
            return MainDb().query(RSSTVEPISODES).filter(RSSTVEPISODES.RSSID == int(rid)).update(
                {
                    "EPISODES": ",".join(episodes)
                }
            )
        else:
            return MainDb().insert(RSSTVEPISODES(
                RSSID=rid,
                EPISODES=",".join(episodes)
            ))

    @staticmethod
    def get_rss_tv_episodes(rid):
        """
        查询电视剧订阅缺失剧集
        """
        if not rid:
            return []
        ret = MainDb(RSSTVEPISODES.EPISODES).filter(RSSTVEPISODES.RSSID == int(rid)).first()
        if ret:
            return [int(epi) for epi in str(ret[0]).split(',')]
        else:
            return None

    @staticmethod
    def delete_rss_tv_episodes(rid):
        """
        删除电视剧订阅缺失剧集
        """
        if not rid:
            return []
        return MainDb().query(RSSTVEPISODES).filter(RSSTVEPISODES.RSSID == int(rid)).delete()

    @staticmethod
    def update_rss_tv_state(title=None, year=None, season=None, rssid=None, state='R'):
        """
        更新电视剧订阅状态
        """
        if not title and not rssid:
            return False
        if rssid:
            return MainDb().query(RSSTVS).filter(RSSTVS.ID == int(rssid)).update(
                {
                    "STATE": state
                })
        else:
            return MainDb().query(RSSTVS).filter(RSSTVS.NAME == title,
                                                 RSSTVS.YEAR == str(year),
                                                 RSSTVS.SEASON == season).update(
                {
                    "STATE": state
                })

    @staticmethod
    def is_sync_in_history(path, dest):
        """
        查询是否存在同步历史记录
        """
        if not path:
            return False
        count = MainDb().query(SYNCHISTORY).filter(SYNCHISTORY.PATH == os.path.normpath(path),
                                                   SYNCHISTORY.DEST == os.path.normpath(dest)).count()
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_sync_history(path, src, dest):
        """
        插入黑名单记录
        """
        if not path or not dest:
            return False
        if DbHelper.is_sync_in_history(path, dest):
            return False
        else:
            return MainDb().insert(SYNCHISTORY(
                PATH=os.path.normpath(path),
                SRC=os.path.normpath(src),
                dest=os.path.normpath(dest)
            ))

    @staticmethod
    def get_users():
        """
        查询用户列表
        """
        return MainDb().query(CONFIGUSERS).all()

    @staticmethod
    def is_user_exists(name):
        """
        判断用户是否存在
        """
        if not name:
            return False
        count = MainDb().query(CONFIGUSERS).filter(CONFIGUSERS.NAME == name).count()
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_user(name, password, pris):
        """
        新增用户
        """
        if not name or not password:
            return False
        if DbHelper.is_user_exists(name):
            return False
        else:
            return MainDb().insert(CONFIGUSERS(
                NAME=name,
                PASSWORD=password,
                PRIS=pris
            ))

    @staticmethod
    def delete_user(name):
        """
        删除用户
        """
        return MainDb().query(CONFIGUSERS).filter(CONFIGUSERS.NAME == name).delete()

    @staticmethod
    def get_transfer_statistics(days=30):
        """
        查询历史记录统计
        """
        begin_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        return MainDb().query(TRANSFERHISTORY.TYPE,
                              func.substr(TRANSFERHISTORY.DATE, 1, 10),
                              func.count('*')
                              ).filter(TRANSFERHISTORY.DATE > begin_date).group_by(
            func.substr(TRANSFERHISTORY.DATE, 1, 10)
        ).order_by(TRANSFERHISTORY.DATE).all()

    @staticmethod
    def update_site_user_statistics_site_name(new_name, old_name):
        """
        更新站点用户数据中站点名称
        """
        return MainDb().query(SITEUSERINFOSTATS).filter(SITEUSERINFOSTATS.SITE == old_name).update(
            {
                "SITE": new_name
            }
        )

    @staticmethod
    def update_site_user_statistics(site_user_infos: list):
        """
        更新站点用户粒度数据
        """
        if not site_user_infos:
            return
        update_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        data_list = []
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
            favicon = site_user_info.site_favicon
            msg_unread = site_user_info.message_unread
            data_list.append(SITEUSERINFOSTATS(
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
                FAVICON=favicon,
                MSG_UNREAD=msg_unread
            ))
        return MainDb().insert(data_list)

    @staticmethod
    def update_site_seed_info_site_name(new_name, old_name):
        """
        更新站点做种数据中站点名称
        :param new_name: 新的站点名称
        :param old_name: 原始站点名称
        :return:
        """
        return MainDb().query(SITEUSERSEEDINGINFO).filter(SITEUSERSEEDINGINFO.SITE == old_name).update(
            {
                "SITE": new_name
            }
        )

    @staticmethod
    def update_site_seed_info(site_user_infos: list):
        """
        更新站点做种数据
        """
        if not site_user_infos:
            return
        update_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        data_list = []
        for site_user_info in site_user_infos:
            data_list.append(SITEUSERSEEDINGINFO(
                SITE=site_user_info.site_name,
                UPDATE_AT=update_at,
                SEEDING_INFO=site_user_info.seeding_info,
                URL=site_user_info.site_url
            ))
        return MainDb().insert(data_list)

    @staticmethod
    def is_site_user_statistics_exists(url):
        """
        判断站点用户数据是否存在
        """
        if not url:
            return False
        count = MainDb().query(SITEUSERINFOSTATS).filter(SITEUSERINFOSTATS.URL == url).count()
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def get_site_user_statistics(num=100, strict_urls=None):
        """
        查询站点数据历史
        """
        if strict_urls:
            return MainDb().query(SITEUSERINFOSTATS).filter(
                SITEUSERINFOSTATS.URL.in_(tuple(strict_urls + ["__DUMMY__"]))).limit(num).all()
        else:
            return MainDb().query(SITEUSERINFOSTATS).limit(num).all()

    @staticmethod
    def is_site_statistics_history_exists(url, date):
        """
        判断站点历史数据是否存在
        """
        if not url or not date:
            return False
        count = MainDb().query(SITESTATISTICSHISTORY).filter(SITESTATISTICSHISTORY.URL == url,
                                                             SITESTATISTICSHISTORY.DATE == date).count()
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def update_site_statistics_site_name(new_name, old_name):
        """
        更新站点做种数据中站点名称
        :param new_name: 新站点名称
        :param old_name: 原始站点名称
        :return:
        """
        return MainDb().query(SITESTATISTICSHISTORY).filter(SITESTATISTICSHISTORY.SITE == old_name).update(
            {
                "SITE": new_name
            }
        )

    @staticmethod
    def insert_site_statistics_history(site_user_infos: list):
        """
        插入站点数据
        """
        if not site_user_infos:
            return
        date_now = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        data_list = []
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
            data_list.append(SITESTATISTICSHISTORY(
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
        return MainDb().insert(data_list)

    @staticmethod
    def get_site_statistics_history(site, days=30):
        """
        查询站点数据历史
        """
        return MainDb().query(SITESTATISTICSHISTORY).filter(
            SITESTATISTICSHISTORY.SITE == site).order_by(
            SITESTATISTICSHISTORY.DATE.asc()
        ).limit(days)

    @staticmethod
    def get_site_seeding_info(site):
        """
        查询站点做种信息
        """
        return MainDb().query(SITEUSERSEEDINGINFO.SEEDING_INFO).filter(
            SITEUSERSEEDINGINFO.SITE == site).first()

    @staticmethod
    def get_site_statistics_recent_sites(days=7, strict_urls=None):
        """
        查询近期上传下载量
        """
        # 查询最大最小日期
        if strict_urls is None:
            strict_urls = []

        b_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        date_ret = MainDb().query(func.max(SITESTATISTICSHISTORY.DATE),
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
                sql = """
                     SELECT SITE, MIN(UPLOAD), MIN(DOWNLOAD), MAX(UPLOAD), MAX(DOWNLOAD)
                     FROM (SELECT SITE, DATE, SUM(UPLOAD) as UPLOAD, SUM(DOWNLOAD) as DOWNLOAD FROM SITE_STATISTICS_HISTORY WHERE DATE >= ? AND URL in {} GROUP BY SITE, DATE) X 
                     GROUP BY SITE""".format(tuple(strict_urls + ["__DUMMY__"]))
            else:
                sql = """SELECT SITE, MIN(UPLOAD), MIN(DOWNLOAD), MAX(UPLOAD), MAX(DOWNLOAD)
                     FROM (SELECT SITE, DATE, SUM(UPLOAD) as UPLOAD, SUM(DOWNLOAD) as DOWNLOAD FROM SITE_STATISTICS_HISTORY WHERE DATE >= ? GROUP BY SITE, DATE) X 
                     GROUP BY SITE"""
            for ret_b in MainDb().select_by_sql(sql, (min_date,)):
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

    @staticmethod
    def is_exists_download_history(title, tmdbid, mtype=None):
        """
        查询下载历史是否存在
        """
        if not title or not tmdbid:
            return False
        if mtype:
            count = MainDb().query(DOWNLOADHISTORY).filter(
                (DOWNLOADHISTORY.TITLE == title) | (DOWNLOADHISTORY.TMDBID == tmdbid),
                DOWNLOADHISTORY.TYPE == mtype).count()
        else:
            count = MainDb().query(DOWNLOADHISTORY).filter(
                (DOWNLOADHISTORY.TITLE == title) | (DOWNLOADHISTORY.TMDBID == tmdbid)).count()
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_download_history(media_info):
        """
        新增下载历史
        """
        if not media_info:
            return False
        if not media_info.title or not media_info.tmdb_id:
            return False
        if DbHelper.is_exists_download_history(media_info.title, media_info.tmdb_id, media_info.type.value):
            return MainDb().query(DOWNLOADHISTORY).filter(DOWNLOADHISTORY.TITLE == media_info.title,
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
            return MainDb().insert(DOWNLOADHISTORY(
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

    @staticmethod
    def get_download_history(date=None, hid=None, num=30, page=1):
        """
        查询下载历史
        """
        if hid:
            return MainDb().query(DOWNLOADHISTORY).filter(DOWNLOADHISTORY.ID == int(hid)).all()
        elif date:
            return MainDb().query(DOWNLOADHISTORY).filter(
                DOWNLOADHISTORY.DATE > date).order_by(DOWNLOADHISTORY.DATE.desc()).all()
        else:
            offset = (int(page) - 1) * int(num)
            return MainDb().query(DOWNLOADHISTORY).order_by(
                DOWNLOADHISTORY.DATE.desc()).limit(num).offset(offset).all()

    @staticmethod
    def is_media_downloaded(title, tmdbid):
        """
        根据标题和年份检查是否下载过
        """
        if DbHelper.is_exists_download_history(title, tmdbid):
            return True
        count = MainDb().query(TRANSFERHISTORY).filter(TRANSFERHISTORY.TITLE == title).count()
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_brushtask(brush_id, item):
        """
        新增刷流任务
        """
        if not brush_id:
            return MainDb().insert(SITEBRUSHTASK(
                NAME=item.get('name'),
                SITE=item.get('site'),
                FREELEECH=item.get('free'),
                RSS_RULE=str(item.get('rss_rule')),
                REMOVE_RULE=str(item.get('remove_rule')),
                SEED_SIZE=item.get('seed_size'),
                INTEVAL=item.get('interval'),
                DOWNLOADER=item.get('downloader'),
                TRANSFER=item.get('transfer'),
                DOWNLOAD_COUNT=0,
                REMOVE_COUNT=0,
                DOWNLOAD_SIZE=0,
                UPLOAD_SIZE=0,
                STATE=item.get('state'),
                LST_MOD_DATE=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            ))
        else:
            return MainDb().query(SITEBRUSHTASK).filter(SITEBRUSHTASK.ID == int(brush_id)).update(
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

    @staticmethod
    def delete_brushtask(brush_id):
        """
        删除刷流任务
        """
        MainDb().query(SITEBRUSHTASK).filter(SITEBRUSHTASK.ID == int(brush_id)).delete()
        MainDb().query(SITEBRUSHTORRENTS).filter(SITEBRUSHTORRENTS.TASK_ID == brush_id).delete()

    @staticmethod
    def get_brushtasks(brush_id=None):
        """
        查询刷流任务
        """
        if brush_id:
            sql = "SELECT T.ID,T.NAME,T.SITE,'',T.INTEVAL,T.STATE,T.DOWNLOADER,T.TRANSFER," \
                  "T.FREELEECH,T.RSS_RULE,T.REMOVE_RULE,T.SEED_SIZE," \
                  "T.DOWNLOAD_COUNT,T.REMOVE_COUNT,T.DOWNLOAD_SIZE,T.UPLOAD_SIZE,T.LST_MOD_DATE,D.NAME " \
                  "FROM SITE_BRUSH_TASK T " \
                  "LEFT JOIN SITE_BRUSH_DOWNLOADERS D ON D.ID = T.DOWNLOADER " \
                  "WHERE T.ID = ?"
            return []
        else:
            sql = "SELECT T.ID,T.NAME,T.SITE,'',T.INTEVAL,T.STATE,T.DOWNLOADER,T.TRANSFER," \
                  "T.FREELEECH,T.RSS_RULE,T.REMOVE_RULE,T.SEED_SIZE," \
                  "T.DOWNLOAD_COUNT,T.REMOVE_COUNT,T.DOWNLOAD_SIZE,T.UPLOAD_SIZE,T.LST_MOD_DATE,D.NAME " \
                  "FROM SITE_BRUSH_TASK T " \
                  "LEFT JOIN SITE_BRUSH_DOWNLOADERS D ON D.ID = T.DOWNLOADER "
            return []

    @staticmethod
    def get_brushtask_totalsize(brush_id):
        """
        查询刷流任务总体积
        """
        if not brush_id:
            return 0
        ret = MainDb().query(func.sum(cast(SITEBRUSHTORRENTS.TORRENT_SIZE,
                                           Integer))).filter(SITEBRUSHTORRENTS.TASK_ID == brush_id,
                                                             SITEBRUSHTORRENTS.DOWNLOAD_ID != '0').first()
        if ret:
            return int(ret[0])
        else:
            return 0

    @staticmethod
    def add_brushtask_download_count(brush_id):
        """
        增加刷流下载数
        """
        if not brush_id:
            return
        return MainDb().query(SITEBRUSHTASK).filter(SITEBRUSHTASK.ID == int(brush_id)).update(
            {
                "DOWNLOAD_COUNT": SITEBRUSHTASK.DOWNLOAD_COUNT + 1,
                "LST_MOD_DATE": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            }
        )

    @staticmethod
    def get_brushtask_remove_size(brush_id):
        """
        获取已删除种子的上传量
        """
        if not brush_id:
            return 0
        return MainDb().query(SITEBRUSHTORRENTS.TORRENT_SIZE).filter(SITEBRUSHTORRENTS.TASK_ID == brush_id,
                                                                     SITEBRUSHTORRENTS.DOWNLOAD_ID != '0').first()

    @staticmethod
    def add_brushtask_upload_count(brush_id, upload_size, download_size, remove_count):
        """
        更新上传下载量和删除种子数
        """
        if not brush_id:
            return
        delete_upsize = 0
        delete_dlsize = 0
        remove_sizes = DbHelper.get_brushtask_remove_size(brush_id)
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
        return MainDb().query(SITEBRUSHTASK).filter(SITEBRUSHTASK.ID == int(brush_id)).update({
            "REMOVE_COUNT": SITEBRUSHTASK.REMOVE_COUNT + remove_count,
            "UPLOAD_SIZE": int(upload_size) + delete_upsize,
            "DOWNLOAD_SIZE": int(download_size) + delete_dlsize,
        })

    @staticmethod
    def insert_brushtask_torrent(brush_id, title, enclosure, downloader, download_id, size):
        """
        增加刷流下载的种子信息
        """
        if not brush_id:
            return
        if DbHelper.is_brushtask_torrent_exists(brush_id, title, enclosure):
            return False
        return MainDb().insert(SITEBRUSHTORRENTS(
            TASK_ID=brush_id,
            TORRENT_NAME=title,
            TORRENT_SIZE=size,
            ENCLOSURE=enclosure,
            DOWNLOADER=downloader,
            DOWNLOAD_ID=download_id,
            LST_MOD_DATE=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        ))

    @staticmethod
    def get_brushtask_torrents(brush_id):
        """
        查询刷流任务所有种子
        """
        if not brush_id:
            return []
        return MainDb().query(SITEBRUSHTORRENTS).filter(SITEBRUSHTORRENTS.TASK_ID == brush_id,
                                                        SITEBRUSHTORRENTS.DOWNLOAD_ID != '0').all()

    @staticmethod
    def is_brushtask_torrent_exists(brush_id, title, enclosure):
        """
        查询刷流任务种子是否已存在
        """
        if not brush_id:
            return False
        count = MainDb().query(SITEBRUSHTORRENTS).filter(SITEBRUSHTORRENTS.TASK_ID == brush_id,
                                                         SITEBRUSHTORRENTS.TORRENT_NAME == title,
                                                         SITEBRUSHTORRENTS.ENCLOSURE == enclosure).count()
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def update_brushtask_torrent_state(ids: list):
        """
        更新刷流种子的状态
        """
        if not ids:
            return
        for _id in ids:
            MainDb().query(SITEBRUSHTORRENTS).filter(SITEBRUSHTORRENTS.TASK_ID == _id[1],
                                                     SITEBRUSHTORRENTS.DOWNLOAD_ID == _id[2]).update(
                {
                    "TORRENT_SIZE": _id[0],
                    "DOWNLOAD_ID": '0'
                }
            )

    @staticmethod
    def delete_brushtask_torrent(brush_id, download_id):
        """
        删除刷流种子记录
        """
        if not download_id or not brush_id:
            return
        return MainDb().query(SITEBRUSHTORRENTS).filter(SITEBRUSHTORRENTS.TASK_ID == brush_id,
                                                        SITEBRUSHTORRENTS.DOWNLOAD_ID == download_id).delete()

    @staticmethod
    def get_user_downloaders(did=None):
        """
        查询自定义下载器
        """
        if did:
            return MainDb().query(SITEBRUSHDOWNLOADERS).filter(SITEBRUSHDOWNLOADERS.ID == int(did)).first()
        else:
            return MainDb().query(SITEBRUSHDOWNLOADERS).all()

    @staticmethod
    def update_user_downloader(did, name, dtype, user_config, note):
        """
        新增自定义下载器
        """
        if did:
            return MainDb().query(SITEBRUSHDOWNLOADERS).filter(SITEBRUSHDOWNLOADERS.ID == int(did)).update(
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
            return MainDb().insert(SITEBRUSHDOWNLOADERS(
                NAME=name,
                TYPE=dtype,
                HOST=user_config.get("host"),
                PORT=user_config.get("port"),
                USERNAME=user_config.get("username"),
                PASSWORD=user_config.get("password"),
                SAVE_DIR=user_config.get("save_dir"),
                NOTE=note
            ))

    @staticmethod
    def delete_user_downloader(did):
        """
        删除自定义下载器
        """
        return MainDb().query(SITEBRUSHDOWNLOADERS).filter(SITEBRUSHDOWNLOADERS.ID == int(did)).delete()

    @staticmethod
    def add_filter_group(name, default='N'):
        """
        新增规则组
        """
        if default == 'Y':
            DbHelper.set_default_filtergroup(0)
        group_id = DbHelper.get_filter_groupid_by_name(name)
        if group_id:
            return MainDb().query(CONFIGFILTERGROUP).filter(CONFIGFILTERGROUP.ID == int(group_id)).update({
                "IS_DEFAULT": default
            })
        else:
            return MainDb().insert(CONFIGFILTERGROUP(
                GROUP_NAME=name,
                IS_DEFAULT=default
            ))

    @staticmethod
    def get_filter_groupid_by_name(name):
        ret = MainDb().query(CONFIGFILTERGROUP).filter(CONFIGFILTERGROUP.GROUP_NAME == name).first()
        if ret:
            return ret[0]
        else:
            return ""

    @staticmethod
    def set_default_filtergroup(groupid):
        """
        设置默认的规则组
        """
        MainDb().query(CONFIGFILTERGROUP).filter(CONFIGFILTERGROUP.ID == int(groupid)).update({
            "IS_DEFAULT": 'Y'
        })
        MainDb().query(CONFIGFILTERGROUP).filter(CONFIGFILTERGROUP.ID != int(groupid)).update({
            "IS_DEFAULT": 'N'
        })

    @staticmethod
    def delete_filtergroup(groupid):
        """
        删除规则组
        """
        MainDb().query(CONFIGFILTERRULES).filter(CONFIGFILTERRULES.GROUP_ID == groupid).delete()
        return MainDb().query(CONFIGFILTERGROUP).filter(CONFIGFILTERGROUP.ID == int(groupid)).delete()

    @staticmethod
    def delete_filterrule(ruleid):
        """
        删除规则
        """
        return MainDb().query(CONFIGFILTERRULES).filter(CONFIGFILTERRULES.ID == int(ruleid)).delete()

    @staticmethod
    def insert_filter_rule(item, ruleid=None):
        """
        新增规则
        """
        if ruleid:
            return MainDb().query(CONFIGFILTERRULES).filter(CONFIGFILTERRULES.ID == int(ruleid)).update(
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
            return MainDb().insert(CONFIGFILTERRULES(
                ROLE_NAME=item.get("name"),
                PRIORITY=item.get("pri"),
                INCLUDE=item.get("include"),
                EXCLUDE=item.get("exclude"),
                SIZE_LIMIT=item.get("size"),
                NOTE=item.get("free")
            ))

    @staticmethod
    def get_userrss_tasks(taskid=None):
        if taskid:
            return MainDb().query(CONFIGUSERRSS).filter(CONFIGUSERRSS.ID == int(taskid)).all()
        else:
            return MainDb().query(CONFIGUSERRSS).all()

    @staticmethod
    def delete_userrss_task(tid):
        if not tid:
            return False
        return MainDb().query(CONFIGUSERRSS).filter(CONFIGUSERRSS.ID == int(tid)).delete()

    @staticmethod
    def update_userrss_task_info(tid, count):
        if not tid:
            return False
        return MainDb().query(CONFIGUSERRSS).filter(CONFIGUSERRSS.ID == int(tid)).update(
            {
                "PROCESS_COUNT": CONFIGUSERRSS.PROCESS_COUNT + count,
                "UPDATE_TIME": time.strftime('%Y-%m-%d %H:%M:%S',
                                             time.localtime(time.time()))
            }
        )

    @staticmethod
    def update_userrss_task(item):
        if item.get("id") and DbHelper.get_userrss_tasks(item.get("id")):
            return MainDb().query(CONFIGUSERRSS).filter(CONFIGUSERRSS.ID == int(item.get("id"))).update(
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
                    "NOTE": item.get("note")
                }
            )
        else:
            return MainDb().insert(CONFIGUSERRSS(
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
                NOTE=item.get("note")
            ))

    @staticmethod
    def get_userrss_parser(pid=None):
        if pid:
            return MainDb().query(CONFIGRSSPARSER).filter(CONFIGRSSPARSER.ID == int(pid)).first()
        else:
            return MainDb().query(CONFIGRSSPARSER).all()

    @staticmethod
    def delete_userrss_parser(pid):
        if not pid:
            return False
        return MainDb().query(CONFIGRSSPARSER).filter(CONFIGRSSPARSER.ID == int(pid)).delete()

    @staticmethod
    def update_userrss_parser(item):
        if not item:
            return False
        if item.get("id") and DbHelper.get_userrss_parser(item.get("id")):
            return MainDb().query(CONFIGRSSPARSER).filter(CONFIGRSSPARSER.ID == int(item.get("id"))).update(
                {
                    "NAME": item.get("name"),
                    "TYPE": item.get("type"),
                    "FORMAT": item.get("format"),
                    "PARAMS": item.get("params")
                }
            )
        else:
            return MainDb().insert(CONFIGRSSPARSER(
                NAME=item.get("name"),
                TYPE=item.get("type"),
                FORMAT=item.get("format"),
                PARAMS=item.get("params")
            ))

    @staticmethod
    def excute(sql):
        return MainDb().excute(sql)

    @staticmethod
    def insert_userrss_task_history(task_id, title, downloader):
        """
        增加自定义RSS订阅任务的下载记录
        """
        return MainDb().insert(USERRSSTASKHISTORY(
            TASK_ID=task_id,
            TITLE=title,
            DOWNLOADER=downloader,
            DATE=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        ))

    @staticmethod
    def get_userrss_task_history(task_id):
        """
        查询自定义RSS订阅任务的下载记录
        """
        if not task_id:
            return []
        return MainDb().query(USERRSSTASKHISTORY).filter(USERRSSTASKHISTORY.TASK_ID == task_id).all()

    @staticmethod
    def get_rss_history(rtype=None, rid=None):
        """
        查询RSS历史
        """
        if rid:
            return MainDb().query(RSSHISTORY).filter(RSSHISTORY.ID == int(rid)).all()
        elif rtype:
            return MainDb().query(RSSHISTORY).filter(RSSHISTORY.TYPE == rtype).all()
        return MainDb().query(RSSHISTORY).all()

    @staticmethod
    def is_exists_rss_history(rssid):
        """
        判断RSS历史是否存在
        """
        if not rssid:
            return False
        count = MainDb().query(RSSHISTORY).filter(RSSHISTORY.RSSID == rssid).count()
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_rss_history(rssid, rtype, name, year, tmdbid, image, desc, season=None, total=None, start=None):
        """
        登记RSS历史
        """
        if not DbHelper.is_exists_rss_history(rssid):
            return MainDb().insert(RSSHISTORY(
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

    @staticmethod
    def delete_rss_history(rssid):
        """
        删除RSS历史
        """
        if not rssid:
            return False
        return MainDb().query(RSSHISTORY).filter(RSSHISTORY.ID == int(rssid)).delete()

    @staticmethod
    def insert_custom_word(replaced, replace, front, back, offset, wtype, gid, season, enabled, regex, whelp,
                           note=None):
        """
        增加自定义识别词
        """
        return MainDb().insert(CUSTOMWORDS(
            REPLACED=replaced,
            REPLACE=replace,
            FRONT=front,
            BACK=back,
            OFFSET=int(offset),
            TYPE=int(wtype),
            GROUP_ID=int(gid),
            SEASON=int(season),
            ENABLED=int(enabled),
            REGEX=int(regex),
            HELP=whelp,
            NOTE=note
        ))

    @staticmethod
    def delete_custom_word(wid):
        """
        删除自定义识别词
        """
        return MainDb().query(CUSTOMWORDS).filter(CUSTOMWORDS.ID == int(wid)).delete()

    @staticmethod
    def check_custom_word(wid, enabled):
        """
        设置自定义识别词状态
        """
        return MainDb().query(CUSTOMWORDS).filter(CUSTOMWORDS.ID == int(wid)).update(
            {
                "ENABLED": int(enabled)
            }
        )

    @staticmethod
    def get_custom_words(wid=None, gid=None, enabled=None, wtype=None, regex=None):
        """
        查询自定义识别词
        """
        if wid:
            return MainDb().query(CUSTOMWORDS).filter(CUSTOMWORDS.ID == int(wid)).all()
        elif gid:
            return MainDb().query(CUSTOMWORDS).filter(CUSTOMWORDS.GROUP_ID == int(gid)).all()
        elif type and enabled is not None and regex is not None:
            return MainDb().query(CUSTOMWORDS).filter(CUSTOMWORDS.ENABLED == int(enabled),
                                                      CUSTOMWORDS.TYPE == int(wtype),
                                                      CUSTOMWORDS.REGEX == int(regex)).all()
        return MainDb().query(CUSTOMWORDS).all()

    @staticmethod
    def is_custom_words_existed(replaced=None, front=None, back=None):
        """
        查询自定义识别词
        """
        if replaced:
            count = MainDb().query(CUSTOMWORDS).filter(CUSTOMWORDS.REPLACED == replaced).count()
        elif front and back:
            count = MainDb().query(CUSTOMWORDS).filter(CUSTOMWORDS.FRONT == front,
                                                       CUSTOMWORDS.BACK == back).count()
        else:
            return False
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def insert_custom_word_groups(title, year, wtype, tmdbid, season_count, note=None):
        """
        增加自定义识别词组
        """
        return MainDb().insert(CUSTOMWORDGROUPS(
            TITLE=title,
            YEAR=year,
            TYPE=int(wtype),
            TMDBID=int(tmdbid),
            SEASON_COUNT=int(season_count),
            NOTE=note
        ))

    @staticmethod
    def delete_custom_word_group(wid):
        """
        删除自定义识别词组
        """
        if not wid:
            return
        MainDb().query(CUSTOMWORDS).filter(CUSTOMWORDS.GROUP_ID == int(wid)).delete()
        MainDb().query(CUSTOMWORDGROUPS).filter(CUSTOMWORDGROUPS.ID == int(wid)).delete()

    @staticmethod
    def get_custom_word_groups(gid=None, tmdbid=None, wtype=None):
        """
        查询自定义识别词组
        """
        if gid:
            return MainDb().query(CUSTOMWORDGROUPS).filter(CUSTOMWORDGROUPS.ID == int(gid)).all()
        if tmdbid and wtype:
            return MainDb().query(CUSTOMWORDGROUPS).filter(CUSTOMWORDGROUPS.TMDBID == int(tmdbid),
                                                           CUSTOMWORDGROUPS.TYPE == int(wtype)).all()
        return MainDb().query(CUSTOMWORDGROUPS).all()

    @staticmethod
    def is_custom_word_group_existed(tmdbid=None, wtype=None):
        """
        查询自定义识别词组
        """
        if not wtype or not tmdbid:
            return False
        count = MainDb().query(CUSTOMWORDGROUPS).filter(CUSTOMWORDGROUPS.TMDBID == int(tmdbid),
                                                        CUSTOMWORDGROUPS.TYPE == int(wtype)).count()
        if count > 0:
            return True
        else:
            return False
