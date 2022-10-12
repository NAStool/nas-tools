import os.path
import regex as re

import log
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
    # 应用屏蔽词
    used_ignored_words = []
    # 应用替换词
    used_replaced_words = []
    # 应用集数偏移
    used_offset_words = []
    # 屏蔽词
    ignored_words = config.get_config('laboratory').get("ignored_words")
    if ignored_words:
        try:
            ignored_words = re.sub(r"\|\|", '|', ignored_words)
            ignored_words = re.compile(r'%s' % ignored_words)
            # 去重
            used_ignored_words = list(set(re.findall(ignored_words, title)))
            if used_ignored_words:
                title = re.sub(ignored_words, '', title)
        except Exception as err:
            log.error("【Meta】自定义屏蔽词设置有误：%s" % str(err))
    # 替换词
    replaced_words = config.get_config('laboratory').get("replaced_words")
    if replaced_words:
        replaced_words = replaced_words.split("||")
        for replaced_word in replaced_words:
            try:
                if not replaced_word:
                    continue
                replaced_word_info = replaced_word.split("@")
                if re.findall(r'%s' % replaced_word_info[0], title):
                    used_replaced_words.append(replaced_word)
                    title = re.sub(r'%s' % replaced_word_info[0], r'%s' % replaced_word_info[-1], title)
            except Exception as err:
                log.error("【Meta】自定义替换词 %s 格式有误：%s" % (replaced_word, str(err)))
    # 集数偏移
    offset_words = config.get_config('laboratory').get("offset_words")
    if offset_words:
        offset_words = offset_words.split("||")
        for offset_word in offset_words:
            if not offset_word:
                continue
            offset_word_info = offset_word.split("@")
            try:
                front_word = offset_word_info[0]
                back_word = offset_word_info[1]
                offset_num = int(offset_word_info[2])
                if back_word and not re.findall(r'%s' % back_word, title):
                    continue
                if front_word and not re.findall(r'%s' % front_word, title):
                    continue
                offset_word_info_re = re.compile(r'(?<=%s[\W\w]*)[0-9]+(?=[\W\w]*%s)' % (front_word, back_word))
                episode_nums_str = re.findall(offset_word_info_re, title)
                if not episode_nums_str:
                    continue
                episode_nums_int = [int(x) for x in episode_nums_str]
                episode_nums_dict = dict(zip(episode_nums_str, episode_nums_int))
                used_offset_words.append(offset_word)
                # 集数向前偏移，集数按升序处理
                if offset_num < 0:
                    episode_nums_list = sorted(episode_nums_dict.items(), key=lambda x: x[1])
                # 集数向后偏移，集数按降序处理
                else:
                    episode_nums_list = sorted(episode_nums_dict.items(), key=lambda x: x[1], reverse=True)
                for episode_num in episode_nums_list:
                    episode_offset_re = re.compile(
                        r'(?<=%s[\W\w]*)%s(?=[\W\w]*%s)' % (front_word, episode_num[0], back_word))
                    title = re.sub(episode_offset_re, r'%s' % str(episode_num[1] + offset_num).zfill(2), title)
            except Exception as err:
                log.error("【Meta】自定义集数偏移 %s 格式有误：%s" % (offset_word, str(err)))
    # 判断是否处理文件
    if title and os.path.splitext(title)[-1] in RMT_MEDIAEXT:
        fileflag = True
    else:
        fileflag = False
    if mtype == MediaType.ANIME or is_anime(title):
        meta_info = MetaAnime(title, subtitle, fileflag)
        meta_info.ignored_words = used_ignored_words
        meta_info.replaced_words = used_replaced_words
        meta_info.offset_words = used_offset_words
        return meta_info
    else:
        meta_info = MetaVideo(title, subtitle, fileflag)
        meta_info.ignored_words = used_ignored_words
        meta_info.replaced_words = used_replaced_words
        meta_info.offset_words = used_offset_words
        return meta_info


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
