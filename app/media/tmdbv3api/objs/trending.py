from app.media.tmdbv3api.tmdb import TMDb


class Trending(TMDb):
    _urls = {
        "trending": "/trending/%s/%s"
    }

    def trending(self, media_type="all", trending="week", page=1):
        return self._get_obj(
            self._call(
                self._urls["trending"] % (media_type, trending),
                "page=" + str(page)
            )
        )
