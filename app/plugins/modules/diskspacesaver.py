import datetime
import hashlib
import json
import os

import log
from app.plugins.modules._base import _IPluginModule


def get_sha1(file_path):
    """
    计算文件的 SHA1 值
    """
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(1024)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()


def find_duplicates(folder_path, _ext_list, _file_size, last_result):
    """
    查找重复的文件，返回字典，key 为文件的 SHA1 值，value 为文件路径的列表
    """
    duplicates = {}
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            file_ext = os.path.splitext(file_path)[1]
            allow_ext = _ext_list
            if file_ext.lower() not in allow_ext:
                continue
            if os.path.getsize(file_path) >= _file_size * 1024 * 1024:

                file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                file_size = os.path.getsize(file_path)
                sha1 = None

                # 查找是否存在相同路径的文件
                for file_info in last_result['file_info']:
                    if file_path == file_info['filePath']:
                        # 如果文件大小和修改时间都一致，则直接使用之前计算的 sha1 值
                        if file_size == file_info['fileSize'] and str(file_mtime) == file_info['fileModifyTime']:
                            log.info(
                                '【Plugin】磁盘空间释放 文件 {} 的大小和修改时间与上次处理结果一致，直接使用上次处理结果'.format(file_path))
                            sha1 = file_info['fileSha1']
                        break

                if sha1 is None:
                    log.info('【Plugin】磁盘空间释放 计算文件 {} 的 SHA1 值'.format(file_path))
                    sha1 = get_sha1(file_path)
                    file_info = {'filePath': file_path, 'fileSize': file_size, 'fileModifyTime': str(file_mtime),
                                 'fileSha1': sha1}
                    last_result['file_info'].append(file_info)

                if sha1 in duplicates:
                    duplicates[sha1].append(file_path)
                else:
                    duplicates[sha1] = [file_path]

    return duplicates


def process_duplicates(duplicates):
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
                        log.info('【Plugin】磁盘空间释放 文件 {} 和 {} 是同一个文件，无需处理'.format(files[0], file_path))
                    else:
                        os.remove(file_path)
                        os.link(files[0], file_path)
                        log.info('【Plugin】磁盘空间释放 文件 {} 和 {} 是重复文件，已用硬链接替换'.format(files[0], file_path))
                else:
                    log.info('【Plugin】磁盘空间释放 文件 {} 和 {} 不在同一个磁盘，无法用硬链接替换'.format(files[0], file_path))
                    continue


def load_last_result(last_result_path):
    """
    加载上次处理的结果
    """
    if os.path.exists(last_result_path):
        with open(last_result_path, 'r') as f:
            return json.load(f)
    else:
        return {'file_info': [], 'inode_info': []}


def save_last_result(last_result_path, last_result):
    """
    保存处理结果到文件
    """
    with open(last_result_path, 'w') as f:
        json.dump(last_result, f)


class DiskSpaceSaver(_IPluginModule):
    # 插件名称
    module_name = "磁盘空间释放"
    # 插件描述
    module_desc = "计算文件SHA1，同磁盘下相同SHA1的文件只保留一个，其他的用硬链接替换。"
    # 插件图标
    module_icon = "diskusage.jpg"
    # 主题色
    module_color = "bg-yellow"
    # 插件版本
    module_version = "1.0"
    # 插件作者
    module_author = "link2fun"
    # 插件配置项ID前缀
    module_config_prefix = "diskspace_saver_"
    # 加载顺序
    module_order = 20
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
                    # 同一行
                    [
                        {
                            'title': '文件SHA1信息存储路径(文件路径)',
                            'required': "required",
                            'tooltip': '如果是docker写容器内的路径，如果是宿主机写宿主机的路径，如 E:/temp/result.json',
                            'type': 'text',
                            'content': [
                                {
                                    'id': 'result_path',
                                    'placeholder': '文件SHA1信息存储路径'
                                }
                            ]
                        }
                    ],
                    # 文件后缀
                    [
                        {
                            'title': '文件后缀',
                            'required': "required",
                            'tooltip': '只识别这些后缀的文件，多个后缀用英文逗号隔开',
                            'type': 'text',
                            'content':
                                [{
                                    'id': 'ext_list',
                                    'placeholder': '文件后缀, 多个后缀用英文逗号隔开'
                                }]
                        }
                    ],
                    # 文件大小
                    [
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
                                    'placeholder': '文件路径',
                                    'rows': 5
                                }
                        }
                    ],
                    [
                        {
                            'title': '现在运行一次',
                            'required': "",
                            'tooltip': '目前不支持定时, 只有勾选了才会运行一次',
                            'type': 'switch',
                            'id': 'run_now',
                        }
                    ],
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
        result_path = config.get('result_path')

        run_now = config.get('run_now')
        if not run_now:
            return

        config['run_now'] = False
        self.update_config(config)

        # 如果没有配置信息， 则不处理
        if not path_list or not file_size or not ext_list or not result_path:
            log.info(f"【Plugin】磁盘空间释放配置信息不完整，不进行处理")
            return

        log.info(f"【Plugin】磁盘空间释放配置信息：{config}")

        # 依次处理每个目录
        for path in path_list:
            log.info(f"【Plugin】磁盘空间释放 开始处理目录：{path}")
            # 如果目录不存在， 则不处理
            if not os.path.exists(path):
                log.info(f"【Plugin】磁盘空间释放 目录不存在，不进行处理")
                continue

            # 如果目录不是文件夹， 则不处理
            if not os.path.isdir(path):
                log.info(f"【Plugin】磁盘空间释放 目录不是文件夹，不进行处理")
                continue

            # 如果目录不是绝对路径， 则不处理
            if not os.path.isabs(path):
                log.info(f"【Plugin】磁盘空间释放 目录不是绝对路径，不进行处理")
                continue

            _last_result = load_last_result(result_path)
            log.info(f"【Plugin】磁盘空间释放 加载上次处理结果，共有 {len(_last_result['file_info'])} 个文件。")
            _duplicates = find_duplicates(path, ext_list, int(file_size), _last_result)
            log.info(f"【Plugin】磁盘空间释放 找到 {len(_duplicates)} 个重复文件。")
            process_duplicates(_duplicates)
            log.info(f"【Plugin】磁盘空间释放 处理完毕。")
            save_last_result(result_path, _last_result)
            log.info(f"【Plugin】磁盘空间释放 保存处理结果。")

    def get_state(self):
        return False

    def stop_service(self):
        """
        退出插件
        """
        pass
