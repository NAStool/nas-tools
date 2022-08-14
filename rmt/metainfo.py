import re

from rmt.meta.metaanime import MetaAnime
from rmt.meta.metavideo import MetaVideo
from utils.types import MediaType


def MetaInfo(title, subtitle=None, mtype=None):
    """
    媒体整理入口，根据名称和副标题，判断是哪种类型的识别，返回对应对象
    :param title: 标题、种子名、文件名
    :param subtitle: 副标题、描述
    :param mtype: 指定识别类型，为空则自动识别类型
    :return: MetaAnime、MetaVideo
    """
    if mtype == MediaType.ANIME or is_anime(title):
        return MetaAnime(title, subtitle)
    else:
        return MetaVideo(title, subtitle)


def is_anime(name):
    """
    判断是否为动漫
    :param name: 名称
    :return: 是否动漫
    """
    if not name:
        return False
    if re.search(r"S\d{2}\s*-\s*S\d{2}|S\d{2}|\s+S\d{1,2}|EP?\d{2,4}\s*-\s*EP?\d{2,4}|EP?\d{2,4}|\s+EP?\d{1,4}", name, re.IGNORECASE):
        return False
    if re.search(r'\[[0-9XVPI-]+]\[', name, re.IGNORECASE):
        return True
    if re.search(r'【[0-9XVPI-]+】【', name, re.IGNORECASE):
        return True
    if re.search(r'\s+-\s+[\dv]{1,4}\s+', name, re.IGNORECASE):
        return True
    return False
