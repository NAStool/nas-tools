class IndexerConf(object):

    def __init__(self, datas=None, cookie=None, name=None):
        if not datas:
            return
        self.datas = datas
        self.id = self.datas.get('id')
        self.name = self.datas.get('name') if not name else name
        self.domain = self.datas.get('domain')
        self.userinfo = self.datas.get('userinfo')
        self.search = self.datas.get('search')
        self.torrents = self.datas.get('torrents')
        self.category_mappings = self.datas.get('category_mappings')
        self.cookie = cookie

    def get_userinfo(self):
        return self.userinfo

    def get_search(self):
        return self.search

    def get_torrents(self):
        return self.torrents

    def get_category_mapping(self):
        return self.category_mappings
