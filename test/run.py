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
    print(MetaInfo('The.303.2018.1080p.BluRay.x264 - UNVEiL[EtHD].mkv').__dict__)
    print(MetaInfo('[1985].1985.2018.1080p.BluRay.x265.AC3-QaFoNE.mp4').__dict__)
