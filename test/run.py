import os
import re

import anitopy
from pt.downloader import Downloader
from pt.jackett import Jackett
from pt.rss import Rss
from rmt.media import Media
from rmt.metainfo import MetaInfo
from utils.db_helper import select_by_sql
from utils.functions import is_anime
from utils.sqls import get_tv_keys
from web.backend.search_torrents import search_medias_for_web

if __name__ == "__main__":
    '''
    with open('torrentnames.txt', 'r', encoding='utf-8') as f:
        names = f.readlines()
        for name in names:
            meta_info = MetaInfo(name)
            print(meta_info.get_name())
    with open('filenames.txt', 'r', encoding='utf-8') as f:
        names = f.readlines()
        for name in names:
            meta_info = MetaInfo(name)
            print(meta_info.get_name())
    print(MetaInfo('归来.4k修复版.2004.CC.1080p').__dict__)
    print(MetaInfo('2046.4k修复版.2004.CC.1080p').__dict__)
    print(MetaInfo('[秘密访客].Home.Sweet.Home.2021.BlueRay.1080p').__dict__)
    print(MetaInfo('The.355.2021.BluRay.1080p').__dict__)
    print(MetaInfo('[神奇女侠.1984].Wonder.Woman.1984.2020.3D.BluRay.1080p').__dict__)
    print(MetaInfo('亲爱的.2014.TW.1080p.国语.简繁中字').__dict__)
    print(MetaInfo('医是医，二是二 - S01E02 - 第 10 集.mp4').__dict__)
    print(MetaInfo('Interstellar.IMAX.1080p.HDR.10bit.BT2020.DTS.HD').__dict__)
    print(MetaInfo('玻璃樽(未删减版).Gorgeous.UNCUT.1999.BluRay.1080p.x265.10bit').__dict__)
    print(MetaInfo('Kingmaker.2022.KOREAN.1080p.WEBRip.AAC2.0.x264-Imagine').__dict__)
    print(MetaInfo('[第 1 季 Ep6]Sweet Home - 第 6 集.mkv').__dict__)
    print(MetaInfo('[LPSub]Paripi Koumei[01][HEVC AAC][1080p][CH].mkv').__dict__)
    print(MetaInfo('[LPSub]Paripi Koumei[01][HEVC AAC][1080p][CH].mkv', anime=True).__dict__)
    print(MetaInfo('S01E01.mkv').__dict__)
    print(MetaInfo('[Nekomoe kissaten][Paripi Koumei][01][1080p][CHS].mp4', anime=True).__dict__)
    print(MetaInfo('[Sakurato] Kenja no Deshi o Nanoru Kenja [12][HEVC-10bit 1080p AAC][CHS&CHT].mkv', anime=True).__dict__)
    print(MetaInfo('[NC-Raws] 東方少年 - 06 (Baha 1920x1080 AVC AAC MP4).mp4', anime=True).__dict__)
    print(MetaInfo('[Nekomoe kissaten&LoliHouse] Paripi Koumei - 01 [WebRip 1080p HEVC-10bit AAC ASSx2].mkv', anime=True).__dict__)    
    print(MetaInfo('[Sono Bisque Doll wa Koi wo Suru][12][BIG5][1080P][MP4]', anime=True).__dict__)
    print(MetaInfo('[云光字幕组]恐怖神棍节 S3 Karakai Jouzu no S3[02][简体中文]', anime=True).__dict__)
    print(is_anime('[Nekomoe kissaten&LoliHouse] Paripi Koumei - 01 [WebRip 1080p HEVC-10bit AAC ASSx2].mkv'))
    print(is_anime('[NC-Raws] 東方少年 - 06 (Baha 1920x1080 AVC AAC MP4).mp4'))
    print(is_anime('[Sakurato] Kenja no Deshi o Nanoru Kenja [12][HEVC-10bit 1080p AAC][CHS&CHT].mkv'))
    print(is_anime('[LPSub]Paripi Koumei[01][HEVC AAC][1080p][CH].mkv'))
    print(is_anime('医是医，二是二 - S01E02 - 第 10 集.mp4'))
    print(is_anime('[LPSub]Paripi Koumei[HEVC AAC][2160x1080][CH].mkv'))
    print(is_anime('[Sono Bisque Doll wa Koi wo Suru][01-12][BIG5][1080P][MP4]'))
    print(MetaInfo('[Sono Bisque Doll wa Koi Wo Suru][06][BIG5][1080p].mp4', anime=True).__dict__)
    print(MetaInfo('Kenja no Deshi o Nanoru Kenja[12][1080p][CHS&CHT].mkv', anime=True).__dict__)
    print(MetaInfo('[Sono Bisque Doll wa Koi wo Suru][01-12][BIG5][1080P][MP4]', anime=True).__dict__)
    print(MetaInfo('[Nekomoe kissaten][Paripi Koumei][01][1080p][CHS].mp4', anime=True).__dict__)
    print(MetaInfo('[NC-Raws] 東方少年 - 06 (Baha 1920x1080 AVC AAC MP4).mp4', anime=True).__dict__)
    print(MetaInfo('[LPSub][Paripi Koumei][01][1080p][CHS].mp4', anime=True).__dict__)
    print(MetaInfo('[三少爷的剑]CHC.Kingmaker.2022.KOREAN.1080p.WEBRip.AAC2.0.x264-Imagine').__dict__)
    print(MetaInfo('[orion origin]Sono Bisque Doll wa Koi wo Suru [12] [END] [x265] [1440p] [DB].mkv', anime=True).__dict__)
    print(is_anime('[U2-Rip] SLAM DUNK 第005話「根性なしの午後」(BDrip 1440x1080 H264 FLAC).mkv'))
    print(MetaInfo('[U2-Rip] SLAM DUNK 第005話「根性なしの午後」(BDrip 1440x1080 H264 FLAC).mkv').__dict__)
    print(MetaInfo('进击的巨人.第4季.Attack.on.Titan.S04E28.1080p.WEB-DL.H264.ACC-OurTV.mkv').__dict__)
    print(MetaInfo('The Knick 2014-2015 Complete 1080p Blu-ray x265 AC3￡cXcY@FRDS').__dict__)
    print(select_by_sql('SELECT * FROM RSS_TVKEYS'))
    media_info = Media().get_media_info('Paripi Koumei S01E01 1080p B-Global WEB-DL H264 AAC-CHDWEB')
    print(Rss().is_torrent_match(media_info, [], get_tv_keys()))
    print(MetaInfo('西部世界 第2集.mkv').__dict__)
    print(MetaInfo('刺客伍六七.第03季.Scissor.Seven.Ⅲ.2021.第01话.WEB-DL.1080P.AVC.DD+2.0＆AAC.GB-XHGM.mkv').__dict__)
    print(MetaInfo('Percent.World.3D.2022.2160p.WEB-DL.H265.DDP5.1-LeagueWEB.mkv').__dict__)
    print(MetaInfo('刺客伍六七.第03季.Scissor.Seven.Ⅲ.2021.第06话.WEB-DL.1080P.AVC.DD+2.0＆AAC.GB-XHGM.mkv').__dict__)
    '''
    # Jackett().search_one_media('电视剧 行尸走肉')
    # search_medias_for_web('Walking Dead')
    print(MetaInfo('神奇女侠.1984.Wonder.Woman.1984.2020.3D.BluRay.1080p').__dict__)
    print(MetaInfo('神奇女侠.Wonder.Woman.1984.2020.3D.BluRay.1080p').__dict__)
    print(MetaInfo('Wonder.Woman.1984.2020.3D.BluRay.1080p').__dict__)
    print(MetaInfo('神奇女侠.1984.2020.3D.BluRay.1080p').__dict__)
    print(MetaInfo('1984.2020.3D.BluRay.1080p').__dict__)
