import qbittorrentapi
import urllib3
import log
from config import get_config
from rmt.media import transfer_media

# 全局设置
urllib3.disable_warnings()


# 连接qbittorrent
def login_qbittorrent():
    try:
        # 登录
        config = get_config()
        qbhost = config['qbittorrent'].get('qbhost')
        qbport = config['qbittorrent'].get('qbport')
        qbusername = config['qbittorrent'].get('qbusername')
        qbpassword = config['qbittorrent'].get('qbpassword')
        qbt = qbittorrentapi.Client(host=qbhost,
                                    port=qbport,
                                    username=qbusername,
                                    password=qbpassword,
                                    VERIFY_WEBUI_CERTIFICATE=False)
        qbt.auth_log_in()
        return qbt
    except Exception as err:
        log.error("【RUN】出错：" + str(err))
        return None


# 读取当前任务列表
def get_qbittorrent_tasks():
    # 读取qBittorrent列表
    config = get_config()
    qbt = login_qbittorrent()
    torrents = qbt.torrents_info()
    trans_qbpath = config['qbittorrent'].get('save_path')
    trans_containerpath = config['qbittorrent'].get('save_containerpath')
    path_list = []
    for torrent in torrents:
        log.debug(torrent.name + "：" + torrent.state)
        if torrent.state == "uploading" or torrent.state == "stalledUP":
            true_path = torrent.content_path
            if trans_containerpath:
                true_path = true_path.replace(str(trans_qbpath), str(trans_containerpath))
            path_list.append(true_path + "|" + torrent.hash)
    qbt.auth_log_out()
    return path_list


# 读取所有种子信息
def get_qbittorrent_torrents():
    # 读取qBittorrent列表
    qbt = login_qbittorrent()
    if not qbt:
        log.error("【RMT】错误：qbittorrent连接失败！")
        return []
    torrents = qbt.torrents_info()
    qbt.auth_log_out()
    return torrents


# 迁移完成后设置种子状态
def set_qb_torrent_status(hash_str):
    qbc = login_qbittorrent()
    if not qbc:
        log.error("【RMT】错误：qbittorrent连接失败！")
        return
    # 打标签
    qbc.torrents_add_tags("已整理", hash_str)
    # 超级做种
    qbc.torrents_set_force_start(True, hash_str)
    log.info("【RMT】设置qBittorrent种类状态成功！")
    qbc.auth_log_out()


# 处理qbittorrent中的种子
def transfer_qbittorrent_task():
    config = get_config()
    trans_qbpath = config['qbittorrent'].get('save_path')
    trans_containerpath = config['qbittorrent'].get('save_containerpath')
    # 处理所有任务
    torrents = get_qbittorrent_torrents()
    for torrent in torrents:
        log.debug("【RMT】" + torrent.name + "：" + torrent.state)
        if torrent.state == "uploading" or torrent.state == "stalledUP":
            true_path = torrent.content_path
            if trans_containerpath:
                true_path = true_path.replace(str(trans_qbpath), str(trans_containerpath))
            done_flag = transfer_media(in_from="qBittorrent", in_name=torrent.name, in_path=true_path)
            if done_flag:
                set_qb_torrent_status(torrent.hash)


# 添加qbittorrent任务
def add_qbittorrent_torrent(turl, tpath):
    qbc = login_qbittorrent()
    qbc_ret = qbc.torrents_add(turl, None, tpath)
    qbc.auth_log_out()
    return qbc_ret
