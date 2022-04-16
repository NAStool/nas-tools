from tmdbv3api.tmdb import TMDb
from tmdbv3api.as_obj import AsObj

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


class Search(TMDb):
    _urls = {
        "companies": "/search/company",
        "collections": "/search/collection",
        "keywords": "/search/keyword",
        "movies": "/search/movie",
        "multi": "/search/multi",
        "people": "/search/person",
        "tv_shows": "/search/tv",
    }

    def companies(self, params):
        """
        Search for movies.
        :param params:
        :return:
        """
        return self._get_obj(self._call(self._urls["companies"], urlencode(params)))

    def collections(self, params):
        """
        Search for movies.
        :param params:
        :return:
        """
        return self._get_obj(self._call(self._urls["collections"], urlencode(params)))

    def keywords(self, params):
        """
        Search for movies.
        :param params:
        :return:
        """
        return self._get_obj(self._call(self._urls["keywords"], urlencode(params)))
    
    def movies(self, params):
        """
        Search for movies.
        :param params:
        :return:
        """
        return self._get_obj(self._call(self._urls["movies"], urlencode(params)))

    def multi(self, params):
        """
        Search for movies.
        :param params:
        :return:
        """
        return self._get_obj(self._call(self._urls["multi"], urlencode(params)))

    def people(self, params):
        """
        Search for movies.
        :param params:
        :return:
        """
        return self._get_obj(self._call(self._urls["people"], urlencode(params)))

    def tv_shows(self, params):
        """
        Search for movies.
        :param params:
        :return:
        """
        return self._get_obj(self._call(self._urls["tv_shows"], urlencode(params)))
