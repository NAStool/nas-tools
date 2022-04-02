from rmt.media import Media
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
    media = Media().get_media_info("鱿鱼游戏第1季 2021")
    print(media.__dict__)
    '''
    media = MetaInfo("鱿鱼游戏.cd1.2021")
    print(media.__dict__)
