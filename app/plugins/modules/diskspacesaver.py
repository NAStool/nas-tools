import datetime
import hashlib
import json
import os

from app.plugins.modules._base import _IPluginModule
from app.utils import SystemUtils


class DiskSpaceSaver(_IPluginModule):
    # 插件名称
    module_name = "磁盘空间释放"
    # 插件描述
    module_desc = "计算文件SHA1，同磁盘下相同SHA1的文件只保留一个，其他的用硬链接替换。"
    # 插件图标
    module_icon = "diskusage.jpg"
    # 主题色
    module_color = "#FE9003"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "link2fun"
    # 作者主页
    author_url = "https://github.com/link2fun"
    # 插件配置项ID前缀
    module_config_prefix = "diskspace_saver_"
    # 加载顺序
    module_order = 13
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _path = ''
    _size = 100

    @staticmethod
    def get_fields():
        return [
            # 同一板块
            {
                'type': 'div',
                'content': [
                    # 文件后缀
                    [
                        {
                            'title': '文件后缀',
                            'required': "required",
                            'tooltip': '只识别这些后缀的文件，多个后缀用英文逗号隔开，如：.mkv,.mp4',
                            'type': 'text',
                            'content':
                                [{
                                    'id': 'ext_list',
                                    'placeholder': '文件后缀, 多个后缀用英文逗号隔开'
                                }]
                        },
                        {
                            'title': '文件大小（MB）',
                            'required': "required",
                            'tooltip': '单位 MB, 大于该大小的文件才会进行SHA1计算',
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
                            'title': '磁盘目录(目录下的文件应均属于同一个分区)',
                            'required': '',
                            'tooltip': '要进行SHA1计算的文件路径，每行一个路径，请确保路径正确 且路径下均属于同一个磁盘分区',
                            'type': 'textarea',
                            'content':
                                {
                                    'id': 'path_list',
                                    'placeholder': '每行一个路径',
                                    'rows': 5
                                }
                        }
                    ],
                    [
                        {
                            'title': '立即运行一次',
                            'required': "",
                            'tooltip': '目前不支持定时, 只有勾选了才会运行一次',
                            'type': 'switch',
                            'id': 'run_now',
                        },
                        {
                            'title': '仅查重',
                            'required': "",
                            'tooltip': '仅查重，不进行删除和硬链接替换',
                            'type': 'switch',
                            'id': 'dry_run',
                        },
                        {
                            'title': '快速模式',
                            'required': "",
                            'tooltip': '快速模式，不计算文件整体SHA1，只计算文件头部/中间/尾部的SHA1，速度快，但有可能会误判，请谨慎使用',
                            'type': 'switch',
                            'id': 'fast',
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
        file_size = config.get('file_size')
        # config.get('ext_list') 用 , 分割为 list 并去除重复值
        ext_list = list(set(config.get('ext_list').split(',')))
        result_path = os.path.join(self.get_data_path(), "sha1.json")
        # 兼容旧配置
        old_result_path = config.get("result_path")
        if old_result_path:
            del config["result_path"]
            if os.path.exists(old_result_path) and not os.path.exists(result_path):
                SystemUtils.move(old_result_path, result_path)

        dry_run = config.get('dry_run', False)
        fast = config.get('fast', False)

        run_now = config.get('run_now')
        if not run_now:
            return

        config['run_now'] = False
        self.update_config(config)

        # 如果没有配置信息， 则不处理
        if not path_list or not file_size or not ext_list or not result_path:
            self.info(f"磁盘空间释放配置信息不完整，不进行处理")
            return

        self.info(f"磁盘空间释放配置信息：{config}")

        # 依次处理每个目录
        for path in path_list:
            self.info(f"磁盘空间释放 开始处理目录：{path}")
            # 如果目录不存在， 则不处理
            if not os.path.exists(path):
                self.info(f"磁盘空间释放 目录不存在，不进行处理")
                continue

            # 如果目录不是文件夹， 则不处理
            if not os.path.isdir(path):
                self.info(f"磁盘空间释放 目录不是文件夹，不进行处理")
                continue

            # 如果目录不是绝对路径， 则不处理
            if not os.path.isabs(path):
                self.info(f"磁盘空间释放 目录不是绝对路径，不进行处理")
                continue

            _last_result = self.load_last_result(result_path)
            self.info(f"磁盘空间释放 加载上次处理结果，共有 {len(_last_result['file_info'])} 个文件。")
            _duplicates = self.find_duplicates(path, ext_list, int(file_size), _last_result, fast)
            self.info(f"磁盘空间释放 找到 {len(_duplicates)} 个重复文件。")
            self.process_duplicates(_duplicates, dry_run)
            self.info(f"磁盘空间释放 处理完毕。")
            self.save_last_result(result_path, _last_result)
            self.info(f"磁盘空间释放 保存处理结果。")

    def get_state(self):
        return False

    def stop_service(self):
        """
        退出插件
        """
        pass

    @staticmethod
    def get_sha1(file_path, buffer_size=128 * 1024, fast=False):
        """
        计算文件的 SHA1 值, fast 为 True 时读取文件前中后buffer_size大小的数据计算SHA1值
        """
        h = hashlib.sha1()
        buffer = bytearray(buffer_size)
        # using a memoryview so that we can slice the buffer without copying it
        buffer_view = memoryview(buffer)
        with open(file_path, 'rb', buffering=0) as f:
            if fast:
                # 获取文件大小
                file_size = os.path.getsize(file_path)
                # 读取文件前buffer_size大小的数据计算SHA1值
                n = f.readinto(buffer)
                h.update(buffer_view[:n])
                # 读取文件中间buffer_size大小的数据计算SHA1值
                if file_size > buffer_size * 2:
                    f.seek(file_size // 2)
                    n = f.readinto(buffer)
                    h.update(buffer_view[:n])
                    # 读取文件后buffer_size大小的数据计算SHA1值
                    f.seek(-buffer_size, os.SEEK_END)
                    n = f.readinto(buffer)
                    h.update(buffer_view[:n])
            else:
                # 读取文件所有数据计算SHA1值
                for n in iter(lambda: f.readinto(buffer), 0):
                    h.update(buffer_view[:n])
        return h.hexdigest()

    def find_duplicates(self, folder_path, _ext_list, _file_size, last_result, fast=False):
        """
        查找重复的文件，返回字典，key 为文件的 SHA1 值，value 为文件路径的列表
        """
        duplicates = {}
        file_group_by_size = {}
        # 先进行依次过滤
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                file_ext = os.path.splitext(file_path)[1]
                file_size = os.path.getsize(file_path)
                if file_ext.lower() not in _ext_list:
                    continue

                if os.path.getsize(file_path) < _file_size * 1024 * 1024:
                    continue
                file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_group_by_size.get(file_size) is None:
                    file_group_by_size[file_size] = []

                file_group_by_size[file_size].append(
                    {'filePath': file_path, 'fileExt': file_ext, 'fileSize': file_size,
                     'fileModifyTime': str(file_mtime)})

        # 循环 file_group_by_size
        for file_size, file_list in file_group_by_size.items():
            # 如果文件数量大于1，进行sha1计算
            if len(file_list) <= 1:
                # 没有大小一样的 不需要处理
                self.debug(f'磁盘空间释放 {file_list[0]["filePath"]} 大小相同的文件数量为1，无需计算sha1')
                continue
            for file_info in file_list:
                file_path = file_info['filePath']
                file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                file_size = os.path.getsize(file_path)
                sha1 = None

                # 查找是否存在相同路径的文件
                for info in last_result['file_info']:
                    if file_path == info['filePath']:
                        # 如果文件大小和修改时间都一致，则直接使用之前计算的 sha1 值
                        if file_size == info['fileSize'] and str(file_mtime) == info['fileModifyTime']:
                            self.info(
                                f'磁盘空间释放 文件 {file_path} 的大小和修改时间与上次处理结果一致，直接使用上次处理结果')
                            sha1 = info['fileSha1']
                        break

                if sha1 is None:
                    self.info(f'磁盘空间释放 计算文件 {file_path} 的 SHA1 值')
                    sha1 = self.get_sha1(file_path, fast=fast)
                    file_info = {'filePath': file_path,
                                 'fileSize': file_size,
                                 'fileModifyTime': str(file_mtime),
                                 'fileSha1': sha1}
                    last_result['file_info'].append(file_info)

                if sha1 in duplicates:
                    duplicates[sha1].append(file_path)
                else:
                    duplicates[sha1] = [file_path]
        return duplicates

    def process_duplicates(self, duplicates, dry_run=False):
        """
        处理重复的文件，保留一个文件，其他的用硬链接替换
        """
        for sha1, files in duplicates.items():
            if len(files) > 1:

                for file_path in files[1:]:
                    stat_first = os.stat(files[0])
                    stat_compare = os.stat(file_path)
                    if stat_first.st_dev == stat_compare.st_dev:
                        if stat_first.st_ino == stat_compare.st_ino:
                            self.info(f'磁盘空间释放 文件 {files[0]} 和 {file_path} 是同一个文件，无需处理')
                        else:
                            if dry_run:
                                self.info(f'磁盘空间释放 文件 {files[0]} 和 {file_path} 是重复文件，dry_run中，不做处理')
                                continue
                            # 使用try catch
                            try:
                                # 先备份原文件
                                os.rename(file_path, file_path + '.bak')
                                # 用硬链接替换原文件
                                os.link(files[0], file_path)
                                # 删除备份文件
                                os.remove(file_path + '.bak')
                                self.info(f'磁盘空间释放 文件 {files[0]} 和 {file_path} 是重复文件，已用硬链接替换')
                            except Exception as err:
                                print(str(err))
                                # 如果硬链接失败，则将备份文件改回原文件名
                                os.rename(file_path + '.bak', file_path)
                                self.info(f'磁盘空间释放 文件 {files[0]} 和 {file_path} 是重复文件，'
                                          '硬链接替换失败，已恢复原文件')
                    else:
                        self.info(f'磁盘空间释放 文件 {files[0]} 和 {file_path} 不在同一个磁盘，无法用硬链接替换')
                        continue

    @staticmethod
    def load_last_result(last_result_path):
        """
        加载上次处理的结果
        """
        if os.path.exists(last_result_path):
            with open(last_result_path, 'r') as f:
                return json.load(f)
        else:
            return {'file_info': [], 'inode_info': []}

    @staticmethod
    def save_last_result(last_result_path, last_result):
        """
        保存处理结果到文件
        """
        with open(last_result_path, 'w') as f:
            json.dump(last_result, f)
