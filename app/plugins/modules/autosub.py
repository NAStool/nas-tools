import os
import re
import subprocess
import tempfile
import time

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

    def __init__(self):
        self.additional_args = '-t 4 -p 1'
        self.translate_zh = False
        self.translate_only = False
        self.whisper_model = None
        self.whisper_main = None
        self.file_size = None

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
                            'tooltip': '打开后立即运行一次（点击此对话框的确定按钮后即会运行），关闭后触发运行的任务如果在运行中也会停止',
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
                            'title': '仅英文字幕翻译',
                            'required': "",
                            'tooltip': '打开后仅翻译已有英文字幕，不做语音识别，关闭后将自动识别语音并生成英文字幕',
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

        # 依次处理每个目录
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

            log.info(f"【Plugin】自动字幕生成 处理完成。")

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

            file_name, file_ext = os.path.splitext(video_file)
            subtitle_path = f"{file_name}.en.srt"
            # 如果字幕文件已存在， 则不处理
            if self.translate_zh:
                subtitle_path = f"{file_name}.zh.srt"
            if os.path.exists(subtitle_path):
                continue

            log.info(f"【Plugin】自动字幕生成 开始处理文件：{video_file}")
            if not self.translate_only:
                # 生成字幕
                ret, lang = self.__generate_subtitle(video_file, file_name)
                if not ret:
                    continue
            else:
                # 只翻译字幕，默认英文
                lang = 'en'
                if not os.path.exists(f"{file_name}.{lang}.srt"):
                    log.info(f"【Plugin】自动字幕生成 原始字幕文件不存在，不进行处理")
                    continue

            if self.translate_zh:
                # 翻译字幕
                log.info(f"【Plugin】自动字幕生成 开始翻译字幕")
                self.__translate_zh_subtitle(f"{file_name}.{lang}.srt", f"{file_name}.zh.srt")
                log.info(f"【Plugin】自动字幕生成 翻译字幕完成：{file_name}.zh.srt")

    def __generate_subtitle(self, video_file, subtitle_file):
        """
        生成字幕
        :param video_file: 视频文件
        :param subtitle_file: 字幕文件, 不包含后缀
        :return: 生成成功返回True，字幕语言，否则返回False, None
        """
        # 导出音频到临时文件
        with tempfile.NamedTemporaryFile(prefix='autosub-', suffix='.wav', delete=True) as audio_file:
            # 提取音频
            log.info(f"【Plugin】自动字幕生成 提取音频：{audio_file.name}")
            FfmpegHelper().extract_wav_from_video(video_file, audio_file.name)
            log.info(f"【Plugin】自动字幕生成 提取音频完成：{audio_file.name}")

            # 生成字幕
            command = [self.whisper_main] + self.additional_args.split()
            command += ['-l', 'auto', '-m', self.whisper_model, '-osrt', '-of', audio_file.name, audio_file.name]
            log.info(f"【Plugin】自动字幕生成 生成字幕")
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

    def get_state(self):
        return False

    def stop_service(self):
        """
        退出插件
        """
        pass
