import os
import time
from subprocess import call

import log
from config import get_config, RMT_FAVTYPE
from rmt.metainfo import MetaInfo
from utils.functions import get_location
from message.send import Message
from utils.types import MediaCatagory, MediaType

PLAY_LIST = []


def report_to_discord(event):
    # 读取配置
    config = get_config()
    if config.get('media'):
        movie_path = config['media'].get('movie_path')
        movie_subtypedir = config['media'].get('movie_subtypedir', True)
    else:
        movie_path = None
        movie_subtypedir = True

    message_title = None
    tmdb_id = None
    media_type = None
    # System
    log.debug('【EMBY】事件类型：' + event.category)
    if event.category == 'system':
        if event.action == 'webhooktest':
            log.info("【EMBY】system.webhooktest")
    # Playback
    elif event.category == 'playback':
        media_type = event.media_type
        ignore_list = config['message'].get('webhook_ignore')
        if ignore_list:
            if event.user_name in ignore_list or \
                    event.device_name in ignore_list or \
                    (event.user_name + ':' + event.device_name) in ignore_list:
                log.info('【EMBY】忽略的用户或设备，不通知：%s %s' % (event.user_name, event.device_name))
        list_id = event.user_name + event.item_name + event.ip + event.device_name + event.client
        if event.action == 'start':
            message_title = '【EMBY】用户 %s 开始播放 %s' % (event.user_name, event.item_name)
            tmdb_id = event.tmdb_id
            if list_id not in PLAY_LIST:
                PLAY_LIST.append(list_id)
        elif event.action == 'stop':
            if list_id in PLAY_LIST:
                message_title = '【EMBY】用户 %s 停止播放 %s' % (event.user_name, event.item_name)
                tmdb_id = event.tmdb_id
                PLAY_LIST.remove(list_id)
            else:
                log.debug('【EMBY】重复Stop通知，丢弃：' + list_id)
    elif event.category == 'user':
        if event.action == 'login':
            if event.status.upper() == 'F':
                message_title = '【EMBY】用户 %s 登录 %s 失败！' % (event.user_name, event.server_name)
            else:
                message_title = '【EMBY】用户 %s 登录了 %s' % (event.user_name, event.server_name)
    elif event.category == 'item':
        if event.action == 'rate':
            if not movie_subtypedir or not movie_path:
                return
            if os.path.isdir(event.movie_path):
                movie_dir = event.movie_path
            else:
                movie_dir = os.path.dirname(event.movie_path)
            if movie_dir.count(movie_path) == 0:
                return
            name = movie_dir.split('/')[-1]
            org_type = movie_dir.split('/')[-2]
            if org_type not in [MediaCatagory.HYDY.value, MediaCatagory.WYDY.value]:
                return
            if org_type == MediaCatagory.JXDY.value:
                return
            new_path = os.path.join(movie_path, MediaCatagory.JXDY.value, name)
            log.info("【EMBY】开始转移文件 %s 到 %s ..." % (movie_dir, new_path))
            if os.path.exists(new_path):
                log.info("【EMBY】目录 %s 已存在！" % new_path)
                return
            ret = call(['mv', movie_dir, new_path])
            if ret == 0:
                message_title = '【EMBY】电影 %s 已从 %s 转移到 %s' % (event.movie_name, org_type, RMT_FAVTYPE)
            else:
                message_title = '【EMBY】电影 %s 转移失败！' % event.movie_name

    if message_title:
        desp = ""
        if event.category == 'playback':
            address = get_location(event.ip)
            desp = '设备：' + event.device_name \
                   + '\n客户端：' + event.client \
                   + '\nIP地址：' + event.ip \
                   + '\n位置：' + address \
                   + '\n时间：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        elif event.category == 'user':
            if event.action == 'login':
                address = get_location(event.ip)
                desp = '设备：' + event.device_name \
                       + '\nIP地址：' + event.ip \
                       + '\n位置：' + address \
                       + '\n时间：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        elif event.category == 'item':
            if event.action == 'rate':
                desp = '时间：' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        # Report Message
        if tmdb_id:
            image_url = MetaInfo.get_backdrop_image(media_type, None, tmdb_id, "https://emby.media/notificationicon.png")
        else:
            image_url = ""
        Message().sendmsg(message_title, desp, image_url)
