from app.media.tmdbv3api.tmdb import TMDb


class Trending(TMDb):
    _urls = {"trending": "/trending/%s/%s"}

    def _trending(self, media_type="all", time_window="day", page=1):
        return self._get_obj(
            self._call(
                self._urls["trending"] % (media_type, time_window),
                "page=%s" % page
            )
        )

    def all_day(self, page=1):
        """
        Get all daily trending
        :param page: int
        :return:
        """
        return self._trending(media_type="all", time_window="day", page=page)

    def all_week(self, page=1):
        """
        Get all weekly trending
        :param page: int
        :return:
        """
        return self._trending(media_type="all", time_window="week", page=page)

    def movie_day(self, page=1):
        """
        Get movie daily trending
        :param page: int
        :return:
        """
        return self._trending(media_type="movie", time_window="day", page=page)

    def movie_week(self, page=1):
        """
        Get movie weekly trending
        :param page: int
        :return:
        """
        return self._trending(media_type="movie", time_window="week", page=page)

    def tv_day(self, page=1):
        """
        Get tv daily trending
        :param page: int
        :return:
        """
        return self._trending(media_type="tv", time_window="day", page=page)

    def tv_week(self, page=1):
        """
        Get tv weekly trending
        :param page: int
        :return:
        """
        return self._trending(media_type="tv", time_window="week", page=page)

    def person_day(self, page=1):
        """
        Get person daily trending
        :param page: int
        :return:
        """
        return self._trending(media_type="person", time_window="day", page=page)

    def person_week(self, page=1):
        """
        Get person weekly trending
        :param page: int
        :return:
        """
        return self._trending(media_type="person", time_window="week", page=page)
