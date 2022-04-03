import anitopy

from rmt.metainfo import MetaInfo

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
    '''
    print(anitopy.parse('[SweetSub&VCB-Studio] Chikyuugai Shounen Shoujo [Movie 02][Ma10p_1080p][x265_flac]'))
    print(MetaInfo('[SweetSub&VCB-Studio] Chikyuugai Shounen Shoujo [Movie 02][Ma10p_1080p][x265_flac]', None, True).__dict__)
