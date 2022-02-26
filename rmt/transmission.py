import os.path

import transmission_rpc
import urllib3
import log
from config import get_config, RMT_MEDIAEXT
from rmt.media import transfer_media

# 全局设置
urllib3.disable_warnings()


# 连接transmission
def login_transmission():
    try:
        # 登录
        config = get_config()
        trhost = config['transmission'].get('trhost')
        trport = config['transmission'].get('trport')
        trusername = config['transmission'].get('trusername')
        trpassword = config['transmission'].get('trpassword')
        trt = transmission_rpc.Client(host=trhost,
                                      port=trport,
                                      username=trusername,
                                      password=trpassword,
                                      timeout=10)
        return trt
    except Exception as err:
        log.error("【RUN】出错：" + str(err))
        return None


# 根据transmission的文件清单，获取种子的下载路径
def get_tr_download_path(save_path, tr_files):
    path_list = []
    for tr_file in tr_files:
        if os.path.splitext(tr_file.name)[-1] in RMT_MEDIAEXT:
            if tr_file.name not in path_list:
                path_list.append(tr_file.name)
    # 返回list(多个路径)中，所有path共有的最长的路径
    return os.path.join(save_path, os.path.commonprefix(path_list))


# 读取当前任务列表
def get_transmission_tasks():
    # 读取transmission列表
    config = get_config()
    trt = login_transmission()
    torrents = trt.get_torrents()
    trans_trpath = config['transmission'].get('save_path')
    trans_containerpath = config['transmission'].get('save_containerpath')
    path_list = []
    for torrent in torrents:
        log.debug(torrent.name + "：" + torrent.status)
        if (torrent.status == "seeding" or torrent.status == "seed_pending") and "已整理" not in torrent.labels:
            true_path = get_tr_download_path(torrent.download_dir, torrent.files())
            if trans_containerpath:
                true_path = true_path.replace(str(trans_trpath), str(trans_containerpath))
            path_list.append(true_path + "|" + str(torrent.id))
    return path_list


# 读取所有种子信息
def get_transmission_torrents():
    # 读取transmission列表
    trt = login_transmission()
    if not trt:
        log.error("【RMT】错误：transmission连接失败！")
        return []
    torrents = trt.get_torrents()
    return torrents


# 迁移完成后设置种子状态
def set_tr_torrent_status(id_str):
    trc = login_transmission()
    if not trc:
        log.error("【RMT】错误：transmission连接失败！")
        return
    # 打标签
    trc.change_torrent(labels=["已整理"], ids=id_str)
    log.info("【RMT】设置transmission种类状态成功！")


# 处理transmission中的种子
def transfer_transmission_task():
    config = get_config()
    trans_trpath = config['transmission'].get('save_path')
    trans_containerpath = config['transmission'].get('save_containerpath')
    # 处理所有任务
    torrents = get_transmission_torrents()
    for torrent in torrents:
        log.debug("【RMT】" + torrent.name + "：" + torrent.status)
        if (torrent.status == "seeding" or torrent.status == "seed_pending") and "已整理" not in torrent.labels:
            true_path = get_tr_download_path(torrent.download_dir, torrent.files())
            if trans_containerpath:
                true_path = true_path.replace(str(trans_trpath), str(trans_containerpath))
            done_flag = transfer_media(in_from="transmission", in_name=torrent.name, in_path=true_path)
            if done_flag:
                set_tr_torrent_status(torrent.id)


# 添加transmission任务
def add_transmission_torrent(turl, tpath):
    qbt = login_transmission()
    qbt_ret = qbt.add_torrent(torrent=turl, download_dir=tpath)
    return qbt_ret
