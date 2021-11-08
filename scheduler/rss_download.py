# RSS下载器
import os
import re

import requests
import log
import settings
from xml.dom.minidom import parse
import xml.dom.minidom

from functions import login_qbittorrent, is_chinese
from message.send import sendmsg
from rmt.media import get_media_info, get_media_file_season, get_media_file_seq

logger = log.Logger("scheduler").logger
# 读取配置
rss_jobs = eval(settings.get("rss.rss_job"))
save_path = settings.get("rss.save_path")
movie_path = settings.get("rss.movie_path")
tv_path = settings.get("rss.tv_path")
fav_type = settings.get("rmt.rmt_favtype")
media_exts = settings.get("rmt.rmt_mediaext").split(",")
movie_types = settings.get("rmt.rmt_movietype").split(",")
rss_cache_list = []
rss_cache_name = []


# 添加qbittorrent任务
def add_qbittorrent_torrent(turl):
    qbc = login_qbittorrent()
    qbc_ret = qbc.torrents_add(turl, None, save_path)
    qbc.auth_log_out()
    return qbc_ret


def parse_rssxml(url):
    ret_array = []
    if not url:
        return ret_array
    try:
        logger.info("【RSS】开始下载：" + url)
        ret = requests.get(url)
    except Exception as e:
        logger.error("【RSS】下载失败：" + str(e))
        return ret_array
    if ret:
        ret_xml = ret.text
        try:
            # 解析XML
            dom_tree = xml.dom.minidom.parseString(ret_xml)
            rootNode = dom_tree.documentElement
            items = rootNode.getElementsByTagName("item")
            for item in items:
                # 获取XML值
                title = item.getElementsByTagName("title")[0].firstChild.data
                category = item.getElementsByTagName("category")[0].firstChild.data
                enclosure = item.getElementsByTagName("enclosure")[0].getAttribute("url")
                tmp_dict = {'title': title, 'category': category, 'enclosure': enclosure}
                ret_array.append(tmp_dict)
            logger.info("【RSS】下载成功，发现更新：" + str(len(items)))
        except Exception as e2:
            logger.error("【RSS】解析失败：" + str(e2))
            return ret_array
    return ret_array


def run_rssdownload():
    succ_list = []
    for rss_job in rss_jobs:
        # 读取子配置
        rssurl = settings.get("rss." + rss_job + "_rssurl")
        movie_type = eval(settings.get("rss." + rss_job + "_movie_type"))
        movie_res = eval(settings.get("rss." + rss_job + "_movie_re"))
        tv_res = eval(settings.get("rss." + rss_job + "_tv_re"))
        # 下载RSS
        logger.info("【RSS】正在处理：" + rss_job)
        rss_result = parse_rssxml(rssurl)
        if len(rss_result) == 0:
            continue
        for res in rss_result:
            try:
                title = res['title']
                category = res['category']
                enclosure = res['enclosure']
                if title not in rss_cache_list:
                    rss_cache_list.append(title)
                else:
                    logger.debug("【RSS】" + title + "已处理过，跳过...")
                    continue
                match_flag = False
                if movie_type and (category in movie_type):
                    search_type = "电影"
                    # 过滤
                    for movie_re in movie_res:
                        if re.search(movie_re, title):
                            match_flag = True
                            break
                else:
                    search_type = "电视剧"
                    # 过滤
                    for tv_re in tv_res:
                        if re.search(tv_re, title):
                            match_flag = True
                            break
                if match_flag:
                    logger.info("【RSS】" + title + "匹配成功!")
                else:
                    logger.info("【RSS】" + title + "不匹配规则，跳过...")
                    continue
                logger.info("【RSS】开始检索媒体信息:" + title)
                media_info = get_media_info(title, title, search_type)
                search_type = media_info['search']
                media_type = media_info["type"]
                media_title = media_info["name"]
                media_year = media_info["year"]
                if not is_chinese(media_title):
                    logger.info("【RSS】没有中文看不懂，跳过：" + media_title)
                    continue
                # 判断是否已存在
                media_name = media_title + " (" + media_year + ")"
                if search_type == "电影":
                    if media_name not in rss_cache_name:
                        rss_cache_name.append(media_name)
                    else:
                        logger.debug("【RSS】电影已处理过，跳过：" + media_name)
                        continue
                    # 确认是否已存在
                    exist_flag = False
                    for m_type in movie_types:
                        media_path = os.path.join(movie_path, m_type, media_name)
                        # 目录是否存在
                        logger.debug("【RSS】路径：" + media_path)
                        if os.path.exists(media_path):
                            logger.info("【RSS】电影目录已存在，跳过：" + media_path)
                            exist_flag = True
                            break
                    if exist_flag:
                        continue
                else:
                    # 剧集目录
                    media_path = os.path.join(tv_path, media_type, media_name)
                    # 剧集是否存在
                    # Sxx
                    file_season = get_media_file_season(title)
                    # 季 Season xx
                    season_str = "Season " + str(int(file_season.replace("S", "")))
                    season_dir = os.path.join(media_path, season_str)
                    # Exx
                    file_seq = get_media_file_seq(title)
                    if file_seq != "":
                        # 集 xx
                        file_seq_num = str(int(file_seq.replace("E", "").replace("P", "")))
                        # 文件路径
                        file_path = os.path.join(season_dir, media_title + " - " + file_season + file_seq + " - " + "第 " + file_seq_num + " 集")
                        exist_flag = False
                        for ext in media_exts:
                            logger.debug("【RSS】路径：" + file_path + ext)
                            if os.path.exists(file_path + ext):
                                exist_flag = True
                                logger.error("【RSS】剧集文件已存在，跳过：" + file_path + ext)
                                break
                        if exist_flag:
                            continue
                    else:
                        if os.path.exists(season_dir):
                            logger.error("【RSS】剧集目录已存在，跳过：" + season_dir)
                            continue
            except Exception as e:
                logger.error("【RSS】错误：" + str(e))
                continue
            # 添加qbittorrent任务
            logger.info("【RSS】添加qBittorrent任务：" + title)
            try:
                ret = add_qbittorrent_torrent(enclosure)
                if ret and ret.find("Ok") != -1:
                    msg_item = "> " + media_name + "：" + title
                    if msg_item not in succ_list:
                        succ_list.append(msg_item)
            except Exception as e:
                logger.error("【RSS】添加qBittorrent任务出错：" + str(e))
        logger.info("【RSS】" + rss_job + "处理结束！")
    if len(succ_list) > 0:
        sendmsg("【RSS】qBittorrent新增下载", "\n\n".join(succ_list))


if __name__ == "__main__":
    run_rssdownload()
