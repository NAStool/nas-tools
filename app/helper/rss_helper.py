import xml.dom.minidom

from app.db import MainDb, DbPersist
from app.db.models import RSSTORRENTS
from app.utils import RssTitleUtils, StringUtils, RequestUtils, ExceptionUtils, DomUtils
from config import Config


class RssHelper:
    _db = MainDb()

    @staticmethod
    def parse_rssxml(url, proxy=False):
        """
        解析RSS订阅URL，获取RSS中的种子信息
        :param url: RSS地址
        :param proxy: 是否使用代理
        :return: 种子信息列表，如为None代表Rss过期
        """
        _special_title_sites = {
            'pt.keepfrds.com': RssTitleUtils.keepfriends_title
        }

        _rss_expired_msg = [
            "RSS 链接已过期, 您需要获得一个新的!",
            "RSS Link has expired, You need to get a new one!"
        ]

        # 开始处理
        ret_array = []
        if not url:
            return []
        site_domain = StringUtils.get_url_domain(url)
        try:
            ret = RequestUtils(proxies=Config().get_proxies() if proxy else None).get_res(url)
            if not ret:
                return []
            ret.encoding = ret.apparent_encoding
        except Exception as e2:
            ExceptionUtils.exception_traceback(e2)
            return []
        if ret:
            ret_xml = ret.text
            try:
                # 解析XML
                dom_tree = xml.dom.minidom.parseString(ret_xml)
                rootNode = dom_tree.documentElement
                items = rootNode.getElementsByTagName("item")
                for item in items:
                    try:
                        # 标题
                        title = DomUtils.tag_value(item, "title", default="")
                        if not title:
                            continue
                        # 标题特殊处理
                        if site_domain and site_domain in _special_title_sites:
                            title = _special_title_sites.get(site_domain)(title)
                        # 描述
                        description = DomUtils.tag_value(item, "description", default="")
                        # 种子页面
                        link = DomUtils.tag_value(item, "link", default="")
                        # 种子链接
                        enclosure = DomUtils.tag_value(item, "enclosure", "url", default="")
                        if not enclosure and not link:
                            continue
                        # 部分RSS只有link没有enclosure
                        if not enclosure and link:
                            enclosure = link
                            link = None
                        # 大小
                        size = DomUtils.tag_value(item, "enclosure", "length", default=0)
                        if size and str(size).isdigit():
                            size = int(size)
                        else:
                            size = 0
                        # 发布日期
                        pubdate = DomUtils.tag_value(item, "pubDate", default="")
                        if pubdate:
                            # 转换为时间
                            pubdate = StringUtils.get_time_stamp(pubdate)
                        # 返回对象
                        tmp_dict = {'title': title,
                                    'enclosure': enclosure,
                                    'size': size,
                                    'description': description,
                                    'link': link,
                                    'pubdate': pubdate}
                        ret_array.append(tmp_dict)
                    except Exception as e1:
                        ExceptionUtils.exception_traceback(e1)
                        continue
            except Exception as e2:
                # RSS过期 观众RSS 链接已过期，您需要获得一个新的！  pthome RSS Link has expired, You need to get a new one!
                if ret_xml in _rss_expired_msg:
                    return None
                ExceptionUtils.exception_traceback(e2)
        return ret_array

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

    def is_rssd_by_enclosure(self, enclosure):
        """
        查询RSS是否处理过，根据下载链接
        """
        if not enclosure:
            return True
        if self._db.query(RSSTORRENTS).filter(RSSTORRENTS.ENCLOSURE == enclosure).count() > 0:
            return True
        else:
            return False

    def is_rssd_by_simple(self, torrent_name, enclosure):
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
    def simple_delete_rss_torrents(self, title, enclosure=None):
        """
        删除RSS的记录
        """
        if enclosure:
            self._db.query(RSSTORRENTS).filter(RSSTORRENTS.TORRENT_NAME == title,
                                               RSSTORRENTS.ENCLOSURE == enclosure).delete()
        else:
            self._db.query(RSSTORRENTS).filter(RSSTORRENTS.TORRENT_NAME == title).delete()

    @DbPersist(_db)
    def truncate_rss_history(self):
        """
        清空RSS历史记录
        """
        self._db.query(RSSTORRENTS).delete()
