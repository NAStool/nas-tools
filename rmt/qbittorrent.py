# qBittorrent媒体文件转移
import os
import sys
import urllib3
import log
import settings

# 全局设置
from functions import login_qbittorrent
from rmt.media import transfer_directory

urllib3.disable_warnings()
logger = log.Logger("rmt").logger


# ----------------------------函数 BEGIN-----------------------------------------
# 迁移完成后设置种子状态
def set_torrent_status(qbc, hash_str):
    if qbc:
        # 打标签
        qbc.torrents_add_tags("已整理", hash_str)
        # 超级做种
        qbc.torrents_set_force_start(True, hash_str)
        logger.info("设置qBittorrent种类状态成功！")


# 处理所有qbittorrent中的种子
def transfer_qbittorrent_task():
    qbc = login_qbittorrent()
    if not qbc:
        logger.error("连接qbittorrent失败！")
        return
    torrents = qbc.torrents_info()
    trans_qbpath = settings.get("rmt.rmt_qbpath")
    trans_containerpath = settings.get("rmt.rmt_containerpath")
    for torrent in torrents:
        logger.info(torrent.name + "：" + torrent.state)
        if torrent.state == "uploading" or torrent.state == "stalledUP":
            true_path = torrent.content_path.replace(str(trans_qbpath), str(trans_containerpath))
            transfer_directory("qBittorrent", torrent.name, true_path)
            set_torrent_status(qbc, torrent.hash)
    qbc.auth_log_out()
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

        logger.debug("输入参数：" + str(sys.argv))
        rmt_qbpath = settings.get("rmt.rmt_qbpath")
        rmt_containerpath = settings.get("rmt.rmt_containerpath")
        QB_Path = QB_Path.replace(str(rmt_qbpath), str(rmt_containerpath))
        if not os.path.exists(QB_Path):
            logger.error("找不到文件：" + QB_Path)
            quit()
        logger.info("开始处理：" + QB_Name)
        ret = transfer_directory("qBittorrent", QB_Name, QB_Path, QB_Year, QB_Type, MV_Flag)
        if QB_Hash:
            qbt_client = login_qbittorrent()
            set_torrent_status(qbt_client, QB_Hash)
            qbt_client.auth_log_out()
        if ret:
            logger.info(QB_Name + "处理成功！")
        else:
            logger.error(QB_Name + "处理失败！")
    else:
        # 处理所有qbittorrent中的种子
        transfer_qbittorrent_task()

# ----------------------------主流程 END--------------------------------------
