import json

import openai

from app.utils.commons import singleton
from config import Config


@singleton
class OpenAiHelper:
    _api_key = None
    _api_url = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        self._api_key = Config().get_config("openai").get("api_key")
        if self._api_key:
            openai.api_key = self._api_key
        self._api_url = Config().get_config("openai").get("api_url")
        if self._api_url:
            openai.api_base = self._api_url + "/v1"
        else:
            proxy_conf = Config().get_proxies()
            if proxy_conf and proxy_conf.get("https"):
                openai.proxy = proxy_conf.get("https")

    def get_state(self):
        return True if self._api_key else False

    def get_media_name(self, filename):
        """
        从文件名中提取媒体名称等要素
        :param filename: 文件名
        :return: Json
        """
        if not self.get_state():
            return None
        result = ""
        try:
            _filename_prompt = "I will give you a movie/tvshow file name.You need to return a Json." \
                               "\nPay attention to the correct identification of the film name." \
                               "\n{\"title\":string,\"version\":string,\"part\":string,\"year\":string,\"resolution\":string,\"season\":number|null,\"episode\":number|null}"
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": _filename_prompt
                    },
                    {
                        "role": "user",
                        "content": filename
                    }
                ])
            result = completion.choices[0].message.content
            return json.loads(result)
        except Exception as e:
            print(f"{str(e)}：{result}")
            return {}

    def get_answer(self, text):
        """
        获取答案
        :param text: 输入文本
        :return:
        """
        if not self.get_state():
            return ""
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "请使用中文，并尽可能详尽地回答我。"
                    },
                    {
                        "role": "user",
                        "content": text
                    }])
            return completion.choices[0].message.content
        except Exception as e:
            print(e)
            return ""
