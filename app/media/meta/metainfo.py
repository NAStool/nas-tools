import os.path
import re

from app.media.meta.metaanime import MetaAnime
from app.media.meta.metavideo import MetaVideo
from app.utils.types import MediaType
from config import RMT_MEDIAEXT, Config


def MetaInfo(title, subtitle=None, mtype=None):
    """
    媒体整理入口，根据名称和副标题，判断是哪种类型的识别，返回对应对象
    :param title: 标题、种子名、文件名
    :param subtitle: 副标题、描述
    :param mtype: 指定识别类型，为空则自动识别类型
    :return: MetaAnime、MetaVideo
    """
    config = Config()
    ignored_words = config.get_config('laboratory').get("ignored_words").split("|")
    replaced_words = config.get_config('laboratory').get("replaced_words").split("|")
    if ignored_words:
        for ignored_word in ignored_words:
            title = title.replace(ignored_word, "")
    if replaced_words:
        for replaced_word in replaced_words:
            replaced_word_info = replaced_word.split("@")
            title = title.replace(replaced_word_info[0], replaced_word_info[-1])
    if os.path.splitext(title)[-1] in RMT_MEDIAEXT:
        fileflag = True
    else:
        fileflag = False
    if mtype == MediaType.ANIME or is_anime(title):
        return MetaAnime(title, subtitle, fileflag)
    else:
        return MetaVideo(title, subtitle, fileflag)


def is_anime(name):
    """
    判断是否为动漫
    :param name: 名称
    :return: 是否动漫
    """
    if not name:
        return False
    if re.search(r'【[+0-9XVPI-]+】\s*【', name, re.IGNORECASE):
        return True
    if re.search(r'\s+-\s+[\dv]{1,4}\s+', name, re.IGNORECASE):
        return True
    if re.search(r"S\d{2}\s*-\s*S\d{2}|S\d{2}|\s+S\d{1,2}|EP?\d{2,4}\s*-\s*EP?\d{2,4}|EP?\d{2,4}|\s+EP?\d{1,4}", name,
                 re.IGNORECASE):
        return False
    if re.search(r'\[[+0-9XVPI-]+]\s*\[', name, re.IGNORECASE):
        return True
    return False
