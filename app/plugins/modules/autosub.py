import os
import re
import subprocess
import tempfile
import time
import traceback

import iso639
import srt

import log
from app.helper import FfmpegHelper
from app.helper.openai_helper import OpenAiHelper
from app.plugins.modules._base import _IPluginModule
from app.utils import SystemUtils
from config import RMT_MEDIAEXT


class AutoSub(_IPluginModule):
    # 插件名称
    module_name = "AI字幕自动生成"
    # 插件描述
    module_desc = "使用whisper自动生成视频文件字幕。"
    # 插件图标
    module_icon = "autosubtitles.jpeg"
    # 主题色
    module_color = "bg-cyan"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "olly"
    # 插件配置项ID前缀
    module_config_prefix = "autosub"
    # 加载顺序
    module_order = 21
    # 可使用的用户级别
    auth_level = 2

    # 私有属性
    _running = False

    def __init__(self):
        self.additional_args = '-t 4 -p 1'
        self.translate_zh = False
        self.translate_only = False
        self.whisper_model = None
        self.whisper_main = None
        self.file_size = None
        self.process_count = 0
        self.skip_count = 0
        self.fail_count = 0
        self.success_count = 0

    @staticmethod
    def get_fields():
        return [
            # 同一板块
            {
                'type': 'div',
                'content': [
                    # 同一行
                    [
                        {
                            'title': 'whisper.cpp路径',
                            'required': "required",
                            'tooltip': '填写whisper.cpp主程序路径，如/config/plugin/autosub/main',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'whisper_main',
                                    'placeholder': 'whisper.cpp主程序路径'
                                }
                            ]
                        }
                    ],
                    # 模型路径
                    [
                        {
                            'title': 'whisper.cpp模型路径',
                            'required': "required",
                            'tooltip': '填写whisper.cpp模型路径，如/config/plugin/autosub/models/ggml-base.en.bin，'
                                       '可从https://github.com/ggerganov/whisper.cpp/tree/master/models处下载',
                            'type': 'text',
                            'content':
                                [{
                                    'id': 'whisper_model',
                                    'placeholder': 'whisper.cpp模型路径'
                                }]
                        }
                    ],
                    # 文件大小
                    [
                        {
                            'title': '文件大小（MB）',
                            'required': "required",
                            'tooltip': '单位 MB, 大于该大小的文件才会进行字幕生成',
                            'type': 'text',
                            'content':
                                [{
                                    'id': 'file_size',
                                    'placeholder': '文件大小, 单位MB'
                                }]
                        }
                    ],
                    [
                        {
                            'title': '媒体路径',
                            'required': '',
                            'tooltip': '要进行字幕生成的路径，每行一个路径，请确保路径正确',
                            'type': 'textarea',
                            'content':
                                {
                                    'id': 'path_list',
                                    'placeholder': '文件路径',
                                    'rows': 5
                                }
                        }
                    ],
                    [
                        {
                            'title': '立即运行一次',
                            'required': "",
                            'tooltip': '打开后立即运行一次',
                            'type': 'switch',
                            'id': 'run_now',
                        },
                        {
                            'title': '翻译为中文',
                            'required': "",
                            'tooltip': '打开后将自动翻译非中文字幕，生成双语字幕，关闭后只生成英文字幕，需要配置OpenAI API Key',
                            'type': 'switch',
                            'id': 'translate_zh',
                        },
                        {
                            'title': '仅已有字幕翻译',
                            'required': "",
                            'tooltip': '打开后仅翻译已有字幕，不做语音识别，关闭后将自动识别语音并生成字幕',
                            'type': 'switch',
                            'id': 'translate_only',
                        }
                    ]
                ]
            },
            {
                'type': 'details',
                'summary': '高级参数',
                'tooltip': 'whisper.cpp的高级参数，请勿随意修改',
                'content': [
                    [
                        {
                            'required': "",
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'additional_args',
                                    'placeholder': '-t 4 -p 1'
                                }
                            ]
                        }
                    ]
                ]
            }
        ]

    def init_config(self, config=None):
        # 如果没有配置信息， 则不处理
        if not config:
            return

        # config.get('path_list') 用 \n 分割为 list 并去除重复值和空值
        path_list = list(set(config.get('path_list').split('\n')))
        # file_size 转成数字
        self.file_size = config.get('file_size')
        self.whisper_main = config.get('whisper_main')
        self.whisper_model = config.get('whisper_model')
        self.translate_zh = config.get('translate_zh', False)
        self.translate_only = config.get('translate_only', False)
        self.additional_args = config.get('additional_args', '-t 4 -p 1')

        run_now = config.get('run_now')
        if not run_now:
            return

        config['run_now'] = False
        self.update_config(config)

        # 如果没有配置信息， 则不处理
        if not path_list or not self.file_size or not self.whisper_main or not self.whisper_model:
            log.info(f"【Plugin】自动字幕生成 配置信息不完整，不进行处理")
            return

        if not os.path.exists(self.whisper_main):
            log.info(f"【Plugin】自动字幕生成 whisper.cpp主程序不存在，不进行处理")
            return

        if not os.path.exists(self.whisper_model):
            log.info(f"【Plugin】自动字幕生成 whisper.cpp模型文件不存在，不进行处理")
            return

        # 校验扩展参数是否包含异常字符
        if self.additional_args and re.search(r'[\s;|&]', self.additional_args):
            log.info(f"【Plugin】自动字幕生成 扩展参数包含异常字符，不进行处理")
            return

        # 校验文件大小是否为数字
        if not self.file_size.isdigit():
            log.info(f"【Plugin】自动字幕生成 文件大小不是数字，不进行处理")
            return

        if self._running:
            log.info(f"【Plugin】自动字幕生成 上一次任务还未完成，不进行处理")
            return

        # 依次处理每个目录
        try:
            self._running = True
            self.success_count = self.skip_count = self.fail_count = self.process_count = 0
            for path in path_list:
                log.info(f"【Plugin】自动字幕生成 开始处理目录：{path}")
                # 如果目录不存在， 则不处理
                if not os.path.exists(path):
                    log.info(f"【Plugin】自动字幕生成 目录不存在，不进行处理")
                    continue

                # 如果目录不是文件夹， 则不处理
                if not os.path.isdir(path):
                    log.info(f"【Plugin】自动字幕生成 目录不是文件夹，不进行处理")
                    continue

                # 如果目录不是绝对路径， 则不处理
                if not os.path.isabs(path):
                    log.info(f"【Plugin】自动字幕生成 目录不是绝对路径，不进行处理")
                    continue

                # 处理目录
                self.__process_folder_subtitle(path)
        except Exception as e:
            log.info(f"【Plugin】自动字幕生成 处理异常: {e}")
        finally:
            log.info(f"【Plugin】自动字幕生成 处理完成: "
                     f"成功{self.success_count} / 跳过{self.skip_count} / 失败{self.fail_count} / 共{self.process_count}")
            self._running = False

    def __process_folder_subtitle(self, path):
        """
        处理目录字幕
        :param path:
        :return:
        """
        # 获取目录媒体文件列表
        for video_file in self.__get_library_files(path):
            if not video_file:
                continue
            # 如果文件大小小于指定大小， 则不处理
            if os.path.getsize(video_file) < int(self.file_size):
                continue

            self.process_count += 1
            try:
                # 判断目的字幕（和内嵌）是否已存在
                if self.__target_subtitle_exists(video_file):
                    log.info(f"【Plugin】自动字幕生成 字幕文件已经存在，不进行处理")
                    self.skip_count += 1
                    continue
                file_name, file_ext = os.path.splitext(video_file)

                log.info(f"【Plugin】自动字幕生成 开始处理文件：{video_file}")
                # 生成字幕
                ret, lang = self.__generate_subtitle(video_file, file_name, self.translate_only)
                if not ret:
                    if self.translate_only:
                        self.skip_count += 1
                    else:
                        self.fail_count += 1
                    continue

                if self.translate_zh:
                    # 翻译字幕
                    log.info(f"【Plugin】自动字幕生成 开始翻译字幕")
                    self.__translate_zh_subtitle(f"{file_name}.{lang}.srt", f"{file_name}.zh.srt")
                    log.info(f"【Plugin】自动字幕生成 翻译字幕完成：{file_name}.zh.srt")

                self.success_count += 1
            except Exception as e:
                log.error(f"【Plugin】自动字幕生成 处理异常：{e}")
                # 打印调用栈
                traceback.print_exc()
                self.fail_count += 1

    def __generate_subtitle(self, video_file, subtitle_file, only_extract=False):
        """
        生成字幕
        :param video_file: 视频文件
        :param subtitle_file: 字幕文件, 不包含后缀
        :return: 生成成功返回True，字幕语言，否则返回False, None
        """
        # 获取视频文件音轨信息
        ret, audio_index, audio_lang = self.__get_video_prefer_audio(video_file)
        if not ret:
            return False, None
        if not iso639.find(audio_lang) or not iso639.to_iso639_1(audio_lang):
            log.info(f"【Plugin】自动字幕生成 未知语言音轨")
            audio_lang = 'auto'
        else:
            # 外挂字幕文件存在， 则不处理
            exist, lang = self.__external_subtitle_exists(video_file, audio_lang)
            if exist:
                log.info(f"【Plugin】自动字幕生成 外挂字幕文件已经存在，使用已有字幕文件，字幕语言 {lang}")
                return True, iso639.to_iso639_1(audio_lang)
            # 获取视频文件字幕信息
            ret, subtitle_index, subtitle_lang = self.__get_video_prefer_subtitle(video_file, audio_lang)
            if ret and audio_lang == subtitle_lang:
                # 如果音轨和字幕语言一致， 则直接提取字幕
                log.info(f"【Plugin】自动字幕生成 提取内嵌字幕")
                audio_lang = iso639.to_iso639_1(audio_lang)
                FfmpegHelper().extract_subtitle_from_video(video_file,
                                                           f"{subtitle_file}.{audio_lang}.srt", subtitle_index)
                return True, audio_lang
            audio_lang = iso639.to_iso639_1(audio_lang)

        if only_extract:
            log.info(f"【Plugin】自动字幕生成 未开启语音识别，且无已有字幕文件，跳过后续处理")
            return False, None

        # 清理异常退出的临时文件
        tempdir = tempfile.gettempdir()
        for file in os.listdir(tempdir):
            if file.startswith('autosub-'):
                os.remove(os.path.join(tempdir, file))

        with tempfile.NamedTemporaryFile(prefix='autosub-', suffix='.wav', delete=True) as audio_file:
            # 提取音频
            log.info(f"【Plugin】自动字幕生成 提取音频：{audio_file.name}")
            FfmpegHelper().extract_wav_from_video(video_file, audio_file.name, audio_index)
            log.info(f"【Plugin】自动字幕生成 提取音频完成：{audio_file.name}")

            # 生成字幕
            command = [self.whisper_main] + self.additional_args.split()
            command += ['-l', audio_lang, '-m', self.whisper_model, '-osrt', '-of', audio_file.name, audio_file.name]
            log.info(f"【Plugin】自动字幕生成 开始生成字幕, lang {audio_lang}")
            ret = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if ret.returncode == 0:
                # 从output中获取语言 "whisper_full_with_state: auto-detected language: en (p = 0.973642)"
                output = ret.stdout.decode('utf-8') if ret.stdout else ""
                lang = re.search(r"auto-detected language: (\w+)", output)
                if lang and lang.group(1):
                    lang = lang.group(1)
                else:
                    lang = "en"
                log.info(f"【Plugin】自动字幕生成 生成字幕成功，原始语言：{lang}")
                # 复制字幕文件
                SystemUtils.copy(f"{audio_file.name}.srt", f"{subtitle_file}.{lang}.srt")
                log.info(f"【Plugin】自动字幕生成 复制字幕文件：{subtitle_file}.{lang}.srt")
                # 删除临时文件
                os.remove(f"{audio_file.name}.srt")
                return True, lang
            else:
                log.info(f"【Plugin】自动字幕生成 生成字幕失败")
                return False, None

    @staticmethod
    def __get_library_files(in_path, exclude_path=None):
        """
        获取目录媒体文件列表
        """
        if not os.path.isdir(in_path):
            yield in_path
            return

        for root, dirs, files in os.walk(in_path):
            if exclude_path and any(os.path.abspath(root).startswith(os.path.abspath(path))
                                    for path in exclude_path.split(",")):
                continue

            for file in files:
                cur_path = os.path.join(root, file)
                # 检查后缀
                if os.path.splitext(file)[-1].lower() in RMT_MEDIAEXT:
                    yield cur_path

    @staticmethod
    def __load_srt(file_path):
        """
        加载字幕文件
        :param file_path: 字幕文件路径
        :return:
        """
        with open(file_path, 'r', encoding="utf8") as f:
            srt_text = f.read()
        return list(srt.parse(srt_text))

    @staticmethod
    def __save_srt(file_path, srt_data):
        """
        保存字幕文件
        :param file_path: 字幕文件路径
        :param srt_data: 字幕数据
        :return:
        """
        with open(file_path, 'w', encoding="utf8") as f:
            f.write(srt.compose(srt_data))

    @staticmethod
    def __get_video_prefer_audio(video_file, prefer_lang=None):
        """
        获取视频的首选音轨，如果有多音轨， 优先指定语言音轨，否则获取默认音轨
        :param video_file:
        :return:
        """
        # 获取视频元数据，判断多音轨，及其音轨语言
        video_meta = FfmpegHelper().get_video_metadata(video_file)
        if not video_meta:
            log.info(f"【Plugin】自动字幕生成 获取视频元数据失败")
            return False, None, None

        if type(prefer_lang) == str and prefer_lang:
            prefer_lang = [prefer_lang]

        # 获取首选音轨
        audio_lang = None
        audio_index = None
        audio_stream = filter(lambda x: x.get('codec_type') == 'audio', video_meta.get('streams', []))
        for index, stream in enumerate(audio_stream):
            if not audio_index:
                audio_index = index
                audio_lang = stream.get('tags', {}).get('language')
            # 获取默认音轨
            if stream.get('disposition', {}).get('default'):
                audio_index = index
                audio_lang = stream.get('tags', {}).get('language')
            # 获取指定语言音轨
            if prefer_lang and stream.get('tags', {}).get('language') in prefer_lang:
                audio_index = index
                audio_lang = stream.get('tags', {}).get('language')
                break

        # 如果没有音轨， 则不处理
        if audio_index is None:
            log.info(f"【Plugin】自动字幕生成 没有音轨，不进行处理")
            return False, None, None

        log.info(f"【Plugin】自动字幕生成 选中音轨信息：{audio_index}, {audio_lang}")
        return True, audio_index, audio_lang

    @staticmethod
    def __get_video_prefer_subtitle(video_file, prefer_lang=None):
        """
        获取视频的首选字幕，如果有多字幕， 优先指定语言字幕， 否则获取默认字幕
        :param video_file:
        :return:
        """
        # 获取视频元数据，获取内嵌字幕，及其字幕语言
        video_meta = FfmpegHelper().get_video_metadata(video_file)
        if not video_meta:
            log.info(f"【Plugin】自动字幕生成 获取视频元数据失败")
            return False, None, None

        if type(prefer_lang) == str and prefer_lang:
            prefer_lang = [prefer_lang]

        # 获取首选字幕
        subtitle_lang = None
        subtitle_index = None
        subtitle_stream = filter(lambda x: x.get('codec_type') == 'subtitle', video_meta.get('streams', []))
        for index, stream in enumerate(subtitle_stream):
            # 如果是强制字幕，则跳过
            if stream.get('disposition', {}).get('forced'):
                continue

            if not subtitle_index:
                subtitle_index = index
                subtitle_lang = stream.get('tags', {}).get('language')
            # 获取默认字幕
            if stream.get('disposition', {}).get('default'):
                subtitle_index = index
                subtitle_lang = stream.get('tags', {}).get('language')
            # 获取指定语言字幕
            if prefer_lang and stream.get('tags', {}).get('language') in prefer_lang:
                subtitle_index = index
                subtitle_lang = stream.get('tags', {}).get('language')
                break

        # 如果没有字幕， 则不处理
        if subtitle_index is None:
            log.debug(f"【Plugin】自动字幕生成 没有内嵌字幕")
            return False, None, None

        log.debug(f"【Plugin】自动字幕生成 命中内嵌字幕信息：{subtitle_index}, {subtitle_lang}")
        return True, subtitle_index, subtitle_lang

    def __translate_zh_subtitle(self, source_subtitle, dest_subtitle):
        """
        调用OpenAI 翻译字幕
        :param source_subtitle:
        :param dest_subtitle:
        :return:
        """
        # 读取字幕文件
        srt_data = self.__load_srt(source_subtitle)
        for item in srt_data:
            # 跳过空行和无意义的字幕
            if not item.content and not item.content.strip():
                continue
            content = item.content.strip()
            if content.startswith('[') and content.endswith(']'):
                continue
            if content.startswith('(') and content.endswith(')'):
                continue
            # 调用OpenAI翻译
            # 免费OpenAI Api Limit: 20 / minute
            ret, result = OpenAiHelper().translate_to_zh(item.content)
            if not ret:
                if "Rate limit reached" in result:
                    log.info(f"【Plugin】自动字幕生成 OpenAI Api Rate limit reached, sleep 60s")
                    time.sleep(60)
                    # 重试
                    ret, result = OpenAiHelper().translate_to_zh(item.content)
                else:
                    continue

            if not ret or not result:
                continue
            item.content += '\n' + result

        # 保存字幕文件
        self.__save_srt(dest_subtitle, srt_data)

    def __external_subtitle_exists(self, video_file, prefer_langs=None):
        """
        外部字幕文件是否存在
        :param video_file:
        :return:
        """
        video_dir, video_name = os.path.split(video_file)
        video_name, video_ext = os.path.splitext(video_name)

        if type(prefer_langs) == str and prefer_langs:
            prefer_langs = [prefer_langs]

        for subtitle_lang in prefer_langs:
            dest_subtitle = os.path.join(video_dir, f"{video_name}.{subtitle_lang}.srt")
            if os.path.exists(dest_subtitle):
                return True, subtitle_lang

        return False, None

    def __target_subtitle_exists(self, video_file):
        """
        目标字幕文件是否存在
        :param video_file:
        :return:
        """
        if self.translate_zh:
            prefer_langs = ['zh', 'chi']
        else:
            prefer_langs = ['en', 'eng']

        exist, lang = self.__external_subtitle_exists(video_file, prefer_langs)
        if exist:
            return True

        ret, subtitle_index, subtitle_lang = self.__get_video_prefer_subtitle(video_file, prefer_lang=prefer_langs)
        if ret and subtitle_lang in prefer_langs:
            return True

        return False

    def get_state(self):
        return False

    def stop_service(self):
        """
        退出插件
        """
        pass
