from urllib.parse import urlencode

import log
from config import Config
from app.message.channel.channel import IMessageChannel
from app.utils import RequestUtils


class IyuuMsg(IMessageChannel):
    _token = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        config = Config()
        message = config.get_config('message')
        if message:
            self._token = message.get('iyuu', {}).get('iyuu_token')

    def get_status(self):
        """
        测试连通性
        """
        flag, msg = self.send_msg("测试", "这是一条测试消息")
        if not flag:
            log.error("【MSG】发送消息失败：%s" % msg)
        return flag

    def send_msg(self, title, text="", image="", url="", user_id=""):
        """
        发送爱语飞飞消息
        :param title: 消息标题
        :param text: 消息内容
        :param image: 未使用
        :param url: 未使用
        :param user_id: 未使用
        """
        if not title and not text:
            return False, "标题和内容不能同时为空"
        if not self._token:
            return False, "参数未配置"
        try:
            sc_url = "http://iyuu.cn/%s.send?%s" % (self._token, urlencode({"text": title, "desp": text}))
            res = RequestUtils().get_res(sc_url)
            if res:
                ret_json = res.json()
                errno = ret_json.get('errcode')
                error = ret_json.get('errmsg')
                if errno == 0:
                    return True, error
                else:
                    return False, error
            else:
                return False, "未获取到返回信息"
        except Exception as msg_e:
            return False, str(msg_e)

    def send_list_msg(self, title, medias: list, user_id=""):
        pass
