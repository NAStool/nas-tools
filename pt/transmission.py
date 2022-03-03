import os.path

import transmission_rpc
import urllib3
import log
from config import get_config, RMT_MEDIAEXT

# 全局设置
from rmt.media import Media

urllib3.disable_warnings()


class Transmission:
    __trhost = None
    __trport = None
    __trusername = None
    __trpassword = None
    __save_path = None
    __save_containerpath = None
    trc = None
    media = None

    def __init__(self):
        config = get_config()
        if config.get('transmission'):
            self.__trhost = config['transmission'].get('trhost')
            self.__trport = config['transmission'].get('trport')
            self.__trusername = config['transmission'].get('trusername')
            self.__trpassword = config['transmission'].get('trpassword')
            self.__save_path = config['transmission'].get('save_path')
            self.__save_containerpath = config['transmission'].get('save_containerpath')
            self.media = Media()
            if self.__trhost and self.__trport:
                self.trc = self.__login_transmission()

    # 连接transmission
    def __login_transmission(self):
        try:
            # 登录
            trt = transmission_rpc.Client(host=self.__trhost,
                                          port=self.__trport,
                                          username=self.__trusername,
                                          password=self.__trpassword,
                                          timeout=10)
            return trt
        except Exception as err:
            log.error("【TR】transmission连接出错：%s" % str(err))
            return None

    # 根据transmission的文件清单，获取种子的下载路径
    @staticmethod
    def __get_tr_download_path(save_path, tr_files):
        path_list = []
        for tr_file in tr_files:
            if os.path.splitext(tr_file.name)[-1] in RMT_MEDIAEXT:
                if tr_file.name not in path_list:
                    path_list.append(tr_file.name)
        # 返回list(多个路径)中，所有path共有的最长的路径
        return os.path.join(save_path, os.path.commonprefix(path_list))

    # 读取当前任务列表
    def get_transmission_tasks(self):
        # 读取transmission列表
        torrents = self.trc.get_torrents()
        path_list = []
        for torrent in torrents:
            log.debug(torrent.name + "：" + torrent.status)
            # 3.0版本以下的Transmission没有labels
            label = ""
            handlered_flag = False
            try:
                label = torrent.labels
            except Exception as e:
                log.warn("【TR】当前transmission版本可能过低，请安装3.0以上版本！")
            if label and "已整理" in label:
                handlered_flag = True
            if (torrent.status == "seeding" or torrent.status == "seed_pending") and not handlered_flag:
                true_path = self.__get_tr_download_path(torrent.download_dir, torrent.files())
                if self.__save_containerpath:
                    true_path = true_path.replace(str(self.__save_path), str(self.__save_containerpath))
                path_list.append(true_path + "|" + str(torrent.id))
        return path_list

    # 读取所有种子信息
    def get_transmission_torrents(self):
        # 读取transmission列表
        if not self.trc:
            return []
        torrents = self.trc.get_torrents()
        return torrents

    # 迁移完成后设置种子状态
    def set_tr_torrent_status(self, id_str):
        if not self.trc:
            return
        # 打标签
        self.trc.change_torrent(labels=["已整理"], ids=id_str)
        log.info("【TR】设置transmission种子标签成功！")

    # 处理transmission中的种子
    def transfer_transmission_task(self):
        # 处理所有任务
        torrents = self.get_transmission_torrents()
        for torrent in torrents:
            log.debug("【TR】" + torrent.name + "：" + torrent.status)
            if (torrent.status == "seeding" or torrent.status == "seed_pending") and "已整理" not in torrent.labels:
                true_path = self.__get_tr_download_path(torrent.download_dir, torrent.files())
                if self.__save_containerpath:
                    true_path = true_path.replace(str(self.__save_path), str(self.__save_containerpath))
                done_flag = self.media.transfer_media(in_from="Transmission", in_path=true_path)
                if done_flag:
                    self.set_tr_torrent_status(torrent.id)
                else:
                    log.error("【TR】%s 转移失败：" % torrent.name)

    # 添加transmission任务
    def add_transmission_torrent(self, turl, tpath):
        return self.trc.add_torrent(torrent=turl, download_dir=tpath)

        # 删除种子

    def delete_transmission_torrents(self, delete_file, ids):
        if not self.trc:
            return False
        return self.trc.remove_torrent(delete_data=delete_file, ids=ids)
