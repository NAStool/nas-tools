from config import Config
from rmt.server.emby import Emby
from rmt.server.jellyfin import Jellyfin


class MediaServer:
    server = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        media = config.get_config('media')
        if media:
            if media.get('media_server') == "jellyfin":
                self.server = Jellyfin()
            else:
                self.server = Emby()

    def get_activity_log(self, limit):
        if not self.server:
            return []
        return self.server.get_activity_log(limit)

    def get_user_count(self):
        if not self.server:
            return 0
        return self.server.get_user_count()

    def get_medias_count(self):
        if not self.server:
            return None
        return self.server.get_medias_count()

    def refresh_root_library(self):
        if not self.server:
            return
        return self.server.refresh_root_library()

    def get_image_by_id(self, item_id, image_type):
        if not self.server:
            return None
        return self.server.get_image_by_id(item_id, image_type)

    def get_no_exists_episodes(self, meta_info,
                               season_number,
                               episode_count):
        if not self.server:
            return None
        return self.server.get_no_exists_episodes(meta_info,
                                                  season_number,
                                                  episode_count)

    def get_movies(self, title, year=None):
        if not self.server:
            return None
        return self.server.get_movies(title, year)

    def refresh_library_by_items(self, items):
        if not self.server:
            return
        return self.server.refresh_library_by_items(items)
