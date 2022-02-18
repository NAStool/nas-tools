import sys
import qbittorrentapi
import urllib3
import log
from config import get_config
from rmt.media import transfer_directory


# 全局设置
urllib3.disable_warnings()


# ----------------------------函数 BEGIN-----------------------------------------
# 连接qbittorrent
def login_qbittorrent():
    try:
        # 登录
        config = get_config()
        qbhost = config['qbittorrent']['qbhost']
        qbport = config['qbittorrent']['qbport']
        qbusername = config['qbittorrent']['qbusername']
        qbpassword = config['qbittorrent']['qbpassword']
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
    trans_qbpath = config['qbittorrent']['save_path']
    trans_containerpath = config['qbittorrent']['save_containerpath']
    path_list = []
    for torrent in torrents:
        log.debug(torrent.name + "：" + torrent.state)
        if torrent.state == "uploading" or torrent.state == "stalledUP":
            true_path = torrent.content_path
            if trans_containerpath:
                true_path = torrent.content_path.replace(str(trans_qbpath), str(trans_containerpath))
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
def set_torrent_status(hash_str):
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
    trans_qbpath = config['qbittorrent']['save_path']
    trans_containerpath = config['qbittorrent']['save_containerpath']
    # 处理所有任务
    torrents = get_qbittorrent_torrents()
    for torrent in torrents:
        log.debug("【RMT】" + torrent.name + "：" + torrent.state)
        if torrent.state == "uploading" or torrent.state == "stalledUP":
            true_path = torrent.content_path
            if trans_containerpath:
                true_path = torrent.content_path.replace(str(trans_qbpath), str(trans_containerpath))
            done_flag = transfer_directory(in_from="qBittorrent", in_name=torrent.name, in_path=true_path)
            if done_flag:
                set_torrent_status(torrent.hash)

# ----------------------------函数 END-----------------------------------------


# ----------------------------主流程 BEGIN--------------------------------------
if __name__ == "__main__":
    # 输入参数：名称、路径、HASH
    if len(sys.argv) > 3:
        QB_Name = sys.argv[1]
        QB_Path = sys.argv[2]
        QB_Hash = sys.argv[3]
    else:
        QB_Name = None
        QB_Path = None
        QB_Hash = None

    if QB_Name and QB_Path:
        # 输入参数：年份
        if len(sys.argv) > 4:
            QB_Year = sys.argv[4]
        else:
            QB_Year = None

        # 输入参数：类型
        if len(sys.argv) > 5:
            QB_Type = sys.argv[5]
        else:
            QB_Type = None

        # 输入参数：复制或移动
        if len(sys.argv) > 6:
            MV_Flag = sys.argv[6] == "T" or False
        else:
            MV_Flag = False

        log.debug("【RMT】输入参数：" + str(sys.argv))
        log.info("【RMT】开始处理：" + QB_Name)
        ret = transfer_directory(in_from="qBittorrent", in_name=QB_Name, in_path=QB_Path, in_year=QB_Year,
                                 in_type=QB_Type, mv_flag=MV_Flag)
        if QB_Hash:
            set_torrent_status(QB_Hash)
    else:
        # 处理所有qbittorrent中的种子
        transfer_qbittorrent_task()

# ----------------------------主流程 END--------------------------------------
