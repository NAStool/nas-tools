from app.media.tmdbv3api.as_obj import AsObj
from app.media.tmdbv3api.tmdb import TMDb

try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote


class TV(TMDb):
    _urls = {
        "details": "/tv/%s",
        "latest": "/tv/latest",
        "search_tv": "/search/tv",
        "popular": "/tv/popular",
        "top_rated": "/tv/top_rated",
        "similar": "/tv/%s/similar",
        "recommendations": "/tv/%s/recommendations",
        "videos": "/tv/%s/videos",
        "airing_today": "/tv/airing_today",
        "on_the_air": "/tv/on_the_air",
        "screened_theatrically": "/tv/%s/screened_theatrically",
        "external_ids": "/tv/%s/external_ids",
        "reviews": "/tv/%s/reviews",
        "keywords": "/tv/%s/keywords",
        "watch_providers": "/tv/%s/watch/providers",
        "translations": "/tv/%s/translations",
        "season_details": "/tv/%s/season/%s",
        "alternative_titles": "/tv/%s/alternative_titles",
        "credits": "/tv/%s/credits",
        "discover": "/discover/tv",
        "images": "/tv/%s/images",
    }

    def details(
            self, show_id, append_to_response=""
    ):
        """
        Get the primary TV show details by id.
        :param show_id:
        :param append_to_response:
        :return:
        """
        if append_to_response == "all":
            append_to_response = "images,credits,alternative_titles,translations,external_ids"
        elif append_to_response is None:
            append_to_response = "alternative_titles,translations,external_ids"
        return AsObj(
            **self._call(
                self._urls["details"] % str(show_id),
                "append_to_response=" + append_to_response,
            )
        )

    def latest(self):
        """
        Get the most newly created TV show. This is a live response and will continuously change.
        :return:
        """
        return AsObj(**self._call(self._urls["latest"], ""))

    def search(self, term, page=1):
        """
        Search for a TV show.
        :param term:
        :param page:
        :return:
        """
        return self._get_obj(
            self._call(
                self._urls["search_tv"], "query=" + quote(term) + "&page=" + str(page)
            )
        )

    def similar(self, tv_id, page=1):
        """
        Get the primary TV show details by id.
        :param tv_id:
        :param page:
        :return:
        """
        return self._get_obj(
            self._call(self._urls["similar"] % str(tv_id), "page=" + str(page))
        )

    def popular(self, page=1):
        """
        Get a list of the current popular TV shows on TMDb. This list updates daily.
        :param page:
        :return:
        """
        return self._get_obj(self._call(self._urls["popular"], "page=" + str(page)))

    def top_rated(self, page=1):
        """
        Get a list of the top rated TV shows on TMDb.
        :param page:
        :return:
        """
        return self._get_obj(self._call(self._urls["top_rated"], "page=" + str(page)))

    def recommendations(self, tv_id, page=1):
        """
        Get the list of TV show recommendations for this item.
        :param tv_id:
        :param page:
        :return:
        """
        return self._get_obj(
            self._call(self._urls["recommendations"] % tv_id, "page=" + str(page))
        )

    def videos(self, tv_id, page=1):
        """
        Get the videos that have been added to a TV show.
        :param tv_id:
        :param page:
        :return:
        """
        return self._get_obj(
            self._call(self._urls["videos"] % tv_id, "page=" + str(page))
        )

    def airing_today(self, page=1):
        """
        Get a list of TV shows that are airing today.
        This query is purely day based as we do not currently support airing times.
        :param page:
        :return:
        """
        return self._get_obj(
            self._call(self._urls["airing_today"], "page=" + str(page))
        )

    def on_the_air(self, page=1):
        """
        Get a list of shows that are currently on the air.
        :param page:
        :return:
        """
        return self._get_obj(self._call(self._urls["on_the_air"], "page=" + str(page)))

    def screened_theatrically(self, tv_id):
        """
        Get a list of seasons or episodes that have been screened in a film festival or theatre.
        :param tv_id:
        :return:
        """
        return self._get_obj(
            self._call(self._urls["screened_theatrically"] % tv_id, "")
        )

    def external_ids(self, vid):
        """
        Get the external ids for a TV show.
        :param vid:
        :return:
        """
        return self._get_obj(
            self._call(self._urls["external_ids"] % (str(vid)), ""), None
        )

    def keywords(self, tv_id):
        """
        Get the keywords that have been added to a TV show.
        :param tv_id: int
        :return:
        """
        return self._get_obj(self._call(self._urls["keywords"] % tv_id, ""))

    def reviews(self, tv_id, page=1):
        """
        Get the reviews for a TV show.
        :param page: int
        :param tv_id: int
        :return:
        """
        return self._get_obj(
            self._call(self._urls["reviews"] % tv_id, "page=" + str(page))
        )

    def watch_providers(self, tv_id):
        """
        Get the Watch Providers for a TV show.
        :param tv_id:
        :return:
        """
        return AsObj(**self._call(self._urls["watch_providers"] % tv_id, ""))

    def translations(self, tv_id):
        """
        Get the translations for a TV show.
        :param tv_id: tvid
        :return:
        """
        return AsObj(**self._call(self._urls["translations"] % tv_id, ""))

    def season_details(self, tv_id, season_number):
        """
        Get the Season Detail for a TV show.
        :param tv_id: tmdbid
        :param season_number: season number
        :return:
        """
        return AsObj(**self._call(self._urls["season_details"] % (tv_id, season_number), ""))

    def alternative_titles(self, tv_id):
        """
        Get all of the alternative titles for a TV show.
        :param tv_id:
        :return:
        """
        return AsObj(**self._call(self._urls["alternative_titles"] % tv_id, ""))

    def credits(self, tv_id):
        """
        Get the cast and crew for a TV show.
        :param tv_id:
        :return:
        """
        return AsObj(**self._call(self._urls["credits"] % tv_id, ""))

    def discover(self, page):
        """
        Tv discover.
        :param page:
        :return:
        """
        return AsObj(**self._call(self._urls["discover"], "page=" + str(page)))

    def images(self, tv_id, include_image_language=""):
        """
        Get the images that belong to a movie.
        Querying images with a language parameter will filter the results.
        If you want to include a fallback language (especially useful for backdrops) you can use the include_image_language parameter.
        This should be a comma seperated value like so: include_image_language=en,null.
        :param tv_id:
        :param include_image_language:
        :return:
        """
        return AsObj(**self._call(self._urls['images'] % tv_id, "include_image_language=" + include_image_language))
