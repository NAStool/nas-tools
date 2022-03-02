# 定时更新themoviedb中正在上映的影片并下载预告让emby展示
import shutil
import sys
from datetime import datetime
import os
from subprocess import call
import log
from config import get_config, RMT_MEDIAEXT, RMT_MOVIETYPE, YOUTUBE_DL_CMD, HOT_TRAILER_INTERVAL_TOTAL
from functions import get_dir_files_by_ext, get_dir_files_by_name, system_exec_command, is_chinese
from message.send import Message
from rmt.media import Media


class HotTrailer:
    __runing_flag = False
    __media_config = None
    media = None
    message = None

    def __init__(self):
        config = get_config()
        self.__media_config = config.get('media', {})
        self.media = Media()
        self.message = Message()

    # 启动服务
    def run_schedule(self, refresh_flag=True):
        try:
            if self.__runing_flag:
                log.error("【RUN】hottrailers任务正在执行中...")
            else:
                self.run_hottrailer(refresh_flag)
        except Exception as err:
            self.__runing_flag = False
            log.error("【RUN】执行任务hottrailers出错：%s" % str(err))

    # 将预告目录中的预告片转移到电影目录，如果存在对应的电影了的话
    def transfer_trailers(self, in_path):
        # 读取配置
        movie_path = self.__media_config.get('movie_path')
        trailer_file_list = get_dir_files_by_ext(in_path, RMT_MEDIAEXT)
        if len(trailer_file_list) == 0:
            log.info("【HOT-TRAILER】%s 不存在预告片，删除目录..." % in_path)
            shutil.rmtree(in_path, ignore_errors=True)
            return
        for trailer_file in trailer_file_list:
            if not os.path.exists(trailer_file):
                log.warn("【HOT-TRAILER】%s 原文件不存在，跳过..." % trailer_file)
                continue
            trailer_file_dir = os.path.dirname(trailer_file)
            trailer_file_name = os.path.basename(trailer_file_dir)
            trailer_file_ext = os.path.splitext(trailer_file)[1]

            # 对应的电影名称
            dest_path = os.path.join(movie_path, trailer_file_name)
            movie_subtypedir = self.__media_config.get('movie_subtypedir', True)
            trans_files_flag = False
            if movie_subtypedir:
                # 启用了分类
                for movie_type in RMT_MOVIETYPE:
                    dest_path = os.path.join(movie_path, movie_type, trailer_file_name)
                    if os.path.exists(dest_path):
                        trans_files_flag = True
                        break
            else:
                if os.path.exists(dest_path):
                    trans_files_flag = True

            if trans_files_flag:
                log.info("【HOT-TRAILER】%s 进行转移..." % trailer_file_name)
                dest_file_list = get_dir_files_by_ext(dest_path, RMT_MEDIAEXT)
                for dest_movie_file in dest_file_list:
                    if dest_movie_file.find("-trailer.") != -1:
                        log.debug("【HOT-TRAILER】已找到预告片，跳过...")
                        continue
                    trailer_dest_file = os.path.splitext(dest_movie_file)[0] + "-trailer" + trailer_file_ext
                    if os.path.exists(trailer_dest_file):
                        log.info("【HOT-TRAILER】%s 文件已存在，跳过..." % trailer_dest_file)
                        continue
                    log.debug("【HOT-TRAILER】正在复制：%s 到 %s" % (trailer_file, trailer_dest_file))
                    call(["cp", trailer_file, trailer_dest_file])
                    log.info("【HOT-TRAILER】转移完成：%s" % trailer_dest_file)
                # 删除预告
                shutil.rmtree(trailer_file_dir, ignore_errors=True)
                log.warn("【HOT-TRAILER】%s已删除！" % trailer_file_dir)
            else:
                log.info("【HOT-TRAILER】%s 不存在对应电影，保留在预告目录..." % trailer_file_name)

    def run_hottrailer(self, refresh_flag=True):
        # 读取配置
        hottrailer_path = self.__media_config.get('hottrailer_path')
        movie_path = self.__media_config.get('movie_path')
        start_time = datetime.now()
        if refresh_flag and hottrailer_path:
            self.__runing_flag = True
            # 正在上映与即将上映
            playing_list = []
            log.info("【HOT-TRAILER】检索正在上映电影...")
            page = 1
            now_playing = self.media.get_moive_now_playing(page)
            now_playing_total = 0
            while len(now_playing) > 0 and now_playing_total < HOT_TRAILER_INTERVAL_TOTAL:
                now_playing_total = now_playing_total + len(now_playing)
                log.debug(">第 " + str(page) + " 页：" + str(now_playing_total))
                playing_list = playing_list + now_playing
                page = page + 1
                now_playing = self.media.get_moive_now_playing(page)
            log.info("【HOT-TRAILER】正在上映：" + str(now_playing_total))
            log.info("【HOT-TRAILER】检索即将上映电影...")
            page = 1
            upcoming = self.media.get_moive_upcoming(page)
            upcoming_total = 0
            while len(upcoming) > 0 and upcoming_total < HOT_TRAILER_INTERVAL_TOTAL:
                upcoming_total = upcoming_total + len(upcoming)
                log.debug(">第 %s 页：%s" % (str(page), str(upcoming_total)))
                playing_list = playing_list + upcoming
                page = page + 1
                upcoming = self.media.get_moive_upcoming(page)
            log.info("【HOT-TRAILER】即将上映：%s" % str(upcoming_total))

            # 检索和下载预告片
            total_count = 0
            fail_count = 0
            succ_count = 0
            notfound_count = 0
            for item in playing_list:
                total_count = total_count + 1
                try:
                    movie_id = item.id
                    movie_title = item.title
                    log.info("【HOT-TRAILER】开始下载：" + movie_title + "...")
                    if not is_chinese(movie_title):
                        log.info("【HOT-TRAILER】" + movie_title + " 没有中文看不懂，跳过...")
                        continue
                    movie_year = item.release_date[0:4]
                    log.info(str(total_count) + "、电影：" + str(movie_id) + " - " + movie_title)
                    trailer_dir = hottrailer_path + "/" + movie_title + " (" + movie_year + ")"
                    file_path = trailer_dir + "/" + movie_title + " (" + movie_year + ").%(ext)s"
                    if os.path.exists(trailer_dir):
                        log.info("【HOT-TRAILER】" + movie_title + " 预告目录已存在，跳过...")
                        continue
                    exists_flag = False
                    movie_subtypedir = self.__media_config.get('movie_subtypedir', True)
                    if movie_subtypedir:
                        for movie_type in RMT_MOVIETYPE:
                            movie_dir = os.path.join(movie_path, movie_type, movie_title + " (" + movie_year + ")")
                            exists_trailers = get_dir_files_by_name(movie_dir, "-trailer.")
                            if len(exists_trailers) > 0:
                                exists_flag = True
                                break
                    else:
                        movie_dir = os.path.join(movie_path, movie_title + " (" + movie_year + ")")
                        exists_trailers = get_dir_files_by_name(movie_dir, "-trailer.")
                        if len(exists_trailers) > 0:
                            exists_flag = True

                    if exists_flag:
                        log.info("【HOT-TRAILER】%s 电影目录已存在预告片，跳过..." % movie_title)
                        continue
                    # 开始下载
                    try:
                        movie_videos = self.media.get_moive_metainfo(movie_id, 'en-US')
                    except Exception as err:
                        log.error("【HOT-TRAILER】错误：%s" % str(err))
                        continue
                    log.info("【HOT-TRAILER】%s 预告片总数：%s" % (movie_title, str(len(movie_videos))))
                    if len(movie_videos) > 0:
                        succ_flag = False
                        for video in movie_videos:
                            trailer_key = video.key
                            log.debug(">下载：" + trailer_key)
                            exec_cmd = YOUTUBE_DL_CMD.replace("$PATH", file_path).replace("$KEY", trailer_key)
                            log.debug(">开始执行命令：" + exec_cmd)
                            # 获取命令结果
                            result_err, result_out = system_exec_command(exec_cmd, 600)
                            if result_err:
                                log.error("【HOT-TRAILER】" + movie_title + "-" + trailer_key + " 下载失败：" + result_err)
                            if result_out:
                                log.info("【HOT-TRAILER】" + movie_title + " 下载完成：" + result_out)
                            if result_err != "":
                                continue
                            else:
                                succ_flag = True
                                break
                        if succ_flag:
                            succ_count = succ_count + 1
                        else:
                            fail_count = fail_count + 1
                            shutil.rmtree(trailer_dir, ignore_errors=True)
                    else:
                        notfound_count = notfound_count + 1
                        log.info("【HOT-TRAILER】" + movie_title + " 未检索到预告片")
                except Exception as err:
                    log.error("【HOT-TRAILER】错误：" + str(err))
            # 发送消息
            end_time = datetime.now()
            self.message.sendmsg("【HotTrialer】电影预告更新完成", "耗时：%s 秒\n\n总数：%s\n\n完成：%s\n\n未找到：%s\n\n出错：%s" % (
                str((end_time - start_time).seconds),
                str(total_count),
                str(succ_count),
                str(notfound_count),
                str(fail_count)))

        log.info("【HOT-TRAILER】开始转移存量预告片...")
        trailer_dir_list = os.listdir(hottrailer_path)
        for trailer_dir in trailer_dir_list:
            trailer_dir = os.path.join(hottrailer_path, trailer_dir)
            if os.path.isdir(trailer_dir):
                self.transfer_trailers(trailer_dir)
        log.info("【HOT-TRAILER】存量预告片转移完成！")
        self.__runing_flag = False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        flag = sys.argv[1] == "T" or False
    else:
        flag = False
    HotTrailer().run_schedule(flag)
