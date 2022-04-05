import anitopy

from rmt.metainfo import MetaInfo
from utils.functions import is_anime

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
    '''
    print(MetaInfo('Kenja no Deshi o Nanoru Kenja[12][1080p][CHS&CHT].mkv', anime=True).__dict__)
    print(MetaInfo('[Sono Bisque Doll wa Koi wo Suru][01-12][BIG5][1080P][MP4]', anime=True).__dict__)
    print(MetaInfo('[Nekomoe kissaten][Paripi Koumei][01][1080p][CHS].mp4', anime=True).__dict__)
    print(MetaInfo('[NC-Raws] 東方少年 - 06 (Baha 1920x1080 AVC AAC MP4).mp4', anime=True).__dict__)

