import os
import shutil

from lxml import etree

import log
from app.sites.sites import Sites
from app.sites.siteconf import SiteConf
from app.helper import SiteHelper
from app.utils import RequestUtils, StringUtils, PathUtils, ExceptionUtils
from config import Config, RMT_SUBEXT


class SiteSubtitle:

    siteconf = None
    sites = None
    _save_tmp_path = None

    def __init__(self):
        self.siteconf = SiteConf()
        self.sites = Sites()
        self._save_tmp_path = Config().get_temp_path()
        if not os.path.exists(self._save_tmp_path):
            os.makedirs(self._save_tmp_path)

    def download(self, media_info, site_id, cookie, ua, download_dir):
        """
        从站点下载字幕文件，并保存到本地
        """

        if not media_info.page_url:
            return
        # 字幕下载目录
        log.info("【Sites】开始从站点下载字幕：%s" % media_info.page_url)
        if not download_dir:
            log.warn("【Sites】未找到字幕下载目录")
            return

        # 站点流控
        if self.sites.check_ratelimit(site_id):
            return

        # 读取网站代码
        request = RequestUtils(cookies=cookie, headers=ua)
        res = request.get_res(media_info.page_url)
        if res and res.status_code == 200:
            if not res.text:
                log.warn(f"【Sites】读取页面代码失败：{media_info.page_url}")
                return
            html = etree.HTML(res.text)
            sublink_list = []
            for xpath in self.siteconf.get_subtitle_conf():
                sublinks = html.xpath(xpath)
                if sublinks:
                    for sublink in sublinks:
                        if not sublink:
                            continue
                        if not sublink.startswith("http"):
                            base_url = StringUtils.get_base_url(media_info.page_url)
                            if sublink.startswith("/"):
                                sublink = "%s%s" % (base_url, sublink)
                            else:
                                sublink = "%s/%s" % (base_url, sublink)
                        sublink_list.append(sublink)
            # 下载所有字幕文件
            for sublink in sublink_list:
                log.info(f"【Sites】找到字幕下载链接：{sublink}，开始下载...")
                # 下载
                ret = request.get_res(sublink)
                if ret and ret.status_code == 200:
                    # 创建目录
                    if not os.path.exists(download_dir):
                        os.makedirs(download_dir)
                    # 保存ZIP
                    file_name = SiteHelper.get_url_subtitle_name(ret.headers.get('content-disposition'), sublink)
                    if not file_name:
                        log.warn(f"【Sites】链接不是字幕文件：{sublink}")
                        continue
                    if file_name.lower().endswith(".zip"):
                        # ZIP包
                        zip_file = os.path.join(self._save_tmp_path, file_name)
                        # 解压路径
                        zip_path = os.path.splitext(zip_file)[0]
                        with open(zip_file, 'wb') as f:
                            f.write(ret.content)
                        # 解压文件
                        shutil.unpack_archive(zip_file, zip_path, format='zip')
                        # 遍历转移文件
                        for sub_file in PathUtils.get_dir_files(in_path=zip_path, exts=RMT_SUBEXT):
                            target_sub_file = os.path.join(download_dir,
                                                           os.path.splitext(os.path.basename(sub_file))[0])
                            log.info(f"【Sites】转移字幕 {sub_file} 到 {target_sub_file}")
                            SiteHelper.transfer_subtitle(sub_file, target_sub_file)
                        # 删除临时文件
                        try:
                            shutil.rmtree(zip_path)
                            os.remove(zip_file)
                        except Exception as err:
                            ExceptionUtils.exception_traceback(err)
                    else:
                        sub_file = os.path.join(self._save_tmp_path, file_name)
                        # 保存
                        with open(sub_file, 'wb') as f:
                            f.write(ret.content)
                        target_sub_file = os.path.join(download_dir,
                                                       os.path.splitext(os.path.basename(sub_file))[0])
                        log.info(f"【Sites】转移字幕 {sub_file} 到 {target_sub_file}")
                        SiteHelper.transfer_subtitle(sub_file, target_sub_file)
                else:
                    log.error(f"【Sites】下载字幕文件失败：{sublink}")
                    continue
            if sublink_list:
                log.info(f"【Sites】{media_info.page_url} 页面字幕下载完成")
            else:
                log.warn(f"【Sites】{media_info.page_url} 页面未找到字幕下载链接")
        elif res is not None:
            log.warn(f"【Sites】连接 {media_info.page_url} 失败，状态码：{res.status_code}")
        else:
            log.warn(f"【Sites】无法打开链接：{media_info.page_url}")
