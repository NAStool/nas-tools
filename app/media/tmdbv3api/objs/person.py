from app.media.tmdbv3api.as_obj import AsObj
from app.media.tmdbv3api.tmdb import TMDb

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


class Person(TMDb):
    _urls = {
        "details": "/person/%s",
        "changes": "/person/%s/changes",
        "movie_credits": "/person/%s/movie_credits",
        "tv_credits": "/person/%s/tv_credits",
        "combined_credits": "/person/%s/combined_credits",
        "external_ids": "/person/%s/external_ids",
        "images": "/person/%s/images",
        "tagged_images": "/person/%s/tagged_images",
        "translations": "/person/%s/translations",
        "latest": "/person/latest",
        "popular": "/person/popular",
    }

    def details(
            self,
            person_id,
            append_to_response="combined_credits,translations,external_ids",
    ):
        """
        Get the primary person details by id.
        :param person_id:
        :param append_to_response:
        :return:
        """
        return AsObj(
            **self._call(
                self._urls["details"] % person_id,
                "append_to_response=" + append_to_response,
            )
        )

    def changes(self, person_id, start_date="", end_date="", page=1):
        """
        Get the changes for a person. By default only the last 24 hours are returned.
        You can query up to 14 days in a single query by using the start_date and end_date query parameters.
        :param person_id:
        :param start_date:
        :param end_date:
        :param page:
        :return:
        """
        return self._get_obj(
            self._call(
                self._urls["changes"] % person_id,
                urlencode({
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "page": str(page)
                })
            ),
            "changes"
        )

    def movie_credits(self, person_id):
        """
        Get the movie credits for a person.
        :param person_id:
        :return:
        """
        return self._get_obj(
            self._call(
                self._urls["movie_credits"] % person_id,
                ""
            ),
            "cast"
        )

    def tv_credits(self, person_id):
        """
        Get the TV show credits for a person.
        :param person_id:
        :return:
        """
        return self._get_obj(
            self._call(
                self._urls["tv_credits"] % person_id,
                ""
            ),
            "cast"
        )

    def combined_credits(self, person_id):
        """
        Get the movie and TV credits together in a single response.
        :param person_id:
        :return:
        """
        return AsObj(**self._call(self._urls["combined_credits"] % person_id, ""))

    def external_ids(self, person_id):
        """
        Get the external ids for a person.
        :param person_id:
        :return:
        """
        return self._get_obj(
            self._call(self._urls["external_ids"] % (str(person_id)), ""), None
        )

    def images(self, person_id):
        """
        Get the images for a person.
        :param person_id:
        :param include_image_language:
        :return:
        """
        return AsObj(**self._call(self._urls['images'] % person_id, ""))

    def tagged_images(self, person_id):
        """
        Get the images that this person has been tagged in.
        :param person_id:
        :param include_image_language:
        :return:
        """
        return AsObj(**self._call(self._urls['tagged_images'] % person_id, ""))

    def translations(self, person_id):
        """
        Get a list of translations that have been created for a person.
        :param person_id:
        :return:
        """
        return AsObj(**self._call(self._urls["translations"] % person_id, ""))

    def latest(self):
        """
        Get the most newly created person. This is a live response and will continuously change.
        :return:
        """
        return AsObj(**self._call(self._urls["latest"], ""))

    def popular(self, page=1):
        """
        Get the list of popular people on TMDB. This list updates daily.
        :param page:
        :return:
        """
        return self._get_obj(self._call(self._urls["popular"], "page=" + str(page)))
