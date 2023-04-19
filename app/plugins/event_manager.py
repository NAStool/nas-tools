from queue import Queue, Empty

import log
from app.utils.commons import singleton
from app.utils.types import EventType


@singleton
class EventManager:
    """
    事件管理器
    """

    # 事件队列
    _eventQueue = None
    # 事件响应函数字典
    _handlers = {}

    def __init__(self):
        self.init_config()

    def init_config(self):
        # 事件队列
        self._eventQueue = Queue()
        # 事件响应函数字典
        self._handlers = {}

    def get_event(self):
        """
        获取事件
        """
        try:
            event = self._eventQueue.get(block=True, timeout=7)
            handlerList = self._handlers.get(event.event_type)
            return event, handlerList or []
        except Empty:
            return None, []

    def add_event_listener(self, etype: EventType, handler):
        """
        注册事件处理
        """
        try:
            handlerList = self._handlers[etype.value]
        except KeyError:
            handlerList = []
            self._handlers[etype.value] = handlerList
        if handler not in handlerList:
            handlerList.append(handler)
            log.debug(f"已注册事件：{etype.value}{handler}")

    def remove_event_listener(self, etype: EventType, handler):
        """
        移除监听器的处理函数
        """
        try:
            handlerList = self._handlers[etype.value]
            if handler in handlerList[:]:
                handlerList.remove(handler)
            if not handlerList:
                del self._handlers[etype.value]
        except KeyError:
            pass

    def send_event(self, etype: EventType, data: dict = None):
        """
        发送事件
        """
        if etype not in EventType:
            return
        event = Event(etype.value)
        event.event_data = data or {}
        log.debug(f"发送事件：{etype.value} - {event.event_data}")
        self._eventQueue.put(event)

    def register(self, etype: [EventType, list]):
        """
        事件注册
        :param etype: 事件类型
        """

        def decorator(f):
            if isinstance(etype, list):
                for et in etype:
                    self.add_event_listener(et, f)
            elif type(etype) == type(EventType):
                for et in etype.__members__.values():
                    self.add_event_listener(et, f)
            else:
                self.add_event_listener(etype, f)
            return f

        return decorator


class Event(object):
    """
    事件对象
    """

    def __init__(self, event_type=None):
        # 事件类型
        self.event_type = event_type
        # 字典用于保存具体的事件数据
        self.event_data = {}


# 实例引用，用于注册事件
EventHandler = EventManager()
