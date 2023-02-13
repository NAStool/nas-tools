import datetime
import time
from collections import deque

from app.utils.commons import singleton


@singleton
class MessageCenter:
    _message_queue = deque(maxlen=50)
    _message_index = 0

    def __init__(self):
        pass

    def insert_system_message(self, level, title, content=None):
        """
        新增系统消息
        :param level: 级别
        :param title: 标题
        :param content: 内容
        """
        if not level or not title:
            return
        if not content and title.find("：") != -1:
            strings = title.split("：")
            if strings and len(strings) > 1:
                title = strings[0]
                content = strings[1]
        title = title.replace("\n", "<br>").strip() if title else ""
        content = content.replace("\n", "<br>").strip() if content else ""
        self.__append_message_queue(level, title, content)

    def __append_message_queue(self, level, title, content):
        """
        将消息增加到队列
        """
        self._message_queue.appendleft({"level": level,
                                        "title": title,
                                        "content": content,
                                        "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))})

    def get_system_messages(self, num=20, lst_time=None):
        """
        查询系统消息
        :param num:条数
        :param lst_time: 最后时间
        """
        if not lst_time:
            return list(self._message_queue)[-num:]
        else:
            ret_messages = []
            for message in list(self._message_queue):
                if (datetime.datetime.strptime(message.get("time"), '%Y-%m-%d %H:%M:%S') - datetime.datetime.strptime(
                        lst_time, '%Y-%m-%d %H:%M:%S')).seconds > 0:
                    ret_messages.append(message)
                else:
                    break
            return ret_messages
