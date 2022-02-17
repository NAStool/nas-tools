# RSS下载器
import os
import re

import requests
import log
import settings
from xml.dom.minidom import parse
import xml.dom.minidom

from functions import is_chinese
from message.send import sendmsg
from rmt.media import get_media_info, get_media_file_season, get_media_file_seq
from rmt.qbittorrent import login_qbittorrent

rss_cache_list = []
rss_cache_name = []
RUNING_FLAG = False


def run_rssdownload():
    try:
        global RUNING_FLAG
        if RUNING_FLAG:
            log.error("【RUN】rssdownload任务正在执行中...")
        else:
            RUNING_FLAG = True
            rssdownload()
            RUNING_FLAG = False
    except Exception as err:
        RUNING_FLAG = False
        log.error("【RUN】执行任务rssdownload出错：" + str(err))
        sendmsg("【NASTOOL】执行任务rssdownload出错！", str(err))


# 添加qbittorrent任务
def add_qbittorrent_torrent(turl, tpath):
    qbc = login_qbittorrent()
    qbc_ret = qbc.torrents_add(turl, None, tpath)
    qbc.auth_log_out()
    return qbc_ret


def parse_rssxml(url):
    ret_array = []
    if not url:
        return ret_array
    try:
        log.info("【RSS】开始下载：" + url)
        ret = requests.get(url)
    except Exception as e:
        log.error("【RSS】下载失败：" + str(e))
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
            log.info("【RSS】下载成功，发现更新：" + str(len(items)))
        except Exception as e2:
            log.error("【RSS】解析失败：" + str(e2))
            return ret_array
    return ret_array


def rssdownload():
    # 读取配置
    rss_jobs = eval(settings.get("rss.rss_job"))
    save_path = settings.get("qbittorrent.save_path")
    movie_path = settings.get("movie.movie_path")
    tv_path = settings.get("tv.tv_path")
    media_exts = settings.get("rmt.rmt_mediaext").split(",")
    movie_types = settings.get("rmt.rmt_movietype").split(",")
    succ_list = []
    for rss_job in rss_jobs:
        # 读取子配置
        rssurl = settings.get("rss." + rss_job + "_rssurl")
        if not rssurl:
            log.error("【RSS】" + str(rss_job) + "未配置rssurl，无法下载订阅！")
            continue
        movie_type = eval(settings.get("rss." + rss_job + "_movie_type"))
        movie_res = eval(settings.get("rss." + rss_job + "_movie_re"))
        log.info("【RSS】电影规则清单：" + ' '.join(movie_res))
        tv_res = eval(settings.get("rss." + rss_job + "_tv_re"))
        log.info("【RSS】电视剧规则清单：" + ' '.join(tv_res))
        # 下载RSS
        log.info("【RSS】正在处理：" + rss_job)
        rss_result = parse_rssxml(rssurl)
        if len(rss_result) == 0:
            continue
        for res in rss_result:
            try:
                title = res['title']
                category = res['category']
                enclosure = res['enclosure']
                # 判断是否处理过
                if enclosure not in rss_cache_list:
                    rss_cache_list.append(enclosure)
                else:
                    log.debug("【RSS】" + title + " 已处理过，跳过...")
                    continue
                match_flag = False
                if movie_type and (category in movie_type):
                    search_type = "电影"
                    # 匹配种子标题是否匹配关键字
                    for movie_re in movie_res:
                        if re.search(movie_re, title):
                            match_flag = True
                            break
                else:
                    search_type = "电视剧"
                    # 匹配种子标题是否匹配关键字
                    for tv_re in tv_res:
                        if re.search(tv_re, title):
                            match_flag = True
                            break
                if match_flag:
                    log.info("【RSS】" + title + " 种子标题匹配成功!")
                else:
                    log.info("【RSS】" + title + " 种子标题不匹配，继接拉取媒体描述信息进行匹配...")

                log.info("【RSS】开始检索媒体信息:" + title)
                media_info = get_media_info(title, title, search_type)
                media_type = media_info["type"]
                media_title = media_info["name"]
                media_year = media_info["year"]

                rss_chinese = settings.get("rss.rss_chinese")
                if rss_chinese.upper() == "TRUE" and not is_chinese(media_title):
                    log.info("【RSS】该媒体在TMDB中没有中文描述，跳过：" + media_title)
                    continue

                # 匹配媒体信息标题是否匹配关键字
                if search_type == "电影":
                    # 匹配种子标题是否匹配关键字，需要完全匹配
                    for movie_re in movie_res:
                        if movie_re == media_title:
                            match_flag = True
                            log.info("【RSS】" + title + " 电影名称匹配成功!")
                            break
                else:
                    # 匹配种子标题是否匹配关键字，需要完全匹配
                    for tv_re in tv_res:
                        if tv_re == media_title:
                            log.info("【RSS】" + title + " 电影名称匹配成功!")
                            match_flag = True
                            break

                # 匹配后处理...
                if match_flag:
                    # 判断是否已存在
                    media_name = media_title + " (" + media_year + ")"
                    if search_type == "电影":
                        if media_name not in rss_cache_name:
                            rss_cache_name.append(media_name)
                        else:
                            log.debug("【RSS】电影标题已处理过，跳过：" + media_name)
                            continue
                        # 确认是否已存在
                        exist_flag = False
                        for m_type in movie_types:
                            media_path = os.path.join(movie_path, m_type, media_name)
                            # 目录是否存在
                            log.debug("【RSS】路径：" + media_path)
                            if os.path.exists(media_path):
                                log.info("【RSS】电影目录已存在该电影，跳过：" + media_path)
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
                                log.debug("【RSS】路径：" + file_path + ext)
                                if os.path.exists(file_path + ext):
                                    exist_flag = True
                                    log.error("【RSS】该剧集文件已存在，跳过：" + file_path + ext)
                                    break
                            if exist_flag:
                                continue
                    # 添加qbittorrent任务
                    log.info("【RSS】添加qBittorrent任务：" + title)
                    try:
                        ret = add_qbittorrent_torrent(enclosure, save_path)
                        if ret and ret.find("Ok") != -1:
                            msg_item = "> " + media_name + "：" + title
                            if msg_item not in succ_list:
                                succ_list.append(msg_item)
                    except Exception as e:
                        log.error("【RSS】添加qBittorrent任务出错：" + str(e))
                else:
                    log.info("【RSS】规则匹配不成功：" + media_title)
            except Exception as e:
                log.error("【RSS】错误：" + str(e))
                continue
        log.info("【RSS】" + rss_job + "处理结束！")
    if len(succ_list) > 0:
        sendmsg("【RSS】qBittorrent新增下载", "\n\n".join(succ_list))


if __name__ == "__main__":
    run_rssdownload()
