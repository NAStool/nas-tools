import warnings

from app.media.tmdbv3api.as_obj import AsObj
from app.media.tmdbv3api.tmdb import TMDb

try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


class Movie(TMDb):
    _urls = {
        "details": "/movie/%s",
        "alternative_titles": "/movie/%s/alternative_titles",
        "changes": "/movie/%s/changes",
        "credits": "/movie/%s/credits",
        "external_ids": "/movie/%s/external_ids",
        "images": "/movie/%s/images",
        "keywords": "/movie/%s/keywords",
        "lists": "/movie/%s/lists",
        "reviews": "/movie/%s/reviews",
        "videos": "/movie/%s/videos",
        "recommendations": "/movie/%s/recommendations",
        "latest": "/movie/latest",
        "now_playing": "/movie/now_playing",
        "top_rated": "/movie/top_rated",
        "upcoming": "/movie/upcoming",
        "popular": "/movie/popular",
        "search_movie": "/search/movie",
        "similar": "/movie/%s/similar",
        "external": "/find/%s",
        "release_dates": "/movie/%s/release_dates",
        "watch_providers": "/movie/%s/watch/providers",
        "translations": "/movie/%s/translations",
        "discover": "/discover/movie"
    }

    def details(
            self,
            movie_id,
            append_to_response="",
    ):
        """
        Get the primary information about a movie.
        :param movie_id:
        :param append_to_response:
        :return:
        """
        if append_to_response == "all":
            append_to_response = "images,credits,alternative_titles,translations,external_ids"
        elif append_to_response is None:
            append_to_response = "alternative_titles,translations,external_ids"
        return AsObj(
            **self._call(
                self._urls["details"] % movie_id,
                "append_to_response=" + append_to_response,
            )
        )

    def alternative_titles(self, movie_id):
        """
        Get all of the alternative titles for a movie.
        :param movie_id:
        :return:
        """
        return AsObj(**self._call(self._urls["alternative_titles"] % movie_id, ""))

    def changes(self, movie_id, start_date="", end_date="", page=1):
        """
        Get all of the alternative titles for a movie.
        You can query up to 14 days in a single query by using the start_date and end_date query parameters.
        :param movie_id:
        :param start_date:
        :param end_date:
        :param page:
        :return:
        """
        return self._get_obj(
            self._call(
                self._urls["changes"] % movie_id,
                urlencode({
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "page": str(page)
                })
            ),
            "changes"
        )

    def credidiscoverts(self, movie_id):
        """
        Get the cast and crew for a movie.
        :param movie_id:
        :return:
        """
        return AsObj(**self._call(self._urls["credits"] % movie_id, ""))

    def external_ids(self, movie_id):
        """
        Get the external ids for a movie.
        :param movie_id:
        :return:
        """
        return self._get_obj(
            self._call(self._urls["external_ids"] % (str(movie_id)), ""), None
        )

    def images(self, movie_id, include_image_language=""):
        """
        Get the images that belong to a movie.
        Querying images with a language parameter will filter the results. 
        If you want to include a fallback language (especially useful for backdrops) you can use the include_image_language parameter. 
        This should be a comma seperated value like so: include_image_language=en,null.
        :param movie_id:
        :param include_image_language:
        :return:
        """
        return AsObj(**self._call(self._urls['images'] % movie_id, "include_image_language=" + include_image_language))

    def keywords(self, movie_id):
        """
        Get the keywords associated to a movie.
        :param movie_id:
        :return:
        """
        return AsObj(**self._call(self._urls['keywords'] % movie_id, ''))

    def lists(self, movie_id, page=1):
        """
        Get a list of lists that this movie belongs to.
        :param movie_id:
        :param page:
        :return:
        """
        return self._get_obj(
            self._call(self._urls["lists"] % movie_id, "page=" + str(page))
        )

    def recommendations(self, movie_id, page=1):
        """
        Get a list of recommended movies for a movie.
        :param movie_id:
        :param page:
        :return:
        """
        return self._get_obj(
            self._call(self._urls["recommendations"] % movie_id, "page=" + str(page))
        )

    def release_dates(self, movie_id):
        """
        Get the release date along with the certification for a movie.
        :param movie_id:
        :return:
        """
        return AsObj(**self._call(self._urls['release_dates'] % movie_id, ''))

    def reviews(self, movie_id, page=1):
        """
        Get the user reviews for a movie.
        :param movie_id:
        :param page:
        :return:
        """
        return self._get_obj(
            self._call(self._urls["reviews"] % movie_id, "page=" + str(page))
        )

    def videos(self, vid, page=1):
        """
        Get the videos that have been added to a movie.
        :param vid:
        :param page:
        :return:
        """
        return self._get_obj(self._call(self._urls["videos"] % vid, "page=" + str(page)))

    def latest(self):
        """
        Get the most newly created movie. This is a live response and will continuously change.
        :return:
        """
        return AsObj(**self._call(self._urls["latest"], ""))

    def now_playing(self, page=1):
        """
        Get a list of movies in theatres.
        :param page:
        :return:
        """
        return self._get_obj(self._call(self._urls["now_playing"], "page=" + str(page)))

    def top_rated(self, page=1):
        """
        Get the top rated movies on TMDb.
        :param page:
        :return:
        """
        return self._get_obj(self._call(self._urls["top_rated"], "page=" + str(page)))

    def upcoming(self, page=1):
        """
        Get a list of upcoming movies in theatres.
        :param page:
        :return:
        """
        return self._get_obj(self._call(self._urls["upcoming"], "page=" + str(page)))

    def popular(self, page=1):
        """
        Get a list of the current popular movies on TMDb. This list updates daily.
        :param page:
        :return:
        """
        return self._get_obj(self._call(self._urls["popular"], "page=" + str(page)))

    def search(self, term, page=1):
        """
        Search for movies.
        :param term:
        :param page:
        :return:
        """
        return self._get_obj(
            self._call(
                self._urls["search_movie"],
                "query=" + quote(term) + "&page=" + str(page),
            )
        )

    def similar(self, movie_id, page=1):
        """
        Get a list of similar movies.
        :param movie_id:
        :param page:
        :return:
        """
        return self._get_obj(
            self._call(self._urls["similar"] % movie_id, "page=" + str(page))
        )

    def external(self, external_id, external_source):
        """
        The find method makes it easy to search for objects in our database by an external id. For example, an IMDB ID.
        :param external_id: str
        :param external_source str
        :return:
        """
        warnings.warn("external method is deprecated use tmdbv3api.Find().find(external_id, external_source)",
                      DeprecationWarning)
        return self._get_obj(
            self._call(
                self._urls["external"] % external_id,
                "external_source=" + external_source,
            ),
            key=None,
        )

    def watch_providers(self, movie_id):
        """
        Get the Watch Providers for a movie.
        :param movie_id:
        :return:
        """
        return AsObj(**self._call(self._urls["watch_providers"] % movie_id, ""))

    def translations(self, movie_id):
        """
        Get the Watch Providers for a movie.
        :param movie_id:
        :return:
        """
        return AsObj(**self._call(self._urls["translations"] % movie_id, ""))

    def discover(self, page):
        """
        Movie discover.
        :param page:
        :return:
        """
        return AsObj(**self._call(self._urls["discover"], "page=" + str(page)))

    def credits(self, movie_id):
        """
        Get the Credits for a movie.
        :param movie_id:
        :return:
        """
        return AsObj(**self._call(self._urls["credits"] % movie_id, ""))
