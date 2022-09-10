# -*- coding: utf-8 -*-
from cacheout import CacheManager, LRUCache

CACHES = {
    "tmdb_supply": {'maxsize': 200}
}

cacheman = CacheManager(CACHES, cache_class=LRUCache)
