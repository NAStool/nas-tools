from rmt.metainfo import MetaInfo

if __name__ == "__main__":
    with open('torrents.txt', 'r', encoding='utf-8') as f:
        names = f.readlines()
        for name in names:
            meta_info = MetaInfo(name)
            print(meta_info.get_name())
