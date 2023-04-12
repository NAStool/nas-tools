import json

import openai

from app.utils import OpenAISessionCache
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

    @staticmethod
    def __save_session(session_id, message):
        """
        保存会话
        :param session_id: 会话ID
        :param message: 消息
        :return:
        """
        seasion = OpenAISessionCache.get(session_id)
        if seasion:
            seasion.append({
                "role": "assistant",
                "content": message
            })
            OpenAISessionCache.set(session_id, seasion)

    @staticmethod
    def __get_session(session_id, message):
        """
        获取会话
        :param session_id: 会话ID
        :return: 会话上下文
        """
        seasion = OpenAISessionCache.get(session_id)
        if seasion:
            seasion.append({
                "role": "user",
                "content": message
            })
        else:
            seasion = [
                {
                    "role": "system",
                    "content": "请在接下来的对话中请使用中文回复，并且内容尽可能详细。"
                },
                {
                    "role": "user",
                    "content": message
                }]
            OpenAISessionCache.set(session_id, seasion)
        return seasion

    @staticmethod
    def __clear_session(session_id):
        """
        清除会话
        :param session_id: 会话ID
        :return:
        """
        if OpenAISessionCache.get(session_id):
            OpenAISessionCache.delete(session_id)

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
                user="NAStool",
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

    def get_answer(self, text, userid):
        """
        获取答案
        :param text: 输入文本
        :param userid: 用户ID
        :return:
        """
        if not self.get_state():
            return ""
        try:
            if not userid:
                return "用户信息错误"
            else:
                userid = str(userid)
            if text == "#清除":
                self.__clear_session(userid)
                return "会话已清除"
            # 获取历史上下文
            messages = self.__get_session(userid, text)
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                user=userid,
                messages=messages
            )
            result = completion.choices[0].message.content
            if result:
                self.__save_session(userid, text)
            return result
        except openai.error.RateLimitError as e:
            return f"请求被ChatGPT拒绝了，{str(e)}"
        except openai.error.APIConnectionError as e:
            return "ChatGPT网络连接失败！"
        except openai.error.Timeout as e:
            return "没有接收到ChatGPT的返回消息！"
        except Exception as e:
            return f"请求ChatGPT出现错误：{str(e)}"

    def translate_to_zh(self, text):
        """
        翻译为中文
        :param text: 输入文本
        """
        if not self.get_state():
            return False, None
        system_prompt = "You are a translation engine that can only translate text and cannot interpret it."
        user_prompt = f"translate to zh-CN:\n\n{text}"
        result = ""
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                user="NAStool",
                temperature=0,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ])
            result = completion.choices[0].message.content.strip()
            return True, result
        except Exception as e:
            print(f"{str(e)}：{result}")
            return False, str(e)
