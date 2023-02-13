from app.media.tmdbv3api.tmdb import TMDb

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


class Discover(TMDb):
    _urls = {
        "movies": "/discover/movie",
        "tvs": "/discover/tv"
    }

    def discover_movies(self, params, page=1):
        """
        Discover movies by different types of data like average rating, number of votes, genres and certifications.
        :param params: dict
        :param page: int
        :return:
        """
        if not params:
            params = {}
        if page:
            params.update({"page": page})
        return self._get_obj(
            self._call(
                self._urls["movies"],
                urlencode(params)
            ),
            "results"
        )

    def discover_tv_shows(self, params, page=1):
        """
        Discover TV shows by different types of data like average rating, number of votes, genres,
        the network they aired on and air dates.
        :param params: dict
        :param page: int
        :return:
        """
        if not params:
            params = {}
        if page:
            params.update({"page": page})
        return self._get_obj(
            self._call(
                self._urls["tvs"],
                urlencode(params)
            ),
            "results"
        )
