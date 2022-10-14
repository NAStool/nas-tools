from app.media.tmdbv3api.as_obj import AsObj
from app.media.tmdbv3api.tmdb import TMDb


class Find(TMDb):
    _urls = {
        "find": "/find/%s"
    }

    def find_by_imdbid(self, imdbid):
        return self._call(
                self._urls["find"] % imdbid,
                "external_source=imdb_id")
