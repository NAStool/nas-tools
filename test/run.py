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
    name = '[OurBits] [112189] Bu Liang Ren 2018 S03 Complete 1080p WEB-DL AAC H.264-OurTV'
    media = MetaInfo(name, None, True)
    print(media.__dict__)
