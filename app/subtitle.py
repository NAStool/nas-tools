import os.path
import platform
import re
import shutil
from subprocess import call

import log
from app.helper.sub_helper import SubHelper
from config import Config, RMT_SUBEXT
from app.utils.commons import singleton
from app.utils import RequestUtils, PathUtils
from app.utils.types import MediaType


@singleton
class Subtitle:
    subhelper = None
    __save_tmp_path = None
    __server = None
    __host = None
    __api_key = None
    __remote_path = None
    __local_path = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.__save_tmp_path = os.path.join(Config().get_config_path(), "temp")
        if not os.path.exists(self.__save_tmp_path):
            os.makedirs(self.__save_tmp_path)
        subtitle = Config().get_config('subtitle')
        if subtitle:
            self.__server = subtitle.get("server")
            if self.__server == "chinesesubfinder":
                self.__api_key = subtitle.get("chinesesubfinder", {}).get("api_key")
                self.__host = subtitle.get("chinesesubfinder", {}).get('host')
                if self.__host:
                    if not self.__host.startswith('http'):
                        self.__host = "http://" + self.__host
                    if not self.__host.endswith('/'):
                        self.__host = self.__host + "/"
                self.__local_path = subtitle.get("chinesesubfinder", {}).get("local_path")
                self.__remote_path = subtitle.get("chinesesubfinder", {}).get("remote_path")
            else:
                self.subhelper = SubHelper()

    def download_subtitle(self, items):
        """
        字幕下载入口
        :param items: {"type":, "file", "file_ext":, "name":, "title", "year":, "season":, "episode":, "bluray":}
        """
        if not self.__server:
            return
        if not items:
            return
        if self.__server == "opensubtitles":
            self.__download_opensubtitles(items)
        elif self.__server == "chinesesubfinder":
            self.__download_chinesesubfinder(items)

    def search_opensubtitles(self, item):
        """
        爬取OpenSubtitles.org字幕
        """
        if not self.subhelper:
            return []
        return self.subhelper.search_subtitles(item)

    def __download_opensubtitles(self, items):
        """
        调用OpenSubtitles Api下载字幕
        """
        if not self.subhelper:
            return
        subtitles_cache = {}
        for item in items:
            if not item:
                continue
            if not item.get("name") or not item.get("file"):
                continue
            if item.get("type") == MediaType.TV and not item.get("imdbid"):
                log.warn("【Subtitle】电视剧类型需要imdbid检索字幕，跳过...")
                continue
            subtitles = subtitles_cache.get(item.get("name"))
            if subtitles is None:
                log.info("【Subtitle】开始从Opensubtitle.org检索字幕: %s" % item.get("name"))
                subtitles = self.search_opensubtitles(item)
                if not subtitles:
                    subtitles_cache[item.get("name")] = []
                    log.info("【Subtitle】%s 未检索到字幕" % item.get("name"))
                else:
                    subtitles_cache[item.get("name")] = subtitles
                    log.info("【Subtitle】opensubtitles.org返回数据：%s" % len(subtitles))
            if not subtitles:
                continue
            # 成功数
            subtitle_count = 0
            for subtitle in subtitles:
                # 标题
                if not item.get("imdbid"):
                    if str(subtitle.get('title')) != "%s (%s)" % (item.get("name"), item.get("year")):
                        continue
                # 季
                if item.get('season') \
                        and str(subtitle.get('season').replace("Season", "").strip()) != str(item.get('season')):
                    continue
                # 集
                if item.get('episode') \
                        and str(subtitle.get('episode')) != str(item.get('episode')):
                    continue
                # 字幕文件名
                SubFileName = subtitle.get('description')
                # 下载链接
                Download_Link = subtitle.get('link')
                # 下载后的字幕文件路径
                Media_File = "%s%s" % (item.get("file"), item.get("file_ext"))
                log.info("【Subtitle】正在从opensubtitles.org下载字幕 %s 到 %s " % (SubFileName, Media_File))
                # 下载
                ret = RequestUtils(cookies=self.subhelper.get_cookie(),
                                   headers=self.subhelper.get_ua()).get_res(Download_Link)
                if ret and ret.status_code == 200:
                    # 保存ZIP
                    file_name = re.findall(r"filename=\"(.+)\"", ret.headers.get('content-disposition'))[0]
                    zip_file = os.path.join(self.__save_tmp_path, file_name)
                    zip_path = os.path.splitext(zip_file)[0]
                    with open(zip_file, 'wb') as f:
                        f.write(ret.content)
                    # 解压文件
                    shutil.unpack_archive(zip_file, zip_path, format='zip')
                    # 遍历转移文件
                    for sub_file in PathUtils.get_dir_files(in_path=zip_path, exts=RMT_SUBEXT):
                        self.__transfer_subtitle(sub_file, Media_File)
                    # 删除临时文件
                    try:
                        shutil.rmtree(zip_path)
                        os.remove(zip_file)
                    except Exception as err:
                        print(str(err))
                else:
                    log.error("【Subtitle】下载字幕文件失败：%s" % Download_Link)
                    continue
                # 最多下载3个字幕
                subtitle_count += 1
                if subtitle_count > 2:
                    break
            if not subtitle_count:
                if item.get('episode'):
                    log.info("【Subtitle】%s 季：%s 集：%s 未找到符合条件的字幕" % (
                        item.get("name"), item.get("season"), item.get("episode")))
                else:
                    log.info("【Subtitle】%s 未找到符合条件的字幕" % item.get("name"))
            else:
                log.info("【Subtitle】%s 共下载 %s 个字幕" % (item.get("name"), subtitle_count))

    def __download_chinesesubfinder(self, items):
        """
        调用ChineseSubFinder下载字幕
        """
        if not self.__host or not self.__api_key:
            return
        req_url = "%sapi/v1/add-job" % self.__host
        notify_items = []
        for item in items:
            if not item:
                continue
            if not item.get("name") or not item.get("file"):
                continue
            if item.get("bluray"):
                file_path = "%s.mp4" % item.get("file")
            else:
                if os.path.splitext(item.get("file"))[-1] != item.get("file_ext"):
                    file_path = "%s%s" % (item.get("file"), item.get("file_ext"))
                else:
                    file_path = item.get("file")

            # 路径替换
            if self.__local_path and self.__remote_path and file_path.startswith(self.__local_path):
                file_path = file_path.replace(self.__local_path, self.__remote_path)

            # 一个名称只建一个任务
            if file_path not in notify_items:
                notify_items.append(file_path)
                log.info("【Subtitle】通知ChineseSubFinder下载字幕: %s" % file_path)
                params = {
                    "video_type": 0 if item.get("type") == MediaType.MOVIE else 1,
                    "physical_video_file_full_path": file_path,
                    "task_priority_level": 3,
                    "media_server_inside_video_id": "",
                    "is_bluray": item.get("bluray")
                }
                try:
                    res = RequestUtils(headers={"Authorization": "Bearer %s" % self.__api_key}).post(req_url,
                                                                                                     json=params)
                    if not res or res.status_code != 200:
                        log.error("【Subtitle】调用ChineseSubFinder API失败！")
                    else:
                        # 如果文件目录没有识别的nfo元数据， 此接口会返回控制符，推测是ChineseSubFinder的原因
                        # emby refresh元数据时异步的
                        if res.text:
                            job_id = res.json().get("job_id")
                            message = res.json().get("message")
                            if not job_id:
                                log.warn("【Subtitle】ChineseSubFinder下载字幕出错：%s" % message)
                            else:
                                log.info("【Subtitle】ChineseSubFinder任务添加成功：%s" % job_id)
                        else:
                            log.error("【Subtitle】%s 当前目录缺失nfo元数据：" % file_path)
                except Exception as e:
                    log.error("【Subtitle】连接ChineseSubFinder出错：" + str(e))

    @staticmethod
    def __transfer_subtitle(sub_file, media_file):
        """
        转移字幕
        """
        new_sub_file = "%s%s" % (os.path.splitext(media_file)[0], os.path.splitext(sub_file)[-1])
        if os.path.exists(new_sub_file):
            return 1
        else:
            if platform.system() == "Windows":
                return os.system('copy /Y "{}" "{}"'.format(sub_file, new_sub_file))
            else:
                return call(['cp', sub_file, new_sub_file])
