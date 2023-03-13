import json

import openai

from app.utils.commons import singleton
from config import Config


@singleton
class OpenAiHelper:
    _api_key = None
    _prompt = "I will give you a movie/tvshow file name.You need to return a Json." \
              "\nPay attention to the correct identification of the film name." \
              "\n{\"title\":string,\"version\":string,\"part\":string,\"year\":string,\"resolution\":string,\"season\":number|null,\"episode\":number|null}"

    def __init__(self):
        self._api_key = Config().get_config("openai").get("api_key")
        if self._api_key:
            openai.api_key = self._api_key

    def get_media_name(self, filename):
        if not self._api_key:
            return None
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": self._prompt
                    },
                    {
                        "role": "user",
                        "content": filename
                    }
                ])
            result = completion.choices[0].message.content
            return json.loads(result)
        except Exception as e:
            print(e)
            return {}
